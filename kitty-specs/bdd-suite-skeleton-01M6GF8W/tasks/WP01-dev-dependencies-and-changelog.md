---
work_package_id: WP01
title: Dev dependencies, changelog and the 11.4.0 version declaration
dependencies: []
requirement_refs:
- C-002
- C-003
- FR-020
- FR-022
- NFR-005
planning_base_branch: issue-197-bdd-suite-skeleton
merge_target_branch: issue-197-bdd-suite-skeleton
branch_strategy: Planning artifacts for this mission were generated on issue-197-bdd-suite-skeleton. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into issue-197-bdd-suite-skeleton unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-bdd-suite-skeleton-01M6GF8W
base_commit: 1489d53a2082c0a2ed1c8dcb724a7ffe31551f47
created_at: '2026-11-03T11:05:46.266272+00:00'
subtasks:
- T001
- T002
- T003
- T023
phase: Phase 1 - Foundations
agent: claude
history:
- '2026-11-03: created by /spec-kitty.tasks'
agent_profile: python-pedro
authoritative_surface: pyproject.toml
create_intent:
- docs/changelog/unreleased/197-bdd-suite-skeleton.md
execution_mode: code_change
owned_files:
- pyproject.toml
- uv.lock
- docs/changelog/unreleased/197-bdd-suite-skeleton.md
- src/spec_kitty_events/__init__.py
- COMPATIBILITY.md
- README.md
- CHANGELOG.md
- java/build.gradle.kts
role: implementer
tags: []
tracker_refs: []
---

# WP01 — Dev dependencies, changelog and the 11.4.0 version declaration

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load the assigned profile with the `/spk-charter-profile-load` skill (profile `python-pedro`). Then load governance with `spec-kitty charter context --action implement`. Then read, in `kitty-specs/bdd-suite-skeleton-01M6GF8W/`:
- `spec.md`: FR-020, FR-022, C-003;
- `plan.md`: approach 6;
- `research.md`: R-2, R-3 and R-6.

## Objective

Make `pytest-bdd` and `gherkin-official` available wherever the repo's tests run:
- the `dev` dependency group, used by `uv run` and `make test-fast`;
- the `[project.optional-dependencies].dev` extra, installed by the required `acceptance` check as `.[dev,conformance]`.

Lock them reproducibly at pytest-bdd 9.0.1, prove that the published package's base requirements are unchanged, and record the mission's change as a single changelog fragment.

## Branch Strategy

The planning base and the merge target are both `issue-197-bdd-suite-skeleton`. The workspace is the lane worktree that `finalize-tasks` computed (`lanes.json`). Start with:

```bash
spec-kitty agent action implement WP01 --agent <name> --mission bdd-suite-skeleton-01M6GF8W
```

## STOP conditions (escalate, do not decide)

- The lock would change the version of any package already in `uv.lock` other than by adding new ones. `typing-extensions` and `packaging` are already locked and must not move.
- A runtime dependency (`[project].dependencies`) would need to change.
- pytest-bdd 9.0.1 cannot resolve against the locked pytest 9.1.1.

## Subtasks

### T001 — Add dev dependencies and relock

1. In `pyproject.toml`:
   - In `[dependency-groups].dev`, add after `pyyaml`:
     ```toml
     # Scenario suite (tests/scenarios, #197): the reference step binding and the Gherkin
     # parser the contract check (scripts/scenario_contract.py) imports directly.
     "pytest-bdd>=9.0.1,<10",
     "gherkin-official>=29,!=31.0.0,!=32.0.0",
     ```
   - In `[project.optional-dependencies].dev`, add the same two lines. `acceptance.yml` installs this extra, not the group.
   - Do not touch `[project].dependencies` or the `conformance` extra.
2. Relock, holding pytest-bdd at the version vetted in research R-3:
   ```bash
   uv lock --upgrade-package pytest-bdd==9.0.1
   ```
   - If `parse` resolves to anything newer than 1.22.4, re-run with `--upgrade-package parse==1.22.4`.
   - Record the resolved versions of pytest-bdd, gherkin-official, mako, MarkupSafe, parse, parse-type and six.
3. Run `git diff uv.lock` and confirm that it only adds packages, plus the root project's dependency lists. The diff must not change any pre-existing package version.
4. Run `uv sync` and then `uv run python -c "import importlib.metadata as m, pytest_bdd, gherkin; print(m.version('pytest-bdd'))"`. pytest-bdd has no `__version__` attribute.

**Validation**:
- Both lists contain both lines.
- The lock holds pytest-bdd 9.0.1. Its floor matters: 9.0.0 breaks on pytest 9.2.0 (`FixtureManager` has no `_arg2fixturedefs`), and `acceptance` installs unlocked (post-tasks squad, I-m1).
- No existing locked version changes.

### T002 — Verify the wheel metadata

1. Run `uv build --wheel -o /tmp/<scratch>/dist`, or `python -m build --wheel`, as `acceptance` does.
2. Extract `*.dist-info/METADATA` and compare its `Requires-Dist` lines with the same build from `main` at branch point. Use `git stash` or a temporary worktree of `origin/main`.
3. The expected difference is exactly two added lines, each ending `; extra == "dev"`, one for pytest-bdd and one for gherkin-official. Lines without an `extra ==` marker must be byte-identical.
4. Paste both metadata excerpts into the WP handoff note, where the reviewer checks them. Commit no build output.

**Validation**: the base requirement lines are identical and only two `extra == "dev"` lines are added (squad R-M2).

### T003 — Changelog fragment [P]

Create `docs/changelog/unreleased/197-bdd-suite-skeleton.md` following `docs/changelog/unreleased/README.md`:

