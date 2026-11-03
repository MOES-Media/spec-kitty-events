---
work_package_id: WP02
title: Public class-fixture verdict
dependencies: []
requirement_refs:
- C-001
- C-002
- C-007
- FR-010
- FR-019
- NFR-002
- NFR-003
- NFR-005
- SC-005
planning_base_branch: issue-197-bdd-suite-skeleton
merge_target_branch: issue-197-bdd-suite-skeleton
branch_strategy: Planning artifacts for this mission were generated on issue-197-bdd-suite-skeleton. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into issue-197-bdd-suite-skeleton unless the human explicitly redirects the landing branch.
subtasks:
- T004
- T005
- T006
- T007
- T008
phase: Phase 1 - Foundations
agent: claude
history:
- '2026-11-03: created by /spec-kitty.tasks'
agent_profile: python-pedro
authoritative_surface: src/spec_kitty_events/conformance/class_verdict.py
create_intent:
- src/spec_kitty_events/conformance/class_verdict.py
- tests/test_class_fixture_verdict.py
execution_mode: code_change
owned_files:
- src/spec_kitty_events/conformance/class_verdict.py
- src/spec_kitty_events/conformance/__init__.py
- src/spec_kitty_events/conformance/README.md
- tests/test_conformance_classes.py
- tests/test_class_fixture_verdict.py
role: implementer
tags: []
tracker_refs: []
---

# WP02 — Public class-fixture verdict (ruling R4)

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load the assigned profile with the `/spk-charter-profile-load` skill (profile `python-pedro`). Then load governance with `spec-kitty charter context --action implement`. Then read, in `kitty-specs/bdd-suite-skeleton-01M6GF8W/`:
- `spec.md`: FR-010, FR-019, US5, C-001, C-007;
- `plan.md`: approach 1;
- `contracts/class-fixture-verdict.md`, **the contract you implement**;
- `research.md`: R-1, R-5 and the post-plan squad table (A-M1, A-M2, R-M1).

## Objective

Today the verdict that the class-taxonomy fixtures pin comes from private helpers in `tests/test_conformance_classes.py`:
- `_validate_envelope` (around line 176),
- `_validate_lane_mapping` (around 295),
- `_validate_for_class` (around 350),
- `_classify_pydantic_error` (around 162),
- and the constants `_PAYLOAD_MODELS`, `_REQUIRED_ENVELOPE_FIELDS` and `_CANONICAL_LANE_VALUES` (around 136-159).

Move that **behaviour** into a public, documented function, `spec_kitty_events.conformance.class_fixture_verdict`. Make the test's helpers delegate to it, without changing a single assertion.

## Branch Strategy

The planning base and the merge target are both `issue-197-bdd-suite-skeleton`. The workspace is the lane worktree from `lanes.json`:

```bash
spec-kitty agent action implement WP02 --agent <name> --mission bdd-suite-skeleton-01M6GF8W
```

## STOP conditions (escalate, do not decide)

- Any `assert`, any parametrize list or any count pin in an existing test would have to change.
- Any fixture, schema or `manifest.json` byte would have to change.
- A second new public symbol seems necessary. C-007 allows exactly one: `class_fixture_verdict`.
- An existing class fixture's verdict changes. That means the move altered behaviour.

## Subtasks

### T004 — Create `src/spec_kitty_events/conformance/class_verdict.py`

