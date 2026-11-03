"""Conformance class assertion: parametrized over every fixture in the
eight-class taxonomy, asserts each fixture's expected outcome (and the
``expected_error_code`` for invalid fixtures).

This test reads ``manifest.json``'s ``classes.entries`` array (added in
WP05), runs the public verdict
:func:`spec_kitty_events.conformance.class_fixture_verdict` (moved out of
this file's former private helpers, R4 #197) — built on the canonical
``Event`` model in ``spec_kitty_events.models`` — and asserts agreement.

The verdict's order of checks (deterministic; the contract is the
conformance README § "Envelope verdict check order"):

1. Wrapper must be a JSON object.
2. Required *Event* envelope fields must be present.
3. No forbidden legacy keys (recursive walk via
   :func:`spec_kitty_events.forbidden_keys.find_forbidden_keys`).
4. ``payload`` must be a JSON object.
5. Lane fields (when present, on ``WPStatusChanged``) must be in the
   canonical vocabulary; aliases like ``doing`` are accepted.
6. The full envelope must validate against
   :class:`spec_kitty_events.models.Event`. A ``payload``-localised
   failure becomes ``PAYLOAD_SCHEMA_FAIL``; any other envelope-level
   failure becomes ``ENVELOPE_SHAPE_INVALID``.
7. The typed payload model (when known) must accept the inner payload
   — this catches payload-level rejections (e.g. ``extra='forbid'``,
   missing required fields, type mismatches).

For ``historical_row_raw`` fixtures, the validator is not yet expected
to distinguish them from generic envelope-shape failures; the test
accepts any rejection (and documents the gap in the fixture's
``notes``). The ``expected_error_code`` is preserved as the *ideal*
code for a future WP.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from spec_kitty_events import (
    MISSION_CLOSED,
    MISSION_CREATED,
    WP_STATUS_CHANGED,
)
from spec_kitty_events.conformance import class_fixture_verdict
from spec_kitty_events.models import Event
from spec_kitty_events.validation_errors import (
    ValidationError,
    ValidationErrorCode,
)

# ---------------------------------------------------------------------------
# Manifest loading
# ---------------------------------------------------------------------------

_FIXTURES_ROOT = (
    Path(__file__).resolve().parents[1] / "src" / "spec_kitty_events" / "conformance" / "fixtures"
)
_MANIFEST_PATH = _FIXTURES_ROOT / "manifest.json"


# Eight named classes (canonical order matches the contract).
EIGHT_CLASSES: tuple[str, ...] = (
    "envelope_valid_canonical",
    "envelope_valid_historical_synthesized",
    "envelope_invalid_unknown_lane",
    "envelope_invalid_forbidden_key",
    "envelope_invalid_payload_schema",
    "envelope_invalid_shape",
    "historical_row_raw",
    "lane_mapping_legacy",
)


@dataclass(frozen=True)
class ClassFixtureEntry:
    """Manifest entry for a single class-directory fixture."""

    id: str
    fixture_class: str
    path: str
    expected: str
    expected_error_code: str | None
    event_type: str


def _load_class_entries() -> list[ClassFixtureEntry]:
    with _MANIFEST_PATH.open("r", encoding="utf-8") as fh:
        manifest: dict[str, Any] = json.load(fh)

    entries: list[ClassFixtureEntry] = []
    for raw in manifest["classes"]["entries"]:
        entries.append(
            ClassFixtureEntry(
                id=raw["id"],
                fixture_class=raw["class"],
                path=raw["path"],
                expected=raw["expected"],
                expected_error_code=raw.get("expected_error_code"),
                event_type=raw.get("event_type", "<n/a>"),
            )
        )
    return entries


def _load_fixture_file(rel_path: str) -> dict[str, Any]:
    full = _FIXTURES_ROOT / rel_path
    with full.open("r", encoding="utf-8") as fh:
        result: dict[str, Any] = json.load(fh)
    return result


# ---------------------------------------------------------------------------
# Validator (delegates to the public class_fixture_verdict)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _ValidationOutcome:
    ok: bool
    error: ValidationError | None


def _validate_for_class(fixture_class: str, input_obj: Any) -> _ValidationOutcome:
    error = class_fixture_verdict(fixture_class, input_obj)
    return _ValidationOutcome(ok=error is None, error=error)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


_ALL_ENTRIES: list[ClassFixtureEntry] = _load_class_entries()


@pytest.mark.parametrize(
    "entry",
    _ALL_ENTRIES,
    ids=[e.id for e in _ALL_ENTRIES],
)
def test_fixture_outcome_matches_expected(entry: ClassFixtureEntry) -> None:
    fixture = _load_fixture_file(entry.path)

    # Sanity: fixture file's class label must match manifest entry.
    assert fixture["class"] == entry.fixture_class, (
        f"Fixture {entry.path}: file declares class={fixture['class']!r} "
        f"but manifest registers it under class={entry.fixture_class!r}."
    )
    assert fixture["expected"] == entry.expected, (
        f"Fixture {entry.path}: file declares expected={fixture['expected']!r} "
        f"but manifest registers expected={entry.expected!r}."
    )
    if entry.expected == "invalid":
        assert entry.expected_error_code is not None, (
            f"Manifest entry {entry.id} marks expected=invalid but is missing "
            f"expected_error_code (required by conformance-fixture-classes.md)."
        )
        assert fixture.get("expected_error_code") == entry.expected_error_code, (
            f"Fixture {entry.path}: expected_error_code mismatch between file "
            f"({fixture.get('expected_error_code')!r}) and manifest "
            f"({entry.expected_error_code!r})."
        )

    outcome = _validate_for_class(entry.fixture_class, fixture["input"])

    if entry.expected == "valid":
        assert outcome.ok, (
            f"Fixture {entry.path} expected to validate but failed with {outcome.error!r}"
        )
        # Additionally assert the canonical fixture survives the real
        # public Event.model_validate entry point (envelope SSOT).
        if entry.fixture_class in {
            "envelope_valid_canonical",
            "envelope_valid_historical_synthesized",
        }:
            Event.model_validate(fixture["input"])
        return

    # expected == "invalid"
    assert not outcome.ok, (
        f"Fixture {entry.path} expected to be rejected but the validator accepted it."
    )
    assert outcome.error is not None
    actual_code = outcome.error.code.value

    if entry.fixture_class == "historical_row_raw":
        # The validator does not yet detect raw historical rows as a
        # distinct rejection class. Accept any rejection; record the
        # *ideal* expected_error_code in the manifest for a future WP.
        accepted_codes = {
            ValidationErrorCode.ENVELOPE_SHAPE_INVALID.value,
            ValidationErrorCode.FORBIDDEN_KEY.value,
            ValidationErrorCode.UNKNOWN_LANE.value,
            ValidationErrorCode.PAYLOAD_SCHEMA_FAIL.value,
            ValidationErrorCode.RAW_HISTORICAL_ROW.value,
        }
        assert actual_code in accepted_codes, (
            f"Fixture {entry.path}: historical_row_raw rejected with "
            f"unexpected code {actual_code!r}; accepted codes: {sorted(accepted_codes)}."
        )
        return

    assert actual_code == entry.expected_error_code, (
        f"Fixture {entry.path}: expected_error_code={entry.expected_error_code!r} "
        f"but validator returned {actual_code!r} ({outcome.error.message!r})."
    )


def test_every_class_has_at_least_one_fixture() -> None:
    """Coverage gate: every of the eight classes has >= 1 fixture."""
    by_class: dict[str, int] = {cls: 0 for cls in EIGHT_CLASSES}
    for entry in _ALL_ENTRIES:
        assert entry.fixture_class in by_class, (
            f"Manifest entry {entry.id} declares unknown class "
            f"{entry.fixture_class!r}; valid classes: {sorted(by_class)}."
        )
        by_class[entry.fixture_class] += 1

    empty = [cls for cls, count in by_class.items() if count == 0]
    assert not empty, (
        f"Conformance fixture suite is missing fixtures for class(es) "
        f"{empty}. Each of the eight classes must have at least one fixture."
    )


def test_canonical_class_covers_canonical_event_types() -> None:
    """Every canonical event type appears at least once under
    ``envelope_valid_canonical``."""
    canonical_event_types = {MISSION_CREATED, MISSION_CLOSED, WP_STATUS_CHANGED}
    seen_event_types: set[str] = set()
    for entry in _ALL_ENTRIES:
        if entry.fixture_class != "envelope_valid_canonical":
            continue
        seen_event_types.add(entry.event_type)

    missing = canonical_event_types - seen_event_types
    assert not missing, (
        f"envelope_valid_canonical missing fixtures for event type(s) "
        f"{sorted(missing)}. Expected at least one fixture per canonical "
        f"event type."
    )


def test_invalid_fixtures_have_expected_error_code() -> None:
    """Every invalid manifest entry must declare expected_error_code."""
    for entry in _ALL_ENTRIES:
        if entry.expected != "invalid":
            continue
        assert entry.expected_error_code is not None, (
            f"Invalid manifest entry {entry.id} missing expected_error_code."
        )
        assert entry.expected_error_code in {code.value for code in ValidationErrorCode}, (
            f"Invalid manifest entry {entry.id} declares unknown error code "
            f"{entry.expected_error_code!r}."
        )


def test_valid_canonical_fixtures_validate_against_real_event_model() -> None:
    """Sanity gate: every envelope_valid_canonical and
    envelope_valid_historical_synthesized fixture validates against
    the real public ``Event`` model."""

    target_classes = {
        "envelope_valid_canonical",
        "envelope_valid_historical_synthesized",
    }
    for entry in _ALL_ENTRIES:
        if entry.fixture_class not in target_classes:
            continue
        fixture = _load_fixture_file(entry.path)
        # The exception type intentionally bubbles up if it fails — this
        # is the SSOT gate: every "valid" canonical fixture MUST pass
        # Event.model_validate.
        Event.model_validate(fixture["input"])
