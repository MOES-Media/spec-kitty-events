---
affected_files: []
cycle_number: 2
mission_slug: bdd-suite-skeleton-01M6GF8W
reproduction_command:
reviewed_at: '2026-11-03T12:20:35Z'
reviewer_agent: claude
wp_id: WP05
---

# WP05 reopened by the orchestrator (one gap from the approving review)

The spec's edge case "Several ordered codes" says a step binding that compares only the first code must fail SC-004's planted check. Reversing `skew_missing_version`'s two codes cannot catch that, because the first code changes either way. A binding comparing `actual[:1]` passes all 32 tests.

**Add**: a strict-journal mutation row that changes only the **second** code. For example, pin `skew_missing_version.json` `expected_error_codes` to `["ENVELOPE_SHAPE_INVALID", "ENVELOPE_SHAPE_INVALID"]`; it must fail exactly {008}. Run it in its own group, as strict rows must. Prove it by temporarily mutating the binding to compare only the first code: the new row must go red. Then revert.

**Optional, minor**: make case 3c's message assertion derive the disk count instead of hard-coding `4`.

Change nothing else.