1. **Docstring**: say that this is the class-taxonomy envelope verdict (R4, #197), moved from `tests/test_conformance_classes.py`, and point to the README section that holds its check order.
2. **Imports, from defining submodules only.** This is critical (squad A-M1, reproduced): importing from the root `spec_kitty_events` gives `ImportError: cannot import name 'LANE_ALIASES' from partially initialized module`. The chain is root `__init__` → `strict` → `conformance.validators` → `conformance/__init__` → this module. So:
   - import `Lane`, `LANE_ALIASES`, `WP_STATUS_CHANGED` and `StatusTransitionPayload` from `spec_kitty_events.status`. Use **this** `Lane`, the one the package root exports; `diary.py` has another `Lane`, with an extra `uninitialized` value, and must not be used;
   - import `MISSION_CREATED`, `MISSION_CLOSED`, `MissionCreatedPayload` and `MissionClosedPayload` from `spec_kitty_events.lifecycle`;
   - import `Event` from `spec_kitty_events.models`, `find_forbidden_keys` and `FORBIDDEN_LEGACY_KEYS` from `spec_kitty_events.forbidden_keys`, and `ValidationError` and `ValidationErrorCode` from `spec_kitty_events.validation_errors`;
   - use pydantic's `ValidationError` aliased as `PydanticValidationError`.
3. **Move the code.** Move `_PAYLOAD_MODELS`, `_REQUIRED_ENVELOPE_FIELDS` (exactly these 10, in this order: `event_id, event_type, aggregate_id, payload, timestamp, build_id, node_id, lamport_clock, correlation_id, project_uuid`), `_CANONICAL_LANE_VALUES`, `_classify_pydantic_error`, `_envelope_verdict` (was `_validate_envelope`) and `_lane_mapping_verdict` (was `_validate_lane_mapping`).
   - Each returns `ValidationError | None` instead of `_ValidationOutcome`.
   - The bodies are otherwise unchanged: same messages, paths, details and order.
4. **Add the class-name set** `_TAXONOMY_CLASSES: frozenset[str]`, containing exactly the eight classes in `contracts/class-fixture-verdict.md`. Cross-check them against `EIGHT_CLASSES` at line 75 of the test.
5. **Public function**:
   ```python
   def class_fixture_verdict(fixture_class: str, fixture_input: object) -> ValidationError | None:
   ```
   - It raises `ValueError` with a message naming the class and pointing to `spec_kitty_events.strict.validate_strict_envelope` when `fixture_class` is not in `_TAXONOMY_CLASSES`.
   - For `lane_mapping_legacy`, a non-dict input returns the existing `PAYLOAD_SCHEMA_FAIL` with an empty path and the message "lane_mapping fixture input must be a JSON object"; otherwise it dispatches to `_lane_mapping_verdict`.
   - Any other class goes to `_envelope_verdict`.
   - The docstring gives the return semantics and the `Raises:` section.
6. Set `__all__ = ["class_fixture_verdict"]`, and type everything for `mypy --strict`.

### T005 — Export

In `src/spec_kitty_events/conformance/__init__.py`, add `from spec_kitty_events.conformance.class_verdict import class_fixture_verdict`, following the file's existing import style. Add `"class_fixture_verdict"` to `__all__`, alphabetically after `"assert_producer_occurrence_preserved"`. Make no other change.

Then confirm:
- `uv run python -c "import spec_kitty_events; from spec_kitty_events.conformance import class_fixture_verdict"` works;
- `uv run python -c "import spec_kitty_events.conformance"` works in a fresh interpreter, which is the other import order.

### T006 — Make the test's helpers delegate (assertions untouched)

In `tests/test_conformance_classes.py`:
- Keep `_ValidationOutcome`, `ClassFixtureEntry`, `EIGHT_CLASSES`, the loaders and **every test function exactly as it is**.
- Replace the bodies of `_validate_envelope`, `_validate_lane_mapping` and `_validate_for_class` with delegation. For example:
  ```python
  def _validate_for_class(fixture_class: str, input_obj: Any) -> _ValidationOutcome:
      error = class_fixture_verdict(fixture_class, input_obj)
      return _ValidationOutcome(ok=error is None, error=error)
  ```
  Keep `_validate_envelope` and `_validate_lane_mapping` as thin wrappers too, if anything else in the file calls them; otherwise remove them.
- Delete the moved constants and `_classify_pydantic_error` only if nothing else in the file uses them. Leave the imports that remain in use, and remove only the ones that become unused (ruff F401).
- Check: `git diff -U0 tests/test_conformance_classes.py | grep '^[-+].*assert'` prints nothing.

### T007 — README: check order and caveat [P]

In `src/spec_kitty_events/conformance/README.md`:
1. Add a section `## Envelope verdict check order` after "Eight-class taxonomy". It contains the function signature, the `ValueError` rule (naming `envelope_strict_journal` → `validate_strict_envelope`), and the two tables from `contracts/class-fixture-verdict.md` copied exactly. Write the required fields as one code-formatted, comma-separated list in row 2, so that T008 can parse them.
2. In the note on `historical_row_raw`, change "may emit `ENVELOPE_SHAPE_INVALID`, `FORBIDDEN_KEY`, or `UNKNOWN_LANE`" so that it also lists `PAYLOAD_SCHEMA_FAIL`, matching the set `test_conformance_classes.py` accepts (read the "any rejection" branch near line 424).

### T008 — `tests/test_class_fixture_verdict.py`

Write one test per point:
1. **Precedence (FR-019)**: build an envelope from `class_taxonomy/envelope_valid_canonical/mission_created_baseline.json` (load it through `importlib.resources`) and add a forbidden key (take one from `FORBIDDEN_LEGACY_KEYS`, for example `feature_slug`, if it is a member) plus an extra payload field. Assert that the code is `FORBIDDEN_KEY`. Then remove the forbidden key and assert `PAYLOAD_SCHEMA_FAIL`.
2. A non-object input (`[]`) gives `ENVELOPE_SHAPE_INVALID`. A missing `build_id` gives `ENVELOPE_SHAPE_INVALID`, with `details["missing"] == ["build_id"]`.
3. `pytest.raises(ValueError)` for `"envelope_strict_journal"` and `"no_such_class"`.
4. **Delegation (SC-005, class-test side)**: `import tests.test_conformance_classes as m`, then:
   - assert `m.class_fixture_verdict is spec_kitty_events.conformance.class_fixture_verdict`;
   - `monkeypatch.setattr(m, "class_fixture_verdict", spy)`, where the spy records its calls and returns a sentinel `ValidationError`;
   - call `m._validate_for_class("envelope_invalid_shape", {})` and assert the spy was called once with those arguments, and that the result carries the sentinel. This proves the helper holds no verdict logic of its own;
   - assert that none of `_REQUIRED_ENVELOPE_FIELDS`, `_PAYLOAD_MODELS` or `_classify_pydantic_error` remains as an attribute of `m`.
   - The step-binding side of SC-005 is proven in WP05 (T020).
5. **README equals tuple**: parse the README row 2 code list and compare it with `class_verdict._REQUIRED_ENVELOPE_FIELDS`. Importing a module-private name from a test is acceptable here; this is the package's own test.
6. **Fresh-interpreter import**: run `subprocess.run([sys.executable, "-c", "import spec_kitty_events; import spec_kitty_events.conformance as c; c.class_fixture_verdict"], check=True)`.

## Gates

```bash
uv run pytest tests/test_conformance_classes.py tests/test_class_fixture_verdict.py tests/test_envelope_strict_journal_class.py tests/test_timestamp_semantics_conformance.py tests/test_fixture_determinism.py --no-cov -q
uv run pytest --pyargs spec_kitty_events.conformance -q          # count must equal main's
uv run mypy --strict src/spec_kitty_events && uv run ruff check . && uv run ruff format --check .
make test-fast
```

Record the commands and counts in the handoff.

Every work package also runs the gate set from CLAUDE.md before handoff:

```bash
make test-fast
uv run pytest --pyargs spec_kitty_events.conformance -q      # count must equal main's
uv run ruff check . && uv run ruff format --check .
uv run python scripts/changelog.py check && uv run python scripts/changelog.py guard
```

## Definition of Done

- T004 to T008 are done.
- The class test passes with 0 changed assertions.
- The new tests pass.
- The `--pyargs` count is unchanged.
- `mypy --strict` and ruff are clean.
- The README tables match the contract.

## Reviewer guidance

- Diff the moved function bodies against the deleted test helpers; they should differ only in return type and imports.
- Grep the diff for `assert` changes.
- Run the fresh-interpreter import yourself.
- Confirm that `__all__` gained exactly one name.
- Note in the handoff that the new public symbol implies a minor version, which the release PR handles. No version or COMPATIBILITY.md edit is made here.
