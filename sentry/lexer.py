from sentry.errors import LexError
from sentry.tokens import Token, TokenType

_SINGLE_CHAR_TOKENS = {
    ".": TokenType.DOT,
    "(": TokenType.LPAREN,
    ")": TokenType.RPAREN,
}


def tokenize(source: str) -> list[Token]:
    tokens: list[Token] = []
    pos = 0
    line = 1
    column = 1

    while pos < len(source):
        ch = source[pos]

        if ch == "\n":
            pos += 1
            line += 1
            column = 1
            continue

        if ch.isspace():
            pos += 1
            column += 1
            continue

        if ch.isalpha() or ch == "_":
            start = pos
            start_column = column
            while pos < len(source) and (source[pos].isalnum() or source[pos] == "_"):
                pos += 1
                column += 1
            value = source[start:pos]
            tokens.append(Token(TokenType.IDENTIFIER, value, line, start_column))
            continue

        if ch in _SINGLE_CHAR_TOKENS:
            tokens.append(Token(_SINGLE_CHAR_TOKENS[ch], ch, line, column))
            pos += 1
            column += 1
            continue

        raise LexError(f"Illegal character {ch!r}", line, column)

    tokens.append(Token(TokenType.EOF, "", line, column))
    return tokens
