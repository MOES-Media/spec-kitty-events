"""Per-PR contract check for the shared BDD scenario suite (no JDK, no step execution).

Reads the ``.feature`` files under ``tests/scenarios`` with ``gherkin-official`` (the parser
pytest-bdd itself uses), reads the step definitions of each step source statically, and
refuses a malformed suite with stable problem codes. Nothing is run.

The contract this script implements, with its 22 rules, its CLI and the grammar of the
promise registers and the steps index, is
``kitty-specs/bdd-suite-skeleton-01M6GF8W/contracts/scenario-contract-check.md``. The model
is core's ``scripts/ci/scenario_contract.py`` (spec-kitty/spec-kitty); it is read, never
imported. Deviations from core:

* **D-1.** Step definitions are read from Python (pytest-bdd decorators), not Java. Step
  sources are keyed by binding name (``--steps NAME=DIR``) in a parser registry, so the
  Java source (``jvm``) can be added in D3 without reworking the check. D1 registers
  ``python`` only.
* **D-2.** Rules core does not have: UNREGISTERED_PROMISE, BAD_BINDING_DECLARATION,
  STEPS_TABLE_DRIFT and FORBIDDEN_TEST_IMPORT. BAD_PROMISE_ID is strengthened: every gating
  scenario carries exactly one ``@promise:`` tag. DUPLICATE_PROMISE is checked across the
  whole tree. Not carried from core: UNSUPPORTED_EXPRESSION (an unread step-definition form
  surfaces as UNBOUND_STEP), NO_STEP_DEFINITIONS and STEP_FILE_UNREADABLE (a missing or
  unreadable step source is a usage error, exit 2).

Known limits of the Python step reader and matcher:

* only ``given``/``when``/``then`` imported from ``pytest_bdd`` (``from pytest_bdd import
  given``, with or without ``as``, or ``import pytest_bdd`` without ``as``) are read;
* the step argument (first positional, or ``name=``) must be a string literal or
  ``parsers.parse(<literal>)``. ``parsers.re``, ``parsers.cfparse``, ``@step``, a
  non-literal string or any other form is not read, so the steps it would bind fail loudly
  as UNBOUND_STEP;
* ``parse`` fields ``{name}`` and ``{name:d}`` become ``.+?`` and ``-?\\d+`` groups; any
  other format spec is treated as ``.+?``, which can over-match;
* ``*`` steps take the keyword of the previous step; a leading ``*`` matches any keyword.

Usage::

    uv run python scripts/scenario_contract.py [--features DIR] [--steps NAME=DIR]... [--index FILE]

Exit status: 0 with no error finding, 1 with at least one, 2 on a usage error.
"""

from __future__ import annotations

import argparse
import ast
import datetime
import os
import re
import sys
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import cast

from gherkin.errors import CompositeParserException, ParserError, ParserException
from gherkin.parser import Parser
from gherkin.parser_types import (
    BackgroundEnvelope,
    Envelope,
    Rule,
    RuleEnvelope,
    Scenario,
    ScenarioEnvelope,
    Step,
    Tag,
)
from gherkin.token_scanner import TokenScanner

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FEATURES = "tests/scenarios"
DEFAULT_STEPS = "python=tests/scenarios/steps"
DEFAULT_INDEX = "tests/scenarios/README.md"

ERROR = "error"
INFO = "info"

# Core codes.
PARSE_ERROR = "PARSE_ERROR"
NO_FEATURES = "NO_FEATURES"
NO_SCENARIOS = "NO_SCENARIOS"
NO_STEPS = "NO_STEPS"
NO_EXAMPLES = "NO_EXAMPLES"
NO_GATING_SCENARIOS = "NO_GATING_SCENARIOS"
UNBOUND_STEP = "UNBOUND_STEP"
AMBIGUOUS_STEP = "AMBIGUOUS_STEP"
BAD_PROMISE_ID = "BAD_PROMISE_ID"
DUPLICATE_PROMISE = "DUPLICATE_PROMISE"
WIP_MISSING_OWNER = "WIP_MISSING_OWNER"
WIP_MISSING_SINCE = "WIP_MISSING_SINCE"
BAD_WIP_OWNER = "BAD_WIP_OWNER"
BAD_WIP_SINCE = "BAD_WIP_SINCE"
BAD_DEFECT = "BAD_DEFECT"
BAD_QA_REF = "BAD_QA_REF"
UNKNOWN_PREFIXED_TAG = "UNKNOWN_PREFIXED_TAG"
BAD_BARE_TAG = "BAD_BARE_TAG"
# Events-specific codes (D-2).
UNREGISTERED_PROMISE = "UNREGISTERED_PROMISE"
BAD_BINDING_DECLARATION = "BAD_BINDING_DECLARATION"
STEPS_TABLE_DRIFT = "STEPS_TABLE_DRIFT"
FORBIDDEN_TEST_IMPORT = "FORBIDDEN_TEST_IMPORT"

