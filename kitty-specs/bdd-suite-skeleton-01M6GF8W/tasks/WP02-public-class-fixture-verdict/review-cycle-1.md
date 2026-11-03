---
affected_files: []
cycle_number: 1
mission_slug: bdd-suite-skeleton-01M6GF8W
reproduction_command:
reviewed_at: '2026-11-03T11:18:01Z'
reviewer_agent: claude
wp_id: WP02
---

# WP02 review feedback (reviewer-renata), cycle 1: changes requested

## Blocking

**[MAJOR] tests/test_class_fixture_verdict.py:46: the precedence test does not pin "check 3 precedes check 6".**

The contract (`contracts/class-fixture-verdict.md:41`) says this test proves that check 3 (forbidden key) "precedes 6 and 7". The README now publishes the same order as public contract. The test's input cannot tell check 3 from check 6. A top-level `feature_slug` plus an extra payload field passes `Event.model_validate`, because `Event` allows extra fields and `payload` is `Dict[str, Any]`. Without the forbidden key, the input fails only at check 7. So the test proves only that 3 runs before 7.

Mutation evidence (reverted afterwards; the worktree is clean):
- **M3.** Swap check 3 and check 6 in `_envelope_verdict`: `tests/test_class_fixture_verdict.py` and `tests/test_conformance_classes.py` both stay green (39 passed).
- **M1.** Move check 3 to sit between check 6 and check 7: still 39 passed.
- **M2.** Move check 3 after check 7: red (the precedence test plus 3 class fixtures fail).

Nothing in the repo now protects the documented 3-before-6 order.

**Fix.** Make the change inside the owned file. Add a case that fails both check 3 and check 6, for example the baseline envelope with `feature_slug` added and `lamport_clock = "not-an-int"`, and assert `FORBIDDEN_KEY`. I checked it: today it gives `FORBIDDEN_KEY`, and under M3 it gives `ENVELOPE_SHAPE_INVALID`, so it kills the mutant. Keep the existing 3-vs-7 case as well.

## Non-blocking

- **[MINOR] kitty-specs/bdd-suite-skeleton-01M6GF8W/contracts/class-fixture-verdict.md:47: the contract overstates what the README lists.**
  - The contract says the README "lists every code the class test accepts". But the test (`tests/test_conformance_classes.py` around line 196) also accepts `RAW_HISTORICAL_ROW`.
  - The README sentence is correct as written. It lists the codes the validator "may emit *instead of* the ideal `RAW_HISTORICAL_ROW`", and the validator never emits `RAW_HISTORICAL_ROW`.
  - So the README needs no change. The contract wording should be corrected by the planner. It is not owned by WP02.
- **[MINOR] Mission-level, not attributable to WP02: `make test-fast` fails `tests/test_version_not_amended.py::test_script_passes_against_this_repo`.**
  - The repo is not shallow, and the tags are present.
  - The guard (`scripts/check_version_not_amended.py`) fails because `src/` changed while `pyproject.toml` still says `11.3.0`, and tag `v11.3.0` exists. The guard's rules do not allow this: the first `src/` change after a tag must bump the version (ADR 0005, Consequences).
  - The spec's R4 says the change is "released as a minor version", but no WP owns that bump. `pyproject.toml` is in WP01's owned files.
  - The required `acceptance` check runs the full pytest suite with `fetch-depth: 0`, so the PR will fail until the version is bumped. Do not fix this in WP02. Escalate to the planner or orchestrator to assign the bump, for example 11.4.0.

## Verified OK (no action)

- **Behaviour preserved.** The moved bodies match the deleted helpers line for line, except for the return type, `_PAYLOAD_MODELS` typing as `type[BaseModel]`, and one comment word. Old helpers and the new function were compared on all 26 `classes.entries` plus 19 synthetic edge inputs: 45 compared, 0 diffs in code, message, path or details.
- **Assertions.** No `assert` line changed.
- **Imports.** No root-package import. `Lane` comes from `status`. Four import orders work in a fresh interpreter: root then conformance, conformance alone, `class_verdict` alone, `strict` then conformance.
- **Public surface.** `__all__` gained exactly `class_fixture_verdict`. `ValueError` is raised for `envelope_strict_journal` and for unknown names, and the message names `validate_strict_envelope`.
- **README tables** match the contract: the 10 fields are in order, and the row numbers and codes match.
- **Spy and README-pin tests** kill their mutants: a helper bypassing the module name, `ok` forced to True, and a reordered README field list all go red.
- **Gates.**
  - `mypy --strict`: clean.
  - `ruff check`: clean.
  - `ruff format --check`: flags only the known WP04 task file.
  - `--pyargs spec_kitty_events.conformance`: 1200 passed, the same as `origin/main`.
  - Targeted gate: 99 passed.
- **Scope.** The WP02 commits touch only the five owned files.
