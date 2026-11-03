---
work_package_id: WP03
title: Scenario contract check
dependencies:
- WP01
requirement_refs:
- C-004
- C-005
- FR-011
- FR-012
- SC-003
planning_base_branch: issue-197-bdd-suite-skeleton
merge_target_branch: issue-197-bdd-suite-skeleton
branch_strategy: Planning artifacts for this mission were generated on issue-197-bdd-suite-skeleton. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into issue-197-bdd-suite-skeleton unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-bdd-suite-skeleton-01M6GF8W
base_commit: 142121f1ba59d908fb335030fa07e47367cb37a3
created_at: '2026-11-03T11:16:13.896446+00:00'
subtasks:
- T009
- T010
- T011
- T012
- T013
phase: Phase 2 - Suite and its gate
agent: claude
history:
- '2026-11-03: created by /spec-kitty.tasks'
agent_profile: python-pedro
authoritative_surface: scripts/scenario_contract.py
create_intent:
- scripts/scenario_contract.py
- tests/test_scenario_contract.py
- tests/fixtures/scenario_contract/README.md
execution_mode: code_change
owned_files:
- scripts/scenario_contract.py
- tests/test_scenario_contract.py
- tests/fixtures/scenario_contract/**
role: implementer
tags: []
tracker_refs: []
---

# WP03 — Scenario contract check

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load the assigned profile with the `/spk-charter-profile-load` skill (profile `python-pedro`). Then load governance with `spec-kitty charter context --action implement`.

Read, in `kitty-specs/bdd-suite-skeleton-01M6GF8W/`:
- `contracts/scenario-contract-check.md`, **the contract you implement**: CLI, output and the 22 rules;
- `spec.md`: FR-011, FR-012, the Intent Summary deviations D-1 and D-2;
- `research.md`: R-4;
- `plan.md`: approach 5.

Core's checker is the model. Read it for structure and messages but **do not import it** (C-002): `/home/user/spec-kitty/spec-kitty/scripts/ci/scenario_contract.py`, a sparse read-only checkout; re-clone it with `git clone --depth 1 --filter=blob:none --sparse https://github.com/spec-kitty/spec-kitty` plus `sparse-checkout set scripts/ci tests/architectural` if it is missing. Read its `test_scenario_contract.py` for the planted-tree pattern.

## Objective

Write a dependency-light, JDK-free checker that refuses a malformed scenario suite with stable codes. Prove every rule with a planted tree. WP05 wires it into `make lint` once the real tree exists. The real tree does not exist yet; WP04 creates it and WP05 adds the real-tree run. This WP's tests use planted trees only.

## Branch Strategy

The planning base and the merge target are both `issue-197-bdd-suite-skeleton`. The workspace is the lane worktree from `lanes.json`:

```bash
spec-kitty agent action implement WP03 --agent <name> --mission bdd-suite-skeleton-01M6GF8W
```

## STOP conditions

- A rule in the contract seems impossible to plant in isolation, because the tree inevitably triggers a second code. Report it, and do not loosen "exactly one code".
- The `gherkin-official` API differs from what is described below (inspect it with `uv run python -c "import gherkin, inspect; ..."`).

## Subtasks

### T009 — Scaffold: CLI, Problem model, parsing, tag inheritance

- **File**: `scripts/scenario_contract.py`. Its module docstring gives the purpose, a link to the contract document, the deviations D-1 and D-2 from core, and its known limits.
- **`Problem`**: `@dataclass(frozen=True)` with `code`, `severity` (`"error"` or `"info"`), `file`, `line` and `message`. Define one constant per code.
- **CLI** (`argparse`):
  - `--features` (default `tests/scenarios`), `--steps NAME=DIR` (repeatable; default `python=tests/scenarios/steps`) and `--index` (default `tests/scenarios/README.md`).
  - Paths are resolved against the repo root (`Path(__file__).resolve().parents[1]`) when relative.
  - Exit 2 on a usage error: an unknown NAME, or a missing directory or file.
  - Print the sorted findings as `<severity> <code> <file>:<line> <message>`, with `file` relative to the features root.
  - Exit 1 if there are any errors, otherwise 0.
- **Public functions for tests**:
  - `check(features: Path, steps: Mapping[str, Path], index: Path) -> list[Problem]`;
  - `discover(features: Path) -> Discovery`, a frozen dataclass with `feature_files: tuple[str, ...]` and `promise_ids: tuple[str, ...]`, both sorted. WP05's real-tree floor uses it (post-tasks squad P-M1);
  - `main(argv: Sequence[str] | None = None) -> int`.
- **Order of work**: T009 → T010 → T011 → T012 → T013, with a planted tree added for each rule as soon as that rule exists. If the WP runs long, land the 18 core rules (T009–T011 and their trees) first and report; do not drop rules.
- **Parsing**: `Parser().parse(TokenScanner(text))` (gherkin-official 42; prototyped by the squad) returns a dict.
  - Tags carry `@` and `location.line`. Children are `background`, `rule` and `scenario`. Outlines have `examples[].tableBody[]`. Steps carry `keywordType` (`Context`, `Action`, `Outcome`, `Conjunction`), and keywords keep a trailing space.
  - Errors raise `CompositeParserException`; take each line from `.errors[i].location`. Each becomes one PARSE_ERROR.
  - Under `mypy --strict`, narrow children with `typing.cast` to the TypedDicts in `gherkin.parser_types`.
  - Walk Feature → (Rule →) Background, Scenario and Scenario Outline, collecting each scenario's effective tags: the union of Feature, Rule and scenario tags with the `@` stripped. For an outline, tags on an Examples block apply to that block's rows. Model each row as its own instance, as core does.
  - Background steps belong to the scenarios that follow it.
  - `And` and `But` take the keyword of the previous step.
  - **Gating** means the effective tags contain neither `wip` nor `manual`.
- Sort files by path, for determinism (NFR-004).

### T010 — Python step-source reader and matcher

- **`read_python_steps(root: Path) -> tuple[list[StepDefinition], list[Problem]]`**: `ast.parse` every `*.py` under `root`.
  - Track `from pytest_bdd import given, when, then, parsers`, including `as` aliases, and `import pytest_bdd`. Recognise decorators whose function is one of those names: `given`, `when` or `then`, attribute or bare.
  - Read the first positional argument (or the `name=` keyword) when it is a string `Constant`, or a `Call` to `parsers.parse` whose single argument is a string `Constant`.
  - Read every decorator in a stacked list.
  - Ignore any other form, so its steps stay UNBOUND_STEP. Record the file and line on each `StepDefinition(keyword, pattern, regex, file, line)`.
- **Pattern to regex**:
  - A plain string matches the step text exactly (`re.escape` it).
  - A `parse` string turns `{name}` into `(?P<name>.+?)`, and `{name:d}` into `(?P<name>-?\d+)`; any other format spec becomes `(.+?)`. Escape the literal text in between, and anchor with `^...$`.
- **Matcher**: for each gating scenario, read the step sources named in its promise's register row (see T012). In D1 that is always `python`. A scenario whose row is missing is matched against `python` alone, so the binding checks still run while UNREGISTERED_PROMISE reports the missing row.
  - Zero matches of the same keyword give UNBOUND_STEP.
  - More than one match gives AMBIGUOUS_STEP.
  - In a non-gating scenario, the same conditions are reported as `info`, not `error`.
- Core matches step keywords (Given, When, Then) strictly, and pytest-bdd also binds by keyword, so a `When` step must match a `when` definition.

### T011 — Structural and tag rules (core codes)

Implement these codes exactly as the contract describes. Take the regexes from core: id `[A-Za-z0-9][A-Za-z0-9._-]*`, bare tag `[A-Za-z0-9][A-Za-z0-9_-]*`, issue number `[1-9][0-9]*`, and a date that must also parse with `datetime.date.fromisoformat`.

PARSE_ERROR, NO_FEATURES, NO_SCENARIOS, NO_STEPS, NO_EXAMPLES, NO_GATING_SCENARIOS, BAD_PROMISE_ID, DUPLICATE_PROMISE, WIP_MISSING_OWNER, WIP_MISSING_SINCE, BAD_WIP_OWNER, BAD_WIP_SINCE, BAD_DEFECT, BAD_QA_REF, UNKNOWN_PREFIXED_TAG and BAD_BARE_TAG.

Notes:
- **BAD_PROMISE_ID is strengthened.** A *gating* scenario with zero `promise:` tags, or more than one, is an error. A `@wip` scenario may lack one.
- **DUPLICATE_PROMISE** is checked across the whole tree.
- **Allowed prefixes**: `promise`, `wip-owner`, `wip-since`, `defect` and `qa`. The bare tags `wip` and `manual` have meaning, and any other bare tag that passes the regex is allowed.

### T012 — Events-specific rules

- **Registers**: for each area, meaning each top-level directory of the features root that contains `.feature` files, read `<area>/PROMISES.md`. Rows are Markdown table lines whose first cell is `` `PR-...` ``; record the Promise and Binding cells.
  - **UNREGISTERED_PROMISE**: a promise tag in the area with no row; a row whose promise no scenario carries; or an area with features but no `PROMISES.md`.
  - **BAD_BINDING_DECLARATION**:
    - a Binding cell outside `python`, `python, jvm` or `@wip`;
    - `@wip` on a non-wip scenario, or a non-`@wip` value on a wip scenario;
    - a binding name in the cell that is not in `--steps`. In D1, `jvm` always errors.
- **STEPS_TABLE_DRIFT**: parse `--index`. Rows look like `| Arrange | \`Given the conformance fixtures of class "<class>"\` |`.
  - Map Arrange and Assume to `given`, Act to `when`, and Assert to `then`. Strip the keyword word from the phrase.
  - Normalise both sides: `{name}` and `{name:fmt}` become `<name>`, then compare the strings, so `"<class>"` equals `"{fixture_class}"` only if the names agree. Make the index use the same placeholder names as the step definitions, and document that in the README in WP04.
  - Report index rows with no definition of that keyword, and definitions (from the `python` source) with no row. The file and line point at the index row or at the definition.
- **FORBIDDEN_TEST_IMPORT**: for every `.py` under each step source, walk `Import` and `ImportFrom`.
  - An absolute module `tests`, or `tests.<x>` where `<x>` is not `scenarios`, is an error.
  - A relative import that resolves above the source root, then into `tests/` outside `tests/scenarios/`, is also an error. Compute the resolution from the file's path relative to the repo root.

### T013 — Planted trees and `tests/test_scenario_contract.py`

- **Location**: one directory per code under `tests/fixtures/scenario_contract/<CODE>/`, holding `features/`, `steps/` and, where needed, `README.md` and `<area>/PROMISES.md`.
- **The NO_FEATURES tree** contains `features/.gitkeep`, because git tracks no empty directory. The checker ignores non-`.feature` files.
- **The PARSE_ERROR tree** keeps a second, valid feature that carries the registered promises, so that only PARSE_ERROR fires.
- **A shared clean baseline**: `tests/fixtures/scenario_contract/_clean/` is a minimal valid tree with one area `demo/`, one behaviour, two scenarios, a `PROMISES.md` and a README index, and its steps in `steps/demo_steps.py`. Each `<CODE>/` tree is the baseline with exactly one defect. Keep the trees tiny.
  - Keep the trees on disk rather than building them in `tmp_path`, so reviewers can read them.
  - A `README.md` in `tests/fixtures/scenario_contract/` explains the layout.
- **Import**: the test imports the checker as `tests/test_changelog_fragments.py:21-22` does (`sys.path.insert` of `scripts/`, then `import scenario_contract`).
- **The test** is parametrized over `sorted(p.name for p in DIR.iterdir() if p.is_dir() and not p.name.startswith(("_", ".")))`. That excludes `_clean`, `README.md`, `conftest.py` and `__pycache__`. For each tree:
  - run `check(tree/"features", {"python": tree/"steps"}, tree/"README.md")`;
  - assert that the set of error codes equals `{CODE}`, where the directory name is the code;
  - also assert `_clean` gives `[]`.
  - Add a test that the set of directories equals the set of the module's 22 code constants, so no rule goes unplanted.
- **Ruff-clean Python**: the planted step modules must be valid, ruff-clean Python. The FORBIDDEN_TEST_IMPORT tree's bad import uses `from tests.test_conformance_classes import EIGHT_CLASSES  # noqa: F401`. A PARSE_ERROR tree breaks only the `.feature` file.
- **Keep pytest from collecting planted steps.** Name planted step modules `*_steps.py` (not `test_*`). They must not import `pytest_bdd` at module import time in a way that registers fixtures globally; the checker reads them statically only, and pytest never imports them because they don't match `test_*.py`. Add `tests/fixtures/scenario_contract/conftest.py` with `collect_ignore_glob = ["*"]` as a belt-and-braces guard.
- Also test `discover()` on `_clean`: the expected feature files and promise ids.
- **Also test the CLI**: `main([...])` returns 1 on a planted tree, 0 on `_clean` and 2 on a missing directory.

## Gates

```bash
uv run pytest tests/test_scenario_contract.py --no-cov -q
uv run mypy --strict scripts/scenario_contract.py   # typed even though it is outside src/
```

Every work package also runs the gate set from CLAUDE.md before handoff:

```bash
make test-fast
uv run pytest --pyargs spec_kitty_events.conformance -q      # count must equal main's
uv run ruff check . && uv run ruff format --check .
uv run python scripts/changelog.py check && uv run python scripts/changelog.py guard
```


## Definition of Done

- 22 planted trees each give exactly their code, and `_clean` is clean.
- The CLI exit codes are tested.
- The coverage test (planted directories equal the code constants) passes.
- ruff and mypy are clean.

## Reviewer guidance

- Spot-check five planted trees: does each differ from `_clean` by one defect?
- Try one unread decorator form (`parsers.re`). It must give UNBOUND_STEP, not pass.
- Check that `info` versus `error` follows gating.
