# Mission Specification: BDD suite skeleton and envelope scenarios

**Mission**: `bdd-suite-skeleton-01M6GF8W`
**Target branch**: `issue-197-bdd-suite-skeleton`
**Created**: 2026-11-03
**Status**: Draft
**Input**: Issue spec-kitty/spec-kitty-events#197 (slice D1 of #121), with the operator's rulings of 2026-11-03 (runner, location, slicing). The Intent Summary below was confirmed by decision `01M6GF9NRFWPG5169D01F350NT`.

Closes spec-kitty/spec-kitty-events#197. Refs #121 (parent, scope D), #117 (epic). Follow-up slices: #198 (D2), #199 (D3). Docs: #122 (E).

## Intent Summary

- **Primary actor**: a maintainer of a binding of the event contract. Today that is the Python reference package. Next is the Java binding, and later any other language. A second actor is the per-PR CI, which must keep the suite honest.
- **Trigger**: the contract's shared behaviour exists only as Python tests over committed fixtures. There is no `.feature` file in the repo, so a second binding has nothing language-neutral to prove itself against.
- **Desired outcome**: a scenario suite that describes the contract in plain language, bound once in Python, kept well formed by a per-PR check, and starting with envelope acceptance and refusal. It mirrors core's scenario conventions so the programme shares one style.
- **Rule that must always hold**: the scenarios name fixtures and never copy them. The verdict a scenario checks is the one the committed fixture pins. The committed schemas and fixtures stay the single source of truth, and a scenario that selects no fixtures fails instead of passing vacuously.
- **Operator rulings (2026-11-03)**:
  - **R1, runner.** A Python BDD runner (pytest-bdd) is the reference binding and binds every step. A Cucumber-JVM binding of a subset follows in D3 (#199).
  - **R2, location.** The suite lives in the repository under `tests/scenarios/` and is not shipped in the package.
  - **R3, slicing.** D1 is this mission. Ledger and replay are D2 (#198). Upcast, compatibility and the JVM binding are D3 (#199).
- **Reference conventions**: core's `tests/scenarios/**` layout, `@promise:` and `@wip` tags, `PROMISES.md`, `README.md` steps table, and its per-PR scenario contract check (`scripts/ci/scenario_contract.py`, `tests/architectural/test_scenario_contract.py`), read from a sibling checkout on 2026-11-03.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A binding maintainer proves envelope behaviour against shared scenarios (Priority: P1)

A maintainer runs the envelope scenarios and gets a definite pass or fail for each promise. Covered: canonical envelopes are accepted; invalid ones are refused with the reason their fixture pins; an unknown event type is refused; legacy lane strings resolve as pinned.

**Why this priority**: this is the first behaviour any binding must share, and it is the point of the suite.

**Independent Test**: run the suite through the Python binding. Every envelope scenario passes. Changing the pinned code of one invalid fixture in a scratch copy makes its scenario fail.

**Acceptance Scenarios**:

1. **Given** the canonical envelope fixtures, **When** each is validated, **Then** each is accepted.
2. **Given** the envelope fixtures pinned as refused for a forbidden key, an unknown lane, a payload schema failure or a bad shape, **When** each is validated, **Then** each is refused with exactly the code its fixture pins.
3. **Given** the strict-journal fixture whose event type is not registered, **When** it is validated under the strict profile, **Then** it is refused as an unknown event type.
4. **Given** the legacy lane-mapping fixtures, **When** each legacy lane is resolved, **Then** it resolves, or is refused, exactly as pinned.

---

### User Story 2 - A new fixture is covered without editing any scenario (Priority: P1)

A contract author adds a fixture to a class an envelope scenario already covers. The suite picks it up on the next run, with no change to any feature file.

**Why this priority**: this is what keeps the fixtures, not the scenarios, the single source of truth.

**Independent Test**: in a scratch copy, add a fixture to a covered class. The suite's count of evaluated fixtures rises by one, and the run fails if that fixture's pinned verdict is wrong.

**Acceptance Scenarios**:

1. **Given** a covered class gains one fixture, **When** the suite runs, **Then** that fixture is evaluated and its pinned verdict is checked.
2. **Given** a scenario names a class with no fixtures, or a manifest entry that does not exist, **When** the suite runs, **Then** that scenario fails.

---

### User Story 3 - CI refuses a malformed suite (Priority: P1)

A contributor's PR adds or changes a scenario. The per-PR check refuses the PR if the suite is malformed:
- a step has no binding;
- a feature file does not parse, or has no scenarios or no steps;
- a promise id is malformed or duplicated;
- a draft scenario lacks its owner or start date;
- an area has not declared which bindings cover it.

**Why this priority**: without it the suite decays into prose; core relies on the same gate.

**Independent Test**: run the check over the real suite (it passes), then over one deliberately broken example per rule (each fails with that rule's code).

**Acceptance Scenarios**:

1. **Given** the real suite, **When** the check runs, **Then** it reports no errors.
2. **Given** a planted feature file that breaks exactly one rule, **When** the check runs over it, **Then** it reports that rule's code and only that one.

---

### User Story 4 - A reader finds the steps and promises without reading code (Priority: P2)

A maintainer about to bind the suite in another language reads the suite's index. It lists every step phrase, grouped by Arrange, Act and Assert, and the promise register, which maps each promise id to the requirement it evidences.

**Why this priority**: this is what lets the D3 Java binding, and any later binding, start from documents instead of Python code.

**Independent Test**: every step phrase used in a feature file appears in the steps table. Every promise tag used appears in the promise register, and the register lists no promise that is unused.

**Acceptance Scenarios**:

1. **Given** the suite index and the promise register, **When** they are compared with the feature files, **Then** the step phrases and promise ids match exactly in both directions.

### Edge Cases

- **Raw historical rows.** The `historical_row_raw` class pins an ideal code that today's validator does not always emit; this caveat is documented in the conformance README. Its scenario asserts refusal only. It must not claim the ideal code is emitted, and it must not be dropped.
- **A class whose fixtures pin an ordered list of codes** (the strict profile) is compared against the whole ordered list, not just its first code.
- **A forbidden key at depth ten or more, or inside an array element,** is still refused as a forbidden key; it is not masked by an earlier shape error.
- **A feature file with only `@wip` scenarios** still passes the structural rules. A `@wip` scenario is excluded from the gating run, but it is never excluded from the contract check.
- **The fixture manifest and the folder of a class disagree** (a file on disk is not registered, or an entry has no file). The suite fails rather than silently evaluating one of the two.
- **The pinned error-code vocabulary gains a new code.** The scenarios keep passing unchanged, because the code comes from the fixture, not from the scenario text.

## Domain Language

| Term | Meaning | Avoid |
|---|---|---|
| Scenario suite | The tree of Gherkin feature files under `tests/scenarios/` | "BDD tests", "acceptance tests" (acceptance is a CI check name here) |
| Area | A top-level folder of the suite, one per contract surface (e.g. `envelope/`) | "module" |
| Behaviour | A sub-folder of an area holding one feature file named after it | — |
| Promise | One observable guarantee of the contract, tagged `@promise:PR-EVENTS-<AREA>-NNN` on exactly one scenario | "test case" |
| Binding | The step definitions that connect step phrases to one language's implementation | "glue", "runner" (the runner executes a binding) |
| Reference binding | The Python binding; it binds every step | — |
| Pinned verdict | The outcome a fixture declares: valid, or invalid with its error code or ordered codes | "expected result" when ambiguous |
| Contract check | The per-PR structural check over the suite, with no JVM | "lint" |

## Requirements *(mandatory)*

### Functional Requirements

| ID | Requirement | Status | Delivery | No-op passable? |
|---|---|---|---|---|
| FR-001 | The suite MUST live under `tests/scenarios/`, with one folder per area and one folder per behaviour inside it, holding one feature file named after the behaviour, mirroring core's layout. | Accepted | [build] | no |
| FR-002 | The suite MUST have an index (`tests/scenarios/README.md`) whose steps table lists every step phrase grouped by Arrange, Assume, Act and Assert, and a promise register (`tests/scenarios/PROMISES.md`) mapping every promise id to the requirement it evidences. | Accepted | [build] | no |
| FR-003 | Every scenario MUST carry exactly one promise tag `@promise:PR-EVENTS-<AREA>-NNN`, where AREA is the upper-cased area name and NNN is three digits. Promise ids MUST be unique across the suite. | Accepted | [build] | no |
| FR-004 | A draft scenario MUST be tagged `@wip` together with an owner and a start date, using core's tag grammar. Draft scenarios MUST NOT gate the scenario run, and MUST still pass the contract check. | Accepted | [build] | no |
| FR-005 | Each area MUST declare which bindings cover it, as the reference binding only or also the JVM binding, in a form the contract check can read. In D1, `envelope/` declares the reference binding only. | Accepted | [build] | no |
| FR-006 | Every step that selects inputs MUST select them by fixture class or by manifest entry id. No feature file may contain an envelope, a payload or any other fixture content. | Accepted | [build] | no |
| FR-007 | For each selected fixture, the binding MUST check the verdict the fixture pins: acceptance, or refusal with its exact error code, or its exact ordered list of codes. | Accepted | [build] | no |
| FR-008 | A step that selects zero fixtures MUST fail the scenario. This covers an empty or missing class and an unknown manifest id. It MUST also fail when a class's registered entries and its files on disk disagree. | Accepted | [build] | no |
| FR-009 | The reference binding MUST bind every step phrase in the suite. It MUST reach the contract only through the installed package's public surface and the committed fixtures, never through repository test modules. | Accepted | [build] | no |
| FR-010 | The verdict the binding computes for a class-taxonomy fixture MUST come from one implementation shared with the existing class conformance test, so the two cannot disagree. | Accepted | [build] | no |
| FR-011 | A per-PR contract check that needs no JVM MUST refuse the suite if any of these holds: a feature file does not parse, or has no scenarios or no steps; a step phrase has no binding in the reference binding; a promise tag is malformed or duplicated; a `@wip` scenario lacks its owner or start date, or they are malformed; an area lacks its binding-coverage declaration; or the index or promise register disagrees with the feature files (FR-002). | Accepted | [build] | no |
| FR-012 | Each FR-011 rule MUST have a planted broken example on which the check reports that rule's code. The real suite MUST report no errors. | Accepted | [build] | no — each planted example is the negative control |
| FR-013 | Envelope acceptance: the canonical envelopes and the envelopes synthesized from historical rows MUST each be accepted (`PR-EVENTS-ENVELOPE-001`, `-002`). | Accepted | [build] | no |
| FR-014 | Envelope refusal with a pinned code: the forbidden-key (at every depth, and inside arrays), unknown-lane, payload-schema and bad-shape fixtures MUST each be refused with exactly their pinned code (`PR-EVENTS-ENVELOPE-003`…`-006`). | Accepted | [build] | no |
| FR-015 | Raw historical rows MUST be refused. The scenario asserts refusal only, honouring the documented caveat on the ideal code (`PR-EVENTS-ENVELOPE-007`). | Accepted | [build] | no |
| FR-016 | Fail closed: an envelope whose event type is not registered MUST be refused as an unknown event type under the strict profile (`PR-EVENTS-ENVELOPE-008`). | Accepted | [build] | no |
| FR-017 | Legacy lane mapping: each legacy lane fixture MUST resolve to its pinned canonical lane, or be refused with its pinned code (`PR-EVENTS-ENVELOPE-009`). | Accepted | [build] | no |
| FR-018 | The scenario run and the contract check MUST run in the implementer fast baseline (`make test-fast`) and in at least one check that is required on `main`. | Accepted | [build] | no |
| FR-019 | The change MUST be recorded in one changelog fragment under `docs/changelog/unreleased/`, and `[Unreleased]` MUST NOT be hand-edited. | Accepted | [build] | no |

### Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|---|---|---|---|
| NFR-001 | The scenario run is fast enough for every PR | The whole suite plus the contract check completes in under 15 s on a CI runner | Accepted |
| NFR-002 | The packaged conformance gate is unchanged | `uv run pytest --pyargs spec_kitty_events.conformance`: same pass count as on `main` at branch point, 0 failures | Accepted |
| NFR-003 | Static quality | `ruff check .`, `ruff format --check .` and `mypy --strict` on any new package code report 0 issues | Accepted |
| NFR-004 | Deterministic | Two consecutive runs give identical per-scenario results and identical evaluated-fixture counts | Accepted |
| NFR-005 | Additive diff | 0 changed bytes in committed schemas and fixtures; 0 changed accept/refuse verdicts across the existing test suite | Accepted |

### Constraints

| ID | Constraint | Status |
|---|---|---|
| C-001 | Additive only. No schema, fixture or validator changes what it accepts or refuses. | Binding |
| C-002 | No import of spec-kitty (core), spec-kitty-saas, spec-kitty-tracker or spec-kitty-runtime. | Binding |
| C-003 | The suite is not shipped in the package's distributions (R2). | Binding |
| C-004 | Feature-file text is technology-agnostic: no Python, Java or library identifiers in step phrases. | Binding |
| C-005 | No JVM binding and no Gradle change in D1 (R3). | Binding |
| C-006 | Out of scope: ledger and replay (D2, #198); upcast, compatibility and the JVM binding (D3, #199); documentation-site changes (E, #122). | Binding |
| C-007 | Escalate instead of deciding: a new public package symbol, an edit to an existing test's expectations, any fixture edit, or a deviation from core's conventions beyond renaming. | Binding |
| C-008 | Exactly one adversarial-squad review on the PR. The conformance gate runs on the PR. | Binding |

### Key Entities

- **Feature file**: one behaviour; scenarios with Arrange/Act/Assert steps; tags.
- **Promise**: id `PR-EVENTS-<AREA>-NNN`, owning scenario, requirement it evidences.
- **Area coverage declaration**: area name, and the bindings that cover it.
- **Fixture selector**: a fixture class name or a manifest entry id.
- **Pinned verdict**: `valid`, or `invalid` with one error code or an ordered list of codes.
- **Contract-check finding**: rule code, file, line, severity.

## Success Criteria *(mandatory)*

- **SC-001**: 9 of 9 envelope promises have a scenario that passes through the reference binding. — [build] · no-op passable: no
- **SC-002**: 100% of the fixtures in the classes those promises cover are evaluated, and the evaluated count equals the number of registered entries for those classes. — [build] · no-op passable: no
- **SC-003**: 100% of the contract-check rules fail their planted example, and the real suite passes with 0 errors. — [build] · no-op passable: no
- **SC-004**: Mutating one fixture's pinned verdict in a scratch copy makes exactly the scenario covering it fail (1 of 1 sampled per promise). — [build] · no-op passable: no
- **SC-005**: 0 existing fixtures or schemas change, and the packaged conformance gate's result is identical to `main`'s. — [ratchet] · no-op passable: yes — positive control: SC-001 requires new scenarios to exist and pass

## Assumptions

- The promise-id area token is the upper-cased area folder name, `ENVELOPE` for `envelope/`, following core's `PR-<OFFERING>-<AREA>-NNN` shape with `EVENTS` as the offering.
- Core's `@wip` grammar (owner and since-date tags) is adopted as-is. The plan records the exact tag spellings after reading core's checker.
- The required check that will run the suite is `acceptance`, which already runs the repository's pytest tree. `ci.yml`'s `suite` is not a required check.
- How FR-010's shared verdict is reached (a packaged helper, or the test reusing the binding's code) is a plan decision bounded by C-007. A new public symbol needs escalation.
