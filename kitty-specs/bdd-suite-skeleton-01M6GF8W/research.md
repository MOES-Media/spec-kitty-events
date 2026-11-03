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

| Package | Version | Published | Licence | PyPI author/maintainer | Wheel | Notes |
|---|---|---|---|---|---|---|
| pytest-bdd | 9.0.0 | 2026-09-30 | MIT | Oleg Pidsadnyi, Anatoly Bubenkov; maintainer Alessio Bogon | pure | dev-only; held at 9.0.0 (9.0.1 is from 2026-10-31) |
| gherkin-official | as locked (42.0.1 latest, 2026-08-05) | — | MIT | Cucumber Ltd, Björn Rasmusson | pure | dev-only; parser |
| mako | 1.4.3 | 2026-09-22 | MIT | no author field on PyPI | pure | transitive |
| MarkupSafe | 3.0.4 | 2026-10-02 | BSD-3-Clause | no author field on PyPI | **native** (C speedups; pure fallback in the sdist) | transitive, through mako |
| parse | 1.22.4 | 2026-10-20 | MIT | no author field on PyPI | pure | transitive; exactly 14 days old at planning; if a newer release appears before locking, hold 1.22.4 |
| parse-type | 0.6.6 | 2025-08-11 (releases API) | MIT | Jens Engel (jenisys) | pure | transitive |
| six | 1.17.0 | 2024-12-04 | MIT | no author field on PyPI | pure | transitive, through parse-type |
| typing-extensions | already locked (4.16.0) | — | — | — | — | no change |

- **Controls**:
  - Every new package is dev-only. The wheel's base requirements, those without an `extra ==` marker, are unchanged; only `Provides-Extra: dev` gains entries. A build-metadata check verifies this (squad R-M2).
  - `uv.lock` records sha256 hashes for every artifact.
  - pytest-bdd is bounded at `<10`. gherkin-official takes pytest-bdd's own constraint and is held by the lock.
  - No install script or build hook is involved. Every package except MarkupSafe ships a pure-Python wheel; MarkupSafe ships platform wheels and a pure fallback.
- **Adversarial evidence**: no dependency here touches runtime or security-sensitive paths. The plan-phase squad is asked to challenge this table, and its dispositions are appended below.

## R-4 Core convention fidelity

Read on 2026-11-03 from core's `scripts/ci/scenario_contract.py`, `docs/development/testing/acceptance-scenarios.md` (§Tags) and `tests/scenarios/charter/PROMISES.md`.

- **Adopted unchanged**: the tag vocabulary (`@promise:<id>`, `@wip`, `@wip-owner:<handle>`, `@wip-since:<YYYY-MM-DD>`, `@manual`, `@defect:<n>`, `@qa:<ref>`, bare `[A-Za-z0-9][A-Za-z0-9_-]*`); the id character set `[A-Za-z0-9][A-Za-z0-9._-]*`; tag inheritance from `Feature`/`Rule`/`Examples`; the four PROMISES columns; the README steps table; core's problem codes, by name.
- **Strengthened, declared under D-2**:
  - Core checks a `@promise:` id only when the tag is present. Here every gating scenario must carry exactly one, and a missing tag is reported as BAD_PROMISE_ID.
  - The Binding column uses the closed vocabulary `python` | `python, jvm` | `@wip`, where core uses free text (`bound`, ...).
- **Also adopted after the post-plan squad**: NO_EXAMPLES (Scenario Outlines are allowed), BAD_DEFECT and BAD_QA_REF.
- **Not carried**: UNSUPPORTED_EXPRESSION, because an unread step-definition form shows up as UNBOUND_STEP; NO_STEP_DEFINITIONS and STEP_FILE_UNREADABLE, because a missing or unreadable steps directory is a usage error (exit 2).

## R-5 Check order of the envelope verdict

This is the order of the private dispatcher at branch point (`tests/test_conformance_classes.py:136-365`, helpers and dispatcher), which becomes contract in `contracts/class-fixture-verdict.md`:
1. wrapper is an object;
2. required envelope fields;
3. forbidden keys, recursively;
4. payload is an object;
5. lane vocabulary for `WPStatusChanged`;
6. `Event` model;
7. typed payload model for MissionCreated, MissionClosed and WPStatusChanged.