```markdown
---
section: Added
---

- A technology-agnostic Gherkin scenario suite for the event contract (`tests/scenarios/`, #197, slice D1 of #121). It follows core's scenario conventions: promise tags, `@wip` ownership and per-area `PROMISES.md` registers. Its Python reference step binding checks the verdict each committed conformance fixture pins, never a copy of it. The first area, `envelope/`, holds ten promises: canonical and synthesized envelopes accepted; forbidden key, unknown lane, payload schema and bad shape refused with their pinned codes; raw historical rows refused; the strict journal profile's ordered codes, including an unknown event type, which fails closed; and legacy lane mapping.
  - New public function `spec_kitty_events.conformance.class_fixture_verdict(fixture_class, fixture_input)`. It returns the class-taxonomy envelope verdict that the class conformance test and the step binding share. Its check order is now documented contract in `src/spec_kitty_events/conformance/README.md`. Additive: no fixture, schema or verdict changes.
  - New per-PR contract check `scripts/scenario_contract.py`, also run by `make lint`. It enforces core's scenario rule codes, plus the events-specific promise-register, binding-declaration, steps-table and test-import rules.
  - New dev dependencies `pytest-bdd` and `gherkin-official`, in the dependency group and the `dev` extra. Runtime requirements are unchanged.
```

Then run `uv run python scripts/changelog.py check && uv run python scripts/changelog.py guard`, and `grep -n 'class_fixture_verdict' docs/changelog/unreleased/197-bdd-suite-skeleton.md`, which is FR-022's executable check. Do **not** edit `CHANGELOG.md`.

**COMPATIBILITY.md**: add no entry. Its sections are written per release, by the release PR, which folds this fragment into the next minor's section. Say so in the handoff.

### T023 — Declare version 11.4.0 (added after the WP02 review, 2026-11-03)

**Why**: `scripts/check_version_not_amended.py` (ADR 0005, Consequences) rejects any `src/` change while the working-tree version is already released as a tag. `v11.3.0` exists, and WP02 adds `src/spec_kitty_events/conformance/class_verdict.py`. Spec ruling R4 makes that new public symbol a **minor** release, so the declaration becomes `11.4.0`. The version stays unreleased (no tag) until the release PR.

Edit only the version declarations:
1. `pyproject.toml`: set `version = "11.4.0"`. Then run `uv lock`. The root package's entry in `uv.lock` moves to 11.4.0, and nothing else may change; confirm with `git diff uv.lock`.
2. `src/spec_kitty_events/__init__.py`: `__version__ = "11.4.0"`. Touch nothing else in that file.
3. `README.md`: the `**Package Version**` declaration and the two `pip install "spec-kitty-events...==11.3.0"` lines become 11.4.0 (`tests/test_compatibility_doc.py` pins the declaration).
4. `COMPATIBILITY.md`:
   - set the `**Current package version**` line to `11.4.0`;
   - add a new section above the `11.3.0` one, headed ``## `11.4.0` — envelope verdict made public, contract scenario suite (minor)``. It says the release is additive: no envelope, payload, schema, fixture or verdict changes. It names the new public `spec_kitty_events.conformance.class_fixture_verdict` and its documented check order (link `src/spec_kitty_events/conformance/README.md`), and notes the repository-only scenario suite (`tests/scenarios/`, not shipped).
   - Add a short `### Adopting 11.4.0` subsection: core and saas need no change; another binding can reproduce the envelope verdict from the documented order.
   - Read the 11.2.1 and 11.3.0 sections for tone and shape, and keep the section-ordering contract that `tests/test_compatibility_doc.py` checks.
6. `java/build.gradle.kts`: change only line 14, `version = "11.3.0"`, to `"11.4.0"`. ADR 0004 decision 3 keeps one version line for both artifacts, and the `checkVersionMatchesPyproject` task (run by `:java-binding:check`, `make test-java` and `verifyAll`) fails if the two differ (WP01 review, cycle 2). Do **not** touch `StatusReducer.PORTED_EVENTS_VERSION` or the service conformance `manifest.json` `specKittyEventsVersion`; those are tied to the port review, not to pyproject.
5. `CHANGELOG.md`: change **only** the opening paragraph of `## [Unreleased]` ("…the version stays `11.3.0`…"), which the fragments README allows a version-bumping PR to correct. It should say the version moves to `11.4.0` for a new public conformance function, and keep the sentence about the services. Do **not** touch any `###` subsection; `changelog.py guard` enforces this.

**Validation**:
- `uv run pytest tests/test_compatibility_doc.py tests/test_version_not_amended.py --no-cov -q` is green.
- `uv run python scripts/check_version_not_amended.py` exits 0.
- `make test-java` passes, or, if Maven Central rate-limits the sandbox (HTTP 429), the Python equivalent of `checkVersionMatchesPyproject` passes: `java/build.gradle.kts` `version` equals the `pyproject.toml` `version`. Record which one ran.
- `changelog.py check` and `guard` are green.

Every work package also runs the gate set from CLAUDE.md before handoff:

```bash
make test-fast
uv run pytest --pyargs spec_kitty_events.conformance -q      # count must equal main's
uv run ruff check . && uv run ruff format --check .
uv run python scripts/changelog.py check && uv run python scripts/changelog.py guard
```

## Definition of Done

- T001 to T003 are done and recorded with `mark-status`.
- `uv sync` works.
- The metadata diff is pasted in the handoff.
- Changelog `check` and `guard` are green.
- `ruff check . && ruff format --check .` is green.
- `uv run pytest --pyargs spec_kitty_events.conformance -q` is green. Record the count; it must equal `main`'s.

## Reviewer guidance

- Confirm that the `uv.lock` diff only adds packages.
- Confirm the two `extra == "dev"` metadata lines.
- Confirm the fragment parses: `changelog.py check` passes.
- Confirm that `[project].dependencies` is untouched.
