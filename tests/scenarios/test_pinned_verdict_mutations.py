"""The envelope scenarios cannot pass vacuously: mutations and coverage cases (#197, WP05).

Each test runs the inner suite (``test_envelope.py``) in-process with ``pytest.main`` over a
temporary copy of the packaged conformance fixtures, named by ``SPEC_KITTY_SCENARIO_FIXTURES``
(read by the binding at call time), and asserts the exact set of failing scenarios:

- **Pinned-verdict mutations (SC-004)**: a *pin* mutation changes what a fixture pins and leaves
  its input alone; an *input* mutation changes the input and leaves its pin. Taxonomy pins are
  edited in both the register entry and the file, so the Arrange agreement check passes and the
  Assert step is what fails. Mutations of disjoint classes share a run; the rows of the shared
  ``envelope_strict_journal`` class (008, 009) each run alone.
- **Coverage (SC-002, US2)**: an unregistered, removed, duplicated or skipped fixture fails the
  run, and an added, correctly registered fixture is evaluated (counted by a spy on the public
  verdict function the binding really calls, SC-005).

A no-mutation control proves the copy and the environment variable work: all 10 pass.
Contract: ``kitty-specs/bdd-suite-skeleton-01M6GF8W/contracts/scenario-contract-check.md``
§ "Mutation tests (SC-004, SC-002)".
"""

from __future__ import annotations

import json
import shutil
from collections import Counter
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from importlib.resources import as_file, files
from pathlib import Path
from typing import Any

import pytest

from spec_kitty_events.conformance import class_fixture_verdict
from spec_kitty_events.strict import validate_strict_envelope
from tests.scenarios.steps import envelope_steps
from tests.scenarios.steps.envelope_steps import FIXTURE_ROOT_ENV, Case, ScenarioContext

INNER_SUITE = Path(__file__).resolve().parent / "test_envelope.py"
ALL_PROMISES = frozenset(f"{n:03d}" for n in range(1, 11))
PROMISE_PREFIX = "promise:PR-EVENTS-ENVELOPE-"

CANONICAL = "class_taxonomy/envelope_valid_canonical"
SYNTHESIZED = "class_taxonomy/envelope_valid_historical_synthesized"
FORBIDDEN = "class_taxonomy/envelope_invalid_forbidden_key"
UNKNOWN_LANE = "class_taxonomy/envelope_invalid_unknown_lane"
PAYLOAD = "class_taxonomy/envelope_invalid_payload_schema"
SHAPE = "class_taxonomy/envelope_invalid_shape"
HISTORICAL = "class_taxonomy/historical_row_raw"
STRICT = "class_taxonomy/envelope_strict_journal"
LANES = "class_taxonomy/lane_mapping_legacy"


# --------------------------------------------------------------------------------------------
# The inner run
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class StepFailure:
    """The step that failed a scenario: its type (given/when/then), text and message."""

    type: str
    name: str
    message: str


@dataclass
class Collector:
    """A plugin for the inner run: each scenario's promise, outcome and failing step."""

    promises: dict[str, str] = field(default_factory=dict)
    outcomes: dict[str, set[str]] = field(default_factory=dict)
    steps: dict[str, StepFailure] = field(default_factory=dict)

    def pytest_bdd_before_scenario(self, request: Any, feature: Any, scenario: Any) -> None:
        tags = [t for t in scenario.tags if t.startswith(PROMISE_PREFIX)]
        assert len(tags) == 1, f"{scenario.name}: promise tags {tags}"
        self.promises[request.node.nodeid] = tags[0].removeprefix(PROMISE_PREFIX)

    def pytest_bdd_step_error(
        self, request: Any, step: Any, exception: BaseException, **_: Any
    ) -> None:
        self.steps[request.node.nodeid] = StepFailure(step.type, step.name, str(exception))

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        self.outcomes.setdefault(report.nodeid, set()).add(report.outcome)


