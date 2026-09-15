from sentry.errors import LexError
from sentry.tokens import KEYWORDS, Token, TokenType

_SINGLE_CHAR_TOKENS = {
    ".": TokenType.DOT,
    ",": TokenType.COMMA,
    ":": TokenType.COLON,
    "(": TokenType.LPAREN,
    ")": TokenType.RPAREN,
}

_DURATION_UNITS = ("s", "m", "h")


def tokenize(source: str) -> list[Token]:
    tokens: list[Token] = []
    indent_stack = [0]
    lines = source.split("\n")

    for line_no, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip("\r")

        if line.strip(" \t") == "":
            continue  # blank lines: no tokens, no effect on indentation

        indent = len(line) - len(line.lstrip(" "))
        if "\t" in line[:indent]:
            raise LexError("Tabs are not allowed for indentation", line_no, 1)

        if indent > indent_stack[-1]:
            indent_stack.append(indent)
            tokens.append(Token(TokenType.INDENT, "", line_no, 1))
        else:
            while indent < indent_stack[-1]:
                indent_stack.pop()
                tokens.append(Token(TokenType.DEDENT, "", line_no, 1))
            if indent != indent_stack[-1]:
                raise LexError(
                    f"Indentation does not match any enclosing block "
                    f"(got {indent} spaces)",
                    line_no,
                    indent + 1,
                )

        col = indent
        while col < len(line):
            ch = line[col]

            if ch in (" ", "\t"):
                col += 1
                continue

            if ch.isalpha() or ch == "_":
                start = col
                while col < len(line) and (line[col].isalnum() or line[col] == "_"):
                    col += 1
                text = line[start:col]
                token_type = KEYWORDS.get(text, TokenType.IDENTIFIER)
                tokens.append(Token(token_type, text, line_no, start + 1))
                continue

            if ch.isdigit():
                start = col
                while col < len(line) and line[col].isdigit():
                    col += 1
                if (
                    col < len(line)
                    and line[col] == "."
                    and col + 1 < len(line)
                    and line[col + 1].isdigit()
                ):
                    col += 1
                    while col < len(line) and line[col].isdigit():
                        col += 1
                number_text = line[start:col]

                if col < len(line) and line[col].isalpha():
                    unit_start = col
                    while col < len(line) and line[col].isalpha():
                        col += 1
                    unit = line[unit_start:col]
                    if unit not in _DURATION_UNITS:
                        raise LexError(
                            f"Invalid duration unit {unit!r}", line_no, unit_start + 1
                        )
                    tokens.append(
                        Token(TokenType.DURATION, number_text + unit, line_no, start + 1)
                    )
                else:
                    tokens.append(Token(TokenType.NUMBER, number_text, line_no, start + 1))
                continue

            if ch == '"':
                start_col = col
                col += 1
                content_start = col
                while col < len(line) and line[col] != '"':
                    col += 1
                if col >= len(line):
                    raise LexError("Unterminated string literal", line_no, start_col + 1)
                value = line[content_start:col]
                col += 1  # consume closing quote
                tokens.append(Token(TokenType.STRING, value, line_no, start_col + 1))
                continue

            if ch == "=":
                if col + 1 < len(line) and line[col + 1] == "=":
                    tokens.append(Token(TokenType.EQ, "==", line_no, col + 1))
                    col += 2
                else:
                    raise LexError("Unexpected '='", line_no, col + 1)
                continue

            if ch == "!":
                if col + 1 < len(line) and line[col + 1] == "=":
                    tokens.append(Token(TokenType.NEQ, "!=", line_no, col + 1))
                    col += 2
                else:
                    raise LexError("Unexpected '!'", line_no, col + 1)
                continue

            if ch == "<":
                if col + 1 < len(line) and line[col + 1] == "=":
                    tokens.append(Token(TokenType.LTE, "<=", line_no, col + 1))
                    col += 2
                else:
                    tokens.append(Token(TokenType.LT, "<", line_no, col + 1))
                    col += 1
                continue

            if ch == ">":
                if col + 1 < len(line) and line[col + 1] == "=":
                    tokens.append(Token(TokenType.GTE, ">=", line_no, col + 1))
                    col += 2
                else:
                    tokens.append(Token(TokenType.GT, ">", line_no, col + 1))
                    col += 1
                continue

            if ch in _SINGLE_CHAR_TOKENS:
                tokens.append(Token(_SINGLE_CHAR_TOKENS[ch], ch, line_no, col + 1))
                col += 1
                continue

            raise LexError(f"Illegal character {ch!r}", line_no, col + 1)

        tokens.append(Token(TokenType.NEWLINE, "", line_no, len(line) + 1))

    while len(indent_stack) > 1:
        indent_stack.pop()
        tokens.append(Token(TokenType.DEDENT, "", len(lines) + 1, 1))

    tokens.append(Token(TokenType.EOF, "", len(lines) + 1, 1))
    return tokens
