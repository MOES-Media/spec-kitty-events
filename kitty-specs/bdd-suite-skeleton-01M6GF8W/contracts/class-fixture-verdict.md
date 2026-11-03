# Contract: `spec_kitty_events.conformance.class_fixture_verdict`

```python
def class_fixture_verdict(fixture_class: str, fixture_input: object) -> ValidationError | None
```

- **Export**: in `spec_kitty_events.conformance.__all__`, the only new public symbol (R4).
- **Returns**: `None` when the input is accepted. Otherwise the first `ValidationError` (from `spec_kitty_events.validation_errors`) found by the order below.
- **Raises**: `ValueError` when `fixture_class` is not one of the eight taxonomy classes:
  - `envelope_valid_canonical`, `envelope_valid_historical_synthesized`, `envelope_invalid_unknown_lane`, `envelope_invalid_forbidden_key`, `envelope_invalid_payload_schema`, `envelope_invalid_shape`, `historical_row_raw`, `lane_mapping_legacy`;
  - in particular `envelope_strict_journal`, whose verdict comes from `spec_kitty_events.strict.validate_strict_envelope` (post-plan squad, A-M2).
- **Pure**: no I/O and no global state; the same input always gives the same result.
- **Imports**: from defining submodules only, never from the `spec_kitty_events` package root, so that importing the package cannot form a cycle (post-plan squad, A-M1).
- **Single source**: the check-order tables below are published in `src/spec_kitty_events/conformance/README.md` § "Envelope verdict check order". This file is the design record; once WP01 lands, the README is the contract. A test pins the README's required-field list to the implementation's tuple.

## Envelope check order (first failure wins)

| # | Check | Code |
|---|---|---|
| 1 | Input is a JSON object | `ENVELOPE_SHAPE_INVALID` |
| 2 | Every required envelope field is present: `event_id`, `event_type`, `aggregate_id`, `payload`, `timestamp`, `build_id`, `node_id`, `lamport_clock`, `correlation_id`, `project_uuid` (this order; `details.missing` lists the absent ones in this order) | `ENVELOPE_SHAPE_INVALID` |
| 3 | No forbidden legacy key at any depth, including inside arrays (first in traversal order) | `FORBIDDEN_KEY` |
| 4 | `payload` is a JSON object | `PAYLOAD_SCHEMA_FAIL` |
| 5 | For `WPStatusChanged`, `from_lane` and `to_lane`, when present, are strings among the canonical lanes or `LANE_ALIASES` | `PAYLOAD_SCHEMA_FAIL` (not a string) / `UNKNOWN_LANE` |
| 6 | The envelope validates as `Event` | `PAYLOAD_SCHEMA_FAIL` if the error is anchored at `payload`, else `ENVELOPE_SHAPE_INVALID` |
| 7 | For `MissionCreated`, `MissionClosed` and `WPStatusChanged`, the payload validates as its typed model | `PAYLOAD_SCHEMA_FAIL` |

## Lane-mapping check order (`lane_mapping_legacy`)

| # | Check | Code |
|---|---|---|
| 1a | Input is a JSON object | `PAYLOAD_SCHEMA_FAIL` (empty path) |
| 1b | `legacy_lane` is a string | `PAYLOAD_SCHEMA_FAIL` (path `legacy_lane`) |
| 2 | `legacy_lane` is canonical or in `LANE_ALIASES` | `UNKNOWN_LANE` |
| 3 | If `canonical_lane` is given, the resolved lane equals it | `UNKNOWN_LANE` |

## Pinned by tests

- **`tests/test_conformance_classes.py`, assertions unchanged**: every one of the 26 `classes.entries` fixtures has its pinned verdict.
- **`tests/test_class_fixture_verdict.py`**:
  - forbidden key plus extra payload field gives `FORBIDDEN_KEY` (check 3 precedes 6 and 7);
  - a non-object input gives `ENVELOPE_SHAPE_INVALID`;
  - an unknown class, and `envelope_strict_journal`, raise `ValueError`;
  - the class test's helper delegates to this function (identity);
  - the README field list equals the implementation's tuple;
  - a fresh interpreter can `import spec_kitty_events` and then `spec_kitty_events.conformance.class_fixture_verdict`.
- **README caveat for `historical_row_raw`**: it lists every code the class test accepts: `ENVELOPE_SHAPE_INVALID`, `FORBIDDEN_KEY`, `UNKNOWN_LANE` and `PAYLOAD_SCHEMA_FAIL`.
