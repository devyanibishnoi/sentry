import pytest

from sentry.lexer import tokenize
from sentry.parser import parse
from sentry.semantics import analyze
from sentry.interpreter import run, run_all
from sentry.errors import LexError

COMPLEX_SOURCE = (
    "on credential_compromise:\n"
    "    if alert.severity == \"high\":\n"
    "        if alert.confidence >= 0.9:\n"
    "            disable_user(alert.user) require alert.confidence >= 0.95\n"
    "        else:\n"
    "            disable_user(alert.user) require approval\n"
    "        notify_soc(alert.id)\n"
    "        wait 2m\n"
    "    else:\n"
    "        if alert.confidence >= 0.5:\n"
    "            notify_soc(alert.id) require alert.confidence >= 0.6\n"
    "        else:\n"
    "            notify_soc(alert.id)\n"
    "        wait 10m\n"
    "    wait 1m\n"
)


def _run_complex(alert: dict):
    program = parse(tokenize(COMPLEX_SOURCE))
    analyze(program)
    return run(program, "credential_compromise", alert)


def test_complex_playbook_high_severity_high_confidence_executes_inner_gate():
    alert = {"host": "h", "id": "i", "confidence": 0.97, "severity": "high", "user": "u"}
    log = _run_complex(alert)
    statuses = [e.status for e in log.entries]
    assert statuses == ["executed", "executed", "waited", "waited"]


def test_complex_playbook_high_severity_low_confidence_falls_to_approval_gate():
    alert = {"host": "h", "id": "i", "confidence": 0.5, "severity": "high", "user": "u"}
    log = _run_complex(alert)
    assert log.entries[0].status == "refused"
    assert log.entries[0].reason == "requires manual approval"


def test_complex_playbook_not_high_severity_takes_outer_else():
    alert = {"host": "h", "id": "i", "confidence": 0.55, "severity": "medium", "user": "u"}
    log = _run_complex(alert)
    statuses = [e.status for e in log.entries]
    assert statuses == ["refused", "waited", "waited"]
    assert log.entries[1].reason.startswith("waited 10m")


def test_confidence_exactly_at_gate_threshold_is_satisfied():
    # >= is inclusive: exactly 0.9 must satisfy "alert.confidence >= 0.9"
    source = "on x:\n    isolate_host(alert.host) require alert.confidence >= 0.9\n"
    program = parse(tokenize(source))
    analyze(program)
    alert = {"host": "h", "id": "i", "confidence": 0.9, "severity": "high", "user": "u"}
    log = run(program, "x", alert)
    assert log.entries[0].status == "executed"


def test_confidence_just_below_gate_threshold_is_refused():
    source = "on x:\n    isolate_host(alert.host) require alert.confidence >= 0.9\n"
    program = parse(tokenize(source))
    analyze(program)
    alert = {"host": "h", "id": "i", "confidence": 0.8999999, "severity": "high", "user": "u"}
    log = run(program, "x", alert)
    assert log.entries[0].status == "refused"


def test_zero_duration_wait_is_handled():
    source = "on x:\n    wait 0s\n"
    program = parse(tokenize(source))
    analyze(program)
    log = run(program, "x", {})
    assert log.entries[0].status == "waited"
    assert log.entries[0].reason == "waited 0s (simulated, no real delay)"


def test_on_block_with_only_a_wait_statement_is_valid():
    source = "on x:\n    wait 5m\n"
    program = parse(tokenize(source))
    analyze(program)
    log = run(program, "x", {})
    assert len(log) == 1


def test_program_with_multiple_on_blocks_dispatches_by_name():
    source = (
        "on alert_a:\n"
        "    isolate_host(alert.host)\n"
        "on alert_b:\n"
        "    notify_soc(alert.id)\n"
    )
    program = parse(tokenize(source))
    analyze(program)

    alert = {"host": "h", "id": "i"}
    log_a = run(program, "alert_a", alert)
    log_b = run(program, "alert_b", alert)

    assert log_a.entries[0].action.startswith("isolate_host")
    assert log_b.entries[0].action.startswith("notify_soc")


def test_run_all_executes_every_on_block_regardless_of_name():
    source = (
        "on alert_a:\n"
        "    isolate_host(alert.host)\n"
        "on alert_b:\n"
        "    notify_soc(alert.id)\n"
    )
    program = parse(tokenize(source))
    analyze(program)

    log = run_all(program, {"host": "h", "id": "i"})
    assert len(log) == 2


def test_empty_source_produces_empty_program():
    program = parse(tokenize(""))
    analyze(program)
    assert program.on_blocks == []


def test_deeply_mismatched_dedent_is_a_lex_error():
    # a dedent that doesn't land on any previously open indentation level
    source = "on x:\n    if alert.confidence >= 0.5:\n        isolate_host(alert.host)\n   wait 1m\n"
    with pytest.raises(LexError):
        tokenize(source)
