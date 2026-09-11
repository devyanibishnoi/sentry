import pytest

from sentry.ast_nodes import ActionCall, FieldAccess
from sentry.errors import ParseError
from sentry.lexer import tokenize
from sentry.parser import parse


def test_parses_action_call_with_field_access_arg():
    tokens = tokenize("isolate_host(alert.host)")

    tree = parse(tokens)

    assert tree == ActionCall(
        name="isolate_host",
        args=[FieldAccess(base="alert", field="host")],
    )


def test_missing_closing_paren_raises_parse_error():
    tokens = tokenize("isolate_host(alert.host")

    with pytest.raises(ParseError):
        parse(tokens)


def test_missing_dot_in_field_access_raises_parse_error():
    tokens = tokenize("isolate_host(alerthost)")

    with pytest.raises(ParseError):
        parse(tokens)
