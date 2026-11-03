# Event-contract scenarios

Gherkin scenarios that describe, in plain language, what the event contract promises every
language binding. The Python reference step binding binds every step and runs on every pull
request through pytest-bdd (`tests/scenarios/test_*.py`), inside the repository's standard test
run (#197, slice D1 of #121). A Cucumber-JVM step binding of a subset follows in D3 (#199).

The suite lives in the repository and is not shipped in the package. Scenarios name fixture
classes or fixture register ids; the verdicts they check are the ones the committed fixtures in
`spec_kitty_events/conformance/fixtures/` pin, computed by the package's public functions.

## Layout

One folder per contract area, one folder per behaviour in it, holding a feature file named after
the behaviour. Each area has a promise register, `<area>/PROMISES.md`:

| Folder | Covers |
|--------|--------|
| `envelope/` | Envelope acceptance and refusal: canonical and synthesized envelopes are accepted (`accepts-valid-envelopes/`), invalid envelopes and raw historical rows are refused with their pinned reason (`refuses-with-pinned-reason/`), the strict journal profile refuses with the ordered codes pinned (`strict-journal-profile/`), and legacy lane strings resolve as pinned (`resolves-legacy-lanes/`). Bound in Python only; see `envelope/PROMISES.md` |

The Python step definitions are in `steps/`; `conftest.py` loads them and applies the tag
vocabulary below.

## Available steps

Steps follow Arrange, Assume, Act, Assert. Reuse these before adding new ones.

| Group | Step |
|-------|------|
| Arrange | `Given the conformance fixtures of class "<fixture_class>"` |
| Arrange | `Given the conformance fixture "<fixture_id>" of class "<fixture_class>"` |
| Act | `When each envelope is validated` |
| Act | `When each envelope is validated under the strict journal profile` |
| Act | `When each legacy lane is resolved` |
| Assert | `Then each is accepted` |
| Assert | `Then each is refused with exactly the code its fixture pins` |
| Assert | `Then each is refused` |
| Assert | `Then each is accepted or refused with exactly the codes its fixture pins` |
| Assert | `Then it is refused with the code "<code>"` |
| Assert | `Then every selected fixture was evaluated` |

"The conformance fixtures of class" selects every fixture a class registers: for the eight
taxonomy classes, `manifest.json` `classes.entries`; for `envelope_strict_journal`, the top-level
`fixtures` array. The registered paths must equal the class folder's files on disk, and the
selection must not be empty, or the step fails; it also fails if the class's register repeats an
id or a path. "The conformance fixture" runs the same whole-class selection, with the same checks,
then keeps the one fixture whose register id matches; an unknown id fails the step. "Each is
refused" checks refusal only; it is for `historical_row_raw`, whose pinned code is an ideal
today's validator does not always emit (conformance README). Every Assert step compares each
outcome with that fixture's own pin.
"Every selected fixture was evaluated" checks that the verdict was computed once per selected
fixture and per file on disk.

## Tags

| Tag | Rule |
|-----|------|
| `@promise:<id>` | Names the contract promise the scenario checks, `PR-EVENTS-<AREA>-NNN`. `<id>` matches `[A-Za-z0-9][A-Za-z0-9._-]*`. Exactly one per gating scenario, unique across the suite, and listed in the area's `PROMISES.md`. |
| `@wip` | Scenario is being drafted or fixed. Needs `@wip-owner:<handle>` and `@wip-since:<YYYY-MM-DD>` (a valid date). |
| `@wip-owner:<handle>` | Who owns the draft. `<handle>` matches `[A-Za-z0-9][A-Za-z0-9._-]*`. |
| `@wip-since:<YYYY-MM-DD>` | Date the scenario was marked `@wip`. |
| `@manual` | Never runs automatically. |
| `@defect:<issue>` | Links a known defect. `<issue>` is a positive integer. |
| `@qa:<ref>` | Reference for the QA repository. `<ref>` uses the identifier character set above. |
| `@<bare>` | Any bare tag matching `[A-Za-z0-9][A-Za-z0-9_-]*`, with no `:`. |

Any other tag containing `:` is an unknown prefixed tag and is an error.

Every scenario except those tagged `@wip` or `@manual` gates the run; those two are skipped.
Tags on a `Feature` or `Rule` apply to all scenarios under it.

## Promise registers

Each `<area>/PROMISES.md` has one `## <feature title> — \`<behaviour>/\`` section per behaviour,
with a table `| Promise | Consumer guarantee | Authority | Binding |` and one row per promise.
Binding is `python`, `python, jvm` or `@wip`; it is `@wip` exactly when the scenario is.

## Running

```bash
uv run pytest tests/scenarios --no-cov -q -W error::pytest.PytestUnknownMarkWarning
uv run python scripts/scenario_contract.py               # the contract check
```

`SPEC_KITTY_SCENARIO_FIXTURES` (test-only, documented in `conftest.py`) points the Arrange steps
at another fixture root laid out like the packaged one.

## How to add a promise

1. Pick the area and the behaviour folder, and write the scenario with the steps in
   [Available steps](#available-steps).
2. Tag it `@promise:PR-EVENTS-<AREA>-NNN`, using the next free number in the area.
3. Add its row to `<area>/PROMISES.md`, under the behaviour's section, with Binding `python`.
4. If a new step is needed, add it to `steps/` and to the steps table above, in the same change.
5. Run the scenarios and the contract check (see [Running](#running)).

To draft a scenario that does not gate yet, tag it `@wip @wip-owner:<handle>
@wip-since:<YYYY-MM-DD>` and write `@wip` in its Binding column.
