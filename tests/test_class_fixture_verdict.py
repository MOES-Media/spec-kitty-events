"""Pins the public class-taxonomy verdict (R4, #197).

``spec_kitty_events.conformance.class_fixture_verdict`` is the verdict the
eight-class fixtures pin; ``tests/test_conformance_classes.py`` delegates
to it. These tests pin its check precedence, its rejection of classes
outside the taxonomy, the delegation, and the README's published field
list.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from importlib.resources import files
from pathlib import Path
from typing import Any

import pytest

import spec_kitty_events.conformance
import tests.test_conformance_classes as class_test
from spec_kitty_events.conformance import class_verdict
from spec_kitty_events.conformance.class_verdict import class_fixture_verdict
from spec_kitty_events.forbidden_keys import FORBIDDEN_LEGACY_KEYS
from spec_kitty_events.validation_errors import ValidationError, ValidationErrorCode

_README = (
    Path(__file__).resolve().parents[1] / "src" / "spec_kitty_events" / "conformance" / "README.md"
)


def _baseline_envelope() -> dict[str, Any]:
    resource = files("spec_kitty_events.conformance").joinpath(
        "fixtures/class_taxonomy/envelope_valid_canonical/mission_created_baseline.json"
    )
    envelope: dict[str, Any] = json.loads(resource.read_text(encoding="utf-8"))["input"]
    return envelope


def test_baseline_envelope_is_accepted() -> None:
    assert class_fixture_verdict("envelope_valid_canonical", _baseline_envelope()) is None


def test_forbidden_key_precedes_payload_schema_failure() -> None:
    assert "feature_slug" in FORBIDDEN_LEGACY_KEYS
    envelope = _baseline_envelope()
    envelope["payload"]["unexpected_extra_field"] = "x"
    envelope["feature_slug"] = "legacy"

    with_forbidden = class_fixture_verdict("envelope_invalid_forbidden_key", envelope)
    assert with_forbidden is not None
    assert with_forbidden.code is ValidationErrorCode.FORBIDDEN_KEY

    del envelope["feature_slug"]
    without_forbidden = class_fixture_verdict("envelope_invalid_payload_schema", envelope)
    assert without_forbidden is not None
    assert without_forbidden.code is ValidationErrorCode.PAYLOAD_SCHEMA_FAIL


def test_forbidden_key_precedes_event_model_failure() -> None:
    assert "feature_slug" in FORBIDDEN_LEGACY_KEYS
    envelope = _baseline_envelope()
    envelope["lamport_clock"] = "not-an-int"
    envelope["feature_slug"] = "legacy"

    with_forbidden = class_fixture_verdict("envelope_invalid_forbidden_key", envelope)
    assert with_forbidden is not None
    assert with_forbidden.code is ValidationErrorCode.FORBIDDEN_KEY

    del envelope["feature_slug"]
    without_forbidden = class_fixture_verdict("envelope_invalid_shape", envelope)
    assert without_forbidden is not None
    assert without_forbidden.code is ValidationErrorCode.ENVELOPE_SHAPE_INVALID


def test_non_object_input_is_envelope_shape_invalid() -> None:
    error = class_fixture_verdict("envelope_invalid_shape", [])
    assert error is not None
    assert error.code is ValidationErrorCode.ENVELOPE_SHAPE_INVALID


def test_missing_build_id_is_envelope_shape_invalid() -> None:
    envelope = _baseline_envelope()
    del envelope["build_id"]
    error = class_fixture_verdict("envelope_invalid_shape", envelope)
    assert error is not None
    assert error.code is ValidationErrorCode.ENVELOPE_SHAPE_INVALID
    assert error.details["missing"] == ["build_id"]


@pytest.mark.parametrize("fixture_class", ["envelope_strict_journal", "no_such_class"])
def test_class_outside_taxonomy_raises(fixture_class: str) -> None:
    with pytest.raises(ValueError, match=fixture_class):
        class_fixture_verdict(fixture_class, {})


def test_class_test_helper_delegates_to_public_verdict(monkeypatch: pytest.MonkeyPatch) -> None:
    assert class_test.class_fixture_verdict is spec_kitty_events.conformance.class_fixture_verdict

    sentinel = ValidationError(code=ValidationErrorCode.ENVELOPE_SHAPE_INVALID, message="sentinel")
    calls: list[tuple[str, object]] = []

    def spy(fixture_class: str, fixture_input: object) -> ValidationError | None:
        calls.append((fixture_class, fixture_input))
        return sentinel

    monkeypatch.setattr(class_test, "class_fixture_verdict", spy)
    outcome = class_test._validate_for_class("envelope_invalid_shape", {})

    assert calls == [("envelope_invalid_shape", {})]
    assert outcome.error is sentinel
    assert outcome.ok is False
    for moved in ("_REQUIRED_ENVELOPE_FIELDS", "_PAYLOAD_MODELS", "_classify_pydantic_error"):
        assert not hasattr(class_test, moved), moved


def test_readme_required_fields_match_implementation() -> None:
    readme = _README.read_text(encoding="utf-8")
    section = readme.split("## Envelope verdict check order", 1)[1]
    row = re.search(
        r"^\| 2 \| Every required envelope field is present: `([^`]+)`", section, re.MULTILINE
    )
    assert row is not None
    fields = tuple(name.strip() for name in row.group(1).split(","))
    assert fields == class_verdict._REQUIRED_ENVELOPE_FIELDS


def test_fresh_interpreter_imports_package_then_verdict() -> None:
    subprocess.run(
        [
            sys.executable,
            "-c",
            "import spec_kitty_events; import spec_kitty_events.conformance as c; c.class_fixture_verdict",
        ],
        check=True,
    )
