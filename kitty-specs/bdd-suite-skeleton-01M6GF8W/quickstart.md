# Quickstart

```bash
uv sync                                                  # dev group now includes pytest-bdd
uv run pytest tests/scenarios --no-cov -q                # the scenario suite
uv run python scripts/scenario_contract.py               # the contract check (also in make lint)
uv run pytest tests/test_scenario_contract.py tests/test_conformance_classes.py tests/test_class_fixture_verdict.py --no-cov -q
uv run pytest --pyargs spec_kitty_events.conformance     # packaged gate, unchanged
```

## Adding a promise

1. Pick the area and the behaviour folder, and write the scenario with existing steps from `tests/scenarios/README.md`.
2. Tag it `@promise:PR-EVENTS-<AREA>-NNN`, using the next free number.
3. Add the row to `<area>/PROMISES.md` with Binding `python`.
4. If a new step is needed, add it to `tests/scenarios/steps/` and to the README steps table.
5. Run the contract check.

## Drafting

Tag the scenario `@wip @wip-owner:<handle> @wip-since:<YYYY-MM-DD>` and write `@wip` in its Binding column.
