import argparse
import json
import sys

from sentry.errors import SentryError
from sentry.interpreter import run, run_all
from sentry.lexer import tokenize
from sentry.parser import parse
from sentry.semantics import analyze
from sentry.trace import build_trace, render_html


def _compile(playbook_path: str):
    with open(playbook_path) as f:
        source = f.read()
    program = parse(tokenize(source))
    analyze(program)
    return program


def _load_alert(alert_path: str) -> dict:
    with open(alert_path) as f:
        return json.load(f)


def _cmd_run(args) -> int:
    program = _compile(args.playbook)
    alert = _load_alert(args.alert)
    log = run(program, args.event, alert) if args.event else run_all(program, alert)
    print(log.render())
    return 0


def _cmd_trace(args) -> int:
    program = _compile(args.playbook)
    alert = _load_alert(args.alert)
    blocks = [b for b in program.on_blocks if args.event is None or b.name == args.event]

    if not blocks:
        print(f"error: no 'on {args.event}' block found in {args.playbook}", file=sys.stderr)
        return 1

    sections = [render_html(build_trace(b, alert), title=f"Sentry trace: {b.name}") for b in blocks]
    with open(args.out, "w") as f:
        f.write(sections[0] if len(sections) == 1 else "\n<hr>\n".join(sections))

    print(f"Wrote execution trace to {args.out}")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sentry", description="Sentry: gated, auditable security response playbooks."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a playbook against an alert and print the audit log.")
    run_parser.add_argument("playbook", help="Path to a .sentry playbook file")
    run_parser.add_argument("--alert", required=True, help="Path to a JSON alert file")
    run_parser.add_argument("--event", default=None, help="Only run the 'on <event>' block with this name")
    run_parser.set_defaults(func=_cmd_run)

    trace_parser = subparsers.add_parser("trace", help="Render an execution trace of a playbook as HTML.")
    trace_parser.add_argument("playbook", help="Path to a .sentry playbook file")
    trace_parser.add_argument("--alert", required=True, help="Path to a JSON alert file")
    trace_parser.add_argument("--event", default=None, help="Only trace the 'on <event>' block with this name")
    trace_parser.add_argument("--out", default="trace.html", help="Output HTML file path (default: trace.html)")
    trace_parser.set_defaults(func=_cmd_trace)

    return parser


def main(argv=None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except SentryError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except FileNotFoundError as e:
        print(f"error: file not found: {e.filename}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"error: invalid JSON in alert file: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