CODES: frozenset[str] = frozenset(
    {
        PARSE_ERROR,
        NO_FEATURES,
        NO_SCENARIOS,
        NO_STEPS,
        NO_EXAMPLES,
        NO_GATING_SCENARIOS,
        UNBOUND_STEP,
        AMBIGUOUS_STEP,
        BAD_PROMISE_ID,
        DUPLICATE_PROMISE,
        WIP_MISSING_OWNER,
        WIP_MISSING_SINCE,
        BAD_WIP_OWNER,
        BAD_WIP_SINCE,
        BAD_DEFECT,
        BAD_QA_REF,
        UNKNOWN_PREFIXED_TAG,
        BAD_BARE_TAG,
        UNREGISTERED_PROMISE,
        BAD_BINDING_DECLARATION,
        STEPS_TABLE_DRIFT,
        FORBIDDEN_TEST_IMPORT,
    }
)

_ID_PATTERN = r"[A-Za-z0-9][A-Za-z0-9._-]*"
_ID_RE = re.compile(_ID_PATTERN)
_BARE_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")
_ISSUE_RE = re.compile(r"[1-9][0-9]*")
_DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_PLACEHOLDER_RE = re.compile(r"<([^<>]+)>")
_PARSE_FIELD_RE = re.compile(r"\{\{|\}\}|\{([^{}:]*)(?::([^{}]*))?\}")
_SEPARATOR_CELL_RE = re.compile(r":?-+:?")

_GIVEN, _WHEN, _THEN = "given", "when", "then"
_STEP_KEYWORDS = (_GIVEN, _WHEN, _THEN)
_KEYWORD_TYPES = {"Context": _GIVEN, "Action": _WHEN, "Outcome": _THEN}
_INDEX_GROUPS = {"Arrange": _GIVEN, "Assume": _GIVEN, "Act": _WHEN, "Assert": _THEN}
_INDEX_HEADING = "## Available steps"
_INDEX_HEADER = ["Group", "Step"]
_REGISTER_FILE = "PROMISES.md"
_REGISTER_HEADER = ["Promise", "Consumer guarantee", "Authority", "Binding"]
_WIP_BINDING = "@wip"
_BINDINGS: dict[str, tuple[str, ...]] = {
    "python": ("python",),
    "python, jvm": ("python", "jvm"),
    _WIP_BINDING: (),
}
_PLAIN_TAGS = frozenset({"wip", "manual"})


class UsageError(Exception):
    """A usage error: unknown binding name, missing path, unreadable step source (exit 2)."""


@dataclass(frozen=True)
class Problem:
    """One finding. ``code`` is stable; ``severity`` is ``error`` or ``info``."""

    code: str
    severity: str
    file: str
    line: int
    message: str


@dataclass(frozen=True)
class StepDefinition:
    """One step definition read from a step source."""

    keyword: str  # given | when | then
    pattern: str
    regex: re.Pattern[str]
    file: str
    line: int
    is_parse: bool = False


@dataclass(frozen=True)
class Discovery:
    """What the features tree holds: feature files (relative, posix) and promise ids."""

    feature_files: tuple[str, ...]
    promise_ids: tuple[str, ...]


@dataclass(frozen=True)
class _StepText:
    keyword: str | None  # None: a leading ``*`` step, matched against any keyword
    text: str
    line: int


@dataclass(frozen=True)
class _Instance:
    """One runnable scenario: a Scenario, or one Examples row of a Scenario Outline."""

    file: str  # relative to the features root, posix
    area: str
    line: int
    name: str
    tags: tuple[str, ...]  # effective tags, ``@`` stripped
    steps: tuple[_StepText, ...]

    @property
    def gating(self) -> bool:
        return not (_PLAIN_TAGS & set(self.tags))

    @property
    def wip(self) -> bool:
        return "wip" in self.tags

    def promises(self) -> list[str]:
        return _values(self.tags, "promise")


@dataclass(frozen=True)
class _Row:
    promise: str
    binding: str
    line: int


@dataclass(frozen=True)
class _IndexRow:
    keyword: str
    phrase: str
    line: int


def _problem(code: str, file: str | Path, line: int, message: str) -> Problem:
    return Problem(code, ERROR, str(file), line, message)


def _values(tags: Iterable[str], prefix: str) -> list[str]:
    return [t.partition(":")[2] for t in tags if ":" in t and t.partition(":")[0] == prefix]


