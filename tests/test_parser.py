import pytest

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
from sentry.lexer import tokenize
from sentry.parser import parse


def _parse(source: str) -> Program:
    return parse(tokenize(source))


def test_parses_full_sample_playbook():
    source = (
        "on new_alert:\n"
        "    if alert.confidence >= 0.8:\n"
        "        isolate_host(alert.host) require alert.confidence >= 0.9\n"
        "    else:\n"
        "        notify_soc(alert.id) require approval\n"
        "    wait 5m\n"
    )

    tree = _parse(source)

    assert tree == Program(
        on_blocks=[
            OnBlock(
                name="new_alert",
                body=[
                    IfElse(
                        condition=Comparison(
                            left=FieldAccess(root="alert", path=["confidence"]),
                            operator=">=",
                            right=Literal(value=0.8),
                        ),
                        then_body=[
                            ActionCall(
                                name="isolate_host",
                                args=[FieldAccess(root="alert", path=["host"])],
                                gate=Comparison(
                                    left=FieldAccess(root="alert", path=["confidence"]),
                                    operator=">=",
                                    right=Literal(value=0.9),
                                ),
                            )
                        ],
                        else_body=[
                            ActionCall(
                                name="notify_soc",
                                args=[FieldAccess(root="alert", path=["id"])],
                                gate=ApprovalRequired(),
                            )
                        ],
                    ),
                    WaitStmt(duration=Duration(amount=5, unit="m")),
                ],
            )
        ]
    )


def test_action_call_without_gate():
    tree = _parse("on x:\n    isolate_host(alert.host)\n")
    action = tree.on_blocks[0].body[0]
    assert action == ActionCall(
        name="isolate_host",
        args=[FieldAccess(root="alert", path=["host"])],
        gate=None,
    )


def test_action_call_with_multiple_args():
    tree = _parse('on x:\n    notify(alert.id, "high", 5)\n')
    action = tree.on_blocks[0].body[0]
    assert action.args == [
        FieldAccess(root="alert", path=["id"]),
        Literal(value="high"),
        Literal(value=5),
    ]


def test_chained_field_access():
    tree = _parse("on x:\n    isolate_host(alert.host.ip)\n")
    action = tree.on_blocks[0].body[0]
    assert action.args == [FieldAccess(root="alert", path=["host", "ip"])]


def test_if_without_else():
    tree = _parse(
        "on x:\n"
        "    if alert.confidence >= 0.5:\n"
        "        isolate_host(alert.host)\n"
    )
    stmt = tree.on_blocks[0].body[0]
    assert isinstance(stmt, IfElse)
    assert stmt.else_body is None


def test_string_and_number_literal_comparisons():
    tree = _parse(
        'on x:\n'
        '    if alert.severity == "high":\n'
        '        isolate_host(alert.host)\n'
    )
    condition = tree.on_blocks[0].body[0].condition
    assert condition == Comparison(
        left=FieldAccess(root="alert", path=["severity"]),
        operator="==",
        right=Literal(value="high"),
    )


@pytest.mark.parametrize(
    "source",
    [
        # missing colon after 'on x'
        "on x\n    isolate_host(alert.host)\n",
        # missing closing paren
        "on x:\n    isolate_host(alert.host\n",
        # 'require' with no condition or 'approval' after it
        "on x:\n    isolate_host(alert.host) require\n",
        # 'if' with no comparator
        "on x:\n    if alert.confidence:\n        isolate_host(alert.host)\n",
        # dangling dot in a field access
        "on x:\n    isolate_host(alert.)\n",
    ],
)
def test_malformed_input_raises_parse_error(source):
    with pytest.raises(ParseError):
        _parse(source)
