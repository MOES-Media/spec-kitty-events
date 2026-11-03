# Contract: `spec_kitty_events.conformance.class_fixture_verdict`

```python
def class_fixture_verdict(fixture_class: str, fixture_input: object) -> ValidationError | None
```

- **Export**: in `spec_kitty_events.conformance.__all__`, the only new public symbol (R4).
- **Returns**: `None` when the input is accepted. Otherwise the first `ValidationError` (from `spec_kitty_events.validation_errors`) found by the order below.
- **Pure**: no I/O and no global state; the same input always gives the same result.
- **Classes**:
  - `"lane_mapping_legacy"` takes the lane-mapping order.
  - Any other class name takes the envelope order, as the private dispatcher did at branch point.
  - Unknown class names are not rejected. This is preserved behaviour and is documented.

## Envelope check order (first failure wins)

| # | Check | Code |
|---|---|---|
| 1 | Input is a JSON object | `ENVELOPE_SHAPE_INVALID` |
| 2 | Required envelope fields present (`event_id`, `event_type`, `aggregate_id`, `payload`, `timestamp`, `node_id`, `lamport_clock`, `project_uuid`, `correlation_id`; exact list as moved) | `ENVELOPE_SHAPE_INVALID` |
| 3 | No forbidden legacy key at any depth, including in arrays (first in traversal order) | `FORBIDDEN_KEY` |
| 4 | `payload` is a JSON object | `PAYLOAD_SCHEMA_FAIL` |
| 5 | For `WPStatusChanged`: `from_lane`/`to_lane`, when present, is a string in the canonical lanes or `LANE_ALIASES` | `PAYLOAD_SCHEMA_FAIL` (not a string) / `UNKNOWN_LANE` |
| 6 | The envelope validates as `Event` | `PAYLOAD_SCHEMA_FAIL` if the error is anchored at `payload`, else `ENVELOPE_SHAPE_INVALID` |
| 7 | For `MissionCreated`, `MissionClosed` and `WPStatusChanged`, the payload validates as its typed model | `PAYLOAD_SCHEMA_FAIL` |

## Lane-mapping check order

| # | Check | Code |
|---|---|---|
| 1 | Input is an object, and `legacy_lane` is a string | `PAYLOAD_SCHEMA_FAIL` |
| 2 | `legacy_lane` is canonical or in `LANE_ALIASES` | `UNKNOWN_LANE` |
| 3 | If `canonical_lane` is given, the resolved lane equals it | `UNKNOWN_LANE` |

## Pinned by tests

- **The class test, unchanged**: every `classes.entries` fixture has its pinned verdict.
- **`tests/test_class_fixture_verdict.py`**:
  - an envelope carrying a forbidden key and also an extra payload field returns `FORBIDDEN_KEY`, so check 3 precedes checks 6 and 7;
  - a non-object input returns `ENVELOPE_SHAPE_INVALID` before any other check;
  - the class test's helper delegates to this function (identity).
- **Documentation**: the same two tables appear in `src/spec_kitty_events/conformance/README.md` § "Envelope verdict check order". The `historical_row_raw` caveat in that README lists every code the class test accepts: ENVELOPE_SHAPE_INVALID, FORBIDDEN_KEY, UNKNOWN_LANE and PAYLOAD_SCHEMA_FAIL.