# ---------------------------------------------------------------------------
# Feature parsing
# ---------------------------------------------------------------------------


def _tag_names(tags: Sequence[Tag]) -> tuple[str, ...]:
    return tuple(t["name"][1:] if t["name"].startswith("@") else t["name"] for t in tags)


def _step_texts(steps: Sequence[Step], previous: str | None = None) -> list[_StepText]:
    """Resolve ``And``/``But``/``*`` to the keyword of the step before them."""
    out: list[_StepText] = []
    keyword = previous
    for step in steps:
        keyword = _KEYWORD_TYPES.get(step["keywordType"], keyword)
        out.append(_StepText(keyword, step["text"], step["location"]["line"]))
    return out


def _substitute(text: str, values: Mapping[str, str]) -> str:
    return _PLACEHOLDER_RE.sub(lambda m: values.get(m.group(1), m.group(0)), text)


class _FeatureWalker:
    """Walks one parsed feature into scenario instances and structural problems."""

    def __init__(self, file: str, area: str) -> None:
        self.file = file
        self.area = area
        self.instances: list[_Instance] = []
        self.problems: list[Problem] = []
        self.scenario_count = 0

    def walk_children(
        self, children: Sequence[Envelope], tags: tuple[str, ...], background: list[Step]
    ) -> None:
        own_background = list(background)
        for child in children:
            if "background" in child:
                own_background += cast(BackgroundEnvelope, child)["background"]["steps"]
            elif "rule" in child:
                rule: Rule = cast(RuleEnvelope, child)["rule"]
                self.walk_children(
                    rule["children"], tags + _tag_names(rule["tags"]), own_background
                )
            elif "scenario" in child:
                scenario = cast(ScenarioEnvelope, child)["scenario"]
                self._scenario(scenario, tags, own_background)

    def _scenario(
        self, scenario: Scenario, inherited: tuple[str, ...], background: list[Step]
    ) -> None:
        self.scenario_count += 1
        line = scenario["location"]["line"]
        name = scenario["name"]
        tags = inherited + _tag_names(scenario["tags"])
        if not scenario["steps"]:
            self.problems.append(
                _problem(NO_STEPS, self.file, line, f"scenario {name!r} has no steps")
            )
        base = _step_texts(background)
        last = base[-1].keyword if base else None
        own = _step_texts(scenario["steps"], last)
        examples = scenario.get("examples", [])
        outline = "Outline" in scenario["keyword"] or "Template" in scenario["keyword"]
        if not (outline or examples):
            self._emit(line, name, tags, base + own)
            return
        rows = 0
        for block in examples:
            header_row = block.get("tableHeader")
            header = [c["value"] for c in header_row["cells"]] if header_row else []
            block_tags = tags + _tag_names(block["tags"])
            for body in block.get("tableBody", []):
                rows += 1
                values = dict(zip(header, (c["value"] for c in body["cells"])))
                expanded = [replace(s, text=_substitute(s.text, values)) for s in own]
                self._emit(line, name, block_tags, base + expanded)
        if rows == 0:
            self.problems.append(
                _problem(
                    NO_EXAMPLES,
                    self.file,
                    line,
                    f"scenario outline {name!r} has no Examples rows",
                )
            )
            self._emit(line, name, tags, base + own)

    def _emit(self, line: int, name: str, tags: tuple[str, ...], steps: list[_StepText]) -> None:
        self.instances.append(_Instance(self.file, self.area, line, name, tags, tuple(steps)))


def _area_of(relative: str) -> str:
    parts = relative.split("/")
    return parts[0] if len(parts) > 1 else ""


def _parse_feature(path: Path, relative: str) -> tuple[list[_Instance], list[Problem]]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [], [_problem(PARSE_ERROR, relative, 1, f"cannot read file: {exc}")]
    try:
        document = Parser().parse(TokenScanner(text))
    except CompositeParserException as exc:
        return [], [_parse_problem(relative, e) for e in exc.errors]
    except ParserException as exc:
        return [], [_parse_problem(relative, exc)]
    except ParserError as exc:  # pragma: no cover - defensive: no location available
        return [], [_problem(PARSE_ERROR, relative, 1, str(exc))]
    feature = document.get("feature")
    if feature is None:
        return [], [_problem(PARSE_ERROR, relative, 1, "no Feature line found")]
    walker = _FeatureWalker(relative, _area_of(relative))
    walker.walk_children(feature["children"], _tag_names(feature["tags"]), [])
    if walker.scenario_count == 0:
        walker.problems.append(
            _problem(
                NO_SCENARIOS,
                relative,
                feature["location"]["line"],
                "the feature has no Scenario, Example or Scenario Outline",
            )
        )
    return walker.instances, walker.problems


