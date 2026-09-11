from sentry.ast_nodes import ActionCall, FieldAccess
from sentry.errors import ParseError
from sentry.tokens import Token, TokenType


class Parser:
    def __init__(self, tokens: list[Token]):
        self._tokens = tokens
        self._pos = 0

    def _peek(self) -> Token:
        return self._tokens[self._pos]

    def _advance(self) -> Token:
        token = self._tokens[self._pos]
        self._pos += 1
        return token

    def _expect(self, expected_type: TokenType) -> Token:
        token = self._peek()
        if token.type != expected_type:
            raise ParseError(
                f"Expected {expected_type.name}, got {token.type.name} "
                f"({token.value!r})",
                token.line,
                token.column,
            )
        return self._advance()

    def parse_action_call(self) -> ActionCall:
        name_token = self._expect(TokenType.IDENTIFIER)
        self._expect(TokenType.LPAREN)
        arg = self.parse_field_access()
        self._expect(TokenType.RPAREN)
        self._expect(TokenType.EOF)
        return ActionCall(name=name_token.value, args=[arg])

    def parse_field_access(self) -> FieldAccess:
        base_token = self._expect(TokenType.IDENTIFIER)
        self._expect(TokenType.DOT)
        field_token = self._expect(TokenType.IDENTIFIER)
        return FieldAccess(base=base_token.value, field=field_token.value)


def parse(tokens: list[Token]) -> ActionCall:
    return Parser(tokens).parse_action_call()
