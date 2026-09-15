from sentry.lexer import tokenize
from sentry.parser import parse

SAMPLE_PLAYBOOK = """on new_alert:
    if alert.confidence >= 0.8:
        isolate_host(alert.host) require alert.confidence >= 0.9
    else:
        notify_soc(alert.id) require approval
    wait 5m
"""


def main():
    print("Source:")
    print(SAMPLE_PLAYBOOK)

    tokens = tokenize(SAMPLE_PLAYBOOK)
    print("Tokens:")
    for token in tokens:
        print(f"  {token}")

    tree = parse(tokens)
    print("\nAST:")
    print(f"  {tree}")


if __name__ == "__main__":
    main()
