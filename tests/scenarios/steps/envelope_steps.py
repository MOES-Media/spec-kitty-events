"""Python reference step binding for the ``envelope/`` scenarios (#197).

The binding reaches the contract only through the installed package's public surface
(``spec_kitty_events.conformance.class_fixture_verdict`` and
``spec_kitty_events.strict.validate_strict_envelope``) and the committed fixtures. It never
imports a module from ``tests/`` outside ``tests/scenarios/`` (FR-009).

Each scenario selects fixtures by class or by register id, never by content (FR-006):

- **Register**: for the eight taxonomy classes, ``manifest.json`` ``classes.entries`` filtered
  by ``class``; for ``envelope_strict_journal``, the top-level ``fixtures`` array filtered by
  path prefix.
- **Pins**: for taxonomy classes, ``expected`` and ``expected_error_code`` come from the
  register entry, and the file must agree; for the strict journal profile, they come from the
  file (``expected``, ordered ``expected_error_codes``), and the register's
  ``expected_result`` must agree.
- **Coverage**: the register's ids and paths must each be unique, the register paths must equal
  the ``*.json`` files on disk, and an empty selection fails (``select_class``). The single-fixture
  selection (``select_id``) runs the same whole-class checks first. The closing step checks that
  the verdict was computed once per selected fixture and per file counted on disk.
- **Assert**: every Assert step compares each outcome with that fixture's own pin.

The verdict functions are looked up as module attributes at call time, so a test can
monkeypatch them on this module to count calls.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, then, when

from spec_kitty_events.conformance import class_fixture_verdict
from spec_kitty_events.strict import validate_strict_envelope
from spec_kitty_events.validation_errors import ValidationError

FIXTURE_ROOT_ENV = "SPEC_KITTY_SCENARIO_FIXTURES"
STRICT_JOURNAL_CLASS = "envelope_strict_journal"
LANE_MAPPING_CLASS = "lane_mapping_legacy"


@dataclass(frozen=True)
class Case:
    """One selected fixture: its register id, relative path, parsed file and pins."""

    id: str
    path: str
    document: dict[str, Any]
    expected: str
    codes: tuple[str, ...]

    @property
    def input(self) -> object:
        return self.document.get("input")


@dataclass
class ScenarioContext:
    """State shared by the steps of one scenario."""

    fixture_class: str = ""
    cases: list[Case] = field(default_factory=list)
    disk_count: int = 0
    outcomes: dict[str, object] = field(default_factory=dict)
    calls: int = 0


@pytest.fixture
def scenario_ctx() -> ScenarioContext:
    return ScenarioContext()


# --------------------------------------------------------------------------------------------
# Selection
# --------------------------------------------------------------------------------------------


def _fixture_root() -> Path:
    override = os.environ.get(FIXTURE_ROOT_ENV)
    if override:
        return Path(override)
    return Path(str(files("spec_kitty_events.conformance") / "fixtures"))


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _class_dir(root: Path, fixture_class: str) -> Path:
    return root / "class_taxonomy" / fixture_class


def _disk_paths(root: Path, fixture_class: str) -> list[str]:
    folder = _class_dir(root, fixture_class)
    return sorted(p.relative_to(root).as_posix() for p in folder.rglob("*.json"))


def _register(manifest: dict[str, Any], fixture_class: str) -> list[dict[str, Any]]:
    if fixture_class == STRICT_JOURNAL_CLASS:
        prefix = f"class_taxonomy/{STRICT_JOURNAL_CLASS}/"
        return [f for f in manifest.get("fixtures", []) if f.get("path", "").startswith(prefix)]
    entries = manifest.get("classes", {}).get("entries", [])
    return [e for e in entries if e.get("class") == fixture_class]


def _taxonomy_case(root: Path, entry: dict[str, Any]) -> Case:
    path = entry["path"]
    document = _load_json(root / path)
    expected = entry.get("expected")
    code = entry.get("expected_error_code")
    if expected not in ("valid", "invalid"):
        pytest.fail(f"{entry['id']}: register pins expected={expected!r}")
    if expected == "invalid" and code is None:
        pytest.fail(f"{entry['id']}: register pins invalid with no expected_error_code")
    if expected == "valid" and code is not None:
        pytest.fail(f"{entry['id']}: register pins valid with expected_error_code={code!r}")
    for key, pinned in (("expected", expected), ("expected_error_code", code)):
        if key in document and document[key] != pinned:
            pytest.fail(
                f"{path}: file pins {key}={document[key]!r} but the register "
                f"({entry['id']}) pins {pinned!r}"
            )
    codes = (code,) if code is not None else ()
    return Case(id=entry["id"], path=path, document=document, expected=expected, codes=codes)


def _strict_case(root: Path, entry: dict[str, Any]) -> Case:
    path = entry["path"]
    document = _load_json(root / path)
    expected = document.get("expected")
    codes = tuple(document.get("expected_error_codes") or ())
    if expected not in ("valid", "invalid"):
        pytest.fail(f"{path}: file pins expected={expected!r}")
    if entry.get("expected_result") != expected:
        pytest.fail(
            f"{path}: file pins expected={expected!r} but the register ({entry['id']}) "
            f"pins expected_result={entry.get('expected_result')!r}"
        )
    if (expected == "invalid") != bool(codes):
        pytest.fail(f"{path}: expected={expected!r} disagrees with expected_error_codes={codes!r}")
    return Case(id=entry["id"], path=path, document=document, expected=expected, codes=codes)


def _case(root: Path, fixture_class: str, entry: dict[str, Any]) -> Case:
    if fixture_class == STRICT_JOURNAL_CLASS:
        return _strict_case(root, entry)
    return _taxonomy_case(root, entry)


def _require_unique(fixture_class: str, register: list[dict[str, Any]], key: str) -> None:
    counts = Counter(str(entry.get(key)) for entry in register)
    repeated = sorted(value for value, count in counts.items() if count > 1)
    if repeated:
        pytest.fail(f"class {fixture_class!r}: register repeats {key} {repeated}")


def select_class(root: Path, fixture_class: str) -> list[Case]:
    """Every case a class registers, ordered by path.

    Fails unless the register's ids and paths are each unique, the set of register paths
    equals the set of ``*.json`` files in the class folder, and the selection is not empty.
    """
    manifest = _load_json(root / "manifest.json")
    register = _register(manifest, fixture_class)
    _require_unique(fixture_class, register, "id")
    _require_unique(fixture_class, register, "path")
    register_paths = {entry["path"] for entry in register}
    disk_paths = set(_disk_paths(root, fixture_class))
    if register_paths != disk_paths:
        pytest.fail(
            f"class {fixture_class!r}: register and disk disagree; "
            f"registered but not on disk: {sorted(register_paths - disk_paths)}; "
            f"on disk but not registered: {sorted(disk_paths - register_paths)}"
        )
    if not register:
        pytest.fail(f"class {fixture_class!r} selects no fixtures under {root}")
    ordered = sorted(register, key=lambda entry: str(entry["path"]))
    return [_case(root, fixture_class, entry) for entry in ordered]


def select_id(root: Path, fixture_class: str, fixture_id: str) -> Case:
    """The one case of a class whose register id matches, after the whole-class selection."""
    matches = [case for case in select_class(root, fixture_class) if case.id == fixture_id]
    if len(matches) != 1:
        pytest.fail(
            f"class {fixture_class!r}: register id {fixture_id!r} matches {len(matches)} entries"
        )
    return matches[0]


# --------------------------------------------------------------------------------------------
# Arrange
# --------------------------------------------------------------------------------------------


@given(parsers.parse('the conformance fixtures of class "{fixture_class}"'))
def given_class(scenario_ctx: ScenarioContext, fixture_class: str) -> None:
    """Select every fixture of a class; register and disk must agree."""
    root = _fixture_root()
    scenario_ctx.cases = select_class(root, fixture_class)
    scenario_ctx.fixture_class = fixture_class
    # Counted from the disk glob, independently of the register.
    scenario_ctx.disk_count = len(_disk_paths(root, fixture_class))


@given(parsers.parse('the conformance fixture "{fixture_id}" of class "{fixture_class}"'))
def given_one(scenario_ctx: ScenarioContext, fixture_id: str, fixture_class: str) -> None:
    """Select one fixture by its register id; the whole class must pass selection first."""
    scenario_ctx.cases = [select_id(_fixture_root(), fixture_class, fixture_id)]
    scenario_ctx.fixture_class = fixture_class
    scenario_ctx.disk_count = 1


# --------------------------------------------------------------------------------------------
# Act
# --------------------------------------------------------------------------------------------


def _evaluate(ctx: ScenarioContext, verdict_fn: Callable[[object], object], case: Case) -> None:
    """Compute one case's verdict and record it. Every selected case goes through here."""
    ctx.calls += 1
    ctx.outcomes[case.id] = verdict_fn(case.input)


