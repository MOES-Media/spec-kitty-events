"""The scenario contract check refuses every rule it names, and passes a clean tree (FR-011/012).

``scripts/scenario_contract.py`` is run over planted trees under
``tests/fixtures/scenario_contract/``: ``_clean/`` must report nothing, and each ``<CODE>/``
tree, the baseline with one defect, must report exactly its own code. The real tree
(``tests/scenarios``) is checked by WP05 once it exists. Contract:
``kitty-specs/bdd-suite-skeleton-01M6GF8W/contracts/scenario-contract-check.md``.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import scenario_contract as sc  # noqa: E402

PLANTED = Path(__file__).resolve().parent / "fixtures" / "scenario_contract"
CLEAN = PLANTED / "_clean"
TREES = sorted(
    p.name for p in PLANTED.iterdir() if p.is_dir() and not p.name.startswith(("_", "."))
)
FEATURE = "features/demo/greeting/greeting.feature"


def _check(tree: Path) -> list[sc.Problem]:
    return sc.check(tree / "features", {"python": tree / "steps"}, tree / "README.md")


def _codes(problems: list[sc.Problem], severity: str = sc.ERROR) -> set[str]:
    return {p.code for p in problems if p.severity == severity}


def _args(tree: Path) -> list[str]:
    return [
        "--features",
        str(tree / "features"),
        "--steps",
        f"python={tree / 'steps'}",
        "--index",
        str(tree / "README.md"),
    ]


@pytest.fixture
def clean_copy(tmp_path: Path) -> Path:
    """A writable copy of ``_clean`` for the behaviours a planted tree does not pin."""
    tree = tmp_path / "tree"
    shutil.copytree(CLEAN, tree, ignore=shutil.ignore_patterns("__pycache__"))
    return tree


def _edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1, old
    path.write_text(text.replace(old, new), encoding="utf-8")


def test_the_clean_tree_reports_nothing() -> None:
    assert _check(CLEAN) == []


@pytest.mark.parametrize("code", TREES)
def test_each_planted_tree_reports_exactly_its_code(code: str) -> None:
    problems = _check(PLANTED / code)
    assert _codes(problems) == {code}, [p for p in problems if p.severity == sc.ERROR]


def test_every_code_has_a_planted_tree() -> None:
    assert set(TREES) == set(sc.CODES)
    assert len(sc.CODES) == 22


def test_discover_lists_feature_files_and_promises() -> None:
    found = sc.discover(CLEAN / "features")
    assert found == sc.Discovery(
        feature_files=("demo/greeting/greeting.feature",),
        promise_ids=("PR-demo-001", "PR-demo-002"),
    )


def test_findings_are_sorted_and_relative_to_the_features_root() -> None:
    problems = _check(PLANTED / "FORBIDDEN_TEST_IMPORT")
    assert [(p.file, p.line) for p in problems] == [("../steps/demo_steps.py", 5)]


# --- CLI ---------------------------------------------------------------------------------


def test_cli_exits_0_on_the_clean_tree(capsys: pytest.CaptureFixture[str]) -> None:
    assert sc.main(_args(CLEAN)) == 0
    assert capsys.readouterr().out == ""


def test_cli_exits_1_and_prints_findings_on_a_planted_tree(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert sc.main(_args(PLANTED / "UNBOUND_STEP")) == 1
    out = capsys.readouterr().out.splitlines()
    assert out == [
        "error UNBOUND_STEP demo/greeting/greeting.feature:13 "
        "no python when step definition matches 'the greeting is shouted'"
    ]


@pytest.mark.parametrize(
    ("flag", "value"),
    [
        ("--features", "{missing}"),
        ("--index", "{missing}"),
        ("--steps", "python={missing}"),
        ("--steps", "jvm={steps}"),
        ("--steps", "python"),
    ],
)
def test_cli_exits_2_on_a_usage_error(flag: str, value: str, tmp_path: Path) -> None:
    args = _args(CLEAN)
    args[args.index(flag) + 1] = value.format(missing=tmp_path / "missing", steps=CLEAN / "steps")
    assert sc.main(args) == 2


def test_check_refuses_an_unknown_step_source_name() -> None:
    with pytest.raises(sc.UsageError):
        sc.check(CLEAN / "features", {"jvm": CLEAN / "steps"}, CLEAN / "README.md")


# --- Parsing and tags --------------------------------------------------------------------


def test_tags_are_inherited_from_feature_rule_and_examples(clean_copy: Path) -> None:
    (clean_copy / FEATURE).write_text(
        "@promise:PR-demo-001\n"
        "Feature: Greeting\n"
        "  Rule: one\n"
        "    @bad.rule\n"
        "    Scenario: A known name is greeted\n"
        '      Given the name "Ada"\n'
        "      When the greeting is made\n"
        '      Then the greeting reads "Hello, Ada"\n'
        "\n"
        "  Scenario Outline: Another name is greeted\n"
        '    Given the name "<who>"\n'
        "    When the greeting is made\n"
        '    Then the greeting reads "Hello, <who>"\n'
        "\n"
        "    @qa:-bad\n"
        "    Examples:\n"
        "      | who |\n"
        "      | Bo  |\n",
        encoding="utf-8",
    )
    problems = _check(clean_copy)
    # Feature-level @promise:PR-demo-001 reaches both scenarios; PR-demo-002 has no carrier.
    assert _codes(problems) == {
        sc.BAD_BARE_TAG,
        sc.BAD_QA_REF,
        sc.DUPLICATE_PROMISE,
        sc.UNREGISTERED_PROMISE,
    }
    bare = next(p for p in problems if p.code == sc.BAD_BARE_TAG)
    qa = next(p for p in problems if p.code == sc.BAD_QA_REF)
    assert (bare.line, qa.line) == (5, 10)


def test_background_steps_and_conjunctions_bind_by_the_previous_keyword(
    clean_copy: Path,
) -> None:
    _edit(
        clean_copy / FEATURE,
        '  @promise:PR-demo-001\n  Scenario: A known name is greeted\n    Given the name "Ada"\n',
        '  Background:\n    Given the name "Zed"\n\n'
        '  @promise:PR-demo-001\n  Scenario: A known name is greeted\n    And the name "Ada"\n',
    )
    _edit(
        clean_copy / FEATURE,
        'Then the greeting reads "Hello, Ada"',
        'But the greeting reads "Hello, Ada"',
    )
    problems = _check(clean_copy)
    # "But" after "When" is a when-step: the then-definition does not bind it.
    assert [(p.code, p.line) for p in problems] == [(sc.UNBOUND_STEP, 11)]


def test_a_gating_scenario_needs_exactly_one_promise(clean_copy: Path) -> None:
    _edit(clean_copy / FEATURE, "  @promise:PR-demo-002\n", "")
    assert sc.BAD_PROMISE_ID in _codes(_check(clean_copy))
    _edit(
        clean_copy / FEATURE,
        "  @promise:PR-demo-001\n",
        "  @promise:PR-demo-001 @promise:PR-demo-002\n",
    )
    problems = [p for p in _check(clean_copy) if p.code == sc.BAD_PROMISE_ID]
    assert [(p.line, p.message) for p in problems] == [
        (5, "more than one promise: PR-demo-001, PR-demo-002"),
        (10, "a gating scenario needs @promise:<id>"),
    ]


def test_a_wip_scenario_may_lack_a_promise_and_its_unbound_steps_are_info(
    clean_copy: Path,
) -> None:
    _edit(
        clean_copy / FEATURE,
        "  @promise:PR-demo-002\n",
        "  @wip @wip-owner:ada @wip-since:2026-11-03\n",
    )
    _edit(clean_copy / FEATURE, '"Hello, Bo"', '"Hello, Bo" loudly')
    _edit(clean_copy / FEATURE, '    Given the name "Bo"\n', "    Given a name nobody defined\n")
    _edit(
        clean_copy / "features/demo/PROMISES.md",
        "| `PR-demo-002` | Another name is greeted | demo | `python` |\n",
        "",
    )
    problems = _check(clean_copy)
    assert _codes(problems) == set()
    assert _codes(problems, sc.INFO) == {sc.UNBOUND_STEP}


def test_manual_scenarios_report_binding_problems_as_info(clean_copy: Path) -> None:
    _edit(clean_copy / FEATURE, "  @promise:PR-demo-002\n", "  @promise:PR-demo-002 @manual\n")
    _edit(
        clean_copy / FEATURE,
        '    When the greeting is made\n    Then the greeting reads "Hello, Bo"',
        '    When the greeting is shouted\n    Then the greeting reads "Hello, Bo"',
    )
    problems = _check(clean_copy)
    assert [(p.severity, p.code) for p in problems] == [(sc.INFO, sc.UNBOUND_STEP)]


def test_a_wip_binding_must_agree_with_the_scenario(clean_copy: Path) -> None:
    _edit(clean_copy / "features/demo/PROMISES.md", "| demo | `python` |", "| demo | `@wip` |")
    assert _codes(_check(clean_copy)) == {sc.BAD_BINDING_DECLARATION}


def test_a_binding_outside_the_vocabulary_is_refused(clean_copy: Path) -> None:
    _edit(clean_copy / "features/demo/PROMISES.md", "| demo | `python` |", "| demo | bound |")
    assert _codes(_check(clean_copy)) == {sc.BAD_BINDING_DECLARATION}


def test_an_area_without_a_register_is_unregistered(clean_copy: Path) -> None:
    (clean_copy / "features/demo/PROMISES.md").unlink()
    problems = _check(clean_copy)
    assert [(p.code, p.file) for p in problems] == [(sc.UNREGISTERED_PROMISE, "demo/PROMISES.md")]


# --- Python step source ------------------------------------------------------------------


def test_an_unread_decorator_form_leaves_its_step_unbound(clean_copy: Path) -> None:
    _edit(
        clean_copy / "steps/demo_steps.py",
        '@when("the greeting is made")',
        '@when(parsers.re("the greeting is made"))',
    )
    codes = _codes(_check(clean_copy))
    # The unread definition also drops out of the index comparison.
    assert codes == {sc.UNBOUND_STEP, sc.STEPS_TABLE_DRIFT}


def test_aliases_stacked_decorators_and_name_keyword_are_read(tmp_path: Path) -> None:
    (tmp_path / "x_steps.py").write_text(
        "import pytest_bdd\n"
        "from pytest_bdd import given as arrange, parsers as p\n"
        "\n"
        "@arrange(p.parse('a count of {n:d}'))\n"
        "@pytest_bdd.then(name='done')\n"
        "@pytest_bdd.when(pytest_bdd.parsers.parse('{who} acts'))\n"
        "def f(): ...\n",
        encoding="utf-8",
    )
    definitions, problems = sc.read_python_steps(tmp_path)
    assert problems == []
    assert [(d.keyword, d.pattern, d.line) for d in definitions] == [
        ("given", "a count of {n:d}", 4),
        ("then", "done", 5),
        ("when", "{who} acts", 6),
    ]
    given = definitions[0].regex
    assert given.fullmatch("a count of -12") and not given.fullmatch("a count of x")


def test_a_relative_import_out_of_the_source_root_into_tests_is_forbidden() -> None:
    _, problems = sc.read_python_steps(PLANTED / "_relative_import" / "steps")
    assert [(p.code, p.line) for p in problems] == [(sc.FORBIDDEN_TEST_IMPORT, 3)]


@pytest.mark.parametrize(
    ("source", "forbidden"),
    [
        ("import tests\n", True),
        ("import tests.unit\n", True),
        ("from tests import test_lane_vocabulary\n", True),
        ("from tests import scenarios\n", False),
        ("from tests.scenarios.steps import helpers\n", False),
        ("import testsuite\n", False),
    ],
)
def test_absolute_imports_of_tests(tmp_path: Path, source: str, forbidden: bool) -> None:
    (tmp_path / "x_steps.py").write_text(source, encoding="utf-8")
    _, problems = sc.read_python_steps(tmp_path)
    assert bool(problems) is forbidden


def test_an_unparseable_step_source_is_a_usage_error(tmp_path: Path) -> None:
    (tmp_path / "x_steps.py").write_text("def (:\n", encoding="utf-8")
    with pytest.raises(sc.UsageError):
        sc.read_python_steps(tmp_path)


@pytest.mark.parametrize(
    ("pattern", "text", "matches"),
    [
        ('the class "{fixture_class}"', 'the class "envelope_valid"', True),
        ('the class "{fixture_class}"', "the class envelope_valid", False),
        ("{a} and {a} (twice)", "x and y (twice)", True),
        ("{{literal}} {n:d}", "{literal} 3", True),
        ("{{literal}} {n:d}", "{literal} three", False),
        ("{x:w} word", "anything word", True),
    ],
)
def test_parse_pattern_to_regex(pattern: str, text: str, matches: bool) -> None:
    assert (sc.parse_pattern_to_regex(pattern).fullmatch(text) is not None) is matches
