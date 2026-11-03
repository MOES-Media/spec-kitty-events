# Implementation Plan: BDD suite skeleton and envelope scenarios

**Branch**: `issue-197-bdd-suite-skeleton` | **Date**: 2026-11-03 | **Spec**: [spec.md](spec.md)
**Input**: Mission specification `kitty-specs/bdd-suite-skeleton-01M6GF8W/spec.md` (revision 2) and rulings R1–R4.

## Summary

This plan adds a Gherkin scenario suite under `tests/scenarios/`, a pytest-bdd reference step binding, a per-PR contract check, and ten `envelope/` promises.

The verdict that the class-taxonomy envelope fixtures pin today comes from a private dispatcher in `tests/test_conformance_classes.py`. Per R4, that dispatcher moves, unchanged in behaviour, into a public function `spec_kitty_events.conformance.class_fixture_verdict`. Its check order is documented as contract. The existing class test and the step binding both call that function. The contract check is a standalone script modelled on core's `scripts/ci/scenario_contract.py`; it uses core's rule codes, and its additions are declared as D-1/D-2. It runs in `make lint` and, through a pytest wrapper, in the required `acceptance` check.

## Technical Context

**Language/Version**: Python 3.10+ (package floor; `acceptance` runs 3.12)
**Primary Dependencies**:
- New dev dependency `pytest-bdd>=9.0,<10`, locked at 9.0.0. It brings `gherkin-official`, `mako`, `parse` and `parse-type`.
- Explicit dev dependency `gherkin-official>=29,!=31.0.0,!=32.0.0`, the same constraint pytest-bdd declares. It is listed because the contract check imports the parser directly.
- No runtime dependency change.

**Storage**: committed fixtures under `src/spec_kitty_events/conformance/fixtures/`, read-only
**Testing**: pytest (existing), pytest-bdd (new), `pytester` (built into pytest) for the verdict-mutation tests
**Target Platform**: Linux CI (`acceptance`), and contributors' machines through `make test-fast` and `make lint`
**Project Type**: single Python library plus repository-only test assets
**Performance Goals**: the scenario suite, the mutation tests and the contract check together take under 15 s (NFR-001)
**Constraints**:
- Additive: no existing schema, fixture, assertion or verdict changes.
- The suite is not shipped in the package.
- Nothing is imported from core, saas, tracker or runtime.
- No JVM and no Gradle change.

**Scale/Scope**:
- 10 promises over 4 feature files; 1 public function.
- 1 contract-check script with 22 rules, each with a planted example.
- 34 fixtures evaluated: 26 class-taxonomy entries plus 8 strict-journal files. The 26 are 4 canonical, 3 synthesized, 4 forbidden-key, 2 unknown-lane, 3 payload-schema, 2 shape, 5 historical and 3 lane-mapping.

## Charter Check

*GATE: checked before Phase 0 and again after Phase 1.*

| Charter rule | How this plan meets it | Status |
|---|---|---|
| Testing: pytest, hypothesis, schema drift checks, conformance validation for any contract change | The new public function is covered by the unchanged class test, a precedence test and the scenarios. No schema changes. | pass |
| Quality gates: pytest, schema generation check, `mypy --strict` before merge; `--pyargs` gate on every PR | The new module is in `src/` and typed strictly. The gate is run and recorded in the PR. | pass |
| Review policy: changes to envelopes, payloads, schema versioning or fixtures need a compatibility review | None of them change. The new public function is additive; COMPATIBILITY.md is checked for an "Added API" convention when WP01 is implemented. | pass |
| Performance: deterministic and efficient validation | The verdict function is the existing logic. Scenario selection is sorted by path (NFR-004). | pass |
| Deployment: ships as a library with committed schemas and fixtures | The function ships. The suite does not ship (C-003); `tests/` is not part of the wheel. | pass |
| Package boundary: no consumer imports | No consumer import is added. FORBIDDEN_TEST_IMPORT also guards the step binding against `tests/` imports. | pass |
| DIRECTIVE_051, supply chain | Recorded in `research.md` §R-3 (age, licence, maintainer, lock hashes). The base requirements are unchanged; only the `dev` extra gains entries. | pass, advisory |

Re-check after Phase 1: no new gaps.

## Project Structure

### Documentation (this mission)

```
kitty-specs/bdd-suite-skeleton-01M6GF8W/
├── spec.md, plan.md, research.md, data-model.md, quickstart.md
├── contracts/
│   ├── class-fixture-verdict.md     # public function contract + check order
│   └── scenario-contract-check.md   # CLI, rule codes, step-definition sources
└── research/squad-post-specify.md
```

