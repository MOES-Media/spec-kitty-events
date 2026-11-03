"""FR-004: the tag hook skips @wip and @manual, and consumes the rest of core's vocabulary."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.scenarios.conftest import pytest_bdd_apply_tag


def _dummy() -> Callable[[], None]:
    def scenario() -> None:
        pass

    return scenario


def _marks(function: Callable[[], None]) -> list[pytest.Mark]:
    return list(getattr(function, "pytestmark", []))


@pytest.mark.parametrize(
    ("tag", "reason"),
    [("wip", "@wip: draft scenario, not gating"), ("manual", "@manual")],
)
def test_skipping_tags_mark_in_place_and_are_consumed(tag: str, reason: str) -> None:
    function = _dummy()
    assert pytest_bdd_apply_tag(tag, function) is True
    marks = _marks(function)
    assert [(m.name, m.kwargs.get("reason")) for m in marks] == [("skip", reason)]


@pytest.mark.parametrize(
    "tag",
    [
        "promise:PR-EVENTS-ENVELOPE-001",
        "wip-owner:someone",
        "wip-since:2026-11-03",
        "defect:197",
        "qa:SC-001",
        "slow",
    ],
)
def test_vocabulary_tags_are_consumed_without_a_mark(tag: str) -> None:
    function = _dummy()
    assert pytest_bdd_apply_tag(tag, function) is True
    assert _marks(function) == []


def test_unknown_prefixed_tag_falls_through_to_the_default() -> None:
    function = _dummy()
    assert pytest_bdd_apply_tag("team:events", function) is None
    assert _marks(function) == []