@dataclass(frozen=True)
class Result:
    """One inner run: the promises that passed, and each failed promise's failing step."""

    passed: frozenset[str]
    failed: dict[str, StepFailure]


def _run(monkeypatch: pytest.MonkeyPatch, root: Path) -> Result:
    monkeypatch.setenv(FIXTURE_ROOT_ENV, str(root))
    collector = Collector()
    args = [str(INNER_SUITE), "-p", "no:cacheprovider", "-o", "addopts=", "-q", "--tb=no"]
    exit_code = pytest.main(args, plugins=[collector])
    assert set(collector.outcomes) == set(collector.promises), "a scenario never started"
    passed = {collector.promises[n] for n, o in collector.outcomes.items() if o == {"passed"}}
    failed = {
        collector.promises[n]: collector.steps[n]
        for n, o in collector.outcomes.items()
        if "failed" in o
    }
    assert passed | set(failed) == ALL_PROMISES and not passed & set(failed)
    assert (exit_code == pytest.ExitCode.OK) == (not failed), f"exit code {exit_code}"
    return Result(frozenset(passed), failed)


# --------------------------------------------------------------------------------------------
# Temporary copies
# --------------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def pristine(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Path]:
    """One untouched copy of the packaged fixtures, taken through ``importlib.resources``."""
    target = tmp_path_factory.mktemp("pristine") / "fixtures"
    with as_file(files("spec_kitty_events.conformance") / "fixtures") as source:
        shutil.copytree(source, target)
    yield target


@pytest.fixture
def root(pristine: Path, tmp_path: Path) -> Path:
    """A fresh copy of the pristine fixtures for one run."""
    return Path(shutil.copytree(pristine, tmp_path / "fixtures"))


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump(path: Path, document: Any) -> None:
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def _edit_file(root: Path, rel: str, edit: Callable[[dict[str, Any]], None]) -> None:
    document = _load(root / rel)
    edit(document)
    _dump(root / rel, document)