def _evaluate_all(ctx: ScenarioContext, verdict_fn: Callable[[object], object]) -> None:
    for case in ctx.cases:
        _evaluate(ctx, verdict_fn, case)


@when("each envelope is validated")
def validate_each(scenario_ctx: ScenarioContext) -> None:
    fixture_class = scenario_ctx.fixture_class
    _evaluate_all(scenario_ctx, lambda value: class_fixture_verdict(fixture_class, value))


@when("each envelope is validated under the strict journal profile")
def validate_each_strict(scenario_ctx: ScenarioContext) -> None:
    _evaluate_all(scenario_ctx, lambda value: validate_strict_envelope(value))


@when("each legacy lane is resolved")
def resolve_each_lane(scenario_ctx: ScenarioContext) -> None:
    if scenario_ctx.fixture_class != LANE_MAPPING_CLASS:
        pytest.fail(f"lane resolution needs class {LANE_MAPPING_CLASS!r}")
    _evaluate_all(scenario_ctx, lambda value: class_fixture_verdict(LANE_MAPPING_CLASS, value))


# --------------------------------------------------------------------------------------------
# Assert
# --------------------------------------------------------------------------------------------


def _codes(outcome: object) -> tuple[str, ...]:
    """Normalise a verdict to its ordered error codes; empty means accepted."""
    if outcome is None:
        return ()
    if isinstance(outcome, ValidationError):
        return (outcome.code.value,)
    if isinstance(outcome, Sequence):
        return tuple(error.code.value for error in outcome)
    raise AssertionError(f"unrecognised verdict {outcome!r}")


