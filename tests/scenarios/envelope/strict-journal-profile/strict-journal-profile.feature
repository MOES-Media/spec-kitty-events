# Maintainer notes (not part of the behaviour description):
# - The strict journal profile (FR-016, FR-017). It collects every finding, so a refused
#   fixture pins an ordered list of codes, and the whole list is compared in order.
# - Its fixtures are registered in manifest.json's top-level fixtures array, not in the
#   eight-class taxonomy; the unknown-event-type fixture is selected by its register id.
# - Promises mapped in tests/scenarios/envelope/PROMISES.md.

Feature: The strict journal profile refuses with the ordered codes pinned
  As a maintainer of a language binding of the event contract
  I want journal records judged by the strict profile exactly as their fixtures pin
  So that every binding reports the same findings, in the same order

  @promise:PR-EVENTS-ENVELOPE-008
  Scenario: The strict journal profile accepts or refuses with exactly the ordered codes pinned
    Given the conformance fixtures of class "envelope_strict_journal"
    When each envelope is validated under the strict journal profile
    Then each is accepted or refused with exactly the codes its fixture pins
    And every selected fixture was evaluated

  @promise:PR-EVENTS-ENVELOPE-009
  Scenario: An unregistered event type fails closed
    Given the conformance fixture "class-taxonomy-envelope-strict-journal-unknown-event-type" of class "envelope_strict_journal"
    When each envelope is validated under the strict journal profile
    Then it is refused with the code "UNKNOWN_EVENT_TYPE"
    And every selected fixture was evaluated
