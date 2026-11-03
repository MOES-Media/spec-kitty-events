"""Scenario suite wiring (#197): the tag vocabulary and the Python reference step binding.

Tags follow core's closed vocabulary (``tests/scenarios/README.md`` § Tags):

- ``@wip`` and ``@manual`` skip the scenario, so it never gates the run;
- ``@promise:``, ``@wip-owner:``, ``@wip-since:``, ``@defect:``, ``@qa:`` and any other bare
  tag are consumed without a mark, so they raise no unknown-mark warning;
- any other prefixed tag falls through to pytest-bdd's default, so the run under
  ``-W error::pytest.PytestUnknownMarkWarning`` refuses it (the contract check reports it as
  UNKNOWN_PREFIXED_TAG).

Fixture root override (test-only): ``SPEC_KITTY_SCENARIO_FIXTURES`` names a folder laid out
like the packaged ``spec_kitty_events/conformance/fixtures`` (a ``manifest.json`` and a
``class_taxonomy/`` tree). It is read in one place, the Arrange step of
``tests/scenarios/steps/envelope_steps.py``, at call time. Unset, the packaged fixtures are
used. It exists so mutation tests can run the suite over a temporary copy.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.scenarios.steps.envelope_steps import *  # noqa: F403  (registers the step binding)

_CONSUMED_PREFIXES = ("promise:", "wip-owner:", "wip-since:", "defect:", "qa:")


def pytest_bdd_apply_tag(tag: str, function: Callable[..., object]) -> bool | None:
    """Apply one feature-file tag to a scenario function, marking it in place."""
    if tag == "wip":
        pytest.mark.skip(reason="@wip: draft scenario, not gating")(function)
        return True
    if tag == "manual":
        pytest.mark.skip(reason="@manual")(function)
        return True
    if tag.startswith(_CONSUMED_PREFIXES) or ":" not in tag:
        return True
    return None
