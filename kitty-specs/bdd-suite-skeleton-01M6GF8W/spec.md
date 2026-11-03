# Mission Specification: BDD suite skeleton and envelope scenarios

**Mission**: `bdd-suite-skeleton-01M6GF8W`
**Target branch**: `issue-197-bdd-suite-skeleton`
**Created**: 2026-11-03
**Status**: Draft (revision 2, after the post-specify adversarial squad)
**Input**: Issue spec-kitty/spec-kitty-events#197 (slice D1 of #121) and the operator's rulings of 2026-11-03.
- The Intent Summary was confirmed by decision `01M6GF9NRFWPG5169D01F350NT`.
- Ruling R4 was recorded by decision `01M6GG0TNP61KD4J3YP1AGKQDG`.
- Squad findings and their dispositions: `research/squad-post-specify.md`.

Closes spec-kitty/spec-kitty-events#197. Refs #121 (parent, scope D), #117 (epic). Follow-up slices: #198 (D2), #199 (D3). Docs: #122 (E).

## Intent Summary

- **Primary actor**: a maintainer of a language binding of the event contract. Today that is the Python reference package. Next is the Java binding, and later any other language. A second actor is the per-PR CI, which must keep the suite honest.
- **Trigger**: the contract's shared behaviour exists only as Python tests over committed fixtures, and there is no `.feature` file in the repo. The order in which an envelope's checks run decides which error code a fixture pins. That order exists only in a private function of a test module, so a second binding has nothing it can reproduce.
- **Desired outcome**: a scenario suite that describes the contract in plain language, step-bound once in Python, kept well formed by a per-PR check, and starting with envelope acceptance and refusal. It adopts core's scenario conventions as they are. The envelope verdict, and the check order behind it, become a public, documented part of the conformance package.
- **Rule that must always hold**: the scenarios name fixtures and never copy them. The verdict a scenario checks is the one the committed fixture pins, computed by the same public function the existing class test uses. A scenario that selects no fixtures, or skips one, fails instead of passing vacuously.
- **Operator rulings (2026-11-03)**:
  - **R1, runner.** A Python BDD runner (pytest-bdd) is the reference step binding and binds every step. A Cucumber-JVM step binding of a subset follows in D3 (#199).
  - **R2, location.** The suite lives in the repository under `tests/scenarios/` and is not shipped in the package.
  - **R3, slicing.** D1 is this mission. Ledger and replay are D2 (#198). Upcast, compatibility and the JVM binding are D3 (#199).
  - **R4, verdict home.** The class-taxonomy envelope verdict is promoted to a public function of `spec_kitty_events.conformance`, with its check order documented as contract. This is an additive public symbol, released as a minor version.
- **Reference conventions (adopted as is)**: core's layout under `tests/scenarios/**`, its closed tag vocabulary (`@promise:`, `@wip` with `@wip-owner:` and `@wip-since:`, `@qa:`, `@defect:`, `@manual`), its per-area `PROMISES.md`, its `README.md` steps table, and its contract-check rule codes. They were read from a sibling checkout on 2026-11-03: `tests/scenarios/README.md`, `tests/scenarios/charter/PROMISES.md`, `scripts/ci/scenario_contract.py`, `tests/architectural/test_scenario_contract.py` and `docs/development/testing/acceptance-scenarios.md`.
- **Declared deviations from core** (consequences of R1 and of this repo; all other conventions are adopted unchanged):
  - **D-1.** The contract check reads Python step definitions where core reads Java. It is built to accept more than one step-definition source, so D3 adds the Java source without reworking it.
  - **D-2.** The check adds rules core does not have, named in FR-011 under new codes. These cover the promise register's `Binding` column, drift between the README and register and the feature files, and the reference binding importing repository test modules.
- **Scope honesty**: `envelope/` is bound by the Python step binding only, by design. The Java binding validates CloudEvents rows (`CloudEventValidator`: `type`, `source`, `missionid`, with its own issue codes), not legacy `Event` envelopes, so it cannot bind these promises. JVM coverage starts with `upcast/` in D3.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A binding maintainer proves envelope behaviour against shared scenarios (Priority: P1)

A maintainer runs the envelope scenarios and gets a definite pass or fail for each promise:
- canonical envelopes, and envelopes synthesized from historical rows, are accepted;
- invalid envelopes are refused with the code their fixture pins;
- raw historical rows are refused;
- the strict journal profile refuses with the ordered codes its fixtures pin, including an unknown event type, which fails closed;
- legacy lane strings resolve as pinned.

**Why this priority**: this is the first behaviour any binding must share, and it is the point of the suite.

**Independent Test**: a committed test, over a copy of the fixtures in a temporary folder, changes one pinned verdict per promise and shows that exactly the covering scenario fails.

**Acceptance Scenarios**:

1. **Given** the canonical envelope fixtures, **When** each is validated, **Then** each is accepted.
2. **Given** each fixture of the forbidden-key, unknown-lane, payload-schema and bad-shape classes, **When** it is validated, **Then** it is refused with exactly the code it pins.
3. **Given** the strict-journal fixtures, **When** each is validated under the strict profile, **Then** each is accepted, or refused with exactly the ordered list of codes it pins.
4. **Given** the strict-journal fixture whose event type is not registered, **When** it is validated under the strict profile, **Then** it is refused as an unknown event type.
5. **Given** the legacy lane-mapping fixtures, **When** each legacy lane is resolved, **Then** it resolves, or is refused, exactly as pinned.

---

### User Story 2 - A new fixture is covered without editing any scenario, and none is skipped (Priority: P1)

A contract author adds a fixture to a class an envelope scenario already covers. The suite picks it up on the next run with no change to any feature file. A fixture that is registered but never reaches the verdict fails the run.

**Why this priority**: this is what keeps the fixtures, not the scenarios, the single source of truth.

**Independent Test**: committed tests over a temporary copy cover three cases:
- adding a fixture raises the number of verdict calls by one;
- a selection that skips one fixture fails;
- a class whose register and folder disagree fails.

**Acceptance Scenarios**:

1. **Given** a covered class gains one fixture, **When** the suite runs, **Then** the verdict function is called once more, and that fixture's pinned verdict is checked.
2. **Given** a scenario that names a class with no fixtures, or a manifest id that does not exist, **When** the suite runs, **Then** that scenario fails.
3. **Given** a class's registered entries and its files on disk disagree, **When** the suite runs, **Then** the covering scenario fails.

---

### User Story 3 - CI refuses a malformed suite (Priority: P1)

A contributor's PR adds or changes a scenario. The per-PR check refuses it if the suite breaks any rule listed in FR-011.

**Why this priority**: without it the suite decays into prose; core relies on the same gate.

**Independent Test**: run the check over the real suite and over one planted broken example per rule. The real suite is non-empty and clean. Each planted example reports that rule's code.

**Acceptance Scenarios**:

1. **Given** the real suite, **When** the check runs, **Then** it reports no errors, and it discovers at least one feature file and every promise listed in the registers.
2. **Given** a planted feature tree that breaks exactly one rule, **When** the check runs over it, **Then** it reports that rule's code and no other error.

---

### User Story 4 - A reader finds the steps and promises without reading code (Priority: P2)

A maintainer about to bind the suite in another language reads two documents. The suite index lists every step phrase, grouped Arrange, Assume, Act and Assert. Each area's promise register lists each promise, the consumer guarantee it makes, the authority it evidences, and which language bindings bind it.

**Why this priority**: this is what lets the D3 Java binding, and any later binding, start from documents instead of Python code.

**Independent Test**: the contract check's drift rule passes on the real suite and fails on a planted drift.

**Acceptance Scenarios**:

1. **Given** the suite index, the area registers and the feature files, **When** they are compared, **Then** the step phrases and promise ids match exactly in both directions.

---

### User Story 5 - A binding author reads the envelope verdict as contract (Priority: P2)

A maintainer writing another binding reads, in the conformance package's documentation, the order in which an envelope's checks run, and the error code each check emits. They can then reproduce the pinned codes without reading Python.

**Why this priority**: without the order, pinned codes are an accident of a test file (finding A-M2 of the squad).

**Independent Test**: the documented order names every check that the public verdict function performs, in the same order. A test pins the codes emitted for one input that fails two checks.

**Acceptance Scenarios**:

1. **Given** an envelope that has a forbidden key and also fails the envelope model, **When** its verdict is computed, **Then** the code is the forbidden-key code, as the documented order states.

### Edge Cases

- **Raw historical rows.** The `historical_row_raw` class pins an ideal code that today's validator does not always emit; the conformance README documents this caveat. Its scenario asserts refusal only. It must not claim the ideal code is emitted, and the class must not be dropped. The README's list of codes that may be emitted instead is corrected to match what the class test accepts, which includes the payload-schema code.
- **Several ordered codes.** A strict-journal fixture that pins more than one code (for example `skew_missing_version`, `local_appender_envelope_5_0_0`) is compared against the whole ordered list. A step binding that compares only the first code fails the planted check of SC-004.
- **A forbidden key nested deeply or inside an array element** is still refused with the forbidden-key code (each fixture of the class); it is not masked by an envelope-model error.
- **A feature file with only `@wip` scenarios** still passes the structural rules. A `@wip` scenario is excluded from the gating run, never from the contract check. At the close of D1, `envelope/` has no `@wip` scenario.
- **The pinned error-code vocabulary gains a new code.** The scenarios keep passing unchanged, because the code comes from the fixture, not from the scenario text.
- **A pull request labelled `pr:pause-ci`.** The required checks skip by design (CLAUDE.md, ADR 0005 D3), so the suite runs once the label is removed.

## Domain Language

| Term | Meaning | Avoid |
|---|---|---|
| Scenario suite | The tree of Gherkin feature files under `tests/scenarios/` | "BDD tests", "acceptance tests" (`acceptance` is a CI check name here) |
| Area | A top-level folder of the suite, one per contract surface (e.g. `envelope/`) | "module" |
| Behaviour | A sub-folder of an area holding one feature file named after it | — |
| Promise | One observable guarantee of the contract, tagged `@promise:<id>` on exactly one scenario | "test case" |
| Promise register | An area's `PROMISES.md`: promise, consumer guarantee, authority, binding | — |
| Step binding | The step definitions that connect step phrases to one language's code | "binding" alone (this repo uses "language binding" for the Python and Java packages), "glue" |
| Reference step binding | The Python step binding; it binds every step | — |
| Pinned verdict | The outcome a fixture declares: valid, or invalid with its error code or ordered codes | "expected result" when ambiguous |
| Envelope verdict | The public function's result for one envelope under the documented check order | — |
| Contract check | The per-PR structural check over the suite, with no JVM | "lint" |
| Fixture register | Where a class's fixtures are registered: `manifest.json` `classes.entries` for the eight taxonomy classes, and the top-level `fixtures` array for `envelope_strict_journal` | "the manifest" when the register matters |

## Requirements *(mandatory)*

### Functional Requirements

| ID | Requirement | Status | Delivery | No-op passable? |
|---|---|---|---|---|
| FR-001 | The suite MUST live under `tests/scenarios/`, following core's layout. That means one folder per area, and in it either feature files or one folder per behaviour holding a feature file named after it. D1 uses behaviour folders. | Accepted | [build] | no |
| FR-002 | The suite MUST have an index (`tests/scenarios/README.md`) whose steps table lists every step phrase, grouped Arrange, Assume, Act and Assert. Each area MUST have a promise register (`<area>/PROMISES.md`) in core's four columns: Promise, Consumer guarantee, Authority, Binding. | Accepted | [build] | no |
| FR-003 | Every gating scenario MUST carry exactly one `@promise:<id>` tag. The id MUST match core's grammar and use the form `PR-EVENTS-<AREA>-NNN`. Promise ids MUST be unique across the suite. | Accepted | [build] | no |
| FR-004 | The tag vocabulary MUST be core's closed vocabulary, including `@wip` with `@wip-owner:<handle>` and `@wip-since:<YYYY-MM-DD>`. `@wip` scenarios MUST NOT gate the scenario run, and MUST still pass the contract check. | Accepted | [build] | no |
| FR-005 | The register's Binding column MUST state, per promise, which step bindings bind it (`python`, `python, jvm`, or `@wip`). It is the single source of coverage truth. In D1, every envelope promise reads `python`. | Accepted | [build] | no |
| FR-006 | Every step that selects inputs MUST select them by fixture class name or by the id of an entry in that class's fixture register. No feature file may contain an envelope, a payload or any other fixture content. | Accepted | [build] | no |
| FR-007 | For each selected fixture, the step binding MUST check the verdict the fixture pins: acceptance, or refusal with its exact error code, or its exact ordered list of codes. For `historical_row_raw`, it checks refusal only. | Accepted | [build] | no |
| FR-008 | A selecting step MUST fail its scenario when it selects zero fixtures, which covers an empty class and an unknown id. It MUST also fail when a class's register and its files on disk disagree. | Accepted | [build] | no |
| FR-009 | The reference step binding MUST bind every step phrase. It MUST reach the contract only through the installed package's public surface and the committed fixtures, and never import a module from the repository's `tests/` tree outside `tests/scenarios/`. | Accepted | [build] | no |
| FR-010 | The package MUST provide a public conformance function returning the envelope verdict (accepted, or refused with one error code) for a class-taxonomy envelope fixture, including lane-mapping inputs. The existing class conformance test and the reference step binding MUST both call this same function. The existing test's expectations MUST be unchanged, and it MUST pass. | Accepted | [build] | no |
| FR-011 | A per-PR contract check that needs no JVM MUST read the step definitions of one or more step bindings (in D1, Python only). It MUST refuse the suite with core's codes on: PARSE_ERROR, NO_FEATURES, NO_SCENARIOS, NO_STEPS, NO_GATING_SCENARIOS, UNBOUND_STEP, AMBIGUOUS_STEP, BAD_PROMISE_ID, DUPLICATE_PROMISE, WIP_MISSING_OWNER, WIP_MISSING_SINCE, BAD_WIP_OWNER, BAD_WIP_SINCE, UNKNOWN_PREFIXED_TAG, BAD_BARE_TAG. It MUST also refuse with these events-specific codes: UNREGISTERED_PROMISE (a tag missing from its area register, or a register row with no scenario); BAD_BINDING_DECLARATION (a Binding value outside the vocabulary, or a binding claimed that has no step definition); STEPS_TABLE_DRIFT (index and feature files disagree); FORBIDDEN_TEST_IMPORT (the step binding imports from `tests/` outside `tests/scenarios/`). | Accepted | [build] | no |
| FR-012 | Each FR-011 rule MUST have a planted broken example on which the check reports that rule's code and no other error. The real suite MUST report 0 errors, at least 1 feature file and at least 10 discovered promises. | Accepted | [build] | no, planted examples and the non-empty floor are the controls |
| FR-013 | Envelope acceptance: each canonical fixture and each fixture synthesized from a historical row MUST be accepted (`PR-EVENTS-ENVELOPE-001`, `-002`). | Accepted | [build] | no |
| FR-014 | Refusal with a pinned code: each fixture of the forbidden-key, unknown-lane, payload-schema and bad-shape classes MUST be refused with exactly its pinned code (`PR-EVENTS-ENVELOPE-003` to `-006`). | Accepted | [build] | no |
| FR-015 | Each raw historical row MUST be refused (`PR-EVENTS-ENVELOPE-007`). | Accepted | [build] | no |
| FR-016 | Strict journal profile: each `envelope_strict_journal` fixture MUST be accepted, or refused with exactly its pinned ordered list of codes, by the package's public strict-profile validator (`PR-EVENTS-ENVELOPE-008`). | Accepted | [build] | no |
| FR-017 | Fail closed: the strict-journal fixture whose event type is unregistered MUST be refused as an unknown event type (`PR-EVENTS-ENVELOPE-009`). It is selected by its register id. | Accepted | [build] | no |
| FR-018 | Legacy lane mapping: each legacy lane fixture MUST resolve to its pinned canonical lane, or be refused with its pinned code (`PR-EVENTS-ENVELOPE-010`). | Accepted | [build] | no |
| FR-019 | The conformance package's documentation MUST state the envelope verdict's check order and the code each check emits. A test MUST pin the code for an input that fails more than one check. | Accepted | [build] | no |
| FR-020 | The suite MUST be collected by the repository's standard test run, through a test module that loads the feature files. The scenario runner MUST be added to the development dependencies (the dependency group, the `dev` extra used by the `acceptance` check, and the lock file). | Accepted | [build] | no |
| FR-021 | The scenario run and the contract check MUST run in `make test-fast` and in the required `acceptance` check. The contract check MUST also run in `make lint`. | Accepted | [build] | no |
| FR-022 | The change MUST be recorded in one changelog fragment under `docs/changelog/unreleased/`, with the new public function listed as an addition. `[Unreleased]` MUST NOT be hand-edited. | Accepted | [build] | no |

### Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|---|---|---|---|
| NFR-001 | The scenario run is fast enough for every PR | The suite plus the contract check complete in under 15 s on a CI runner | Accepted |
| NFR-002 | The packaged conformance gate is unchanged in result | `uv run pytest --pyargs spec_kitty_events.conformance`: 0 failures, and no existing case removed or changed in verdict compared with `main` at branch point | Accepted |
| NFR-003 | Static quality | `ruff check .`, `ruff format --check .` and `mypy --strict src/spec_kitty_events`: 0 issues | Accepted |
| NFR-004 | Deterministic | Two consecutive runs give identical per-scenario results and identical verdict-call counts | Accepted |
| NFR-005 | Additive diff | 0 changed bytes in committed schemas and fixtures; 0 changed assertions in existing tests; 0 changed verdicts across the existing test suite | Accepted |

### Constraints

| ID | Constraint | Status |
|---|---|---|
| C-001 | Additive only. No schema, fixture or validator changes what it accepts or refuses. The new public function reproduces the existing verdicts exactly. | Binding |
| C-002 | No import of spec-kitty (core), spec-kitty-saas, spec-kitty-tracker or spec-kitty-runtime. | Binding |
| C-003 | The suite is not shipped in the package's distributions (R2). The new public function is shipped. | Binding |
| C-004 | Feature-file text is technology-agnostic: no Python, Java or library identifiers in step phrases. | Binding |
| C-005 | No JVM step binding and no Gradle change in D1 (R3). | Binding |
| C-006 | Out of scope: ledger and replay (D2, #198); upcast, compatibility and the JVM step binding (D3, #199); documentation-site changes (E, #122). | Binding |
| C-007 | Escalate instead of deciding: any further public package symbol beyond R4, an edit to an existing test's assertions, any fixture edit, or a deviation from core's conventions not listed as D-1 or D-2. | Binding |
| C-008 | Exactly one adversarial-squad review on the PR. The conformance gate runs on the PR. | Binding |

### Key Entities

- **Feature file**: one behaviour; scenarios with Arrange/Act/Assert steps; tags.
- **Promise**: id, owning scenario, consumer guarantee, authority, binding coverage.
- **Fixture selector**: a class name, or an id in that class's fixture register.
- **Pinned verdict**: `valid`, or `invalid` with one code or an ordered list of codes.
- **Envelope verdict**: accepted, or refused with one code, under the documented check order.
- **Contract-check finding**: rule code, file, line, severity.

## Success Criteria *(mandatory)*

- **SC-001**: 10 of 10 envelope promises have a gating (non-`@wip`) scenario that passes through the reference step binding. — [build] · no-op passable: no
- **SC-002**: For every covered class, the verdict-function call count equals the number of fixture files found on disk for that class, counted independently of the register. A planted skipped fixture fails the run. — [build] · no-op passable: no
- **SC-003**: 19 of 19 contract-check rules fail their planted example. The real suite passes with 0 errors, at least 1 feature file and at least 10 promises. — [build] · no-op passable: no
- **SC-004**: For each promise, a committed test changes one pinned verdict in a temporary copy, and exactly the covering scenario fails. For `-007` the test flips `expected` from refused to accepted; for `-008` it reorders a multi-code list. — [build] · no-op passable: no
- **SC-005**: The existing class conformance test passes unchanged against the public function, and an identity check shows it and the step binding call the same function. — [build] · no-op passable: no
- **SC-006**: 0 existing fixtures or schemas change, and the packaged conformance gate has 0 failures and no verdict change. — [ratchet] · no-op passable: yes — positive control: SC-001 requires new scenarios to exist and pass

## Assumptions

- The required check that runs the suite is `acceptance`. It runs `pytest` over `tests/` after installing the `.[dev,conformance]` extras. `ci.yml`'s `suite` is not a required check.
- The public function's name and module placement are plan decisions, bounded by R4 (one public symbol in `spec_kitty_events.conformance`, which may return a small result type) and by C-007.
- How the contract check reads Python step definitions (statically, or by importing the step binding) is a plan decision, bounded by NFR-001 and by FR-011's support for more than one source.
- Issue #199's text says the JVM step binding covers "the matching `envelope/` scenarios". Per this spec's scope note, that is not achievable, so #199 is corrected by a comment when D1's PR opens.
