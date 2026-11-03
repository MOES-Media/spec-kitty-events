# Maintainer notes (not part of the behaviour description):
# - Envelope acceptance (FR-013). Each scenario names a fixture class and never copies a
#   fixture: the classes and their pins live in the conformance package's manifest.json.
# - Promises mapped in tests/scenarios/envelope/PROMISES.md.

Feature: Valid envelopes are accepted
  As a maintainer of a language binding of the event contract
  I want every envelope the contract calls valid to be accepted
  So that producers using the canonical shape are never refused

  @promise:PR-EVENTS-ENVELOPE-001
  Scenario: Canonical envelopes are accepted
    Given the conformance fixtures of class "envelope_valid_canonical"
    When each envelope is validated
    Then each is accepted
    And every selected fixture was evaluated

  @promise:PR-EVENTS-ENVELOPE-002
  Scenario: Envelopes synthesized from historical rows are accepted
    Given the conformance fixtures of class "envelope_valid_historical_synthesized"
    When each envelope is validated
    Then each is accepted
    And every selected fixture was evaluated
