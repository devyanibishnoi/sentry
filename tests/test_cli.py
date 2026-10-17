import json
import os

import pytest

from sentry.cli import main


@pytest.fixture
def playbook_path(tmp_path):
    path = tmp_path / "test.sentry"
    path.write_text(
        "on new_alert:\n"
        "    if alert.confidence >= 0.8:\n"
        "        isolate_host(alert.host) require alert.confidence >= 0.9\n"
        "    else:\n"
        "        notify_soc(alert.id) require approval\n"
        "    wait 5m\n"
    )
    return str(path)


@pytest.fixture
def alert_path(tmp_path):
    path = tmp_path / "alert.json"
    path.write_text(json.dumps({"host": "ws-1", "id": "a1", "confidence": 0.95, "severity": "high", "user": "x"}))
    return str(path)


def test_run_prints_audit_log(playbook_path, alert_path, capsys):
    exit_code = main(["run", playbook_path, "--alert", alert_path])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "EXECUTED" in out
    assert "isolate_host" in out


def test_run_with_event_filters_to_matching_block(playbook_path, alert_path, capsys):
    exit_code = main(["run", playbook_path, "--alert", alert_path, "--event", "new_alert"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "EXECUTED" in out


def test_run_with_nonmatching_event_produces_empty_log(playbook_path, alert_path, capsys):
    exit_code = main(["run", playbook_path, "--alert", alert_path, "--event", "nothing_listens_here"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert out.strip() == ""


def test_trace_writes_html_file(playbook_path, alert_path, tmp_path, capsys):
    out_path = str(tmp_path / "trace.html")
    exit_code = main(["trace", playbook_path, "--alert", alert_path, "--out", out_path])
    capsys.readouterr()
    assert exit_code == 0
    assert os.path.exists(out_path)
    content = open(out_path).read()
    assert "<title>" in content
    assert "EXECUTED" in content


def test_unknown_action_prints_clean_error_not_traceback(tmp_path, alert_path, capsys):
    bad_playbook = tmp_path / "bad.sentry"
    bad_playbook.write_text("on x:\n    nuke(alert.host)\n")

    exit_code = main(["run", str(bad_playbook), "--alert", alert_path])
    err = capsys.readouterr().err

    assert exit_code == 1
    assert err.startswith("error:")
    assert "Unknown action" in err


def test_missing_playbook_file_prints_clean_error(alert_path, capsys):
    exit_code = main(["run", "does_not_exist.sentry", "--alert", alert_path])
    err = capsys.readouterr().err
    assert exit_code == 1
    assert err.startswith("error: file not found")


def test_invalid_json_alert_prints_clean_error(playbook_path, tmp_path, capsys):
    bad_alert = tmp_path / "bad_alert.json"
    bad_alert.write_text("{not valid json")

    exit_code = main(["run", playbook_path, "--alert", str(bad_alert)])
    err = capsys.readouterr().err
    assert exit_code == 1
    assert err.startswith("error: invalid JSON")
