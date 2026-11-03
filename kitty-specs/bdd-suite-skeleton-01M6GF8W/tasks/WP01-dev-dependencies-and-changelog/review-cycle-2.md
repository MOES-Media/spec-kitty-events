---
affected_files: []
cycle_number: 2
mission_slug: bdd-suite-skeleton-01M6GF8W
reproduction_command:
reviewed_at: '2026-11-03T11:20:39Z'
reviewer_agent: claude
wp_id: WP01
---

# WP01 reopened by the orchestrator (scope addition, not a defect)

The WP02 review found that `scripts/check_version_not_amended.py` (ADR 0005) rejects the mission's `src/` change while the version is the already-tagged `11.3.0`. Spec ruling R4 makes the change a minor release, so implement the new subtask **T023**, "Declare version 11.4.0", in the WP prompt.

T001–T003 were approved and stay as they are; only add T023. Validation for T023:
- `tests/test_compatibility_doc.py` is green;
- `tests/test_version_not_amended.py` is green;
- `scripts/check_version_not_amended.py` exits 0;
- changelog `check` and `guard` are green.