def _entries(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = manifest["classes"]["entries"]
    return entries


def _edit_manifest(root: Path, edit: Callable[[dict[str, Any]], None]) -> None:
    _edit_file(root, "manifest.json", edit)


def _repin(root: Path, rel: str, expected: str, code: str | None) -> None:
    """Re-pin a taxonomy fixture in both its register entry and its file."""

    def apply(document: dict[str, Any]) -> None:
        document["expected"] = expected
        document.pop("expected_error_code", None)
        if code is not None:
            document["expected_error_code"] = code

    def apply_register(manifest: dict[str, Any]) -> None:
        matches = [e for e in _entries(manifest) if e["path"] == rel]
        assert len(matches) == 1, f"{rel}: {len(matches)} register entries"
        apply(matches[0])

    _edit_manifest(root, apply_register)
    _edit_file(root, rel, apply)


def _edit_input(root: Path, rel: str, edit: Callable[[dict[str, Any]], None]) -> None:
    _edit_file(root, rel, lambda document: edit(document["input"]))


def _strict_codes(root: Path, rel: str, codes: list[str]) -> None:
    def apply(document: dict[str, Any]) -> None:
        document["expected_error_codes"] = codes

    _edit_file(root, rel, apply)


# --------------------------------------------------------------------------------------------
# The mutation table (SC-004)
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Mutation:
    promise: str
    kind: str  # pin | input
    fixture: str  # the mutated file, relative to the fixture root
    apply: Callable[[Path], None]
    expected: frozenset[str]

    @property
    def fixture_class(self) -> str:
        return self.fixture.split("/")[1]


def _reversed_skew(root: Path) -> None:
    rel = f"{STRICT}/skew_missing_version.json"
    codes = _load(root / rel)["expected_error_codes"]
    assert len(codes) == 2 and codes != codes[::-1], codes
    _strict_codes(root, rel, codes[::-1])


def _set_key(key: str, value: object) -> Callable[[dict[str, Any]], None]:
    def edit(document: dict[str, Any]) -> None:
        assert key in document, key
        document[key] = value

    return edit


def _del_key(key: str) -> Callable[[dict[str, Any]], None]:
    def edit(document: dict[str, Any]) -> None:
        del document[key]

    return edit


def _m(
    promise: str, kind: str, fixture: str, apply: Callable[[Path], None], *expected: str
) -> Mutation:
    return Mutation(promise, kind, fixture, apply, frozenset(expected or (promise,)))


_F001 = f"{CANONICAL}/mission_created_baseline.json"
_F002 = f"{SYNTHESIZED}/from_pre30_envelope.json"
_F003 = f"{FORBIDDEN}/forbidden_key_top_level.json"
_F004 = f"{UNKNOWN_LANE}/to_lane_uppercase.json"
_F005 = f"{PAYLOAD}/wrong_type_wp_count.json"
_F006 = f"{SHAPE}/missing_event_type.json"
_F007 = f"{HISTORICAL}/raw_status_entry.json"
_F008 = f"{STRICT}/skew_missing_version.json"
_F009 = f"{STRICT}/unknown_event_type.json"
_F010_INVALID = f"{LANES}/invalid/awaiting_review_legacy_unmapped.json"
_F010_VALID = f"{LANES}/valid/doing_alias_resolves_to_in_progress.json"

MUTATIONS = {
    "001-pin": _m(
        "001", "pin", _F001, lambda r: _repin(r, _F001, "invalid", "ENVELOPE_SHAPE_INVALID")
    ),
    "001-input": _m("001", "input", _F001, lambda r: _edit_input(r, _F001, _del_key("build_id"))),
    "002-pin": _m(
        "002", "pin", _F002, lambda r: _repin(r, _F002, "invalid", "ENVELOPE_SHAPE_INVALID")
    ),
    "002-input": _m("002", "input", _F002, lambda r: _edit_input(r, _F002, _del_key("event_id"))),
    "003-pin": _m("003", "pin", _F003, lambda r: _repin(r, _F003, "invalid", "UNKNOWN_LANE")),
    "004-pin": _m("004", "pin", _F004, lambda r: _repin(r, _F004, "invalid", "FORBIDDEN_KEY")),
    "005-pin": _m(
        "005", "pin", _F005, lambda r: _repin(r, _F005, "invalid", "ENVELOPE_SHAPE_INVALID")
    ),
    "006-pin": _m(
        "006", "pin", _F006, lambda r: _repin(r, _F006, "invalid", "PAYLOAD_SCHEMA_FAIL")
    ),
    "007-pin": _m("007", "pin", _F007, lambda r: _repin(r, _F007, "valid", None)),
    "008-pin": _m("008", "pin", _F008, _reversed_skew),
    "009-pin": _m(
        "009",
        "pin",
        _F009,
        lambda r: _strict_codes(r, _F009, ["UNSUPPORTED_SCHEMA_VERSION"]),
        "008",
        "009",
    ),
    "009-input": _m(
        "009",
        "input",
        _F009,
        lambda r: _edit_input(r, _F009, _set_key("event_type", "MissionStarted")),
        "008",
        "009",
    ),
    "010-pin": _m("010", "pin", _F010_INVALID, lambda r: _repin(r, _F010_INVALID, "valid", None)),
    "010-input": _m(
        "010",
        "input",
        _F010_VALID,
        lambda r: _edit_input(r, _F010_VALID, _set_key("canonical_lane", "done")),
    ),
}

GROUPS = {
    "taxonomy-pins": [
        "001-pin",
        "002-pin",
        "003-pin",
        "004-pin",
        "005-pin",
        "006-pin",
        "007-pin",
        "010-pin",
    ],
    "taxonomy-inputs": ["001-input", "002-input", "010-input"],
    "strict-008-pin": ["008-pin"],
    "strict-009-pin": ["009-pin"],
    "strict-009-input": ["009-input"],
}


def test_every_mutation_runs_in_exactly_one_group() -> None:
    grouped = [name for names in GROUPS.values() for name in names]
    assert sorted(grouped) == sorted(MUTATIONS)
    covered = {MUTATIONS[name].promise for name in grouped}
    assert covered == ALL_PROMISES
    for names in GROUPS.values():
        classes = [MUTATIONS[name].fixture_class for name in names]
        assert len(classes) == len(set(classes)), f"group shares a class: {classes}"
        if any(c == "envelope_strict_journal" for c in classes):
            assert len(names) == 1, "a strict-journal row must run alone"


def test_unmutated_copy_passes_all_ten(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    result = _run(monkeypatch, root)
    assert result.failed == {}
    assert result.passed == ALL_PROMISES


@pytest.mark.parametrize("group", sorted(GROUPS))
def test_mutation_group_fails_exactly_its_scenarios(
    monkeypatch: pytest.MonkeyPatch, root: Path, group: str
) -> None:
    mutations = [MUTATIONS[name] for name in GROUPS[group]]
    for mutation in mutations:
        mutation.apply(root)
    expected = frozenset().union(*(m.expected for m in mutations))

    result = _run(monkeypatch, root)

    assert set(result.failed) == expected
    for mutation in mutations:
        assert mutation.promise in result.failed
    # The Arrange agreement check passed: every failure is in an Assert (Then) step.
    wrong_step = {p: f for p, f in result.failed.items() if f.type != "then"}
    assert not wrong_step, wrong_step


# --------------------------------------------------------------------------------------------
# Coverage cases (SC-002, US2)
# --------------------------------------------------------------------------------------------


def _arrange_failures(result: Result) -> dict[str, str]:
    assert all(f.type == "given" for f in result.failed.values()), result.failed
    return {p: f.message for p, f in result.failed.items()}


def test_unregistered_or_removed_file_fails_arrange(
    monkeypatch: pytest.MonkeyPatch, root: Path
) -> None:
    shutil.copy(root / _F001, root / CANONICAL / "extra.json")  # case 1: not registered
    (root / f"{FORBIDDEN}/forbidden_key_nested.json").unlink()  # case 2: registered, removed

    messages = _arrange_failures(_run(monkeypatch, root))

    assert set(messages) == {"001", "003"}
    assert "register and disk disagree" in messages["001"]
    assert f"on disk but not registered: ['{CANONICAL}/extra.json']" in messages["001"]
    assert "register and disk disagree" in messages["003"]
    assert (
        f"registered but not on disk: ['{FORBIDDEN}/forbidden_key_nested.json']"
        in (messages["003"])
    )


def test_duplicate_register_entry_fails_arrange(
    monkeypatch: pytest.MonkeyPatch, root: Path
) -> None:
    """Case 3d (WP04 review M3): register ids and paths must be unique."""

    def duplicate(manifest: dict[str, Any]) -> None:
        entries = _entries(manifest)
        first = next(e for e in entries if e["path"] == _F001)
        entries.append(dict(first))

    _edit_manifest(root, duplicate)

    messages = _arrange_failures(_run(monkeypatch, root))

    assert set(messages) == {"001"}
    assert "register repeats id" in messages["001"]


def test_single_fixture_selection_keeps_the_class_check(
    monkeypatch: pytest.MonkeyPatch, root: Path
) -> None:
    """Case 3e (WP04 review, FR-008): 009 selects one id, yet sees the unregistered file."""
    shutil.copy(root / _F009, root / STRICT / "planted.json")

    messages = _arrange_failures(_run(monkeypatch, root))

    assert set(messages) == {"008", "009"}
    for message in messages.values():
        assert f"on disk but not registered: ['{STRICT}/planted.json']" in message


@dataclass
class Spies:
    """Counting spies on the two public verdict functions the binding calls."""

    taxonomy: Counter[str] = field(default_factory=Counter)
    strict: int = 0


def _spy(monkeypatch: pytest.MonkeyPatch) -> Spies:
    spies = Spies()

    def class_spy(fixture_class: str, value: object) -> object:
        spies.taxonomy[fixture_class] += 1
        return class_fixture_verdict(fixture_class, value)

    def strict_spy(value: object) -> object:
        spies.strict += 1
        return validate_strict_envelope(value)

    monkeypatch.setattr(envelope_steps, "class_fixture_verdict", class_spy)
    monkeypatch.setattr(envelope_steps, "validate_strict_envelope", strict_spy)
    return spies


def _count_files(root: Path, folder: str) -> int:
    return sum(1 for _ in (root / folder).rglob("*.json"))


def test_added_registered_fixture_is_evaluated_once_more(
    monkeypatch: pytest.MonkeyPatch, pristine: Path, tmp_path: Path
) -> None:
    """Cases 3 and 3b (SC-002, SC-005): the binding calls the public verdict functions."""
    control_root = Path(shutil.copytree(pristine, tmp_path / "control"))
    control = _spy(monkeypatch)
    assert _run(monkeypatch, control_root).passed == ALL_PROMISES
    # 3b: one strict call per journal file on disk, plus one for 009's single selection.
    assert control.strict == _count_files(control_root, STRICT) + 1
    monkeypatch.undo()

    added_root = Path(shutil.copytree(pristine, tmp_path / "added"))
    added_rel = f"{CANONICAL}/mission_created_copy.json"
    shutil.copy(added_root / _F001, added_root / added_rel)

    def register(manifest: dict[str, Any]) -> None:
        entries = _entries(manifest)
        entry = dict(next(e for e in entries if e["path"] == _F001))
        entry.update(id="envelope-valid-canonical-mission-created-copy", path=added_rel)
        entries.append(entry)

    _edit_manifest(added_root, register)
    added = _spy(monkeypatch)

    result = _run(monkeypatch, added_root)

    assert result.passed == ALL_PROMISES
    assert added.taxonomy["envelope_valid_canonical"] == (
        control.taxonomy["envelope_valid_canonical"] + 1
    )
    assert added.taxonomy - Counter({"envelope_valid_canonical": 1}) == control.taxonomy
    assert added.strict == control.strict


def test_skipped_fixture_fails_its_scenario(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    """Case 3c (SC-002): a case the Act step skips cannot go unnoticed.

    Two skips, in disjoint classes: one case is dropped outright (neither counted nor
    stored), so the Assert step finds it never evaluated; another is evaluated but not
    counted, so only the closing coverage step can notice it.
    """
    dropped = "envelope-valid-canonical-mission-created-baseline"
    uncounted = "envelope-invalid-forbidden-key-nested"
    real = envelope_steps._evaluate

    def skipping(ctx: ScenarioContext, verdict_fn: Callable[[object], object], case: Case) -> None:
        if case.id == dropped:
            return
        if case.id == uncounted:
            ctx.outcomes[case.id] = verdict_fn(case.input)
            return
        real(ctx, verdict_fn, case)

    monkeypatch.setattr(envelope_steps, "_evaluate", skipping)

    result = _run(monkeypatch, root)

    assert set(result.failed) == {"001", "003"}
    assert result.failed["001"].type == "then"
    assert "was never evaluated" in result.failed["001"].message
    assert result.failed["003"].name == "every selected fixture was evaluated"
    assert "verdict calls=3, fixtures on disk=4, selected=4" in result.failed["003"].message


def test_unknown_register_id_fails_selection(pristine: Path) -> None:
    """Case 4: ``select_id`` refuses an id the register does not hold."""
    with pytest.raises(pytest.fail.Exception, match="matches 0 entries"):
        envelope_steps.select_id(pristine, "envelope_strict_journal", "no-such-fixture-id")
