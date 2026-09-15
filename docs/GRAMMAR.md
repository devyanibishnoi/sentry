# Sentry — Formal Grammar (Phase 2 subset)

EBNF for the in-scope Phase 2 subset: sequencing, `if`/`else`, gate
modifiers on action calls, and `wait`. Loops, real tool integration, and a
GUI are out of scope (see `ROADMAP.md`).

Notation: `::=` defines a rule, `|` separates alternatives, `[x]` means `x`
is optional, `{x}` means zero or more repetitions of `x`, `"x"` is a
literal token, UPPERCASE names are tokens produced by the lexer.

```
program        ::= { on_block }

on_block       ::= "ON" IDENTIFIER ":" NEWLINE INDENT statement_list DEDENT

statement_list ::= statement { statement }

statement      ::= action_stmt | if_stmt | wait_stmt

action_stmt    ::= IDENTIFIER "(" [ arg_list ] ")" [ gate ] NEWLINE

arg_list       ::= expression { "," expression }

gate           ::= "REQUIRE" ( comparison | "approval" )

if_stmt        ::= "IF" comparison ":" NEWLINE INDENT statement_list DEDENT
                    [ "ELSE" ":" NEWLINE INDENT statement_list DEDENT ]

wait_stmt      ::= "WAIT" DURATION NEWLINE

comparison     ::= expression comparator expression

comparator     ::= "==" | "!=" | "<" | "<=" | ">" | ">="

expression     ::= field_access | literal

field_access   ::= IDENTIFIER { "." IDENTIFIER }

literal        ::= STRING | NUMBER
```

## Notes on ambiguity / design choices

- **`gate`'s `"approval"` alternative** is not a keyword token — it's
  recognized as a specific `IDENTIFIER` value (`"approval"`) only in this
  one grammar position, right after `REQUIRE`. The lexer has no concept of
  it; the parser checks the token's text. See `KNOWLEDGE_BASE.md` under
  `sentry/tokens.py` for why.
- **`field_access` allows arbitrary chains** (`alert.host.ip`), even though
  the Phase 1 prototype only ever needed one level (`alert.host`). This
  generalizes the `FieldAccess` AST node from `(base, field)` to
  `(root, path)` — see the parser's knowledge-base entry.
- **`wait_stmt` takes a `DURATION` token directly**, not a general
  expression — durations are always literal (`5m`), never computed from a
  field, so there's no need for `wait_stmt` to accept the full `expression`
  rule.
- **No expression nesting/operator precedence** (no `and`/`or`, no
  parenthesized boolean expressions) — `comparison` is exactly one
  `expression comparator expression`, nothing recursive. Kept intentionally
  minimal for this scope; flagged as a natural Phase 3 extension if time
  allows.
