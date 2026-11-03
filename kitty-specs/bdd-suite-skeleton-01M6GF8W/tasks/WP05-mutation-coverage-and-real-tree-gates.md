---
work_package_id: WP05
title: Mutation, coverage and real-tree gates
dependencies:
- WP03
- WP04
requirement_refs:
- C-008
- FR-012
- FR-021
- NFR-001
- NFR-002
- NFR-004
- NFR-005
- SC-002
- SC-003
- SC-004
- SC-006
planning_base_branch: issue-197-bdd-suite-skeleton
merge_target_branch: issue-197-bdd-suite-skeleton
branch_strategy: Planning artifacts for this mission were generated on issue-197-bdd-suite-skeleton. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into issue-197-bdd-suite-skeleton unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T019
- T020
- T021
- T022
phase: Phase 3 - Proof
agent: claude
history:
- '2026-11-03: created by /spec-kitty.tasks'
agent_profile: python-pedro
authoritative_surface: tests/scenarios/test_pinned_verdict_mutations.py
create_intent:
- tests/scenarios/test_pinned_verdict_mutations.py
- tests/test_scenario_contract_real_tree.py
execution_mode: code_change
owned_files:
- tests/scenarios/test_pinned_verdict_mutations.py
- tests/test_scenario_contract_real_tree.py
- Makefile
role: implementer
tags: []
tracker_refs: []
---

# WP05 — Mutation, coverage and real-tree gates

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load the assigned profile with the `/spk-charter-profile-load` skill (profile `python-pedro`). Then load governance with `spec-kitty charter context --action implement`.

Read, in `kitty-specs/bdd-suite-skeleton-01M6GF8W/`:
- `spec.md`: SC-002 to SC-006, US1 and US2 independent tests, NFR-001 and NFR-004;
- `contracts/scenario-contract-check.md`: the section "Mutation tests (SC-004, SC-002)";
- the WP04 handoff: step phrases and promise ids.

## Objective

Prove that the suite cannot pass vacuously:
- **Mutations**: each pinned-verdict mutation fails exactly the scenarios that cover it.
- **Coverage**: a skipped, unregistered or removed fixture fails the run, and an added fixture is picked up.
- **Real tree**: the contract check is clean and non-empty on the real tree.

Then wire the check into `make lint` and measure NFR-001 and NFR-004.

## Branch Strategy

The planning base and the merge target are both `issue-197-bdd-suite-skeleton`. The workspace is the lane worktree from `lanes.json`:

```bash
spec-kitty agent action implement WP05 --agent <name> --mission bdd-suite-skeleton-01M6GF8W
```

## STOP conditions

- A mutation fails a scenario outside its expected set, or fails nothing. This is a real defect in WP04's binding; report it and do not weaken the expected set.
- The NFR-001 budget can only be met by dropping a required control.

## Subtasks

### T014 — `make lint`

In `Makefile`, add `uv run python scripts/scenario_contract.py` to the `lint` target, after the `docs_index.py --check` line. Then run `make lint`; it must be green.

### T019 — Mutation table and grouped pytester runs (SC-004)

- **File**: `tests/scenarios/test_pinned_verdict_mutations.py`. The repo does not enable `pytester` (there is no `pytest_plugins` in `tests/conftest.py`), and a non-root conftest cannot enable it. So run the inner suite with `pytest.main`, in-process:
  - call `pytest.main(["tests/scenarios/test_envelope.py", "-p", "no:cacheprovider", "-o", "addopts=", "-q"], plugins=[collector])`, where `collector` is a small object whose `pytest_runtest_logreport(report)` records `(report.nodeid, report.when, report.outcome)`;
  - set `SPEC_KITTY_SCENARIO_FIXTURES` with `monkeypatch.setenv`. The binding reads it at call time (WP04), so a shared `sys.modules` is safe;
  - if in-process runs prove flaky (module state leaking between runs), fall back to `subprocess.run([sys.executable, "-m", "pytest", ...])` with JUnit XML, and record the switch and its timing in the module docstring.
