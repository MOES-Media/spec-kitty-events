# Maintainer notes (not part of the behaviour description):
# - Legacy lane mapping (FR-018). A legacy lane string resolves to its pinned canonical lane,
#   or is refused with its pinned code; the class mixes both.
# - Promises mapped in tests/scenarios/envelope/PROMISES.md.

Feature: Legacy lane strings resolve as pinned
  As a maintainer of a language binding of the event contract
  I want legacy lane strings resolved to canonical lanes exactly as their fixtures pin
  So that old rows read the same in every binding, and unmapped ones are refused

  @promise:PR-EVENTS-ENVELOPE-010
  Scenario: Legacy lane strings resolve as pinned
    Given the conformance fixtures of class "lane_mapping_legacy"
    When each legacy lane is resolved
    Then each is accepted or refused with exactly the codes its fixture pins
    And every selected fixture was evaluated
