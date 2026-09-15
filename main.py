import json

from sentry.interpreter import run
from sentry.lexer import tokenize
from sentry.parser import parse
from sentry.semantics import analyze

PLAYBOOK_PATH = "samples/host_isolation.sentry"
EVENT_NAME = "new_alert"
ALERT_PATHS = [
    "samples/host_isolation_high_confidence.json",
    "samples/host_isolation_low_confidence.json",
]


def main():
    with open(PLAYBOOK_PATH) as f:
        source = f.read()

    print(f"Playbook ({PLAYBOOK_PATH}):")
    print(source)

    tokens = tokenize(source)
    print(f"Lexed {len(tokens)} tokens.")

    program = parse(tokens)
    print("Parsed into AST:")
    print(f"  {program}\n")

    analyze(program)
    print("Semantic analysis: passed.\n")

    for alert_path in ALERT_PATHS:
        with open(alert_path) as f:
            alert = json.load(f)

        print(f"--- Alert ({alert_path}) ---")
        print(f"  {alert}")

        log = run(program, EVENT_NAME, alert)
        print("Audit log:")
        print(log.render())
        print()


if __name__ == "__main__":
    main()
