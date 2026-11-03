# Envelope promises

<!-- Frozen-contract index for the envelope/ scenarios (#197, slice D1 of #121). Each @promise id
tags exactly one scenario and names the contract guarantee it asserts. Scenarios name fixture
classes or register ids; the pinned verdicts live in the conformance package's manifest.json and
fixture files, never in a feature file. Updated: 2026-11-03. -->

Each row maps a `@promise:` id to the guarantee it asserts, the requirement and fixture register
that evidence it, and the step bindings that bind it. The Binding column is the single source of
coverage truth (FR-005).

`envelope/` is bound in Python only, by design (spec, "Scope honesty"): the Java binding validates
CloudEvents rows (`CloudEventValidator`: `type`, `source`, `missionid`, with its own issue codes),
not legacy `Event` envelopes, so it cannot bind these promises. JVM coverage starts with `upcast/`
in D3 (#199).

## Valid envelopes are accepted — `accepts-valid-envelopes/`

| Promise | Consumer guarantee | Authority | Binding |
|---------|--------------------|-----------|---------|
| `PR-EVENTS-ENVELOPE-001` | Every canonical envelope is accepted. | FR-013; class `envelope_valid_canonical` (`classes.entries`) | python |
| `PR-EVENTS-ENVELOPE-002` | Every envelope synthesized from a historical row is accepted. | FR-013; class `envelope_valid_historical_synthesized` (`classes.entries`) | python |

## Invalid envelopes are refused with their pinned reason — `refuses-with-pinned-reason/`

| Promise | Consumer guarantee | Authority | Binding |
|---------|--------------------|-----------|---------|
| `PR-EVENTS-ENVELOPE-003` | An envelope carrying a forbidden legacy key, at any depth or inside an array, is refused with exactly its pinned code. | FR-014; class `envelope_invalid_forbidden_key` (`classes.entries`) | python |
| `PR-EVENTS-ENVELOPE-004` | An envelope naming an unknown lane is refused with exactly its pinned code. | FR-014; class `envelope_invalid_unknown_lane` (`classes.entries`) | python |
| `PR-EVENTS-ENVELOPE-005` | An envelope whose payload breaks its schema is refused with exactly its pinned code. | FR-014; class `envelope_invalid_payload_schema` (`classes.entries`) | python |
| `PR-EVENTS-ENVELOPE-006` | A badly shaped envelope is refused with exactly its pinned code. | FR-014; class `envelope_invalid_shape` (`classes.entries`) | python |
| `PR-EVENTS-ENVELOPE-007` | A raw historical row is refused (refusal only: the pinned code is the ideal, per the conformance README's caveat). | FR-015; class `historical_row_raw` (`classes.entries`) | python |

## The strict journal profile refuses with the ordered codes pinned — `strict-journal-profile/`

| Promise | Consumer guarantee | Authority | Binding |
|---------|--------------------|-----------|---------|
| `PR-EVENTS-ENVELOPE-008` | Every strict-journal record is accepted, or refused with exactly its pinned ordered list of codes. | FR-016; class `envelope_strict_journal` (top-level `fixtures`) | python |
| `PR-EVENTS-ENVELOPE-009` | A record whose event type is not registered fails closed as an unknown event type. | FR-017; register id `class-taxonomy-envelope-strict-journal-unknown-event-type` (top-level `fixtures`) | python |

## Legacy lane strings resolve as pinned — `resolves-legacy-lanes/`

| Promise | Consumer guarantee | Authority | Binding |
|---------|--------------------|-----------|---------|
| `PR-EVENTS-ENVELOPE-010` | A legacy lane string resolves to its pinned canonical lane, or is refused with its pinned code. | FR-018; class `lane_mapping_legacy` (`classes.entries`) | python |