def _parse_problem(relative: str, error: ParserException) -> Problem:
    return _problem(PARSE_ERROR, relative, error.location["line"], str(error))


def _feature_files(features: Path) -> list[tuple[Path, str]]:
    files = sorted(features.rglob("*.feature"), key=lambda p: p.relative_to(features).as_posix())
    return [(p, p.relative_to(features).as_posix()) for p in files if p.is_file()]


def _parse_tree(features: Path) -> tuple[list[str], list[_Instance], list[Problem]]:
    relatives: list[str] = []
    instances: list[_Instance] = []
    problems: list[Problem] = []
    for path, relative in _feature_files(features):
        relatives.append(relative)
        found, file_problems = _parse_feature(path, relative)
        instances += found
        problems += file_problems
    return relatives, instances, problems


def discover(features: Path) -> Discovery:
    """List the feature files (relative, posix) and the promise ids the tree carries."""
    relatives, instances, _ = _parse_tree(features)
    promises = {p for i in instances for p in i.promises()}
    return Discovery(tuple(sorted(relatives)), tuple(sorted(promises)))


# ---------------------------------------------------------------------------
# Tag vocabulary
# ---------------------------------------------------------------------------


def _valid_date(value: str) -> bool:
    if not _DATE_RE.fullmatch(value):
        return False
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _matches(pattern: re.Pattern[str]) -> Callable[[str], bool]:
    return lambda value: pattern.fullmatch(value) is not None


# prefix -> (value check, problem code, expectation shown to the author)
_VALUE_RULES: dict[str, tuple[Callable[[str], bool], str, str]] = {
    "promise": (_matches(_ID_RE), BAD_PROMISE_ID, f"an id matching {_ID_PATTERN}"),
    "wip-owner": (_matches(_ID_RE), BAD_WIP_OWNER, f"a handle matching {_ID_PATTERN}"),
    "wip-since": (_valid_date, BAD_WIP_SINCE, "a valid date as YYYY-MM-DD"),
    "defect": (_matches(_ISSUE_RE), BAD_DEFECT, "a positive integer issue number"),
    "qa": (_matches(_ID_RE), BAD_QA_REF, f"a reference matching {_ID_PATTERN}"),
}


def _check_one_tag(instance: _Instance, tag: str) -> Problem | None:
    prefix, colon, value = tag.partition(":")
    where = (instance.file, instance.line)
    if not colon:
        if tag in _PLAIN_TAGS or _BARE_RE.fullmatch(tag):
            return None
        return _problem(BAD_BARE_TAG, *where, f"bare tag @{tag} must match {_BARE_RE.pattern}")
    rule = _VALUE_RULES.get(prefix)
    if rule is None:
        return _problem(UNKNOWN_PREFIXED_TAG, *where, f"unknown prefixed tag @{tag}")
    valid, code, expectation = rule
    return None if valid(value) else _problem(code, *where, f"@{tag}: expected {expectation}")


def _check_tags(instance: _Instance) -> list[Problem]:
    where = (instance.file, instance.line)
    problems = [p for p in (_check_one_tag(instance, t) for t in instance.tags) if p]
    promises = instance.promises()
    distinct = sorted(set(promises))
    if instance.gating and not distinct:
        problems.append(_problem(BAD_PROMISE_ID, *where, "a gating scenario needs @promise:<id>"))
    elif len(distinct) > 1:
        listed = ", ".join(distinct)
        problems.append(_problem(BAD_PROMISE_ID, *where, f"more than one promise: {listed}"))
    for value in distinct:
        if promises.count(value) > 1:
            problems.append(_problem(DUPLICATE_PROMISE, *where, f"@promise:{value} is repeated"))
    if instance.wip:
        if not _values(instance.tags, "wip-owner"):
            problems.append(_problem(WIP_MISSING_OWNER, *where, "@wip needs @wip-owner:<handle>"))
        if not _values(instance.tags, "wip-since"):
            problems.append(
                _problem(WIP_MISSING_SINCE, *where, "@wip needs @wip-since:<YYYY-MM-DD>")
            )
    return problems


def _check_duplicates(instances: Sequence[_Instance]) -> list[Problem]:
    """One promise id on two scenarios anywhere in the tree (outline rows are one scenario)."""
    owners: dict[str, list[tuple[str, int]]] = {}
    for instance in instances:
        for value in set(instance.promises()):
            where = (instance.file, instance.line)
            if where not in owners.setdefault(value, []):
                owners[value].append(where)
    problems: list[Problem] = []
    for value, places in sorted(owners.items()):
        first, *others = sorted(places)
        for file, line in others:
            message = f"@promise:{value} is also on {first[0]}:{first[1]}"
            problems.append(_problem(DUPLICATE_PROMISE, file, line, message))
    return problems


