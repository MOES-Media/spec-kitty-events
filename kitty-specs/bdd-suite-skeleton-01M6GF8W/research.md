# Research: BDD suite skeleton and envelope scenarios

Phase 0 of the plan. Every unknown from the Technical Context is resolved here. The squad record for the spec is in `research/squad-post-specify.md`.

## R-1 Where the shared verdict lives

- **Decision**: a public `spec_kitty_events.conformance.class_fixture_verdict` (ruling R4, decision `01M6GG0TNP61KD4J3YP1AGKQDG`).
- **Rationale**: it is the only option that satisfies both FR-009 (public surface only) and FR-010 (one implementation). It also turns the check order into contract that a second binding can reproduce (squad A-M1 and A-M2).
- **Alternatives considered**:
  - a helper under `tests/` (rejected by the operator);
  - the step binding importing the test module (breaks FR-009);
  - a re-implementation (breaks FR-010).
- **Signature**: `class_fixture_verdict(fixture_class: str, fixture_input: object) -> ValidationError | None`. It reuses the existing public `validation_errors.ValidationError`, so no new result type is needed and only one symbol is added.

## R-2 Scenario runner and parser

- **Decision**: pytest-bdd 9.0.0 (R1). The contract check uses `gherkin-official` directly.
- **Rationale**:
  - pytest-bdd binds Gherkin to pytest, which is the repo's runner, so the suite joins `make test-fast` and `acceptance` with no new job.
  - pytest-bdd parses with `gherkin-official`. Using the same parser in the contract check means a file the check accepts is a file the runner can load.
  - Core's checker uses a hand-written line reader because core's runner is Cucumber-JVM. Here the official parser is already a transitive dependency.
- **Alternatives considered**:
  - `behave` (rejected: a second runner, not pytest, so not collected by `acceptance`);
  - porting core's line reader (rejected: about 300 lines duplicating a parser we already depend on);
  - pytest-bdd 8.1.0 (rejected: caps `gherkin-official<30` and is the older line);
  - 9.0.1 (rejected for now: published 2026-10-31, under two weeks old at planning time).

## R-3 Supply chain (DIRECTIVE_051, advisory)

| Package | Version | Published | Licence | Maintainer | Notes |
|---|---|---|---|---|---|
| pytest-bdd | 9.0.0 | 2026-09-30 | MIT | pytest-dev | dev-only; locked |
| gherkin-official | resolved by lock (≤42.x) | 42.0.1: 2026-08-05 | MIT | Cucumber org | dev-only; parser |
| mako | 1.4.3 | 2026-09-22 | MIT | Pallets/SQLAlchemy authors | transitive (pytest-bdd templates) |
| parse | 1.22.4 | 2026-10-20 | MIT | r1chardj0n3s | transitive; 14 days old at planning; if the lock resolves a newer one, hold it at 1.22.4 or an older 1.22.x |
| parse-type | 0.6.6 | 2025-08-11 | MIT | jenisys | transitive |

- **Controls**:
  - Every new package is dev-only. The published wheel's `Requires-Dist` is unchanged, which WP05 verifies with a build.
  - `uv.lock` records sha256 hashes for every artifact.
  - Version ranges are bounded (`<10`, `<43`).
  - No install script or build hook is involved; all are pure-Python wheels.
- **Adversarial evidence**: no dependency here touches runtime or security-sensitive paths. The plan-phase squad is asked to challenge this table, and its dispositions are appended below.

## R-4 Core convention fidelity

Read on 2026-11-03 from core's `scripts/ci/scenario_contract.py`, `docs/development/testing/acceptance-scenarios.md` (§Tags) and `tests/scenarios/charter/PROMISES.md`.

- **Adopted unchanged**: the tag vocabulary (`@promise:<id>`, `@wip`, `@wip-owner:<handle>`, `@wip-since:<YYYY-MM-DD>`, `@manual`, `@defect:<n>`, `@qa:<ref>`, bare `[A-Za-z0-9][A-Za-z0-9_-]*`); the id character set `[A-Za-z0-9][A-Za-z0-9._-]*`; tag inheritance from `Feature`/`Rule`/`Examples`; the four PROMISES columns; the README steps table; core's problem codes, by name.
- **Strengthened, declared under D-2**:
  - Core checks a `@promise:` id only when the tag is present. Here every gating scenario must carry exactly one, and a missing tag is reported as BAD_PROMISE_ID.
  - The Binding column uses the closed vocabulary `python` | `python, jvm` | `@wip`, where core uses free text (`bound`, ...).
- **Not adopted, because there is nothing for them to check in D1**: NO_EXAMPLES, UNSUPPORTED_EXPRESSION, NO_STEP_DEFINITIONS and STEP_FILE_UNREADABLE. An unsupported step-definition form shows up as UNBOUND_STEP. Folding a missing or unreadable steps directory into a usage error (exit 2) is a CLI concern.

## R-5 Check order of the envelope verdict

This is the order of the private dispatcher at branch point (`tests/test_conformance_classes.py:176-292`), which becomes contract in `contracts/class-fixture-verdict.md`:
1. wrapper is an object;
2. required envelope fields;
3. forbidden keys, recursively;
4. payload is an object;
5. lane vocabulary for `WPStatusChanged`;
6. `Event` model;
7. typed payload model for MissionCreated, MissionClosed and WPStatusChanged.

Lane-mapping inputs have their own three-step order.

## R-6 Required check reach

- `acceptance.yml` installs `.[dev,conformance]` and runs `pytest --cov --cov-report=xml` with `testpaths = ["tests"]`, so `tests/scenarios/test_*.py` is collected.
- `make test-fast` runs `uv run pytest --no-cov -q`, which uses the dependency group.
- Both lists of development dependencies (the group and the extra) must therefore gain the new packages (squad D-M3).
