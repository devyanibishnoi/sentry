from sentry.ast_nodes import (
    ActionCall,
    ApprovalRequired,
    Comparison,
    Duration,
    FieldAccess,
    IfElse,
    Literal,
    OnBlock,
    Program,
    WaitStmt,
)
from sentry.errors import ParseError
from sentry.tokens import Token, TokenType

_COMPARATOR_TYPES = {
    TokenType.EQ,
    TokenType.NEQ,
    TokenType.LT,
    TokenType.LTE,
    TokenType.GT,
    TokenType.GTE,
}


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

    # program ::= { on_block }
    def parse_program(self) -> Program:
        on_blocks = []
        while self._peek().type != TokenType.EOF:
            on_blocks.append(self.parse_on_block())
        self._expect(TokenType.EOF)
        return Program(on_blocks=on_blocks)

    # on_block ::= "ON" IDENTIFIER ":" NEWLINE INDENT statement_list DEDENT
    def parse_on_block(self) -> OnBlock:
        self._expect(TokenType.ON)
        name_token = self._expect(TokenType.IDENTIFIER)
        self._expect(TokenType.COLON)
        self._expect(TokenType.NEWLINE)
        self._expect(TokenType.INDENT)
        body = self.parse_statement_list()
        self._expect(TokenType.DEDENT)
        return OnBlock(name=name_token.value, body=body)

    # statement_list ::= statement { statement }
    def parse_statement_list(self) -> list:
        statements = [self.parse_statement()]
        while self._peek().type not in (TokenType.DEDENT, TokenType.EOF):
            statements.append(self.parse_statement())
        return statements

    # statement ::= action_stmt | if_stmt | wait_stmt
    def parse_statement(self):
        token = self._peek()
        if token.type == TokenType.IF:
            return self.parse_if_stmt()
        if token.type == TokenType.WAIT:
            return self.parse_wait_stmt()
        if token.type == TokenType.IDENTIFIER:
            return self.parse_action_stmt()
        raise ParseError(
            f"Expected a statement (action call, 'if', or 'wait'), got "
            f"{token.type.name} ({token.value!r})",
            token.line,
            token.column,
        )

    # action_stmt ::= IDENTIFIER "(" [ arg_list ] ")" [ gate ] NEWLINE
    def parse_action_stmt(self) -> ActionCall:
        name_token = self._expect(TokenType.IDENTIFIER)
        self._expect(TokenType.LPAREN)
        args = []
        if self._peek().type != TokenType.RPAREN:
            args.append(self.parse_expression())
            while self._peek().type == TokenType.COMMA:
                self._advance()
                args.append(self.parse_expression())
        self._expect(TokenType.RPAREN)

        gate = None
        if self._peek().type == TokenType.REQUIRE:
            self._advance()
            gate = self.parse_gate()

        self._expect(TokenType.NEWLINE)
        return ActionCall(name=name_token.value, args=args, gate=gate)

    # gate ::= "REQUIRE" ( comparison | "approval" )
    def parse_gate(self):
        token = self._peek()
        if token.type == TokenType.IDENTIFIER and token.value == "approval":
            self._advance()
            return ApprovalRequired()
        return self.parse_comparison()

    # if_stmt ::= "IF" comparison ":" NEWLINE INDENT statement_list DEDENT
    #             [ "ELSE" ":" NEWLINE INDENT statement_list DEDENT ]
    def parse_if_stmt(self) -> IfElse:
        self._expect(TokenType.IF)
        condition = self.parse_comparison()
        self._expect(TokenType.COLON)
        self._expect(TokenType.NEWLINE)
        self._expect(TokenType.INDENT)
        then_body = self.parse_statement_list()
        self._expect(TokenType.DEDENT)

        else_body = None
        if self._peek().type == TokenType.ELSE:
            self._advance()
            self._expect(TokenType.COLON)
            self._expect(TokenType.NEWLINE)
            self._expect(TokenType.INDENT)
            else_body = self.parse_statement_list()
            self._expect(TokenType.DEDENT)

        return IfElse(condition=condition, then_body=then_body, else_body=else_body)

    # wait_stmt ::= "WAIT" DURATION NEWLINE
    def parse_wait_stmt(self) -> WaitStmt:
        self._expect(TokenType.WAIT)
        duration_token = self._expect(TokenType.DURATION)
        self._expect(TokenType.NEWLINE)
        amount = int(duration_token.value[:-1])
        unit = duration_token.value[-1]
        return WaitStmt(duration=Duration(amount=amount, unit=unit))

    # comparison ::= expression comparator expression
    def parse_comparison(self) -> Comparison:
        left = self.parse_expression()
        operator_token = self._peek()
        if operator_token.type not in _COMPARATOR_TYPES:
            raise ParseError(
                f"Expected a comparison operator (==, !=, <, <=, >, >=), got "
                f"{operator_token.type.name} ({operator_token.value!r})",
                operator_token.line,
                operator_token.column,
            )
        self._advance()
        right = self.parse_expression()
        return Comparison(left=left, operator=operator_token.value, right=right)

    # expression ::= field_access | literal
    def parse_expression(self):
        token = self._peek()
        if token.type == TokenType.IDENTIFIER:
            return self.parse_field_access()
        if token.type in (TokenType.STRING, TokenType.NUMBER):
            return self.parse_literal()
        raise ParseError(
            f"Expected a field access or literal, got {token.type.name} "
            f"({token.value!r})",
            token.line,
            token.column,
        )

    # field_access ::= IDENTIFIER { "." IDENTIFIER }
    def parse_field_access(self) -> FieldAccess:
        root_token = self._expect(TokenType.IDENTIFIER)
        path = []
        while self._peek().type == TokenType.DOT:
            self._advance()
            field_token = self._expect(TokenType.IDENTIFIER)
            path.append(field_token.value)
        return FieldAccess(root=root_token.value, path=path)

    # literal ::= STRING | NUMBER
    def parse_literal(self) -> Literal:
        token = self._advance()
        if token.type == TokenType.STRING:
            return Literal(value=token.value)
        value = float(token.value) if "." in token.value else int(token.value)
        return Literal(value=value)


def parse(tokens: list[Token]) -> Program:
    return Parser(tokens).parse_program()
