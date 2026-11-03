"""Planted step definitions: read statically by the contract check, never imported."""

from pytest_bdd import given, parsers, then, when


@given(parsers.parse('the name "{name}"'))
def the_name(name: str) -> None:
    del name


@given('the name "Ada"')
def the_name_ada() -> None:
    pass


@when("the greeting is made")
def the_greeting_is_made() -> None:
    pass


@then(parsers.parse('the greeting reads "{text}"'))
def the_greeting_reads(text: str) -> None:
    del text
