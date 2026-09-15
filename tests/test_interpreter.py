import pytest

from sentry.errors import InterpreterError
from sentry.lexer import tokenize
from sentry.parser import parse
from sentry.interpreter import run

SOURCE = (
    "on new_alert:\n"
    "    if alert.confidence >= 0.8:\n"
    "        isolate_host(alert.host) require alert.confidence >= 0.9\n"
    "    else:\n"
    "        notify_soc(alert.id) require approval\n"
    "    wait 5m\n"
)


def _run(alert: dict, event_name: str = "new_alert"):
    program = parse(tokenize(SOURCE))
    return run(program, event_name, alert)


def test_high_confidence_executes_and_waits():
    alert = {"host": "ws-12", "id": "a1", "confidence": 0.95, "severity": "high", "user": "jdoe"}
    log = _run(alert)

    assert len(log) == 2
    assert log.entries[0].status == "executed"
    assert log.entries[0].action == "isolate_host('ws-12')"
    assert "gate satisfied" in log.entries[0].reason
    assert log.entries[1].status == "waited"


def test_confidence_above_if_threshold_but_below_gate_threshold_is_refused():
    alert = {"host": "ws-12", "id": "a1", "confidence": 0.85, "severity": "medium", "user": "jdoe"}
    log = _run(alert)

    assert len(log) == 2
    assert log.entries[0].status == "refused"
    assert "gate not satisfied" in log.entries[0].reason
    assert log.entries[1].status == "waited"


def test_low_confidence_takes_else_branch_and_is_refused_for_approval():
    alert = {"host": "ws-12", "id": "a1", "confidence": 0.5, "severity": "low", "user": "jdoe"}
    log = _run(alert)

    assert len(log) == 2
    assert log.entries[0].status == "refused"
    assert log.entries[0].action == "notify_soc('a1')"
    assert log.entries[0].reason == "requires manual approval"
    assert log.entries[1].status == "waited"


def test_unmatched_event_name_produces_empty_log():
    alert = {"host": "ws-12", "id": "a1", "confidence": 0.95, "severity": "high", "user": "jdoe"}
    log = _run(alert, event_name="some_other_event")
    assert len(log) == 0


def test_action_without_gate_always_executes():
    program = parse(tokenize("on x:\n    isolate_host(alert.host)\n"))
    log = run(program, "x", {"host": "ws-1"})
    assert len(log) == 1
    assert log.entries[0].status == "executed"
    assert log.entries[0].reason == "no gate condition"


def test_missing_alert_field_raises_interpreter_error():
    program = parse(tokenize("on x:\n    isolate_host(alert.host)\n"))
    with pytest.raises(InterpreterError, match="Alert data is missing field 'alert.host'"):
        run(program, "x", {"id": "a1"})  # no 'host' key
