# Contract: `scripts/scenario_contract.py`

```
uv run python scripts/scenario_contract.py [--features DIR] [--steps NAME=DIR]... [--index FILE]
```

- **Defaults**: `--features tests/scenarios`, `--steps python=tests/scenarios/steps`, `--index tests/scenarios/README.md`.
- **Exit status**: 0 when there are no error findings, 1 when there is at least one, 2 on a usage error (an unknown binding name, or a missing directory).
- **Output**: one line per finding, `<severity> <code> <file>:<line> <message>`, sorted by file, line and code.
- **Feature parsing**: `gherkin-official`, the parser pytest-bdd itself uses. It is declared as a direct dev dependency because the script imports it.
- **Step sources**: `NAME` is a key in the parser registry. D1 registers `python`, which is a static AST scan of every `given`/`when`/`then` decorator imported from `pytest_bdd`.
  - The argument may be a string literal or `parsers.parse(<literal>)`.
  - Stacked decorators on one function are each read.
  - `parse` fields `{name}` and `{name:fmt}` become regex groups.
  - Any other form (`parsers.re`, `parsers.cfparse`, `@step`, aliased imports, non-literal strings) is not read, so the steps it would bind fail loudly as UNBOUND_STEP.
  - `jvm` is reserved for D3.

## Rules (22)

Each rule has a planted tree at `tests/fixtures/scenario_contract/<CODE>/` that breaks only that rule. Planted Python must be valid and must pass `ruff check` and `ruff format --check`; a deliberately bad import carries `# noqa: F401`.

| Code | Origin | Fires when |
|---|---|---|
| PARSE_ERROR | core | gherkin-official raises on a file |
| NO_FEATURES | core | the features directory holds no `.feature` |
| NO_SCENARIOS | core | a feature has no scenario |
| NO_STEPS | core | a scenario (after Background) has no step |
| NO_EXAMPLES | core | a Scenario Outline has no Examples row |
| NO_GATING_SCENARIOS | core | every scenario in the tree is `@wip` or `@manual` |
| UNBOUND_STEP | core | a gating step matches no definition of a source its promise is declared bound by (D1: `python`) |
| AMBIGUOUS_STEP | core | a gating step matches more than one definition of one source |
| BAD_PROMISE_ID | core, strengthened | a gating scenario has no `@promise:` tag or more than one, or the id breaks `[A-Za-z0-9][A-Za-z0-9._-]*` |
| DUPLICATE_PROMISE | core | one id appears on two scenarios |
| WIP_MISSING_OWNER | core | `@wip` without `@wip-owner:` |
| WIP_MISSING_SINCE | core | `@wip` without `@wip-since:` |
| BAD_WIP_OWNER | core | the owner handle breaks the id character set |
| BAD_WIP_SINCE | core | the since value is not a real `YYYY-MM-DD` date |
| BAD_DEFECT | core | the `@defect:` value is not a positive integer |
| BAD_QA_REF | core | the `@qa:` value breaks the id character set |
| UNKNOWN_PREFIXED_TAG | core | a tag with `:` and a prefix outside `promise`, `wip-owner`, `wip-since`, `defect`, `qa` |
| BAD_BARE_TAG | core | a bare tag breaks `[A-Za-z0-9][A-Za-z0-9_-]*` |
| UNREGISTERED_PROMISE | events (D-2) | a tag is missing from its area's `PROMISES.md`, a row has no scenario, or an area has scenarios but no `PROMISES.md` |
| BAD_BINDING_DECLARATION | events (D-2) | a Binding value is outside `python` / `python, jvm` / `@wip`; `@wip` disagrees with the scenario's tag; or a named binding has no step source given |
| STEPS_TABLE_DRIFT | events (D-2) | an index row (`Arrange`/`Assume` → Given, `Act` → When, `Assert` → Then) has no definition of that keyword, or a definition has no row. Placeholders are normalised: `{name}` / `{name:fmt}` ⇔ `<name>`, with or without surrounding quotes |
| FORBIDDEN_TEST_IMPORT | events (D-2) | a module in a step source imports `tests` or `tests.<x>` where `<x>` is not `scenarios` (`import` or `from … import`, absolute or relative beyond the source root) |

**Not carried from core**:
- UNSUPPORTED_EXPRESSION: an unread step-definition form surfaces as UNBOUND_STEP.
- NO_STEP_DEFINITIONS and STEP_FILE_UNREADABLE: a missing or unreadable source is a usage error, exit 2.

Both points are recorded under deviation D-2.

## Register and index grammar (shared by WP03 and WP04)

- **Index** (`tests/scenarios/README.md`): the steps table sits under a heading `## Available steps`, as a Markdown table with header `| Group | Step |`.
  - Each row looks like ``| Arrange | `Given the conformance fixtures of class "<fixture_class>"` |``.
  - The group is one of Arrange, Assume, Act or Assert. The step cell is one code span: the keyword, a space, then the phrase.
  - A placeholder is written `<name>`, using the same `name` as the step definition's `{name}` or `{name:fmt}` field.
  - Rows outside that table are ignored.
- **Register** (`<area>/PROMISES.md`): one `## <title> — \`<behaviour>/\`` section per behaviour, each with a table whose header is `| Promise | Consumer guarantee | Authority | Binding |`.
  - The Promise cell is a code span `` `PR-…` ``.
  - The Binding cell is `python`, `python, jvm` or `@wip`, optionally in a code span.
  - Other tables in the file are ignored.

## Mutation tests (SC-004, SC-002)

- **One table drives the tests**: (promise, fixture file, mutation, expected failing scenarios). It runs in-process with `pytester` and the arguments `-p no:cacheprovider -o addopts= --no-cov`.
- **Grouping**: mutations whose classes are disjoint share a run. Each group asserts the exact set of failing scenario ids.
- **Shared class**: promises 008 and 009 share `envelope_strict_journal`. Mutating `unknown_event_type.json` must fail exactly {008, 009}, and mutating `skew_missing_version.json` (reordering its codes) must fail exactly {008}.
- **Further cases**: a planted unregistered file fails its class's coverage step; a removed registered file fails the Arrange step; an added correct fixture raises the verdict-call count by one and passes.
- **Fixture root**: `SPEC_KITTY_SCENARIO_FIXTURES` overrides it. The variable is test-only, documented in `tests/scenarios/conftest.py`, and read in one place, the Arrange step, at call time.
