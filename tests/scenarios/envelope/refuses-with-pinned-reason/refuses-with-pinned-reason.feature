# Maintainer notes (not part of the behaviour description):
# - Envelope refusal (FR-014, FR-015). The code each fixture pins follows the envelope verdict
#   check order published in the conformance README; the scenarios name only the class.
# - Raw historical rows pin an ideal code today's validator does not always emit (conformance
#   README, the note on historical_row_raw), so their scenario asserts refusal only.
# - Promises mapped in tests/scenarios/envelope/PROMISES.md.

Feature: Invalid envelopes are refused with their pinned reason
  As a maintainer of a language binding of the event contract
  I want every invalid envelope refused with the reason its fixture pins
  So that every binding refuses the same envelopes for the same reason

  @promise:PR-EVENTS-ENVELOPE-003
  Scenario: An envelope with a forbidden key, at any position, is refused with its pinned code
    Given the conformance fixtures of class "envelope_invalid_forbidden_key"
    When each envelope is validated
    Then each is refused with exactly the code its fixture pins
    And every selected fixture was evaluated

  @promise:PR-EVENTS-ENVELOPE-004
  Scenario: An envelope naming an unknown lane is refused with its pinned code
    Given the conformance fixtures of class "envelope_invalid_unknown_lane"
    When each envelope is validated
    Then each is refused with exactly the code its fixture pins
    And every selected fixture was evaluated

  @promise:PR-EVENTS-ENVELOPE-005
  Scenario: An envelope whose payload breaks its schema is refused with its pinned code
    Given the conformance fixtures of class "envelope_invalid_payload_schema"
    When each envelope is validated
    Then each is refused with exactly the code its fixture pins
    And every selected fixture was evaluated

  @promise:PR-EVENTS-ENVELOPE-006
  Scenario: A badly shaped envelope is refused with its pinned code
    Given the conformance fixtures of class "envelope_invalid_shape"
    When each envelope is validated
    Then each is refused with exactly the code its fixture pins
    And every selected fixture was evaluated

  @promise:PR-EVENTS-ENVELOPE-007
  Scenario: Raw historical rows are refused
    Given the conformance fixtures of class "historical_row_raw"
    When each envelope is validated
    Then each is refused
    And every selected fixture was evaluated
