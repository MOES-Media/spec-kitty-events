---
title: Architectural Decision Records
description: Index of architectural decision records for the spec-kitty-events contract package, with the naming convention and status vocabulary.
doc_status: active
updated: 2026-10-13
type: Index
kind: Hub
---

# Architectural Decision Records

Architectural decisions for `spec-kitty-events`, the package that owns the Spec Kitty
event envelope, payload schemas, conformance fixtures and compatibility policy. This
folder was opened by the CloudEvents envelope ADR below; the package had no ADR folder
before it.

## Naming

`YYYY-MM-DD-N-descriptive-title-with-dashes.md`, where `N` is `1, 2, 3, ...` per ADR
landed on a given date. This is the naming the core `spec-kitty` repository uses.

## Status vocabulary

- `Proposed`: written, direction not yet confirmed.
- `Accepted`: the decision is current policy.
- `Superseded`: a newer ADR replaced it; keep the file for history.
- `Deprecated`: being retired; take no new work from it.

## Records

| ADR | Status | Decision |
|---|---|---|
| [2026-10-13-1 CloudEvents envelope](2026-10-13-1-cloudevents-envelope.md) | Proposed | Adopt CloudEvents 1.0 (structured JSON) as the event envelope; the 3.0.0 transport envelope and the status-diary row become legacy inputs to a read-time upcaster. |

Design detail for the records above lives under [`docs/design/`](../design/).
