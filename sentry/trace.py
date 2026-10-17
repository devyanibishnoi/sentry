from sentry.ast_nodes import ActionCall, ApprovalRequired, IfElse, OnBlock, WaitStmt
from sentry.interpreter import (
    _describe_comparison,
    _eval_comparison,
    _eval_expression,
)

_STATUS_COLORS = {
    "executed": "#2f7a4d",
    "refused": "#a13f34",
    "waited": "#4b5363",
    "taken": "#2f7a4d",
    "skipped": "#9aa3af",
}


def build_trace(on_block: OnBlock, alert: dict) -> dict:
    return {"kind": "on_block", "name": on_block.name, "children": _trace_statements(on_block.body, alert)}


def _trace_statements(statements: list, alert: dict) -> list:
    return [_trace_statement(stmt, alert) for stmt in statements]


def _trace_statement(statement, alert: dict) -> dict:
    if isinstance(statement, ActionCall):
        return _trace_action(statement, alert)
    if isinstance(statement, IfElse):
        return _trace_if(statement, alert)
    if isinstance(statement, WaitStmt):
        return _trace_wait(statement)
    raise ValueError(f"Unrecognized statement type: {type(statement).__name__}")


def _trace_action(call: ActionCall, alert: dict) -> dict:
    args = [_eval_expression(arg, alert) for arg in call.args]
    label = f"{call.name}({', '.join(repr(a) for a in args)})"

    if call.gate is None:
        return {"kind": "action", "label": label, "status": "executed", "reason": "no gate condition"}

    if isinstance(call.gate, ApprovalRequired):
        return {"kind": "action", "label": label, "status": "refused", "reason": "requires manual approval"}

    condition_text = _describe_comparison(call.gate)
    met = _eval_comparison(call.gate, alert)
    status = "executed" if met else "refused"
    verb = "satisfied" if met else "not satisfied"
    return {"kind": "action", "label": label, "status": status, "reason": f"gate {verb}: {condition_text}"}


def _trace_if(stmt: IfElse, alert: dict) -> dict:
    condition_text = _describe_comparison(stmt.condition)
    result = _eval_comparison(stmt.condition, alert)
    return {
        "kind": "if",
        "condition": condition_text,
        "result": result,
        "then": _trace_statements(stmt.then_body, alert),
        "else": _trace_statements(stmt.else_body, alert) if stmt.else_body is not None else None,
    }


def _trace_wait(stmt: WaitStmt) -> dict:
    d = stmt.duration
    return {"kind": "wait", "label": f"wait {d.amount}{d.unit}"}


def render_html(trace: dict, title: str = "Sentry Execution Trace") -> str:
    body = _render_node(trace, taken=True)
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{title}</title>
<style>
body {{ font-family: Consolas, "Cascadia Code", monospace; background: #10151c; color: #dfe6ee;
       padding: 2rem; line-height: 1.5; }}
h1 {{ font-size: 1.1rem; color: #8793a3; font-weight: normal; margin-bottom: 1.5rem; }}
.node {{ margin: 0.15rem 0; padding: 0.35rem 0.7rem; border-left: 3px solid #28323f; }}
.skipped {{ opacity: 0.4; }}
.tag {{ font-weight: bold; padding: 0.05rem 0.4rem; border-radius: 3px; font-size: 0.8rem; margin-right: 0.5rem; }}
.children {{ margin-left: 1.4rem; }}
.reason {{ color: #8793a3; }}
.cond {{ color: #e3a85c; }}
</style></head>
<body>
<h1>{title}</h1>
{body}
</body></html>"""


def _render_node(node: dict, taken: bool) -> str:
    cls = "node" if taken else "node skipped"
    kind = node["kind"]

    if kind == "on_block":
        inner = "".join(_render_node(child, True) for child in node["children"])
        return f'<div class="{cls}">on <b>{node["name"]}</b><div class="children">{inner}</div></div>'

    if kind == "action":
        color = _STATUS_COLORS[node["status"]]
        tag = f'<span class="tag" style="background:{color};color:#10151c">{node["status"].upper()}</span>'
        return f'<div class="{cls}">{tag}{node["label"]} <span class="reason">- {node["reason"]}</span></div>'

    if kind == "wait":
        return f'<div class="{cls}">{node["label"]}</div>'

    if kind == "if":
        taken_color = _STATUS_COLORS["taken"]
        skipped_color = _STATUS_COLORS["skipped"]
        result_tag = (
            f'<span class="tag" style="background:{taken_color};color:#10151c">TRUE</span>'
            if node["result"]
            else f'<span class="tag" style="background:{skipped_color};color:#10151c">FALSE</span>'
        )
        then_html = "".join(_render_node(c, node["result"]) for c in node["then"])
        parts = [
            f'<div class="{cls}">if <span class="cond">{node["condition"]}</span> {result_tag}'
            f'<div class="children">{then_html}</div></div>'
        ]
        if node["else"] is not None:
            else_html = "".join(_render_node(c, not node["result"]) for c in node["else"])
            parts.append(f'<div class="node">else<div class="children">{else_html}</div></div>')
        return "".join(parts)

    raise ValueError(f"Unrecognized trace node kind: {kind}")