### Source code (repository root)

```
src/spec_kitty_events/conformance/
├── class_verdict.py              # NEW: class_fixture_verdict() (moved from tests, R4)
├── __init__.py                   # export class_fixture_verdict
└── README.md                     # NEW section "Envelope verdict check order"; caveat list fixed

tests/test_conformance_classes.py # private helpers replaced by a thin shim over the public
                                  # function; every assertion untouched
tests/test_class_fixture_verdict.py  # NEW: precedence pin (FR-019) + identity (SC-005)

scripts/scenario_contract.py      # NEW: contract check (python -m / make lint)
tests/test_scenario_contract.py   # NEW: real tree clean & non-empty; one planted tree per rule
tests/fixtures/scenario_contract/<rule-code>/...   # NEW: planted broken trees

tests/scenarios/
├── README.md                     # index: layout, tags, steps table, how to run
├── __init__.py, conftest.py      # tag handling (@wip skip, markers), fixture-root override
├── steps/__init__.py
├── steps/envelope_steps.py       # reference step binding (public package surface only)
├── test_envelope.py              # scenarios("envelope") entry point (FR-020)
├── test_pinned_verdict_mutations.py  # SC-002 / SC-004 via pytester over a tmp fixture copy
└── envelope/
    ├── PROMISES.md
    ├── accepts-valid-envelopes/accepts-valid-envelopes.feature        # 001, 002
    ├── refuses-with-pinned-reason/refuses-with-pinned-reason.feature  # 003–007
    ├── strict-journal-profile/strict-journal-profile.feature          # 008, 009
    └── resolves-legacy-lanes/resolves-legacy-lanes.feature            # 010

pyproject.toml, uv.lock           # dev deps (group + `dev` extra)
Makefile                          # lint: + scenario contract check
docs/changelog/unreleased/197-bdd-suite-skeleton.md   # section: Added
```

**Structure Decision**:
- The contract check is a top-level `scripts/` tool, matching the repo's `scripts/changelog.py` and `scripts/docs_index.py`, and core's `scripts/ci/`.
- The step binding sits inside `tests/scenarios/`, so FORBIDDEN_TEST_IMPORT can allow `tests.scenarios.*` and refuse every other `tests.*` import.

## Approach (key decisions; rationale in research.md)

1. **Public verdict (R4, FR-010, FR-019).** The private dispatcher's *behaviour* moves into `conformance/class_verdict.py` as `class_fixture_verdict(fixture_class: str, fixture_input: object) -> ValidationError | None`. The helpers it needs move with it, as module-private names, and it returns `None` for an accepted input.
   - **Imports**: the module imports only from defining submodules: `spec_kitty_events.status`, `.lifecycle`, `.forbidden_keys`, `.models` and `.validation_errors`. It never imports from the package root, because `spec_kitty_events/__init__` → `strict` → `conformance.validators` → `conformance/__init__` would otherwise hit a partially initialised root (squad A-M1, reproduced).
   - **Class names**: a name outside the eight taxonomy classes raises `ValueError`, including `envelope_strict_journal`, which keeps its own public validator (squad A-M2).
   - **The existing test** keeps its name, its `_ValidationOutcome` type and every assertion. Only the bodies of `_validate_envelope`, `_validate_lane_mapping` and `_validate_for_class` become one-line delegations, and `_classify_pydantic_error` moves. `git diff` shows no change to any `assert`.
   - **Equivalence** rests on two things: the unchanged class test passes over all 26 entries, and the moved function bodies are identical apart from imports, as `git diff -M` shows.
   - **New pins** (`tests/test_class_fixture_verdict.py`): precedence, `ValueError` on an unknown class, identity of the delegation target, README field list equals the implementation's tuple, and a fresh-interpreter import of the package.
2. **Scenario wording is technology-agnostic (C-004).**
   - Inputs are named by class or register id in double quotes: `Given the conformance fixtures of class "envelope_invalid_shape"`. That shape binds as pytest-bdd `parsers.parse('... "{fixture_class}"')` today and as a Cucumber `{string}` in D3.
   - Codes appear only as contract vocabulary, for example `"UNKNOWN_EVENT_TYPE"`.
