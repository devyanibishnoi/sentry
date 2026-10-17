# Sentry

A domain-specific language for security response playbooks, where gating —
confidence thresholds and approval requirements — is a first-class grammar
construct instead of a policy layer bolted on by whatever platform executes
the playbook.

```
on new_alert:
    if alert.confidence >= 0.8:
        isolate_host(alert.host) require alert.confidence >= 0.9
    else:
        notify_soc(alert.id) require approval
    wait 5m
```

Every action call can carry a `require` modifier directly in its syntax. A
gate is either a comparison against the alert data (auto-executes if true,
refused otherwise) or the bare word `approval` (always refused
automatically — a human has to sign off). Every decision — executed,
refused, or waited — is written to a structured audit log with a reason.

## Setup

```
python3 -m venv .venv
source .venv/bin/activate          # or .venv\Scripts\activate on Windows
pip install pytest
```

## Running the demo

```
python main.py
```

Runs `samples/host_isolation.sentry` through the full pipeline (lex →
parse → semantic analysis → interpret) against two sample alerts, printing
the tokens, the parsed AST, and both alerts' resulting audit logs.

## Using the CLI

```
python -m sentry run <playbook.sentry> --alert <alert.json> [--event NAME]
python -m sentry trace <playbook.sentry> --alert <alert.json> [--event NAME] [--out trace.html]
```

- `run` executes the playbook against the given alert and prints the audit
  log. Without `--event`, every `on` block in the file runs; with it, only
  the block whose name matches runs.
- `trace` renders an HTML execution trace — the playbook's full branching
  structure with the actual taken path highlighted and the untaken branch
  dimmed, plus every action's outcome and reason. Opens in any browser,
  no dependencies.

Example:

```
python -m sentry run samples/host_isolation.sentry --alert samples/host_isolation_high_confidence.json
python -m sentry trace samples/credential_compromise.sentry --alert samples/credential_compromise_alert.json --out trace.html
```

Any invalid playbook or alert file produces a one-line `error: ...` message
on stderr with exit code 1 — never a raw traceback.

## Running the tests

```
pytest tests/ -v
```

65 tests across lexer, parser, semantic analysis, interpreter, trace
visualization, CLI, and boundary/complex-playbook cases.

## Project layout

```
sentry/           interpreter package
  tokens.py        TokenType, Token
  lexer.py         tokenize() — hand-written scanner
  ast_nodes.py     AST node dataclasses
  parser.py        recursive-descent parser
  symbol_table.py  valid actions + alert schema
  semantics.py     semantic analysis pass
  interpreter.py   tree-walking interpreter + gate resolution
  audit.py         AuditEntry, AuditLog
  trace.py         execution trace visualization
  cli.py           CLI entry point (run, trace subcommands)
  errors.py        SentryError hierarchy
tests/            pytest suite, mirrors the module split above
samples/           sample playbooks (.sentry) + sample alerts (.json)
docs/              formal grammar, implementation progress, performance note
main.py            CLI entry point used for live demos
```

## Language reference

The formal EBNF grammar is in `docs/GRAMMAR.md`. Valid actions and their
expected argument types, and the fields available on `alert`, are defined
in `sentry/symbol_table.py`.

**Gate syntax:** `action(args) require <condition>`, where `<condition>` is
either a comparison (`alert.confidence >= 0.9`) or the literal word
`approval`.

**Valid actions:** `isolate_host`, `notify_soc`, `block_ip`,
`quarantine_file`, `disable_user` — each takes one string argument.

**Alert fields:** `alert.host`, `alert.id`, `alert.severity`, `alert.user`
(strings), `alert.confidence` (number).

## Known simplifications

`wait` is simulated (logged, not a real delay). No string escape sequences.
No boolean `and`/`or` or parenthesized conditions. No loops. The type
system is two flat types, `string` and `number`.
