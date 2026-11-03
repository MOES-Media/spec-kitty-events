---
affected_files: []
cycle_number: 3
mission_slug: bdd-suite-skeleton-01M6GF8W
reproduction_command:
reviewed_at: '2026-11-03T11:28:36Z'
reviewer_agent: claude
wp_id: WP01
---

# WP01 review, cycle 2: rejected (1 MAJOR)

T001 to T003 are unchanged from the approved cycle 1 (commit a6e05466; the only later change to its files is the
`pyproject.toml` version line). Every version declaration T023 lists is correct. The listed gates pass. The reason for
rejection is one declaration that T023's list leaves out.

## [MAJOR] The Java binding version is still 11.3.0, so the Gradle version-coupling check fails

- `java/build.gradle.kts:14` still says `version = "11.3.0"`. The comment just above it reads "Must equal
  [project].version in pyproject.toml: one version line for both artifacts (ADR 0004)". ADR 0004 decision 3 says
  "The Java binding is on the package line."
- `checkVersionMatchesPyproject` (`java/build.gradle.kts:53-71`, wired into `tasks.check`) throws
  `java-binding version 11.3.0 differs from pyproject.toml version 11.4.0 (ADR 0004)`. That fails
  `:java-binding:check`, and with it `make test-java`, `make test-gradle`/`verifyAll` and `make test-full`, which is
  the CI agent's suite. Any later PR or `main` push that touches `java/**` or the producer contract also fails
  `service-gate`.
- Evidence: Gradle could not run here because Maven Central returned HTTP 429, so I ran the task's own logic in
  Python against the lane tree: pyproject 11.4.0, java 11.3.0, DRIFT.

**Fix:** set `java/build.gradle.kts` line 14 to `version = "11.4.0"`, and change nothing else in that file. The file
is not among WP01's `owned_files`, so the **planner** must first add `java/build.gradle.kts` to WP01's owned files and
to T023's edit list. That is the same kind of extension that added T023. Then run
`make test-java` (or `./gradlew :java-binding:checkVersionMatchesPyproject`) and record the result.

These were checked and should **not** move. They are port-review pins, not the working-tree version:
- `StatusReducer.PORTED_EVENTS_VERSION`;
- `service/src/test/resources/conformance/manifest.json` `specKittyEventsVersion` (`ManifestCouplingTest` couples
  these two to each other, not to pyproject).

## Verified green (no action)

- Root `uv.lock` entry: 11.4.0 is the only lock change, and `uv lock --check` passes.
- `__version__`: only that line changed.
- README: the declaration and both `pip install` lines.
- COMPATIBILITY.md:
  - The current-version line is updated.
  - The new 11.4.0 section sits above 11.3.0 and is accurate: it is additive, names `class_fixture_verdict`, and
    says the suite is not shipped.
  - It has an `### Adopting 11.4.0` subsection.
- CHANGELOG.md: only the `[Unreleased]` opening paragraph changed, and no `###` subsection moved.
- `test_compatibility_doc.py` + `test_version_not_amended.py`: 32 passed.
- `check_version_not_amended.py`: ok.
- `changelog.py check` and `guard`: both pass.
- Conformance: 1200 passed.
- `ruff check .`: clean.
- Scope: f4e97466 touches only the six owned files.

## Minor (non-blocking)

- CHANGELOG.md `[Unreleased]` paragraph: the second line ("moves to `11.4.0` for a new public conformance function.
  This repository becomes the home of the") is longer than the surrounding wrap width. Reflow it while you are there.
