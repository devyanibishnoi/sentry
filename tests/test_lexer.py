import pytest

from sentry.errors import LexError
from sentry.lexer import tokenize
from sentry.tokens import TokenType


def test_tokenizes_action_call_line():
    tokens = tokenize("isolate_host(alert.host)")

    types = [t.type for t in tokens]
    assert types == [
        TokenType.IDENTIFIER,
        TokenType.LPAREN,
        TokenType.IDENTIFIER,
        TokenType.DOT,
        TokenType.IDENTIFIER,
        TokenType.RPAREN,
        TokenType.EOF,
    ]

    values = [t.value for t in tokens]
    assert values == ["isolate_host", "(", "alert", ".", "host", ")", ""]


def test_identifier_token_records_start_position():
    tokens = tokenize("isolate_host(alert.host)")

    first = tokens[0]
    assert first.value == "isolate_host"
    assert first.line == 1
    assert first.column == 1

    # 'alert' starts right after '(' at column 14
    alert_token = tokens[2]
    assert alert_token.value == "alert"
    assert alert_token.line == 1
    assert alert_token.column == 14


def test_illegal_character_raises_lex_error():
    with pytest.raises(LexError) as excinfo:
        tokenize("isolate_host(alert.host) #")

    assert excinfo.value.line == 1
    assert excinfo.value.column == 26