def _outcome(ctx: ScenarioContext, case: Case) -> tuple[str, ...]:
    if case.id not in ctx.outcomes:
        pytest.fail(f"{case.path}: was never evaluated")
    return _codes(ctx.outcomes[case.id])


def _require_pins(ctx: ScenarioContext, expected: str) -> None:
    wrong = [case.path for case in ctx.cases if case.expected != expected]
    if wrong:
        pytest.fail(f"these fixtures do not pin {expected!r}: {wrong}")


def _off_pin(ctx: ScenarioContext) -> dict[str, tuple[str, str, tuple[str, ...], tuple[str, ...]]]:
    """Cases whose outcome disagrees with their own pin: the codes, and refused iff invalid."""
    off = {}
    for case in ctx.cases:
        actual = _outcome(ctx, case)
        if actual != case.codes or bool(actual) != (case.expected == "invalid"):
            off[case.path] = (
                case.expected,
                "refused" if actual else "accepted",
                case.codes,
                actual,
            )
    return off


@then("each is accepted")
def each_accepted(scenario_ctx: ScenarioContext) -> None:
    _require_pins(scenario_ctx, "valid")
    off = _off_pin(scenario_ctx)
    assert not off, f"(pinned, verdict, pinned codes, actual codes) differ: {off}"
    refused = {c.path: _outcome(scenario_ctx, c) for c in scenario_ctx.cases}
    refused = {path: codes for path, codes in refused.items() if codes}
    assert not refused, f"pinned valid but refused: {refused}"


@then("each is refused with exactly the code its fixture pins")
def each_refused_with_pinned_code(scenario_ctx: ScenarioContext) -> None:
    _require_pins(scenario_ctx, "invalid")
    off = _off_pin(scenario_ctx)
    assert not off, f"(pinned, verdict, pinned codes, actual codes) differ: {off}"


@then("each is refused")
def each_refused(scenario_ctx: ScenarioContext) -> None:
    """Refusal only, for ``historical_row_raw``.

    The pinned ``RAW_HISTORICAL_ROW`` is the ideal code, which today's validator does not
    always emit (conformance README, the note on ``historical_row_raw``); this step must not
    claim it is. It still compares each verdict with its own pin: refused exactly when the
    fixture pins ``invalid`` with a code.
    """
    _require_pins(scenario_ctx, "invalid")
    off = {
        case.path: (case.expected, case.codes, _outcome(scenario_ctx, case))
        for case in scenario_ctx.cases
        if bool(_outcome(scenario_ctx, case)) != (case.expected == "invalid" and bool(case.codes))
    }
    assert not off, f"(pinned, pinned codes, actual codes): refusal disagrees with pin: {off}"


@then("each is accepted or refused with exactly the codes its fixture pins")
def each_as_pinned(scenario_ctx: ScenarioContext) -> None:
    off = _off_pin(scenario_ctx)
    assert not off, f"(pinned, verdict, pinned codes, actual codes) differ: {off}"


@then(parsers.parse('it is refused with the code "{code}"'))
def refused_with_code(scenario_ctx: ScenarioContext, code: str) -> None:
    """The outcome and the fixture's pin must both be exactly ``[code]``."""
    for case in scenario_ctx.cases:
        assert case.expected == "invalid" and case.codes == (code,), (
            f"{case.path}: pins {case.expected} {list(case.codes)}, not invalid [{code!r}]"
        )
        actual = _outcome(scenario_ctx, case)
        assert actual == (code,), f"{case.path}: refused with {list(actual)}, not [{code!r}]"


@then("every selected fixture was evaluated")
def every_fixture_evaluated(scenario_ctx: ScenarioContext) -> None:
    ctx = scenario_ctx
    assert ctx.cases, "no fixture was selected"
    assert ctx.calls == ctx.disk_count == len(ctx.cases), (
        f"verdict calls={ctx.calls}, fixtures on disk={ctx.disk_count}, selected={len(ctx.cases)}"
    )
