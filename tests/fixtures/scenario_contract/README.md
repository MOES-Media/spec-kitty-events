# Planted trees for the scenario contract check

Data for `tests/test_scenario_contract.py`, which proves every rule of
`scripts/scenario_contract.py` can fail (FR-012). The contract is
`kitty-specs/bdd-suite-skeleton-01M6GF8W/contracts/scenario-contract-check.md`.

## Layout

Each tree mirrors the real suite in miniature:

```
<tree>/
  README.md                         the steps index (`## Available steps`)
  features/demo/PROMISES.md         the promise register of the one area, `demo/`
  features/demo/greeting/*.feature  one behaviour, two scenarios
  steps/demo_steps.py               the Python step source
```

- `_clean/` is the valid baseline. The check reports nothing on it.
- `<CODE>/`, one directory per problem code (22), is `_clean/` with exactly one defect. The
  check reports that code and no other error. The directory name is the code.
- `_relative_import/` holds only a step source, for the relative-import case of
  FORBIDDEN_TEST_IMPORT.

The test parametrizes over the directories that do not start with `_` or `.`, and checks that
their names equal the module's 22 code constants, so no rule goes unplanted.

## Rules for editing

- Keep each `<CODE>/` tree one defect away from `_clean/`. Change `_clean/` first, then
  re-derive the trees; `diff -r _clean <CODE>` shows the defect.
- The step modules are valid, ruff-clean Python named `*_steps.py`. The check reads them
  statically; pytest never imports them (`conftest.py` sets `collect_ignore_glob = ["*"]`).
  A deliberately bad import carries `# noqa: F401`.
- `NO_FEATURES/features/.gitkeep` exists because git tracks no empty directory; the check
  ignores files that are not `.feature`.