3. **Step binding (FR-006–FR-009).**
   - The Arrange step loads the class's register (`classes.entries` for the eight classes; the top-level `fixtures` array filtered by path prefix for `envelope_strict_journal`). It globs the class folder on disk and fails on a mismatch or on an empty selection (FR-008).
   - The Act step calls the public verdict function, or `validate_strict_envelope`, once per fixture through a counting wrapper. It collects every outcome without short-circuiting.
   - The Assert steps compare each outcome with the fixture's pin, report every mismatch together, and finish with `Then every fixture of the class was evaluated`. That step compares the call count with the independent disk glob (SC-002).
   - Fixtures are read from the installed package through `importlib.resources`. The test-only environment variable `SPEC_KITTY_SCENARIO_FIXTURES` overrides the root. It is read in one place, the Arrange step, at call time, because in-process `pytester` runs share `sys.modules`. The step module is imported by `tests/scenarios/conftest.py`, which makes its step fixtures visible to the test modules in that folder. pytest-bdd binds steps through module namespaces, and `pytest_plugins` is not allowed in a non-root conftest.
4. **Tags (FR-003/FR-004).** `conftest.py` implements `pytest_bdd_apply_tag`. pytest-bdd 9 discards the hook's return value, so the hook marks the function in place and returns `True` for every tag the contract allows; anything else falls through to `pytest.mark` and warns. `@wip` becomes a skip marker with reason `wip`, and `@manual` is skipped. `promise:`, `qa:`, `defect:`, `wip-owner:` and `wip-since:` are consumed without registering pytest markers, so the run gives no unknown-mark warnings. The contract check, not pytest, validates the grammar.
5. **Contract check (FR-011/FR-012).**
   - It parses feature files with `gherkin-official`, the same parser pytest-bdd uses, so the two cannot disagree on what parses.
   - It reads Python step definitions statically with `ast`: decorators `given`/`when`/`then` from `pytest_bdd`, with either a string literal or `parsers.parse("<literal>")`. The `parse` fields `{name}` and `{name:fmt}` are translated to regular expressions, and stacked decorators are each read.
   - Any other form leaves its steps unbound, so they fail loudly as UNBOUND_STEP, as core's matcher does.
   - Sources are passed as `--steps python=<dir>`. The parser registry is keyed by binding name, so D3 adds `jvm` by porting core's `_JAVA_STEP_RE`. In D1, any `jvm` claim is BAD_BINDING_DECLARATION.
   - Exit status is 1 on any error.
   - `tests/test_scenario_contract.py` runs the check over the real tree, asserting 0 errors, at least 1 feature and at least 10 promises, and over each planted tree, asserting exactly that tree's one code.
6. **Wiring (FR-020/FR-021).**
   - `pyproject.toml` gains pytest-bdd and gherkin-official in the `dev` dependency group and in the `[project.optional-dependencies].dev` extra; `acceptance` installs that extra. The wheel's base requirements are unchanged; only `Provides-Extra: dev` gains entries, which a build-metadata check verifies (squad R-M2).
   - Planted contract-check trees are valid, ruff-clean Python. A deliberately bad import carries `# noqa: F401`.
   - `uv.lock` is regenerated, with pytest-bdd held at 9.0.0.
   - The `make lint` target gains `uv run python scripts/scenario_contract.py`.
   - `make test-fast` and `acceptance` already collect `tests/`. The suite is collected through `tests/scenarios/test_*.py`.

## Implementation Concern Map

| Concern | Requirements | Depends on |
|---|---|---|
| C1 Public class-fixture verdict, docs, test shim | FR-010, FR-019, SC-005, C-001 | — |
| C2 Contract check script, planted trees, wrapper test | FR-011, FR-012, SC-003 | — (it reads the step binding statically, but its planted trees have their own steps) |
| C3 Suite skeleton, envelope features, registers, reference step binding | FR-001–FR-009, FR-013–FR-018, SC-001 | C1 |
| C4 Mutation and coverage tests | SC-002, SC-004, US2 | C3 |
| C5 Wiring: dependencies, lock, Makefile, changelog fragment; the real-tree contract run goes green | FR-020–FR-022, NFR-001 | C2, C3 |

C1 and C2 can run in parallel. C3 needs C1, C4 needs C3, and C5 closes.

## Risks

- **The moved code diverges from the private code.** Mitigated by the parity run plus the unchanged class test (approach 1).
- **pytest-bdd tag handling changes in a minor release.** Mitigated by pinning `<10` and holding the lock at 9.0.0. The `pytest_bdd_apply_tag` hook has been stable since 4.x.
- **gherkin-official major bumps.** The lock pins the exact version, and pytest-bdd and the contract check share that one parser.
- **NFR-001 budget.** Mutation runs are grouped by disjoint class from the start, with inner runs given `-o addopts= --no-cov` so they skip coverage. Promises 008 and 009 share a class, which `contracts/scenario-contract-check.md` accounts for.
