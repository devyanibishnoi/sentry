from sentry.lexer import tokenize
from sentry.parser import parse

SAMPLE_LINE = "isolate_host(alert.host)"


def main():
    print(f"Source: {SAMPLE_LINE}\n")

    tokens = tokenize(SAMPLE_LINE)
    print("Tokens:")
    for token in tokens:
        print(f"  {token}")

    tree = parse(tokens)
    print("\nAST:")
    print(f"  {tree}")


if __name__ == "__main__":
    main()
