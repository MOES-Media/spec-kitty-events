---
section: Added
---

- A technology-agnostic Gherkin scenario suite for the event contract (`tests/scenarios/`, #197, slice D1 of #121). It follows core's scenario conventions: promise tags, `@wip` ownership and per-area `PROMISES.md` registers. Its Python reference step binding checks the verdict each committed conformance fixture pins, never a copy of it. The first area, `envelope/`, holds ten promises: canonical and synthesized envelopes accepted; forbidden key, unknown lane, payload schema and bad shape refused with their pinned codes; raw historical rows refused; the strict journal profile's ordered codes, including an unknown event type, which fails closed; and legacy lane mapping.
  - New public function `spec_kitty_events.conformance.class_fixture_verdict(fixture_class, fixture_input)`. It returns the class-taxonomy envelope verdict that the class conformance test and the step binding share. Its check order is now documented contract in `src/spec_kitty_events/conformance/README.md`. Additive: no fixture, schema or verdict changes.
  - New per-PR contract check `scripts/scenario_contract.py`, also run by `make lint`. It enforces core's scenario rule codes, plus the events-specific promise-register, binding-declaration, steps-table and test-import rules.
  - New dev dependencies `pytest-bdd` and `gherkin-official`, in the dependency group and the `dev` extra. Runtime requirements are unchanged.
