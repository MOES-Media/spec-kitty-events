# Tasks: BDD suite skeleton and envelope scenarios

**Mission**: `bdd-suite-skeleton-01M6GF8W` · **Branch**: `issue-197-bdd-suite-skeleton` (planning base and merge target)
**Inputs**: `spec.md` (revision 2 plus the post-plan count updates), `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

Subtask completion is event-sourced: record it with `spec-kitty agent tasks mark-status Txxx --status done`. The rows below are references, not checkboxes.

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Add pytest-bdd and gherkin-official to the dev group and the `dev` extra; relock with pytest-bdd held at 9.0.0 | WP01 | |
| T002 | Verify wheel metadata: base requirements unchanged, only `extra == "dev"` entries added | WP01 | |
| T003 | Write the changelog fragment `docs/changelog/unreleased/197-bdd-suite-skeleton.md` | WP01 | [P] |
| T004 | Create `conformance/class_verdict.py` with `class_fixture_verdict` (submodule imports, `ValueError` on unknown class) | WP02 | |
| T005 | Export it from `conformance/__init__.py` | WP02 | |
| T006 | Make the private helpers in `tests/test_conformance_classes.py` delegate to it, with every assertion unchanged | WP02 | |
| T007 | Document the check order and fix the historical caveat in `conformance/README.md` | WP02 | [P] |
| T008 | Write `tests/test_class_fixture_verdict.py` (precedence, ValueError, identity, README-equals-tuple, fresh import) | WP02 | |
| T009 | Scaffold the contract-check script: CLI, Problem model, gherkin parsing, tag inheritance | WP03 | |
| T010 | Python step-source reader (AST), parse-pattern to regex, binding matcher (UNBOUND/AMBIGUOUS) | WP03 | |
| T011 | Structural and tag rules (core codes) | WP03 | |
| T012 | Events rules: UNREGISTERED_PROMISE, BAD_BINDING_DECLARATION, STEPS_TABLE_DRIFT, FORBIDDEN_TEST_IMPORT | WP03 | |
| T013 | 22 planted trees plus `tests/test_scenario_contract.py` (one code per tree) | WP03 | |
| T014 | Wire the check into the `make lint` target, once the real tree exists | WP05 | |
| T015 | Suite skeleton: `tests/scenarios/{__init__,conftest}.py`, tag hook, README index | WP04 | |
| T016 | Step binding: fixture registers, Arrange/Act/Assert steps, counting verdict wrapper | WP04 | |
| T017 | Envelope feature files (4 behaviours, 10 promises) and `envelope/PROMISES.md` | WP04 | |
| T018 | `tests/scenarios/test_envelope.py` entry point; suite green; README steps table complete | WP04 | |
| T019 | Mutation table and grouped pytester runs (SC-004) | WP05 | |
| T020 | Coverage cases: skipped, unregistered and removed fixture; an added fixture raises the call count (SC-002, US2) | WP05 | |
| T021 | Real-tree contract run: 0 errors, ≥1 feature, ≥10 promises (FR-012, SC-003) | WP05 | |
| T022 | Timing (NFR-001) and determinism (NFR-004) evidence; full blast-radius run | WP05 | |

## Phase 1 — Foundations

### WP01 — Dev dependencies and changelog (`tasks/WP01-dev-dependencies-and-changelog.md`)

- **Goal**: pytest-bdd and gherkin-official are available in both dev lists and locked, the published base requirements are proven unchanged, and the change is recorded.
- **Priority**: P1. Every other work package runs on these dependencies.
- **Independent test**: `uv sync` succeeds; `python -c "import pytest_bdd, gherkin"` works; the wheel metadata check passes.
- **Subtasks**:
  - T001 Add dev dependencies and relock (WP01)
  - T002 Verify wheel metadata (WP01)
  - T003 Changelog fragment (WP01)
- **Dependencies**: none.
- **Risks**: the lock resolves a too-new transitive version. Hold it as research R-3 says.

### WP02 — Public class-fixture verdict (`tasks/WP02-public-class-fixture-verdict.md`)

- **Goal**: R4. Move the dispatcher's behaviour into `spec_kitty_events.conformance.class_fixture_verdict`, document its check order, and keep the existing class test's assertions unchanged.
- **Priority**: P1. Requirements FR-010, FR-019, SC-005, C-001.
- **Independent test**: the class test passes unchanged; `tests/test_class_fixture_verdict.py` passes; the `--pyargs` gate is unchanged.
- **Subtasks**:
  - T004 Create `class_verdict.py` (WP02)
  - T005 Export (WP02)
  - T006 Test helpers delegate (WP02)
  - T007 README check order and caveat (WP02)
  - T008 New pins (WP02)
- **Dependencies**: none. It can run in parallel with WP01, because it needs no new package.
- **Risks**: the import cycle (squad A-M1); drift between README and code, which T008 pins.

## Phase 2 — Suite and its gate

### WP03 — Scenario contract check (`tasks/WP03-scenario-contract-check.md`)

- **Goal**: `scripts/scenario_contract.py` with 22 rules, each proven by a planted tree.
- **Priority**: P1. Requirements FR-011, FR-012 (planted half), SC-003 (planted half), C-004.
- **Independent test**: `uv run pytest tests/test_scenario_contract.py --no-cov` is green, and every planted tree reports exactly its own code.
- **Subtasks**:
  - T009 Scaffold, CLI and parsing (WP03)
  - T010 Python step reader and matcher (WP03)
  - T011 Core rules (WP03)
  - T012 Events rules (WP03)
  - T013 Planted trees and the test (WP03)
- **Dependencies**: WP01, for gherkin-official.
- **Risks**: the static reader and pytest-bdd's runtime binding can disagree. The reader fails safe: an unread form is UNBOUND_STEP.

### WP04 — Envelope scenarios and reference step binding (`tasks/WP04-envelope-scenarios-and-step-binding.md`)

- **Goal**: the `tests/scenarios/` tree with 10 `envelope/` promises, bound by Python against the public surface.
- **Priority**: P1. Requirements FR-001 to FR-009, FR-013 to FR-018, FR-020, SC-001.
- **Independent test**: `uv run pytest tests/scenarios --no-cov -q` runs 10 scenarios green, and the contract check is clean on the real tree.
- **Subtasks**:
  - T015 Skeleton and tag hook (WP04)
  - T016 Step binding (WP04)
  - T017 Features and PROMISES (WP04)
  - T018 Entry point and README steps (WP04)
- **Dependencies**: WP01 (pytest-bdd) and WP02 (the public verdict).
- **Risks**: step fixtures only reach the test modules if the conftest imports them, and unknown tags emit warnings if not consumed.

## Phase 3 — Proof

### WP05 — Mutation, coverage and real-tree gates (`tasks/WP05-mutation-coverage-and-real-tree-gates.md`)

- **Goal**: prove that the suite is not vacuous, by mutating pinned verdicts, planting skipped or unregistered fixtures, and running the real-tree contract check. Measure NFR-001 and NFR-004.
- **Priority**: P1. Requirements SC-002, SC-004, FR-012 (real-tree half), FR-021, NFR-001, NFR-004, NFR-005, SC-006.
- **Independent test**: `uv run pytest tests/scenarios/test_pinned_verdict_mutations.py tests/test_scenario_contract_real_tree.py --no-cov` is green, and the whole scenario plus contract set takes under 15 s.
- **Subtasks**:
  - T014 `make lint` (WP05)
  - T019 Mutation table and runs (WP05)
  - T020 Coverage cases (WP05)
  - T021 Real-tree run (WP05)
  - T022 Timing, determinism and blast radius (WP05)
- **Dependencies**: WP03 and WP04.
- **Risks**: the timing budget. Grouped runs with `--no-cov` are required.

## Parallelism and MVP

- WP01 and WP02 run in parallel, then WP03 and WP04 run in parallel, then WP05.
- **MVP**: WP02 plus WP04, the promises themselves. WP03 and WP05 make them trustworthy and are required for the spec.
