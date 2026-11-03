---
affected_files: []
cycle_number: 1
mission_slug: bdd-suite-skeleton-01M6GF8W
reproduction_command:
reviewed_at: '2026-11-03T11:46:48Z'
reviewer_agent: claude
wp_id: WP04
---

# WP04 review: changes requested (reviewer-renata)

Most of this is solid. The suite gives 10 passed plus 9 tag-hook tests with no warnings. The WP03 checker exits 0 against this tree. Imports are public only. Step phrases are free of Python and library identifiers. PROMISES.md has 10 `python` rows, there is no `@wip`, and the conformance gate passes 1200. `ruff check`, `mypy --strict` and `make test-fast` (4332 passed, 130 skipped) are green. Three blocking findings remain.

## [MAJOR] tests/scenarios/steps/envelope_steps.py:183-198 - the single-fixture Arrange step skips the register-versus-disk comparison (declared deviation 1)

FR-008 says "A selecting step MUST fail its scenario ... when a class's register and its files on disk disagree". `select_one` is a selecting step, so FR-008 applies to it. The same rule appears in three other places:
- the data-model invariant, "The set of register paths equals the set of `*.json` files in the class folder, or the selection fails";
- T016, "`select_id` ...: the same selection, then the one case whose register id matches";
- T020.4, which tells WP05 to unit-test a `select_id` helper. This module does not have one.

Evidence, on a scratch copy with an unregistered `envelope_strict_journal/zz_extra.json`: 008 fails, but `-k unregistered_event` (009 alone) passes. A removed `skew_missing_version.json` also leaves 009 green.

The WP05 mutation table does not depend on the deviation either way. Its unregistered-file case is planted in `envelope_valid_canonical`, and its 009 rows expect {008, 009} in any case. So nothing justifies the deviation.

**Fix**: factor the class selection, including the set comparison and the empty check, into a `select_class(root, fixture_class)` helper. Build `select_id` on top of it, filter by id, and call `pytest.fail` unless exactly one entry matches. Keep `disk_count = 1` for the single case.

## [MAJOR] tests/scenarios/steps/envelope_steps.py:263-268 - in `Then each is accepted`, `_require_pins` is the only link to the pin, so a binding that stops checking pins passes

Mutation: delete `_require_pins(scenario_ctx, "valid")` from `each_accepted`. On the scratch copy where `mission_created_baseline.json` is flipped to `invalid` / `FORBIDDEN_KEY` in both the register and the file, the run gives **10 passed**. The same flip fails 001 on the unmutated binding. On the real tree the run also gives 10 passed, so no scenario turns red.

The cause: `each_accepted` compares the outcome with "empty", not with the case's pinned codes. So the pin is read in exactly one place.

**Fix**: compare `_outcome(c) != c.codes` there, the way the refusing steps already do, and keep `_require_pins` as the guard. Then removing either check alone still fails 001 on the flip. `each_refused` has the same single-link shape. WP05's 007 row (register flip) does exercise its guard, but consider the same redundancy there. Also add a committed check that would catch this mutation, either here in `tests/scenarios/` or as a row in WP05's table. WP05's planned 001 row mutates the input, not the pin, so it would not catch it.

## [MAJOR] tests/scenarios/steps/envelope_steps.py:178 - the coverage step cannot tell the disk count from the register count on any committed or planned fixture set

Mutation: `scenario_ctx.disk_count = len(register)`. It survives on the real tree, on an unregistered-file copy (the set comparison at line 169 fails first, the same as on the original) and on a removed-file copy. Only a duplicated register entry tells the two apart: the original fails 001 with `verdict calls=5, fixtures on disk=4, selected=5`, while the mutant passes 10/10. No committed test or WP05 row plants that case.

**Fix**: commit a duplicate-register-entry case that fails the coverage step. Put it in `tests/scenarios/` or add it to WP05's T020 list and record it in the handoff. Alternatively, also check that register ids and paths are unique in Arrange, and say which check owns that failure.

## Minor (do not block; fix while you are in there or file them)

- [MINOR] tests/scenarios/README.md - T015 asks for a "How to add a promise" section, and there is none. Also, "How to run" omits the contract-check command from `quickstart.md`.
- [MINOR] tests/scenarios/test_tag_hook.py - this file is outside WP04's `owned_files` (`tests/scenarios/__init__.py`, `conftest.py`, `README.md`, `test_envelope.py`, `steps/**`, `envelope/**`). The test is useful. Record it as an out-of-map addition, or add it to the map.

## Ruling on the declared deviations

1. **Single-fixture Arrange skips the class-wide comparison.** Rejected. It is inconsistent with FR-008, the data model and T016. It is not required by the WP05 table. See the first MAJOR finding.
2. **Outcomes are normalised to ordered tuples of codes.** Accepted. `None` and `[]` become `()`, a `ValidationError` becomes `(code,)`, and a list becomes its ordered codes. This matches data-model "Verdict outcome" and the strict test's comparison. It keeps the order, so FR-007 and the "several ordered codes" edge case hold. The `AssertionError` on an unrecognised verdict fails closed.

## What passed (evidence)

- Assert steps fail on pins (scratch copies under `/tmp/claude-0/-home-user-spec-kitty-events/1b5fc9bb-7490-5530-be99-930ca6d6de40/scratchpad/rev-wp04/`):
  - canonical flipped to invalid in both places: only 001 fails;
  - a lane-mapping invalid fixture flipped to valid: only 010 fails;
  - a shape code re-pinned in the register only: 006 fails in Arrange on the disagreement.
- `_evaluate` mutations are all killed:
  - skipping the first case fails 10/10;
  - faking the last outcome fails 6;
  - substituting another case's input fails 010 and 008.
- The tag hook returns `True` for `wip`/`manual` (after marking in place) and for the consumed vocabulary, and `None` for other prefixed tags.