- **Temporary copy**: `shutil.copytree` of the package fixtures directory, from `importlib.resources.files("spec_kitty_events.conformance") / "fixtures"`, into `tmp_path`, once per run group (a module-scoped fixture copying from a pristine template).
- **The table**:

  | Promise | Mutation (in the tmp copy) | Expected failing scenarios |
  |---|---|---|
  | 001 | `envelope_valid_canonical/mission_created_baseline.json`: delete `input.build_id` | {001} |
  | 002 | one synthesized fixture: delete `input.event_id` | {002} |
  | 003 | one forbidden-key fixture: set `expected_error_code` to `UNKNOWN_LANE` | {003} |
  | 004 | one unknown-lane fixture: set the code to `FORBIDDEN_KEY` | {004} |
  | 005 | one payload-schema fixture: set the code to `ENVELOPE_SHAPE_INVALID` | {005} |
  | 006 | one shape fixture: set the code to `PAYLOAD_SCHEMA_FAIL` | {006} |
  | 007 | one historical fixture: flip the **register** entry `expected` from invalid to valid (spec SC-004) | {007} |
  | 008 | `skew_missing_version.json`: reverse `expected_error_codes` (a multi-code list; check it has ≥2 entries) | {008} |
  | 009 | `unknown_event_type.json`: set `expected_error_codes` to `["SCHEMA_VERSION_MISSING"]`, or any other code from the closed vocabulary | {008, 009} |
  | 010 | a lane-mapping valid fixture: change `canonical_lane` | {010} |

- **Groups**: mutations of disjoint classes share one run. 008 and 009 share a class, so put them in different runs. Two or three runs in total.
- For each run, assert that the set of failed scenario ids equals the union of the group's expected sets, and that each expected promise's scenario is among them. Map test names to promises with the scenario titles, or by reading the features' `@promise` tags.
- Also run once with **no** mutation and assert 10 passed. This control proves the copy and the environment variable work.

### T020 — Coverage cases (SC-002, US2)

These are separate runs, or combined into the groups above where the classes are disjoint.

1. **Unregistered extra file**: copy a canonical fixture to `envelope_valid_canonical/extra.json` without registering it. 001 fails in Arrange with a register/disk mismatch message.
2. **Removed registered file**: delete one forbidden-key fixture file. 003 fails.
3. **Added, correctly registered fixture**: copy a canonical fixture under a new name, and append a matching `classes.entries` row to the tmp `manifest.json`. 001 still passes. Then add a second fixture, registered but with a wrong pin; 001 fails. Together the two prove that an added fixture is evaluated without any feature-file edit.
4. **Unknown register id**: unit-test the binding's `select_id` helper, imported from `tests.scenarios.steps.envelope_steps`. That is allowed, because it is inside `tests/scenarios`. With an id that does not exist, it raises `pytest.fail.Exception`.

### T021 — Real-tree contract run (FR-012, SC-003)

Create `tests/test_scenario_contract_real_tree.py`. Import the checker the way `tests/test_changelog_fragments.py:21-22` imports `scripts/changelog.py`: `sys.path.insert(0, <repo>/scripts)`, then `import scenario_contract`. Make WP03's `tests/test_scenario_contract.py` use the same pattern. Then call `check()` with the defaults and assert:
- 0 error findings;
- at least 1 feature file and at least 10 distinct promise ids, using a small helper or the parse result the checker exposes. If the checker has no public discovery count, add an optional `stats` out-parameter to `check()`. WP03 owns `scripts/scenario_contract.py`, so making this change here is an out-of-map edit: record it with a one-line rationale.

### T022 — Timing, determinism and blast radius

- **NFR-001**: `time uv run pytest tests/scenarios tests/test_scenario_contract.py tests/test_scenario_contract_real_tree.py --no-cov -q` plus `time uv run python scripts/scenario_contract.py`. Together they must take under 15 s. Record the figures.
- **NFR-004**: run the scenario suite twice and diff the `-rA` outputs. They must be identical.
- **NFR-005 / SC-006**:
  - `git diff origin/main --stat -- src/spec_kitty_events/schemas src/spec_kitty_events/conformance/fixtures` must be empty;
  - `uv run pytest --pyargs spec_kitty_events.conformance -q` must give the same count as `main`.
- **Blast radius**: `make test-fast` and `make lint`. Record the commands and counts for the PR (§6).

## Definition of Done

- The mutation table is fully implemented, and each group's failing set is exact.
- The no-mutation control passes 10.
- The coverage cases pass.
- The real-tree check is clean, with ≥1 feature and ≥10 promises.
- `make lint` includes the check and is green.
- NFR-001, NFR-004 and NFR-005 evidence is recorded.

## Reviewer guidance

- Comment out one Assert step body in WP04's binding locally. At least one mutation group must then fail.
- Verify that the 008/009 group expectations match the contract note.
