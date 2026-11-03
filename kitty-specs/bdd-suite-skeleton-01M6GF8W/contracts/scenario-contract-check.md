# Contract: `scripts/scenario_contract.py`

```
uv run python scripts/scenario_contract.py [--features DIR] [--steps NAME=DIR]... [--index FILE]
```

- **Defaults**: `--features tests/scenarios`, `--steps python=tests/scenarios/steps`, `--index tests/scenarios/README.md`.
- **Exit status**: 0 when there are no error findings, 1 when there is at least one, 2 on a usage error (an unknown binding name, or a missing directory).
- **Output**: one line per finding, `<severity> <code> <file>:<line> <message>`, sorted by file, line and code.
- **Step sources**: `NAME` is a key in the parser registry. D1 registers `python` (an AST scan of `pytest_bdd` `given`/`when`/`then` decorators with a literal or `parsers.parse(literal)`). `jvm` is reserved for D3.

## Rules

Each rule has a planted tree at `tests/fixtures/scenario_contract/<CODE>/`. Each tree holds `features/`, `steps/` and `README.md` as needed, and breaks only that rule.

| Code | Origin | Fires when |
|---|---|---|
| PARSE_ERROR | core | gherkin-official raises on a file |
| NO_FEATURES | core | the features directory holds no `.feature` |
| NO_SCENARIOS | core | a feature has no scenario |
| NO_STEPS | core | a scenario (after Background) has no step |
| NO_GATING_SCENARIOS | core | every scenario in the tree is `@wip` or `@manual` |
| UNBOUND_STEP | core | a gating step matches no definition in any source its promise is declared bound by (in D1, `python`) |
| AMBIGUOUS_STEP | core | a gating step matches more than one definition of one source |
| BAD_PROMISE_ID | core, strengthened | a gating scenario has no `@promise:` tag or more than one, or the id breaks `[A-Za-z0-9][A-Za-z0-9._-]*` |
| DUPLICATE_PROMISE | core | one id appears on two scenarios |
| WIP_MISSING_OWNER | core | `@wip` without `@wip-owner:` |
| WIP_MISSING_SINCE | core | `@wip` without `@wip-since:` |
| BAD_WIP_OWNER | core | the owner handle breaks the id character set |
| BAD_WIP_SINCE | core | the since value is not a real `YYYY-MM-DD` date |
| UNKNOWN_PREFIXED_TAG | core | a tag with `:` and a prefix outside `promise`, `wip-owner`, `wip-since`, `defect`, `qa` |
| BAD_BARE_TAG | core | a bare tag breaks `[A-Za-z0-9][A-Za-z0-9_-]*` |
| UNREGISTERED_PROMISE | events (D-2) | a tag is missing from its area's `PROMISES.md`, a row has no scenario, or an area has scenarios but no `PROMISES.md` |
| BAD_BINDING_DECLARATION | events (D-2) | a Binding value is outside `python` / `python, jvm` / `@wip`; `@wip` disagrees with the scenario's tag; or a named binding has no step source given |
| STEPS_TABLE_DRIFT | events (D-2) | an index table row (`Arrange`/`Assume` → Given, `Act` → When, `Assert` → Then) has no definition of that keyword, or a definition has no row. Placeholders are compared normalised: `"<x>"` ⇔ `"{x}"` |
| FORBIDDEN_TEST_IMPORT | events (D-2) | a module in a step source imports `tests` or `tests.<x>` where `<x>` is not `scenarios` (`import` or `from … import`, absolute or relative beyond the source root) |

## Mutation-test note (SC-004)

- Promises 008 and 009 share the `envelope_strict_journal` class, so mutating `unknown_event_type.json` fails both scenarios. SC-004's "exactly the covering scenario" is read as "exactly the set of scenarios that cover the mutated fixture". For 009 that set is {008, 009}.
- Every other promise covers a class no other promise covers.
