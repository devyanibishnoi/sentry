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
        TokenType.NEWLINE,
        TokenType.EOF,
    ]

    values = [t.value for t in tokens]
    assert values == ["isolate_host", "(", "alert", ".", "host", ")", "", ""]


def test_identifier_token_records_start_position():
    tokens = tokenize("isolate_host(alert.host)")

    first = tokens[0]
    assert first.value == "isolate_host"
    assert first.line == 1
    assert first.column == 1

    alert_token = tokens[2]
    assert alert_token.value == "alert"
    assert alert_token.line == 1
    assert alert_token.column == 14


def test_illegal_character_raises_lex_error():
    with pytest.raises(LexError) as excinfo:
        tokenize("isolate_host(alert.host) #")

    assert excinfo.value.line == 1
    assert excinfo.value.column == 26


def test_keywords_recognized_not_identifiers():
    tokens = tokenize("on if else wait require")

    types = [t.type for t in tokens[:5]]
    assert types == [
        TokenType.ON,
        TokenType.IF,
        TokenType.ELSE,
        TokenType.WAIT,
        TokenType.REQUIRE,
    ]
    # "approval" is deliberately NOT a keyword -- it's an ordinary
    # identifier the parser recognizes contextually after REQUIRE.
    approval_tokens = tokenize("approval")
    assert approval_tokens[0].type == TokenType.IDENTIFIER
    assert approval_tokens[0].value == "approval"


def test_comparison_operators():
    tokens = tokenize("== != < <= > >=")
    types = [t.type for t in tokens[:6]]
    assert types == [
        TokenType.EQ,
        TokenType.NEQ,
        TokenType.LT,
        TokenType.LTE,
        TokenType.GT,
        TokenType.GTE,
    ]


@pytest.mark.parametrize("source", ["a = b", "a ! b"])
def test_bare_equals_or_bang_is_illegal(source):
    with pytest.raises(LexError):
        tokenize(source)


def test_string_literal():
    tokens = tokenize('notify_soc(alert.id) require alert.severity == "high"')
    string_tokens = [t for t in tokens if t.type == TokenType.STRING]
    assert len(string_tokens) == 1
    assert string_tokens[0].value == "high"


def test_unterminated_string_raises_lex_error():
    with pytest.raises(LexError) as excinfo:
        tokenize('require "unterminated')
    assert excinfo.value.line == 1


def test_number_and_duration_literals():
    tokens = tokenize("0.8 5 5m 30s 2h")
    types = [t.type for t in tokens[:5]]
    assert types == [
        TokenType.NUMBER,
        TokenType.NUMBER,
        TokenType.DURATION,
        TokenType.DURATION,
        TokenType.DURATION,
    ]
    values = [t.value for t in tokens[:5]]
    assert values == ["0.8", "5", "5m", "30s", "2h"]


def test_invalid_duration_unit_raises_lex_error():
    with pytest.raises(LexError) as excinfo:
        tokenize("wait 5q")
    assert excinfo.value.column == 7


def test_indentation_produces_matched_indent_dedent():
    source = (
        "on new_alert:\n"
        "    if alert.confidence >= 0.8:\n"
        "        isolate_host(alert.host)\n"
        "    wait 5m\n"
    )
    tokens = tokenize(source)
    indents = sum(1 for t in tokens if t.type == TokenType.INDENT)
    dedents = sum(1 for t in tokens if t.type == TokenType.DEDENT)
    assert indents == 2
    assert dedents == 2  # one for leaving the `if` body, one for the final unwind at EOF

    # DEDENT must appear right before `wait`, since `wait` sits back at the
    # outer block's indentation level after the deeper `if` body.
    wait_index = next(i for i, t in enumerate(tokens) if t.type == TokenType.WAIT)
    assert tokens[wait_index - 1].type == TokenType.DEDENT


def test_inconsistent_dedent_raises_lex_error():
    source = "on x:\n    a()\n  b()\n"
    with pytest.raises(LexError) as excinfo:
        tokenize(source)
    assert excinfo.value.line == 3


def test_blank_lines_are_ignored():
    source = "on x:\n\n    a()\n"
    tokens = tokenize(source)
    types = [t.type for t in tokens]
    # exactly one INDENT despite the blank line sitting between the header
    # and the first statement
    assert types.count(TokenType.INDENT) == 1
