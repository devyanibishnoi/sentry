import operator

from sentry.ast_nodes import (
    ActionCall,
    ApprovalRequired,
    Comparison,
    FieldAccess,
    IfElse,
    Literal,
    Program,
    WaitStmt,
)
from sentry.audit import AuditEntry, AuditLog
from sentry.errors import InterpreterError

_OPERATORS = {
    "==": operator.eq,
    "!=": operator.ne,
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
}


def run(program: Program, event_name: str, alert: dict) -> AuditLog:
    log = AuditLog()
    for on_block in program.on_blocks:
        if on_block.name == event_name:
            _run_statements(on_block.body, alert, log)
    return log


def _run_statements(statements: list, alert: dict, log: AuditLog) -> None:
    for statement in statements:
        _run_statement(statement, alert, log)


def _run_statement(statement, alert: dict, log: AuditLog) -> None:
    if isinstance(statement, ActionCall):
        _run_action_call(statement, alert, log)
    elif isinstance(statement, IfElse):
        if _eval_comparison(statement.condition, alert):
            _run_statements(statement.then_body, alert, log)
        elif statement.else_body is not None:
            _run_statements(statement.else_body, alert, log)
    elif isinstance(statement, WaitStmt):
        duration = statement.duration
        log.record(
            AuditEntry(
                action="wait",
                status="waited",
                reason=f"waited {duration.amount}{duration.unit} (simulated, no real delay)",
            )
        )
    else:
        raise InterpreterError(f"Unrecognized statement type: {type(statement).__name__}")


def _run_action_call(call: ActionCall, alert: dict, log: AuditLog) -> None:
    args = [_eval_expression(arg, alert) for arg in call.args]
    call_desc = f"{call.name}({', '.join(repr(a) for a in args)})"

    if call.gate is None:
        log.record(AuditEntry(action=call_desc, status="executed", reason="no gate condition"))
        return

    if isinstance(call.gate, ApprovalRequired):
        log.record(
            AuditEntry(action=call_desc, status="refused", reason="requires manual approval")
        )
        return

    condition_text = _describe_comparison(call.gate)
    if _eval_comparison(call.gate, alert):
        log.record(
            AuditEntry(
                action=call_desc, status="executed", reason=f"gate satisfied: {condition_text}"
            )
        )
    else:
        log.record(
            AuditEntry(
                action=call_desc,
                status="refused",
                reason=f"gate not satisfied: {condition_text}",
            )
        )


def _eval_comparison(comparison: Comparison, alert: dict) -> bool:
    left = _eval_expression(comparison.left, alert)
    right = _eval_expression(comparison.right, alert)
    return _OPERATORS[comparison.operator](left, right)


def _eval_expression(expr, alert: dict):
    if isinstance(expr, Literal):
        return expr.value
    if isinstance(expr, FieldAccess):
        return _eval_field_access(expr, alert)
    raise InterpreterError(f"Unrecognized expression type: {type(expr).__name__}")


def _eval_field_access(field_access: FieldAccess, alert: dict):
    if field_access.root != "alert":
        raise InterpreterError(f"Unknown variable '{field_access.root}'")

    value = alert
    seen = [field_access.root]
    for step in field_access.path:
        seen.append(step)
        if not isinstance(value, dict) or step not in value:
            raise InterpreterError(f"Alert data is missing field '{'.'.join(seen)}'")
        value = value[step]
    return value


def _describe_expression(expr) -> str:
    if isinstance(expr, Literal):
        return repr(expr.value)
    if isinstance(expr, FieldAccess):
        return ".".join([expr.root, *expr.path])
    raise InterpreterError(f"Unrecognized expression type: {type(expr).__name__}")


def _describe_comparison(comparison: Comparison) -> str:
    return (
        f"{_describe_expression(comparison.left)} {comparison.operator} "
        f"{_describe_expression(comparison.right)}"
    )
