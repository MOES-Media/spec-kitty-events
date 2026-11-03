# Data model

## Feature file (Gherkin)

- **Feature**: title, user statement. Optional tags are inherited by its scenarios.
- **Scenario**: tags plus ordered steps. Gating means it is tagged neither `@wip` nor `@manual`.
- **Step**: a keyword (Given, When, Then, And, But) and text. `And` and `But` inherit the keyword of the step before them.

## Promise register row (`<area>/PROMISES.md`)

| Field | Rule |
|---|---|
| Promise | `` `PR-EVENTS-<AREA>-NNN` ``; it appears as `@promise:` on exactly one scenario of the area |
| Consumer guarantee | Plain-language statement |
| Authority | The spec FR, plus the fixture class or register id |
| Binding | `python`, `python, jvm` or `@wip`. It is `@wip` exactly when the scenario is tagged `@wip`. `jvm` requires a jvm step source |

Rows sit under one `## <feature title> — \`<behaviour>/\`` heading per behaviour folder, as core does.

## Fixture selection (step binding)

| Class | Register | Pin fields | Verdict source |
|---|---|---|---|
| the eight taxonomy classes | `manifest.json` → `classes.entries` (where `class` = name) | entry `expected`; file `expected_error_code` | `class_fixture_verdict` |
| `envelope_strict_journal` | `manifest.json` → `fixtures` whose `path` starts with `class_taxonomy/envelope_strict_journal/` | file `expected`; file `expected_error_codes` (ordered) | `strict.validate_strict_envelope` (codes in order) |

- **Invariants**:
  - The set of register paths equals the set of `*.json` files in the class folder, or the selection fails.
  - A non-empty selection is required.
  - The selection is ordered by path.
  - Every selected fixture is evaluated once, and the evaluated count is compared with the disk count.

## Verdict outcome

- `class_fixture_verdict`: `None` means accepted. A `ValidationError` carries `code`, `message`, `path` and `details`.
- Strict profile: a list of errors. An empty list means accepted; otherwise the codes are compared, in order, with `expected_error_codes`.

## Contract-check finding

A frozen record with `code`, `severity` (`error` or `info`), `file`, `line` and `message`. Exit status is 1 if any finding is an error.