# ---------------------------------------------------------------------------
# Python step source
# ---------------------------------------------------------------------------


def parse_pattern_to_regex(pattern: str) -> re.Pattern[str]:
    """Translate a ``parsers.parse`` format string into an anchored regex."""
    parts: list[str] = []
    seen: set[str] = set()
    index = 0
    for match in _PARSE_FIELD_RE.finditer(pattern):
        parts.append(re.escape(pattern[index : match.start()]))
        index = match.end()
        token = match.group(0)
        if token in ("{{", "}}"):
            parts.append(re.escape(token[0]))
            continue
        name, spec = match.group(1), match.group(2)
        body = r"-?\d+" if spec == "d" else ".+?"
        if name and name.isidentifier() and name not in seen:
            seen.add(name)
            parts.append(f"(?P<{name}>{body})")
        else:
            parts.append(f"({body})")
    parts.append(re.escape(pattern[index:]))
    return re.compile("^" + "".join(parts) + "$")


def _normalise_parse(pattern: str) -> str:
    """``{name}`` and ``{name:fmt}`` become ``<name>``; ``{{``/``}}`` become braces."""

    def repl(match: re.Match[str]) -> str:
        token = match.group(0)
        return token[0] if token in ("{{", "}}") else f"<{match.group(1)}>"

    return _PARSE_FIELD_RE.sub(repl, pattern)


@dataclass
class _Aliases:
    keywords: dict[str, str]  # local name -> given | when | then
    parsers: set[str]
    modules: set[str]  # local names bound to the pytest_bdd module


def _aliases(tree: ast.Module) -> _Aliases:
    aliases = _Aliases({}, set(), set())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "pytest_bdd" and not node.level:
            for alias in node.names:
                local = alias.asname or alias.name
                if alias.name in _STEP_KEYWORDS:
                    aliases.keywords[local] = alias.name
                elif alias.name == "parsers":
                    aliases.parsers.add(local)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "pytest_bdd" and alias.asname is None:
                    aliases.modules.add("pytest_bdd")
    return aliases


def _decorator_keyword(func: ast.expr, aliases: _Aliases) -> str | None:
    if isinstance(func, ast.Name):
        return aliases.keywords.get(func.id)
    if (
        isinstance(func, ast.Attribute)
        and isinstance(func.value, ast.Name)
        and func.value.id in aliases.modules
        and func.attr in _STEP_KEYWORDS
    ):
        return func.attr
    return None


def _is_parsers_parse(func: ast.expr, aliases: _Aliases) -> bool:
    if not (isinstance(func, ast.Attribute) and func.attr == "parse"):
        return False
    owner = func.value
    if isinstance(owner, ast.Name):
        return owner.id in aliases.parsers
    return (
        isinstance(owner, ast.Attribute)
        and owner.attr == "parsers"
        and isinstance(owner.value, ast.Name)
        and owner.value.id in aliases.modules
    )


def _step_argument(call: ast.Call, aliases: _Aliases) -> tuple[str, bool] | None:
    """The step pattern and whether it is a ``parse`` pattern, or None for an unread form."""
    argument: ast.expr | None = call.args[0] if call.args else None
    if argument is None:
        argument = next((k.value for k in call.keywords if k.arg == "name"), None)
    if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
        return argument.value, False
    if (
        isinstance(argument, ast.Call)
        and _is_parsers_parse(argument.func, aliases)
        and len(argument.args) == 1
        and not argument.keywords
        and isinstance(argument.args[0], ast.Constant)
        and isinstance(argument.args[0].value, str)
    ):
        return argument.args[0].value, True
    return None


def _definitions(tree: ast.Module, path: Path) -> list[StepDefinition]:
    aliases = _aliases(tree)
    found: list[StepDefinition] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            keyword = _decorator_keyword(decorator.func, aliases)
            argument = _step_argument(decorator, aliases) if keyword else None
            if keyword is None or argument is None:
                continue
            pattern, is_parse = argument
            regex = parse_pattern_to_regex(pattern) if is_parse else _plain_regex(pattern)
            found.append(
                StepDefinition(keyword, pattern, regex, str(path), decorator.lineno, is_parse)
            )
    return found


def _plain_regex(pattern: str) -> re.Pattern[str]:
    return re.compile("^" + re.escape(pattern) + "$")


def _forbidden_module(dotted: str) -> bool:
    parts = dotted.split(".")
    return parts[0] == "tests" and (len(parts) == 1 or parts[1] != "scenarios")