Lane-mapping inputs have their own order. A non-object input and a non-string `legacy_lane` both give `PAYLOAD_SCHEMA_FAIL`, with different paths.

## R-6 Required check reach

- `acceptance.yml` installs `.[dev,conformance]` and runs `pytest --cov --cov-report=xml` with `testpaths = ["tests"]`, so `tests/scenarios/test_*.py` is collected.
- `make test-fast` runs `uv run pytest --no-cov -q`, which uses the dependency group.
- Both lists of development dependencies (the group and the extra) must therefore gain the new packages (squad D-M3).

## R-7 Prior art for listing class fixtures

- `conformance/loader.py` serves only the legacy `fixtures` categories.
- `tests/test_fixture_determinism.py` (`CLASS_DIRS`) and `tests/test_conformance_classes.py` each list the class fixtures their own way.
- The step binding cannot reuse either one, because FORBIDDEN_TEST_IMPORT forbids importing `tests/` modules. Promoting a listing helper into the package would be a second new public symbol, which C-007 says to escalate.
- **Decision**: the binding keeps its own small loader inside `tests/scenarios/steps/`. Folding the three listers into one is recorded as a follow-up, not done here.

## Adversarial squad, post-plan (2026-11-03)

The delegates were profile-loaded and worked read-only:
- architect-alphonso: changes requested (2 MAJOR);
- researcher-robbie: rework (2 MAJOR);
- randy-reducer: proportionate (0 MAJOR).

No finding diverged: alphonso and robbie independently found the `build_id` omission.

| # | Finding | Disposition | Evidence |
|---|---|---|---|
| A-M1 | The moved module causes an import cycle through the package root | accepted | plan approach 1 (imports); `contracts/class-fixture-verdict.md` (Imports; fresh-interpreter test) |
| A-M2 | Accepting unknown class names creates a second verdict path | accepted | contract "Raises" |
| A-m1 / R-M1 | `build_id` missing from the required-field list | accepted | contract check 2; README-equals-tuple test |
| A-m2 | Tag-hook mechanics: the return value is discarded | accepted | plan approach 4 |
| A-m3 | Import site of the step fixtures unnamed | accepted | plan approach 3 (conftest import) |
| A-m4 | STEPS_TABLE_DRIFT normalisation too narrow | accepted | `contracts/scenario-contract-check.md` |
| A-m5 | pytester runs inherit `--cov`; the env var must be read at call time | accepted | contract "Mutation tests"; plan approach 3 |
| A-n1 | Planted bad import fails ruff | accepted | contract preamble; plan approach 6 |
| R-M2 | The dev extra changes wheel metadata, contradicting "Requires-Dist unchanged" | accepted | R-3 controls; plan approach 6 |
| R-m1 | R-3 table incomplete or unsupported (six, MarkupSafe, maintainers) | accepted | R-3 table |
| R-m2 | BAD_DEFECT and BAD_QA_REF missing; NO_EXAMPLES reason weak | accepted | contract rules (22); spec FR-011 and SC-003 |
| R-n1 | R-5 line range; lane-mapping paths differ | accepted | R-5 |
| R-m3 | Three listers of class fixtures | deferred_with_rationale | R-7: a fold needs a second public symbol (C-007); follow-up issue at PR time |
| R-m4 | ci.yml runs through an external `bin/ci-run.sh` | no change needed | `suite` is not a required check; `acceptance` and `make test-fast` are the gates (R-6) |
| X-1 | Parity-run-then-delete is ceremony | accepted | plan approach 1 (equivalence) |
| X-2 | gherkin `<43` cap is speculative | changed | the pin mirrors pytest-bdd's constraint; it is kept because the check imports gherkin directly |
| X-3 | Env-var seam | accepted (documented, read in one place) | plan approach 3; contract |
| X-4 | Mutation runs grouped by default | accepted | contract "Mutation tests"; plan Risks |
| X-5 | Core codes not carried, undocumented | accepted | contract "Not carried from core" |
| X-6 | Generate the steps table instead of a drift rule | deferred_with_rationale | the spec adopts core's hand-written table (FR-002); generating it is a follow-up proposal for both repos |
| X-7 | The "46 fixtures" arithmetic | accepted | plan Scale (34 = 26 + 8) |
| X-8 | The check-order table is duplicated between contract and README | accepted | the contract names the README as the single source once it lands |
