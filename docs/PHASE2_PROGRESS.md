# Sentry — Phase 2 Implementation Progress

Status as of Phase 2 (targets Review 2). Full technical detail and design
rationale live in the local study notes; this is the reviewer-facing
summary of what exists and why.

## What Phase 2 delivers

A complete pipeline from raw playbook text to a logged execution decision:

```
source (.sentry) → lexer → parser → semantic analysis → interpreter → audit log
```

The Phase 1 prototype only proved the lexer and parser could tokenize and
parse a single hand-written line. Phase 2 turns that into the actual
language: full playbooks with `on` blocks, `if`/`else` branching, and —
the project's central idea — gate modifiers (`require <condition>` or
`require approval`) attached directly to action calls, checked for
validity before execution and enforced at execution time.

## Module-wise breakdown

**Lexer (`sentry/lexer.py`, `sentry/tokens.py`).** Extended from 5 token
types to a full set: keywords (`on`, `if`, `else`, `wait`, `require`),
comparison operators, string/number/duration literals, and Python-style
`INDENT`/`DEDENT`/`NEWLINE` tokens for block structure, using a
stack-based indentation algorithm. Hand-written, no lexer-generator tool.

**Formal grammar (`docs/GRAMMAR.md`).** EBNF for the full in-scope
subset — sequencing, `if`/`else`, gate modifiers, `wait` — written before
the parser, so the parser's structure is a direct translation of it. This
closes the "formal grammar" gap flagged as pending in the Phase 1 doc.

**Parser + AST (`sentry/parser.py`, `sentry/ast_nodes.py`).**
Hand-written recursive-descent parser, one method per grammar rule.
Produces a `Program` of `OnBlock`s, each holding a sequence of
`ActionCall` (optionally gated), `IfElse`, and `WaitStmt` nodes.

**Symbol table (`sentry/symbol_table.py`).** Registry of valid actions and
their expected argument types, and the schema of fields available on
`alert`. Pure data, no logic — kept separate from the checking code that
uses it.

**Semantic analysis (`sentry/semantics.py`).** Walks the AST against the
symbol table before anything executes: rejects undefined actions,
undefined/misspelled alert fields, argument type mismatches, and malformed
gate conditions (including type-incompatible comparisons and invalid
operators for string comparisons).

**Interpreter (`sentry/interpreter.py`).** Tree-walking execution against
a plain `dict` of sample alert data. Handles sequencing, `if`/`else`
branching, and — for every action call — resolves its gate: no gate
executes unconditionally, a comparison gate executes only if the condition
holds against the actual alert data, and an approval gate never executes
automatically.

**Audit log (`sentry/audit.py`).** Structured record of every action the
interpreter encountered, with its outcome (executed / refused / waited)
and a human-readable reason. This is the actual point of the project —
every gating decision the interpreter makes is visible and explainable,
not a black box.

**Samples (`samples/`).** Five sample playbook + alert combinations
covering different action types, a string-based condition, an ungated
action, and a playbook with no `if`/`else` at all — used for the live
Review 2 demonstration via `main.py`.

## Test coverage

40 tests across 4 files (`pytest tests/ -v`, all passing):

| File | Tests | Covers |
|---|---|---|
| `test_lexer.py` | 14 | keywords, operators, literals, indentation, illegal input |
| `test_parser.py` | 11 (15 parametrized cases) | full playbook parsing, malformed input |
| `test_semantics.py` | 9 | undefined actions/fields, type mismatches, malformed gates |
| `test_interpreter.py` | 6 | gate resolution, sequencing, missing alert data |

Every module has at least one deliberately invalid input case alongside
its happy-path coverage.

## Known scope simplifications

- No line/column tracking on semantic errors yet (AST nodes don't carry
  source position) — flagged for Phase 3's richer-diagnostics stretch goal.
- `wait` is simulated (logged, not a real delay).
- No string escape sequences.
- No boolean `and`/`or`, no parenthesized conditions, no loops.
- Type system is two flat types (`string`, `number`) — sufficient for this
  scope, not a general type system.

## Next steps (Phase 3)

CLI integration (`python -m sentry run playbook.sentry --alert alert.json`),
a full testing matrix, richer error messages, a performance note, and the
final report chapters covering implementation and testing.
