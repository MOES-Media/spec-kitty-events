"""Class-taxonomy envelope verdict (ruling R4, #197).

The verdict that the eight-class conformance fixtures pin. It was moved,
behaviour unchanged, from the private helpers of
``tests/test_conformance_classes.py`` so that other callers (the BDD
suite's step bindings among them) reach the same verdict through one
public function, :func:`class_fixture_verdict`.

The order of checks, and therefore which error wins when an input breaks
several rules, is the contract published in
``src/spec_kitty_events/conformance/README.md`` § "Envelope verdict check
order".

Every import comes from the defining submodule, never from the
``spec_kitty_events`` package root: the root imports ``strict``, which
imports ``conformance.validators``, which runs ``conformance/__init__`` and
so this module, while the root is still partially initialised.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from spec_kitty_events.forbidden_keys import FORBIDDEN_LEGACY_KEYS, find_forbidden_keys
from spec_kitty_events.lifecycle import (
    MISSION_CLOSED,
    MISSION_CREATED,
    MissionClosedPayload,
    MissionCreatedPayload,
)
from spec_kitty_events.models import Event
from spec_kitty_events.status import (
    LANE_ALIASES,
    WP_STATUS_CHANGED,
    Lane,
    StatusTransitionPayload,
)
from spec_kitty_events.validation_errors import ValidationError, ValidationErrorCode

__all__ = ["class_fixture_verdict"]


_PAYLOAD_MODELS: dict[str, type[BaseModel]] = {
    MISSION_CREATED: MissionCreatedPayload,
    MISSION_CLOSED: MissionClosedPayload,
    WP_STATUS_CHANGED: StatusTransitionPayload,
}

# Required envelope fields per the public Event model. We pre-check
# these so the verdict can emit ENVELOPE_SHAPE_INVALID with a clear
# missing-fields list before Event.model_validate runs (which would
# emit a Pydantic-internal "Field required" error).
_REQUIRED_ENVELOPE_FIELDS: tuple[str, ...] = (
    "event_id",
    "event_type",
    "aggregate_id",
    "payload",
    "timestamp",
    "build_id",
    "node_id",
    "lamport_clock",
    "correlation_id",
    "project_uuid",
)

_CANONICAL_LANE_VALUES: frozenset[str] = frozenset(member.value for member in Lane)

# The eight classes of the conformance fixture taxonomy.
_TAXONOMY_CLASSES: frozenset[str] = frozenset(
    {
        "envelope_valid_canonical",
        "envelope_valid_historical_synthesized",
        "envelope_invalid_unknown_lane",
        "envelope_invalid_forbidden_key",
        "envelope_invalid_payload_schema",
        "envelope_invalid_shape",
        "historical_row_raw",
        "lane_mapping_legacy",
    }
)


def _classify_pydantic_error(exc: PydanticValidationError) -> ValidationErrorCode:
    """Map a Pydantic Event-level error to a public ValidationErrorCode.

    Errors anchored at ``payload`` (or below) are payload schema
    failures; anything else is an envelope shape failure.
    """

    for err in exc.errors():
        loc = err.get("loc") or ()
        if loc and loc[0] == "payload":
            return ValidationErrorCode.PAYLOAD_SCHEMA_FAIL
    return ValidationErrorCode.ENVELOPE_SHAPE_INVALID


def _envelope_verdict(envelope: object) -> ValidationError | None:
    """Validate a JSON-shape envelope against the package contract.

    Uses the real :class:`Event` model as the envelope source of truth.
    """

    # 1. Wrapper shape.
    if not isinstance(envelope, dict):
        return ValidationError(
            code=ValidationErrorCode.ENVELOPE_SHAPE_INVALID,
            message="envelope must be a JSON object",
            path=[],
            details={"actual_type": type(envelope).__name__},
        )

    # 2. Required envelope fields (pre-check so ENVELOPE_SHAPE_INVALID
    # surfaces a clean missing-fields list ahead of Pydantic).
    missing = [f for f in _REQUIRED_ENVELOPE_FIELDS if f not in envelope]
    if missing:
        return ValidationError(
            code=ValidationErrorCode.ENVELOPE_SHAPE_INVALID,
            message=f"envelope missing required fields: {missing!r}",
            path=[],
            details={"missing": missing},
        )

    # 3. Forbidden keys (recursive). Runs before Event.model_validate so
    # that a deeply nested or array-element forbidden key reports
    # FORBIDDEN_KEY rather than getting masked by a Pydantic
    # extra='forbid' rejection.
    first_forbidden = next(
        find_forbidden_keys(envelope, forbidden=FORBIDDEN_LEGACY_KEYS),
        None,
    )
    if first_forbidden is not None:
        return first_forbidden

    # 4. Payload shape.
    payload = envelope["payload"]
    if not isinstance(payload, dict):
        return ValidationError(
            code=ValidationErrorCode.PAYLOAD_SCHEMA_FAIL,
            message="payload must be a JSON object",
            path=["payload"],
            details={"actual_type": type(payload).__name__},
        )

    # 5. Lane vocabulary check (only meaningful for WPStatusChanged).
    event_type = envelope["event_type"]
    if event_type == WP_STATUS_CHANGED:
        for lane_field in ("from_lane", "to_lane"):
            value = payload.get(lane_field)
            if value is None:
                continue
            if not isinstance(value, str):
                return ValidationError(
                    code=ValidationErrorCode.PAYLOAD_SCHEMA_FAIL,
                    message=f"{lane_field} must be a string",
                    path=["payload", lane_field],
                    details={"actual_type": type(value).__name__},
                )
            if value not in _CANONICAL_LANE_VALUES and value not in LANE_ALIASES:
                return ValidationError(
                    code=ValidationErrorCode.UNKNOWN_LANE,
                    message=f"{lane_field}={value!r} is outside the canonical lane vocabulary",
                    path=["payload", lane_field],
                    details={"value": value},
                )

    # 6. Real Event model validation. Public envelope SSOT.
    try:
        Event.model_validate(envelope)
    except PydanticValidationError as exc:
        code = _classify_pydantic_error(exc)
        return ValidationError(
            code=code,
            message=str(exc),
            path=["payload"] if code == ValidationErrorCode.PAYLOAD_SCHEMA_FAIL else [],
            details={"event_type": event_type},
        )

    # 7. Typed payload model (catches payload-level errors that Event
    # doesn't constrain because it carries `payload: Dict[str, Any]`).
    model = _PAYLOAD_MODELS.get(event_type)
    if model is not None:
        try:
            model(**payload)
        except Exception as exc:  # pydantic.ValidationError or similar
            return ValidationError(
                code=ValidationErrorCode.PAYLOAD_SCHEMA_FAIL,
                message=str(exc),
                path=["payload"],
                details={"event_type": event_type},
            )

    return None


def _lane_mapping_verdict(input_obj: dict[str, Any]) -> ValidationError | None:
    """Validate a lane_mapping_legacy fixture.

    The fixture's ``input`` carries a ``legacy_lane`` and (for valid cases) a
    ``canonical_lane``. The mapping is valid iff ``legacy_lane`` resolves to
    a canonical ``Lane`` (directly or via ``LANE_ALIASES``) and, when
    ``canonical_lane`` is provided, equals it.
    """

    legacy = input_obj.get("legacy_lane")
    if not isinstance(legacy, str):
        return ValidationError(
            code=ValidationErrorCode.PAYLOAD_SCHEMA_FAIL,
            message="legacy_lane must be a string",
            path=["legacy_lane"],
            details={},
        )

    resolved: Lane | None
    if legacy in _CANONICAL_LANE_VALUES:
        resolved = Lane(legacy)
    elif legacy in LANE_ALIASES:
        resolved = LANE_ALIASES[legacy]
    else:
        return ValidationError(
            code=ValidationErrorCode.UNKNOWN_LANE,
            message=f"legacy lane {legacy!r} is outside the canonical lane vocabulary and not in LANE_ALIASES",
            path=["legacy_lane"],
            details={"value": legacy},
        )

    expected_canonical = input_obj.get("canonical_lane")
    if expected_canonical is not None and resolved.value != expected_canonical:
        return ValidationError(
            code=ValidationErrorCode.UNKNOWN_LANE,
            message=(
                f"legacy lane {legacy!r} resolved to {resolved.value!r}, "
                f"not the declared canonical {expected_canonical!r}"
            ),
            path=["canonical_lane"],
            details={"resolved": resolved.value},
        )

    return None


def class_fixture_verdict(fixture_class: str, fixture_input: object) -> ValidationError | None:
    """Return the verdict the class-taxonomy fixtures pin for ``fixture_input``.

    The checks run in the order published in the conformance README
    (§ "Envelope verdict check order"); the first failure wins. The
    function is pure: no I/O, no global state.

    Args:
        fixture_class: One of the eight taxonomy classes. ``lane_mapping_legacy``
            selects the lane-mapping checks; every other class selects the
            envelope checks.
        fixture_input: The fixture's ``input`` value, as loaded from JSON.

    Returns:
        ``None`` when the input is accepted, otherwise the first
        :class:`~spec_kitty_events.validation_errors.ValidationError` found.

    Raises:
        ValueError: If ``fixture_class`` is not one of the eight taxonomy
            classes (for example ``envelope_strict_journal``, whose verdict
            comes from ``spec_kitty_events.strict.validate_strict_envelope``).
    """

    if fixture_class not in _TAXONOMY_CLASSES:
        raise ValueError(
            f"{fixture_class!r} is not a class-taxonomy fixture class "
            f"(expected one of {sorted(_TAXONOMY_CLASSES)}); strict-journal "
            "envelopes are judged by spec_kitty_events.strict.validate_strict_envelope"
        )
    if fixture_class == "lane_mapping_legacy":
        if not isinstance(fixture_input, dict):
            return ValidationError(
                code=ValidationErrorCode.PAYLOAD_SCHEMA_FAIL,
                message="lane_mapping fixture input must be a JSON object",
                path=[],
                details={},
            )
        return _lane_mapping_verdict(fixture_input)
    return _envelope_verdict(fixture_input)
