Feature: Greeting
  A minimal valid tree for the scenario contract check.

  @promise:PR-demo-001
  Scenario: A known name is greeted
    Given the name "Ada"
    When the greeting is made
    Then the greeting reads "Hello, Ada"

  @promise:PR-demo-002 @smoke.test
  Scenario: Another name is greeted
    Given the name "Bo"
    When the greeting is made
    Then the greeting reads "Hello, Bo"
