---
work_package_id: WP04
title: Envelope scenarios and reference step binding
dependencies:
- WP01
- WP02
requirement_refs:
- C-002
- C-003
- C-004
- C-006
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
- FR-009
- FR-013
- FR-014
- FR-015
- FR-016
- FR-017
- FR-018
- FR-020
- SC-001
planning_base_branch: issue-197-bdd-suite-skeleton
merge_target_branch: issue-197-bdd-suite-skeleton
branch_strategy: Planning artifacts for this mission were generated on issue-197-bdd-suite-skeleton. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into issue-197-bdd-suite-skeleton unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
- T018
phase: Phase 2 - Suite and its gate
agent: claude
history:
- '2026-11-03: created by /spec-kitty.tasks'
agent_profile: python-pedro
authoritative_surface: tests/scenarios/
create_intent:
- tests/scenarios/__init__.py
- tests/scenarios/conftest.py
- tests/scenarios/README.md
- tests/scenarios/test_envelope.py
- tests/scenarios/steps/__init__.py
- tests/scenarios/steps/envelope_steps.py
- tests/scenarios/envelope/PROMISES.md
- tests/scenarios/envelope/accepts-valid-envelopes/accepts-valid-envelopes.feature
- tests/scenarios/envelope/refuses-with-pinned-reason/refuses-with-pinned-reason.feature
- tests/scenarios/envelope/strict-journal-profile/strict-journal-profile.feature
- tests/scenarios/envelope/resolves-legacy-lanes/resolves-legacy-lanes.feature
execution_mode: code_change
owned_files:
- tests/scenarios/__init__.py
- tests/scenarios/conftest.py
- tests/scenarios/README.md
- tests/scenarios/test_envelope.py
- tests/scenarios/steps/**
- tests/scenarios/envelope/**
role: implementer
tags: []
tracker_refs: []
---

# WP04 — Envelope scenarios and reference step binding

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load the assigned profile with the `/spk-charter-profile-load` skill (profile `python-pedro`). Then load governance with `spec-kitty charter context --action implement`.

Read, in `kitty-specs/bdd-suite-skeleton-01M6GF8W/`:
- `spec.md`: all of it, especially the Domain Language, FR-001 to FR-018 and the edge cases;
- `plan.md`: approaches 2, 3 and 4;
- `data-model.md`;
- `contracts/scenario-contract-check.md`: the rules your tree must satisfy.

Core's exemplar, read-only, is at `/home/user/spec-kitty/spec-kitty/tests/scenarios/`: see `README.md` and `charter/PROMISES.md`.

## Objective

Create the scenario suite and its Python reference step binding:
- 10 gating `envelope/` promises, `PR-EVENTS-ENVELOPE-001` to `-010`, across 4 behaviour folders;
- each step selects fixtures by class or register id, checks the verdict each fixture pins, and fails on an empty or inconsistent selection;
- the binding uses only the installed package's public surface and the committed fixtures.

## Branch Strategy

The planning base and the merge target are both `issue-197-bdd-suite-skeleton`. The workspace is the lane worktree from `lanes.json`:

```bash
spec-kitty agent action implement WP04 --agent <name> --mission bdd-suite-skeleton-01M6GF8W
```

## STOP conditions

- A fixture's pinned verdict disagrees with the public function or with `validate_strict_envelope`. That is a real contract defect; report it and do not edit the fixture.
- A step needs a Python or library identifier in its phrase (C-004).
- The binding seems to need something from `tests/` outside `tests/scenarios/` (FR-009).

## Subtasks

### T015 — Skeleton: package, conftest and tag hook

- **`tests/scenarios/__init__.py`**: empty, following the repo's `tests/__init__.py` package layout. Also create `tests/scenarios/steps/__init__.py`.
- **`tests/scenarios/conftest.py`**:
  - **Docstring**: the suite layout, and the test-only environment variable `SPEC_KITTY_SCENARIO_FIXTURES`. It is read only by the Arrange step, at call time, and overrides the fixture root for the mutation tests.
  - **Step import**: `from tests.scenarios.steps.envelope_steps import *  # noqa: F403`. pytest-bdd binds step fixtures through the defining module's namespace, so a conftest import makes them visible to every test module in this folder; `pytest_plugins` is not allowed in a non-root conftest.
  - **Tag hook**: implement `pytest_bdd_apply_tag(tag: str, function)`. pytest-bdd 9 passes the tag without `@`, calls the hook with `firstresult=True`, and discards the return value (`scenario.py` around line 328). So:
    - for `wip`: `pytest.mark.skip(reason="@wip: draft scenario, not gating")(function)`, then return `True`;
    - for `manual`: skip with the reason `@manual`, then return `True`;
    - for a tag starting `promise:`, `wip-owner:`, `wip-since:`, `defect:` or `qa:`, and for any other bare tag: return `True` without marking, which consumes it and gives no unknown-mark warning;
    - otherwise return `None`.
    - Verify with `uv run pytest tests/scenarios -W error::pytest.PytestUnknownMarkWarning --no-cov`.
- **`tests/scenarios/README.md`**: the index. Copy core's README sections as a model.
  - **Purpose**: the technology-agnostic contract scenarios, the reference step binding, and the fact that the suite is not shipped.
  - **Layout**: an area table, one row for `envelope/`.
  - **Tags**: core's table, adapted to this repo.
  - **Available steps**: the table that the contract check's STEPS_TABLE_DRIFT reads. Use the placeholder names of the step definitions, for example `"<fixture_class>"`.
  - **How to run**: the commands from `quickstart.md`.
  - **How to add a promise**.

### T016 — Step binding `tests/scenarios/steps/envelope_steps.py`

- **Imports**: only `pytest`, `pytest_bdd` (`given`, `when`, `then`, `parsers`), the standard library, and public package names: `spec_kitty_events.conformance.class_fixture_verdict`, `spec_kitty_events.strict.validate_strict_envelope` and `spec_kitty_events.validation_errors`. Nothing from `tests.` outside `tests.scenarios`.
- **Fixture root**: read `os.environ.get("SPEC_KITTY_SCENARIO_FIXTURES")` inside the Arrange step. If it is unset, use `importlib.resources.files("spec_kitty_events.conformance") / "fixtures"`, converted to a `Path`.
- **Selection** (data-model.md, "Fixture selection"):
  - `select_class(root, fixture_class)`:
    - For a taxonomy class: the register is `manifest["classes"]["entries"]` filtered by `class`. For `envelope_strict_journal`: `manifest["fixtures"]`, filtered by `path.startswith("class_taxonomy/envelope_strict_journal/")`.
    - Disk is `sorted((root/"class_taxonomy"/fixture_class).rglob("*.json"))`; recurse, because `lane_mapping_legacy` has `valid/` and `invalid/` sub-folders.
    - Compare the set of register paths with the set of disk paths, relative to `root`. If they differ, call `pytest.fail` listing both differences.
    - If the selection is empty, call `pytest.fail`.
    - Return ordered `Case` records: id, path, the parsed file, and the pins (`expected`, `expected_error_code` or `expected_error_codes`). For taxonomy classes, `expected` comes from the register entry; check that the file's `expected` agrees, if it has one.
  - `select_id(root, fixture_class, fixture_id)`: the same selection, then the one case whose register id matches. If none matches, call `pytest.fail`.
- **A context object** shared between steps (a pytest fixture `scenario_ctx` returning a dataclass) holds:
  - `cases`, the selected cases;
  - `disk_count`, the independent disk-glob count, computed separately from the register;
  - `outcomes`, a dict from id to outcome;
  - `calls`, an int.
- **Steps**. Each phrase must also appear in the README steps table.
  - **Arrange**:
    - `Given the conformance fixtures of class "{fixture_class}"`;
    - `Given the conformance fixture "{fixture_id}" of class "{fixture_class}"`. This sets `disk_count` to 1 for the single-case coverage check.
  - **Act**:
    - `When each envelope is validated`: calls `class_fixture_verdict(fixture_class, case.input)` per case and stores `None` or the `ValidationError`;
    - `When each envelope is validated under the strict journal profile`: calls `validate_strict_envelope(case.input)` and stores the list of codes;
    - `When each legacy lane is resolved`: calls `class_fixture_verdict("lane_mapping_legacy", case.input)`.
    - Each call goes through one wrapper that increments `calls`. Never short-circuit; evaluate every case.
  - **Assert**. Each collects every mismatch and fails once, listing them all.
    - `Then each is accepted`: every pin is `valid`, and every outcome is `None` or an empty list.
    - `Then each is refused with exactly the code its fixture pins`: every pin is `invalid`, and each outcome's code equals `expected_error_code`.
    - `Then each is refused`: every pin is `invalid`, and every outcome is not `None`. This is for `historical_row_raw`; its docstring cites the README caveat.
    - `Then each is accepted or refused with exactly the codes its fixture pins`: covers the strict profile, where the ordered code list equals `expected_error_codes`, and the lane mapping, a mix of valid and invalid with one code.
    - `Then it is refused with the code "{code}"`.
    - `Then every selected fixture was evaluated`: `calls == disk_count == len(cases)`.
- Read the shape of `validate_strict_envelope`'s result in `src/spec_kitty_events/strict.py` and in `tests/test_envelope_strict_journal_class.py:70-85`, and compare codes the same way that test does. Do not copy its code; call the public function.

### T017 — Feature files and the promise register

Write these four features, each with a user-story header in core's style ("As a maintainer of a language binding …"). Each scenario ends with `Then every selected fixture was evaluated`.

| Behaviour folder | Promise | Scenario (one each) |
|---|---|---|
| `accepts-valid-envelopes/` | 001 | Canonical envelopes are accepted: class `envelope_valid_canonical` |
| | 002 | Envelopes synthesized from historical rows are accepted: class `envelope_valid_historical_synthesized` |
| `refuses-with-pinned-reason/` | 003 | Forbidden key, at any position, refused with its pinned code: `envelope_invalid_forbidden_key` |
| | 004 | Unknown lane refused: `envelope_invalid_unknown_lane` |
| | 005 | Payload that breaks its schema refused: `envelope_invalid_payload_schema` |
| | 006 | Badly shaped envelope refused: `envelope_invalid_shape` |
| | 007 | Raw historical rows are refused: `historical_row_raw`, with `Then each is refused` |
| `strict-journal-profile/` | 008 | The strict journal profile accepts or refuses with exactly the ordered codes pinned: `envelope_strict_journal` |
| | 009 | An unregistered event type fails closed: fixture `class-taxonomy-envelope-strict-journal-unknown-event-type` of class `envelope_strict_journal`, `Then it is refused with the code "UNKNOWN_EVENT_TYPE"` |
| `resolves-legacy-lanes/` | 010 | Legacy lane strings resolve as pinned: `lane_mapping_legacy` |

`envelope/PROMISES.md` follows core's format:
- an HTML comment header;
- one `## <Feature title> — \`<folder>/\`` section per behaviour;
- a table `| Promise | Consumer guarantee | Authority | Binding |`, with one row per promise.
  - **Authority** cites the spec FR and the fixture class or id, for example "spec FR-014; `class_taxonomy/envelope_invalid_shape/`".
  - **Binding** is `python` for all 10 rows.

Add a short paragraph stating that `envelope/` is bound in Python only by design: the Java binding validates CloudEvents rows, not `Event` envelopes. Cite the spec's scope note.

### T018 — Entry point, green run, README completeness

- **`tests/scenarios/test_envelope.py`**:
  ```python
  """Collects the envelope/ scenarios (#197). Steps: tests/scenarios/steps/envelope_steps.py."""
  from pytest_bdd import scenarios

  scenarios("envelope")
  ```
- Run `uv run pytest tests/scenarios --no-cov -q -W error::pytest.PytestUnknownMarkWarning`. It must show 10 passed and 0 skipped.
- Run the contract check against the real tree, if WP03 has merged into your lane base: `uv run python scripts/scenario_contract.py`. It must exit 0. Otherwise note it in the handoff; WP05 runs it.
- Check that the README steps table lists every phrase exactly once, with placeholder names that match the definitions.

## Gates

```bash
uv run pytest tests/scenarios --no-cov -q -W error::pytest.PytestUnknownMarkWarning
uv run pytest --pyargs spec_kitty_events.conformance -q     # unchanged count
uv run ruff check . && uv run ruff format --check .
make test-fast
```

## Definition of Done

- 10 scenarios pass, and none is `@wip`.
- The PROMISES register has 10 rows, all `python`.
- The README steps table is complete.
- There are no warnings.
- The step binding imports only public names.
- The fixture root can be overridden only through the documented environment variable.

## Reviewer guidance

Delete one fixture file in a scratch copy and point `SPEC_KITTY_SCENARIO_FIXTURES` at it. The covering scenario must fail in Arrange. Change one pinned code; exactly the covering scenario must fail. (WP05 commits these checks; here they are a sanity check.)
