"""The scenario contract check is clean, and not empty, on the real tree (FR-012, SC-003).

``scripts/scenario_contract.py`` runs with its defaults over ``tests/scenarios``: it must report
no error, and the tree must hold at least one feature file and exactly the ten envelope
promises, so a clean result cannot come from an empty or truncated tree. Planted trees are
covered by ``tests/test_scenario_contract.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import scenario_contract as sc  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parent.parent
FEATURES = _REPO_ROOT / sc.DEFAULT_FEATURES
STEPS = {"python": _REPO_ROOT / sc.DEFAULT_STEPS.partition("=")[2]}
INDEX = _REPO_ROOT / sc.DEFAULT_INDEX
ENVELOPE_PROMISES = tuple(f"PR-EVENTS-ENVELOPE-{n:03d}" for n in range(1, 11))


def test_real_tree_reports_no_error() -> None:
    errors = [p for p in sc.check(FEATURES, STEPS, INDEX) if p.severity == sc.ERROR]
    assert errors == []


def test_real_tree_is_not_empty() -> None:
    found = sc.discover(FEATURES)
    assert len(found.feature_files) >= 1
    assert len(found.promise_ids) >= 10
    assert found.promise_ids == ENVELOPE_PROMISES


def test_cli_defaults_pass_on_the_real_tree() -> None:
    assert sc.main([]) == 0
