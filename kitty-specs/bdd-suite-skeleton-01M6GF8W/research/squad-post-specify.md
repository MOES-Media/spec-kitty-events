# Adversarial squad — post-specify (2026-11-03)

Question: is spec revision 1 fakeable, does it contradict an existing authority, and is its scope and boundary right for a suite that a second language binding must reuse?

Each delegate was profile-loaded with `spec-kitty agent profile show` and `charter context --action specify`, and worked read-only.

| Delegate | Lens | Verdict |
|---|---|---|
| reviewer-renata | Fakeable or vacuous criteria | Changes requested (4 MAJOR) |
| doctrine-daphne | Authority overlap, convention fidelity | Revise (3 MAJOR) |
| architect-alphonso | Scope and boundary for cross-binding reuse | Changes requested (2 MAJOR) |

Synthesis: two delegates independently found the same root cause, A-M1 and R-M4. The envelope verdict and its check order exist only as a private function of a test module. Option A from A-M1 (a public conformance function) was escalated to the operator under C-007 and accepted as ruling R4 (decision `01M6GG0TNP61KD4J3YP1AGKQDG`). None of the remaining findings diverged, so no second opinion was needed.

## Dispositions

| # | Finding (short) | Disposition | Evidence (spec revision 2) |
|---|---|---|---|
| R-M1 | Strict scope is one single-code fixture; ordered-list edge case is vacuous; strict class register undefined | accepted | FR-016 covers the whole `envelope_strict_journal` class; edge case "several ordered codes"; Fixture register term; SC-004 reorders a multi-code list |
| R-M2 | Evaluated count equals registered entries compares a value with itself | accepted | SC-002 counts verdict calls against an independent disk glob; a planted skipped fixture fails; US2 |
| R-M3 | Real-tree clean check is vacuous on a wrong root | accepted | FR-012 and SC-003 require at least 1 feature and at least 10 promises discovered |
| R-M4 | FR-010 met by moving code without proving equivalence | changed (R4) | FR-010 public function; SC-005 identity check, existing test unchanged and passing |
| R-m1 | Selector "manifest entry id" ambiguous across two registers | accepted | FR-006 and the Fixture register term |
| R-m2 | Mutation field unspecified; -007 code mutation invisible; README caveat list incomplete | accepted | SC-004 (-007 flips `expected`); Edge case corrects the README list |
| R-m3 | `@wip` could exempt the envelope promises | accepted | SC-001 requires gating scenarios; edge case: 0 `@wip` in `envelope/` |
| R-m4 | FR-009 has no negative control | accepted | FR-011 FORBIDDEN_TEST_IMPORT plus a planted example |
| R-m5 | "At every depth" cannot be tested | accepted | FR-014 "each fixture of the class" |
| R-n1 | Scratch-copy checks have no harness | accepted | SC-002 and SC-004 are committed tests over a temporary copy |
| D-M1 | Checker reads Python, not Java: an undeclared deviation | accepted | Intent Summary D-1; FR-011 takes more than one source |
| D-M2 | Coverage declaration and drift rule are not core's; no codes named | accepted | Intent Summary D-2; FR-011 names core and events-specific codes |
| D-M3 | `acceptance` claim omits the dev dependency and the test entry point | accepted | FR-020, FR-021; edge case for `pr:pause-ci` |
| D-m1 | User Story 4 groups differ from FR-002 | accepted | US4 uses four groups |
| D-m2 | `@wip` grammar deferred though it is fixed in core; closed vocabulary unaddressed | accepted | FR-004 |
| D-m3 | PROMISES.md columns and the single source of coverage truth | accepted | FR-002 core columns; FR-005 Binding column is the single source |
| D-m4 | FR-015 must match the class test; cite the registers | accepted | FR-007 (historical: refusal only), FR-010, Fixture register term |
| D-n1 | "Binding" collides with "language binding" | accepted | Domain Language: step binding versus language binding |
| A-M1 | FR-009 with FR-010 forces a public symbol | changed (R4, escalated) | Intent Summary R4; FR-010 |
| A-M2 | Black-box claim versus a check order only in tests; Java cannot bind envelope | accepted | FR-019 documents the check order; US5; Scope honesty note |
| A-m1 | Per-area coverage cannot express a partial JVM subset | accepted | FR-005 coverage per promise |
| A-m2 | Layout and id deviations from core | accepted (adopt core) | FR-001 (core layout), FR-002 (per-area PROMISES), FR-003 (core grammar) |
| A-m3 | Checker hard-codes one binding | accepted | FR-011 one or more step-definition sources |
| A-m4 | Strict class register differs; FR-010 scope | accepted | Fixture register term; FR-016 uses the public strict validator |
| A-n1 | Layout is not split-brain | no change needed | — |
| A-n2 | Scope split is right | no change needed | — |

Follow-up: #199's text claims that the JVM binding can cover `envelope/` scenarios. It will be corrected by a comment when D1's PR opens (spec Assumptions).
