import difflib

from sentry.ast_nodes import (
    ActionCall,
    ApprovalRequired,
    Comparison,
    FieldAccess,
    IfElse,
    Literal,
    OnBlock,
    Program,
    WaitStmt,
)
from sentry.errors import SemanticError
from sentry.symbol_table import ACTIONS, ALERT_SCHEMA

_STRING_ONLY_OPERATORS = {"==", "!="}


def _did_you_mean(name: str, candidates) -> str:
    matches = difflib.get_close_matches(name, list(candidates), n=1, cutoff=0.6)
    return f" (did you mean '{matches[0]}'?)" if matches else ""


def analyze(program: Program) -> None:
    for on_block in program.on_blocks:
        _check_on_block(on_block)


def _check_on_block(on_block: OnBlock) -> None:
    for statement in on_block.body:
        _check_statement(statement)


def _check_statement(statement) -> None:
    if isinstance(statement, ActionCall):
        _check_action_call(statement)
    elif isinstance(statement, IfElse):
        _check_comparison(statement.condition)
        for stmt in statement.then_body:
            _check_statement(stmt)
        if statement.else_body is not None:
            for stmt in statement.else_body:
                _check_statement(stmt)
    elif isinstance(statement, WaitStmt):
        pass  # duration shape is already guaranteed valid by the lexer/parser
    else:
        raise SemanticError(f"Unrecognized statement type: {type(statement).__name__}")


def _check_action_call(call: ActionCall) -> None:
    if call.name not in ACTIONS:
        raise SemanticError(
            f"Unknown action '{call.name}'{_did_you_mean(call.name, ACTIONS)}",
            call.line,
            call.column,
        )

    expected_types = ACTIONS[call.name]
    if len(call.args) != len(expected_types):
        raise SemanticError(
            f"'{call.name}' expects {len(expected_types)} argument(s), "
            f"got {len(call.args)}",
            call.line,
            call.column,
        )

    for arg, expected_type in zip(call.args, expected_types):
        actual_type = _check_expression(arg)
        if actual_type != expected_type:
            raise SemanticError(
                f"'{call.name}' expects a {expected_type} argument, "
                f"got {actual_type}",
                call.line,
                call.column,
            )

    if call.gate is not None:
        _check_gate(call.gate)


def _check_gate(gate) -> None:
    if isinstance(gate, Comparison):
        _check_comparison(gate)
    elif isinstance(gate, ApprovalRequired):
        pass  # always a valid gate, no condition to type-check
    else:
        raise SemanticError(f"Unrecognized gate type: {type(gate).__name__}")


def _check_comparison(comparison: Comparison) -> None:
    left_type = _check_expression(comparison.left)
    right_type = _check_expression(comparison.right)

    if left_type != right_type:
        raise SemanticError(
            f"Malformed condition: cannot compare {left_type} to {right_type}",
            comparison.line,
            comparison.column,
        )

    if left_type == "string" and comparison.operator not in _STRING_ONLY_OPERATORS:
        raise SemanticError(
            f"Malformed condition: '{comparison.operator}' is not valid for "
            f"strings (only == and != are)",
            comparison.line,
            comparison.column,
        )


def _check_expression(expr) -> str:
    if isinstance(expr, Literal):
        return "string" if isinstance(expr.value, str) else "number"
    if isinstance(expr, FieldAccess):
        return _check_field_access(expr)
    raise SemanticError(f"Unrecognized expression type: {type(expr).__name__}")


def _check_field_access(field_access: FieldAccess) -> str:
    if field_access.root != "alert":
        raise SemanticError(
            f"Unknown variable '{field_access.root}' "
            f"(only 'alert' is available inside an on block)",
            field_access.line,
            field_access.column,
        )

    node = ALERT_SCHEMA
    seen = [field_access.root]
    for step in field_access.path:
        seen.append(step)
        if not isinstance(node, dict) or step not in node:
            candidates = node.keys() if isinstance(node, dict) else []
            raise SemanticError(
                f"Unknown field '{'.'.join(seen)}'{_did_you_mean(step, candidates)}",
                field_access.line,
                field_access.column,
            )
        node = node[step]

    if isinstance(node, dict):
        raise SemanticError(
            f"'{'.'.join(seen)}' refers to a group of fields, not a single value",
            field_access.line,
            field_access.column,
        )
    return node
