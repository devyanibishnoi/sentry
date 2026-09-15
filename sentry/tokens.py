from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    IDENTIFIER = auto()
    NUMBER = auto()
    STRING = auto()
    DURATION = auto()

    ON = auto()
    IF = auto()
    ELSE = auto()
    WAIT = auto()
    REQUIRE = auto()

    DOT = auto()
    COMMA = auto()
    COLON = auto()
    LPAREN = auto()
    RPAREN = auto()

    EQ = auto()
    NEQ = auto()
    LT = auto()
    LTE = auto()
    GT = auto()
    GTE = auto()

    INDENT = auto()
    DEDENT = auto()
    NEWLINE = auto()
    EOF = auto()


KEYWORDS = {
    "on": TokenType.ON,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "wait": TokenType.WAIT,
    "require": TokenType.REQUIRE,
}


@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    column: int