def _resolve_relative(path: Path, level: int, module: str | None) -> tuple[list[str], bool]:
    """Resolve a relative import against the repo root: (dotted parts, resolvable)."""
    try:
        package = list(path.resolve().parent.relative_to(REPO_ROOT).parts)
    except ValueError:
        return [], False
    if level - 1 > len(package):
        return [], False
    base = package[: len(package) - (level - 1)]
    return base + (module.split(".") if module else []), True


def _import_targets(
    node: ast.Import | ast.ImportFrom, path: Path, root_parts: list[str] | None
) -> list[str]:
    """Dotted modules an import reaches; a relative one only when it leaves the source root."""
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if node.level:
        parts, ok = _resolve_relative(path, node.level, node.module)
        inside = root_parts is not None and parts[: len(root_parts)] == root_parts
        if not ok or inside:
            return []
    else:
        parts = (node.module or "").split(".")
    if parts in ([], ["tests"]):
        # ``from tests import x`` (or ``from ... import tests``) names modules, not attributes.
        return [".".join([*parts, alias.name]) for alias in node.names]
    return [".".join(parts)]


def _import_problems(tree: ast.Module, path: Path, root: Path) -> list[Problem]:
    try:
        root_parts: list[str] | None = list(root.resolve().relative_to(REPO_ROOT).parts)
    except ValueError:
        root_parts = None
    problems: list[Problem] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        for target in _import_targets(node, path, root_parts):
            if _forbidden_module(target):
                message = f"step source imports {target}; only tests.scenarios is allowed"
                problems.append(_problem(FORBIDDEN_TEST_IMPORT, path, node.lineno, message))
    return problems


def read_python_steps(root: Path) -> tuple[list[StepDefinition], list[Problem]]:
    """Statically read pytest-bdd step definitions and forbidden imports under ``root``."""
    definitions: list[StepDefinition] = []
    problems: list[Problem] = []
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, UnicodeDecodeError, SyntaxError) as exc:
            raise UsageError(f"cannot read step source file {path}: {exc}") from exc
        definitions += _definitions(tree, path)
        problems += _import_problems(tree, path, root)
    return definitions, problems


_READERS: dict[str, Callable[[Path], tuple[list[StepDefinition], list[Problem]]]] = {
    "python": read_python_steps,
}


# ---------------------------------------------------------------------------
# Step matching
# ---------------------------------------------------------------------------


def _match_instance(
    instance: _Instance, sources: Mapping[str, Sequence[StepDefinition]]
) -> list[Problem]:
    severity = ERROR if instance.gating else INFO
    problems: list[Problem] = []
    for step in instance.steps:
        for name, definitions in sources.items():
            hits = [
                d
                for d in definitions
                if (step.keyword is None or d.keyword == step.keyword)
                and d.regex.fullmatch(step.text)
            ]
            label = step.keyword or "any keyword"
            if not hits:
                message = f"no {name} {label} step definition matches {step.text!r}"
                problems.append(Problem(UNBOUND_STEP, severity, instance.file, step.line, message))
            elif len(hits) > 1:
                places = ", ".join(f"{Path(d.file).name}:{d.line}" for d in hits)
                message = f"{step.text!r} matches {len(hits)} {name} step definitions: {places}"
                problems.append(
                    Problem(AMBIGUOUS_STEP, severity, instance.file, step.line, message)
                )
    return problems


# ---------------------------------------------------------------------------
# Registers, bindings and the steps index (D-2)
# ---------------------------------------------------------------------------


def _cells(line: str) -> list[str]:
    inner = line.strip()
    inner = inner[1:] if inner.startswith("|") else inner
    inner = inner[:-1] if inner.endswith("|") else inner
    return [cell.strip() for cell in inner.split("|")]


def _code_span(cell: str) -> str | None:
    if len(cell) >= 2 and cell.startswith("`") and cell.endswith("`") and "`" not in cell[1:-1]:
        return cell[1:-1]
    return None


def _is_separator(cells: Sequence[str]) -> bool:
    return all(_SEPARATOR_CELL_RE.fullmatch(c) for c in cells)


def _tables(lines: Sequence[str], header: list[str]) -> Iterable[tuple[int, list[str]]]:
    """Body rows ``(line, cells)`` of every table whose header row equals ``header``."""
    state = "outside"  # outside | wanted | foreign
    for number, raw in enumerate(lines, start=1):
        stripped = raw.strip()
        if not stripped.startswith("|"):
            state = "outside"
            continue
        cells = _cells(stripped)
        if state == "outside":
            state = "wanted" if cells == header else "foreign"
        elif state == "wanted" and not _is_separator(cells):
            yield number, cells


