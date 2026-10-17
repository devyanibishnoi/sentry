from sentry.lexer import tokenize
from sentry.parser import parse
from sentry.semantics import analyze
from sentry.trace import build_trace, render_html

SOURCE = (
    "on new_alert:\n"
    "    if alert.confidence >= 0.8:\n"
    "        isolate_host(alert.host) require alert.confidence >= 0.9\n"
    "    else:\n"
    "        notify_soc(alert.id) require approval\n"
    "    wait 5m\n"
)


def _trace(alert: dict) -> dict:
    program = parse(tokenize(SOURCE))
    analyze(program)
    return build_trace(program.on_blocks[0], alert)


def test_high_confidence_marks_if_branch_taken():
    alert = {"host": "ws-12", "id": "a1", "confidence": 0.95, "severity": "high", "user": "jdoe"}
    trace = _trace(alert)

    if_node = trace["children"][0]
    assert if_node["kind"] == "if"
    assert if_node["result"] is True
    assert if_node["then"][0]["status"] == "executed"
    assert if_node["else"][0]["label"].startswith("notify_soc")


def test_low_confidence_marks_else_branch_taken():
    alert = {"host": "ws-47", "id": "a2", "confidence": 0.3, "severity": "low", "user": "asmith"}
    trace = _trace(alert)

    if_node = trace["children"][0]
    assert if_node["result"] is False
    assert if_node["then"][0]["status"] == "refused"  # still evaluated, just not taken
    assert if_node["else"][0]["status"] == "refused"   # approval gate, taken branch


def test_wait_node_present_at_top_level():
    alert = {"host": "ws-1", "id": "a3", "confidence": 0.9, "severity": "high", "user": "x"}
    trace = _trace(alert)
    assert trace["children"][1]["kind"] == "wait"
    assert trace["children"][1]["label"] == "wait 5m"


def test_render_html_includes_taken_and_skipped_markup():
    alert = {"host": "ws-1", "id": "a4", "confidence": 0.95, "severity": "high", "user": "x"}
    trace = _trace(alert)
    html = render_html(trace, title="test trace")

    assert "<title>test trace</title>" in html
    assert "EXECUTED" in html
    assert "node skipped" in html  # the untaken else-branch action
