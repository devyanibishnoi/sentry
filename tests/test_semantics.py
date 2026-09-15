import pytest

from sentry.errors import SemanticError
from sentry.lexer import tokenize
from sentry.parser import parse
from sentry.semantics import analyze


def _analyze(source: str) -> None:
    analyze(parse(tokenize(source)))


def test_valid_sample_playbook_passes():
    source = (
        "on new_alert:\n"
        "    if alert.confidence >= 0.8:\n"
        "        isolate_host(alert.host) require alert.confidence >= 0.9\n"
        "    else:\n"
        "        notify_soc(alert.id) require approval\n"
        "    wait 5m\n"
    )
    _analyze(source)  # should not raise


def test_unknown_action_raises_semantic_error():
    with pytest.raises(SemanticError, match="Unknown action"):
        _analyze("on x:\n    nuke_everything(alert.host)\n")


def test_wrong_argument_count_raises_semantic_error():
    with pytest.raises(SemanticError, match="expects 1 argument"):
        _analyze('on x:\n    isolate_host(alert.host, alert.id)\n')


def test_wrong_argument_type_raises_semantic_error():
    with pytest.raises(SemanticError, match="expects a string argument"):
        _analyze("on x:\n    isolate_host(alert.confidence)\n")


def test_unknown_field_raises_semantic_error():
    with pytest.raises(SemanticError, match="Unknown field 'alert.nonexistent'"):
        _analyze("on x:\n    isolate_host(alert.nonexistent)\n")


def test_unknown_root_variable_raises_semantic_error():
    with pytest.raises(SemanticError, match="Unknown variable 'foo'"):
        _analyze("on x:\n    isolate_host(foo.host)\n")


def test_type_mismatch_in_comparison_raises_semantic_error():
    with pytest.raises(SemanticError, match="cannot compare"):
        _analyze(
            'on x:\n'
            '    if alert.severity >= 5:\n'
            '        isolate_host(alert.host)\n'
        )


def test_invalid_operator_for_string_comparison_raises_semantic_error():
    with pytest.raises(SemanticError, match="not valid for strings"):
        _analyze(
            'on x:\n'
            '    if alert.severity >= "high":\n'
            '        isolate_host(alert.host)\n'
        )


def test_type_mismatch_in_gate_condition_raises_semantic_error():
    with pytest.raises(SemanticError, match="cannot compare"):
        _analyze('on x:\n    isolate_host(alert.host) require alert.host >= 5\n')