def _read_register(path: Path) -> list[_Row]:
    rows: list[_Row] = []
    for number, cells in _tables(path.read_text(encoding="utf-8").splitlines(), _REGISTER_HEADER):
        promise = _code_span(cells[0]) if cells else None
        if promise is None:
            continue
        binding = cells[3] if len(cells) > 3 else ""
        rows.append(_Row(promise, _code_span(binding) or binding, number))
    return rows


def _check_registers(
    features: Path, instances: Sequence[_Instance], areas: Iterable[str], steps: Mapping[str, Path]
) -> tuple[list[Problem], dict[tuple[str, str], tuple[str, ...]]]:
    """UNREGISTERED_PROMISE and BAD_BINDING_DECLARATION; also each promise's bound sources."""
    problems: list[Problem] = []
    bound: dict[tuple[str, str], tuple[str, ...]] = {}
    for area in sorted(set(areas)):
        register = f"{area}/{_REGISTER_FILE}" if area else _REGISTER_FILE
        carriers = [i for i in instances if i.area == area]
        if not (features / register).is_file():
            message = f"area {area or '.'!r} has scenarios but no {_REGISTER_FILE}"
            problems.append(_problem(UNREGISTERED_PROMISE, register, 1, message))
            continue
        rows = _read_register(features / register)
        registered = {row.promise for row in rows}
        for instance in carriers:
            for value in instance.promises():
                if value not in registered:
                    message = f"@promise:{value} has no row in {register}"
                    problems.append(
                        _problem(UNREGISTERED_PROMISE, instance.file, instance.line, message)
                    )
        for row in rows:
            owners = [i for i in carriers if row.promise in i.promises()]
            if not owners:
                message = f"{row.promise} is carried by no scenario"
                problems.append(_problem(UNREGISTERED_PROMISE, register, row.line, message))
            problems += _check_binding(register, row, owners, steps)
            names = _BINDINGS.get(row.binding, ())
            bound[(area, row.promise)] = tuple(n for n in names if n in steps)
    return problems, bound


def _check_binding(
    register: str, row: _Row, owners: Sequence[_Instance], steps: Mapping[str, Path]
) -> list[Problem]:
    where = (register, row.line)
    names = _BINDINGS.get(row.binding)
    if names is None:
        allowed = " / ".join(_BINDINGS)
        message = f"{row.promise}: Binding {row.binding!r} is not one of {allowed}"
        return [_problem(BAD_BINDING_DECLARATION, *where, message)]
    problems = [
        _problem(BAD_BINDING_DECLARATION, *where, f"{row.promise}: no {n!r} step source given")
        for n in names
        if n not in steps
    ]
    declared_wip = row.binding == _WIP_BINDING
    for owner in owners:
        if owner.wip != declared_wip:
            state = "is @wip" if owner.wip else "is not @wip"
            message = (
                f"{row.promise}: Binding {row.binding!r} but the scenario at "
                f"{owner.file}:{owner.line} {state}"
            )
            problems.append(_problem(BAD_BINDING_DECLARATION, *where, message))
    return problems


def _read_index(index: Path) -> tuple[list[_IndexRow], list[Problem]]:
    lines = index.read_text(encoding="utf-8").splitlines()
    start = next((n for n, raw in enumerate(lines) if raw.strip() == _INDEX_HEADING), None)
    if start is None:
        return [], [_problem(STEPS_TABLE_DRIFT, index, 1, f"no {_INDEX_HEADING!r} heading")]
    section: list[str] = []
    for raw in lines[start + 1 :]:
        if raw.startswith("#"):
            break
        section.append(raw)
    rows: list[_IndexRow] = []
    problems: list[Problem] = []
    for offset, cells in _tables(section, _INDEX_HEADER):
        number = start + 1 + offset
        keyword = _INDEX_GROUPS.get(cells[0])
        span = _code_span(cells[1]) if len(cells) == 2 else None
        if keyword is None or span is None or " " not in span:
            message = f"malformed steps-index row: {' | '.join(cells)}"
            problems.append(_problem(STEPS_TABLE_DRIFT, index, number, message))
            continue
        rows.append(_IndexRow(keyword, span.split(" ", 1)[1].strip(), number))
    return rows, problems


def _check_index(index: Path, definitions: Sequence[StepDefinition]) -> list[Problem]:
    rows, problems = _read_index(index)
    defined = {
        (d.keyword, _normalise_parse(d.pattern) if d.is_parse else d.pattern): d
        for d in definitions
    }
    listed = {(r.keyword, r.phrase) for r in rows}
    for row in rows:
        if (row.keyword, row.phrase) not in defined:
            message = f"index row {row.keyword} {row.phrase!r} has no {row.keyword} definition"
            problems.append(_problem(STEPS_TABLE_DRIFT, index, row.line, message))
    for (keyword, phrase), definition in sorted(defined.items()):
        if (keyword, phrase) not in listed:
            message = f"{keyword} {phrase!r} has no row in the steps index"
            problems.append(_problem(STEPS_TABLE_DRIFT, definition.file, definition.line, message))
    return problems


# ---------------------------------------------------------------------------
# Check, output and entry point
# ---------------------------------------------------------------------------


def _relative(problem: Problem, features: Path) -> Problem:
    if not os.path.isabs(problem.file):
        return problem
    return replace(problem, file=Path(os.path.relpath(problem.file, features)).as_posix())


def _sort_key(problem: Problem) -> tuple[str, int, str, str, str]:
    return (problem.file, problem.line, problem.code, problem.severity, problem.message)


def check(features: Path, steps: Mapping[str, Path], index: Path) -> list[Problem]:
    """Check the features tree against the step sources and the steps index; sorted findings.

    Raises ``UsageError`` for a binding name outside the registry or an unreadable source.
    """
    unknown = sorted(set(steps) - set(_READERS))
    if unknown:
        raise UsageError(f"unknown step source name(s): {', '.join(unknown)}")
    features = features.resolve()
    sources: dict[str, list[StepDefinition]] = {}
    problems: list[Problem] = []
    for name in sorted(steps):
        definitions, source_problems = _READERS[name](steps[name].resolve())
        sources[name] = definitions
        problems += source_problems
    relatives, instances, parse_problems = _parse_tree(features)
    problems += parse_problems
    if not relatives:
        problems.append(_problem(NO_FEATURES, ".", 1, "no .feature files found"))
    elif not any(i.gating for i in instances):
        message = "no scenario gates (all are @wip or @manual)"
        problems.append(_problem(NO_GATING_SCENARIOS, ".", 1, message))
    for instance in instances:
        problems += _check_tags(instance)
    problems += _check_duplicates(instances)
    register_problems, bound = _check_registers(
        features, instances, (_area_of(r) for r in relatives), steps
    )
    problems += register_problems
    fallback = ["python"] if "python" in sources else sorted(sources)
    for instance in instances:
        names = sorted({n for p in instance.promises() for n in bound.get((instance.area, p), ())})
        chosen = {n: sources[n] for n in (names or fallback)}
        problems += _match_instance(instance, chosen)
    problems += _check_index(index, sources.get("python", []))
    unique = {_relative(p, features) for p in problems}
    return sorted(unique, key=_sort_key)


def _resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="scenario_contract",
        description="Per-PR contract check for the shared BDD scenario suite.",
    )
    parser.add_argument("--features", default=DEFAULT_FEATURES, help="directory of .feature files")
    parser.add_argument(
        "--steps",
        action="append",
        metavar="NAME=DIR",
        help=f"a step source, repeatable (default {DEFAULT_STEPS}); NAME is one of "
        + ", ".join(sorted(_READERS)),
    )
    parser.add_argument("--index", default=DEFAULT_INDEX, help="the steps index (README.md)")
    return parser.parse_args(argv)


def _usage(message: str) -> int:
    print(f"scenario_contract: usage error: {message}", file=sys.stderr)
    return 2


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parse_args(argv)
    except SystemExit as exc:  # argparse reports its own usage errors with exit 2
        return exc.code if isinstance(exc.code, int) else 2
    features = _resolve(args.features)
    index = _resolve(args.index)
    steps: dict[str, Path] = {}
    for item in args.steps or [DEFAULT_STEPS]:
        name, equals, directory = item.partition("=")
        if not equals or not name or not directory:
            return _usage(f"--steps expects NAME=DIR, got {item!r}")
        if name not in _READERS:
            return _usage(f"unknown step source {name!r}; known: {', '.join(sorted(_READERS))}")
        steps[name] = _resolve(directory)
    for label, path, is_dir in [("features", features, True), ("index", index, False)] + [
        (f"steps {n}", p, True) for n, p in steps.items()
    ]:
        if not (path.is_dir() if is_dir else path.is_file()):
            return _usage(f"{label} path {path} does not exist")
    try:
        problems = check(features, steps, index)
    except UsageError as exc:
        return _usage(str(exc))
    for p in problems:
        print(f"{p.severity} {p.code} {p.file}:{p.line} {p.message}")
    errors = sum(1 for p in problems if p.severity == ERROR)
    print(
        f"scenario contract: {errors} error(s), {len(problems) - errors} info",
        file=sys.stderr,
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
