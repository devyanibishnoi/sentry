# Sentry: A Domain-Specific Language for Gated, Auditable Security Response Automation

Compiler Design Laboratory Project (BCSE307P) — Final Report
Devyani Bishnoi · Registration Number: 24BCI0167

---

## Chapter 1: Introduction

Security teams have no shortage of tools that describe what to do when
something goes wrong. What most of them don't do is enforce how much that
response should actually be trusted before it runs. Sentry is a small
language built around that one problem. A security engineer writes an
incident response playbook in it, and instead of approval and audit logging
living somewhere outside the playbook — in whatever platform happens to
execute it — Sentry treats gating as part of the grammar itself. An action
can carry a confidence threshold or require explicit approval, and the
interpreter will not run it until that condition holds, logging the
decision either way, refused or not.

Building Sentry meant building the whole compiler pipeline behind it:
lexing, parsing, semantic validation, interpretation, and — once the core
language was solid — a command-line tool, richer diagnostics, and an
execution trace visualizer. The question this project set out to answer was
whether a language's design can double as a safety mechanism, not just a
way of writing syntax. By the end of Phase 3, that pipeline is complete,
tested, and runnable end to end through a real CLI.

## Chapter 2: Problem Statement

Most security automation today — SOAR platforms, playbook runners like
Ansible — treats a playbook as a flat list of steps to execute. Approval
and audit logging aren't part of the playbook itself; they're handled by
whatever system happens to be running it. Which means the same exact
playbook can behave differently depending on where it's deployed, and
there's no real way to guarantee a high-risk action actually got gated the
way it was supposed to.

Sentry fixes this at the language level rather than the platform level. If
an action needs approval, or a minimum confidence score, that requirement
lives directly in the playbook's source code, not in some external policy
engine the interpreter could theoretically be pointed away from. What this
project actually tries to answer is whether a language can enforce safer
automation just through how it's designed, instead of depending on
whatever happens to be running it.

## Chapter 3: Objectives

1. Work out a formal grammar for Sentry where gating — confidence
   thresholds and approval requirements — sits as a first-class construct
   rather than an external rule. *(Achieved: `docs/GRAMMAR.md`, with
   `require` as a grammar production on the action-call rule itself.)*
2. Get a lexer correctly tokenizing Sentry source: keywords, identifiers,
   operators, string literals, duration literals, and indentation-based
   block structure. *(Achieved: `sentry/lexer.py`, 14 dedicated tests.)*
3. Have a recursive-descent parser turn that token stream into an abstract
   syntax tree, rejecting structurally invalid playbooks with clear
   errors. *(Achieved: `sentry/parser.py`, position-aware `ParseError`.)*
4. Back semantic analysis with a symbol table that validates every action,
   alert field, and gate condition before anything is allowed to run.
   *(Achieved: `sentry/symbol_table.py`, `sentry/semantics.py`, now with
   "did you mean" suggestions and source positions.)*
5. Get a tree-walking interpreter executing valid playbooks against sample
   alert data, handling sequencing, conditionals, and gate decisions
   correctly. *(Achieved: `sentry/interpreter.py`.)*
6. Make sure every executed and every refused action ends up in an audit
   log, so the system's behaviour can be checked after the fact.
   *(Achieved: `sentry/audit.py`.)*
7. *(Added in Phase 3, beyond the original scope)* Integrate the pipeline
   into one CLI tool, add rich compile-time diagnostics, and generate an
   execution trace visualization directly from the AST.

## Chapter 4: Literature Survey / Background Study

Before locking in Sentry's syntax, it was worth looking at what already
exists.

**Ansible** playbooks are declarative, YAML-based, and genuinely good at
describing a sequence of actions, but there's no concept of gating built
in — approval is somebody else's problem, handled by a separate step or
tool entirely.

**SOAR platforms** like Splunk SOAR or Shuffle mostly represent playbooks
as visual workflow graphs, where approval is just another box in the flow
rather than something the execution model itself enforces.

**Sigma**, on the detection side, shows how cleanly a domain-specific
language can express conditions, though it's built for detection, not
response, so execution and gating never really come into it.

**Open Policy Agent's Rego** is closer to what gating conceptually needs,
since it's built specifically to express policy decisions as code. Reading
through how Rego evaluates conditions shaped a lot of how Sentry's gate
expressions ended up structured — this is the closest relative in the
survey.

The most useful thing that came out of this reading wasn't about syntax at
all — it was the tradeoff between an **embedded DSL** and a **standalone
language**. An embedded DSL, say a Python library dressed up to look like a
playbook language, can always be bypassed by just calling the underlying
function directly. Gating stays a convention at that point, never a
guarantee. A standalone interpreted language doesn't have that escape
hatch — there's no API surface to skip past, the interpreter is the only
way anything actually runs. That's the real reason Sentry is built as its
own language instead of a library sitting on top of one, and it remains
the project's strongest originality argument.

## Chapter 5: System Design

Sentry's pipeline traces a playbook from source text all the way to a
logged decision:

```
source text → Lexer → tokens → Parser → AST → Semantic Analyzer
            → validated AST → Interpreter → Audit Log
```

The Lexer reads raw playbook text and produces a token stream, catching
illegal characters and malformed literals early. The Parser consumes that
stream using recursive descent and builds an abstract syntax tree,
rejecting anything structurally invalid with a position-aware error. The
Semantic Analyzer walks that tree against a symbol table of valid actions,
alert fields, and gate conditions, catching type mismatches and undefined
references — now with "did you mean" suggestions — before anything is
allowed to execute. The Interpreter walks only the validated tree,
evaluates conditions, sequences actions, checks each action's gate, and
routes every decision into the audit log.

Phase 3 wraps this pipeline in a CLI (`python -m sentry run` / `trace`) and
adds a parallel visualization path: the same AST, walked a fourth time,
rendered as an HTML execution trace showing the playbook's full branching
structure with the actually-taken path highlighted.

## Chapter 6: Methodology

Sentry follows the same pipeline any compiler or interpreter does, built in
three phases:

**Phase 1 — Prototype.** Proved the lexer and parser could work together,
on one hand-written line (`isolate_host(alert.host)`), tokenized and parsed
into an `ActionCall` holding a `FieldAccess`. No gating, sequencing, or
blocks yet.

**Phase 2 — Core Implementation.** Extended the lexer to a full token set
(keywords, operators, literals, indentation-aware blocks); wrote the formal
EBNF grammar; built the full recursive-descent parser producing a complete
AST (`OnBlock`, gated `ActionCall`, `IfElse`, `WaitStmt`); built the symbol
table and semantic analysis pass; built the tree-walking interpreter with
gate resolution; built the audit log; and assembled a sample-playbook
library for live demonstration.

**Phase 3 — Final Implementation and Testing.** Added source positions to
AST nodes and "did you mean" suggestions to semantic errors; built a CLI
entry point unifying the whole pipeline behind two subcommands (`run`,
`trace`); built an AST-based execution trace visualizer; completed the
testing matrix with a genuinely complex nested playbook and explicit
boundary cases; measured real performance; and wrote user-facing
documentation (this report, `README.md`, `docs/PERFORMANCE.md`).

Each stage was built test-first where the logic was non-trivial: tests for
the expected behaviour were written before the implementation, including
at least one deliberately invalid input per stage, not just the happy
path.

## Chapter 7: Compiler Design Concepts Used

- **Lexical analysis** — hand-written scanner using maximal-munch
  tokenizing for keywords (`on`, `if`, `else`, `wait`, `require`),
  identifiers, operators, string/number/duration literals, and a
  stack-based indentation algorithm producing `INDENT`/`DEDENT`/`NEWLINE`
  tokens (the same technique Python's own tokenizer uses).
- **Context-free grammar design and recursive-descent parsing** — a formal
  EBNF grammar (`docs/GRAMMAR.md`) translated near-mechanically into one
  parser method per production rule, exploiting the grammar's deliberate
  LL(1) property (one token of lookahead always determines which rule
  applies) to avoid backtracking.
- **Abstract syntax tree construction and traversal** — a small set of
  dataclass node types (`ActionCall`, `FieldAccess`, `Comparison`,
  `IfElse`, `WaitStmt`, `OnBlock`, `Program`) that deliberately discard
  concrete syntax (parentheses, colons) once their structural meaning is
  captured, walked independently by three later passes.
- **Symbol table management** — a registry (`ACTIONS`, `ALERT_SCHEMA`)
  tracking valid actions, their expected argument types, and valid alert
  fields, kept as pure data separate from the logic that checks against it.
- **Semantic analysis** — a tree-walking pass performing type checking,
  gate condition validation, and detection of undefined actions or fields,
  using `isinstance`-based dispatch rather than a visitor pattern baked
  into the AST classes.
- **Tree-walking interpretation** — control flow, sequencing, and
  conditional branching evaluated directly over the AST, with gate
  resolution (the project's central mechanism) implemented as a three-way
  dispatch on `ActionCall.gate`'s runtime type.
- **Error handling and diagnostics** — a `SentryError` exception hierarchy
  spanning all four stages (lexical, syntax, semantic, runtime), extended
  in Phase 3 with source positions and fuzzy-match suggestions on semantic
  errors, and surfaced at the CLI layer as clean one-line messages rather
  than raw tracebacks.

## Chapter 8: Implementation

**Lexer (`sentry/lexer.py`, `sentry/tokens.py`).** `tokenize()` processes
source line by line: each line's indentation is resolved first (against a
stack of open indent widths, emitting `INDENT`/`DEDENT` as needed), then
the line's content is scanned character by character for keywords,
identifiers, operators, and literals, ending in a `NEWLINE`. Keywords are
recognized by scanning a run of letters exactly like an identifier, then
checking the resulting text against a fixed lookup table — one code path
for both, rather than two. `approval` is deliberately *not* a keyword; it
lexes as an ordinary identifier, and only the parser gives it meaning, in
the one grammar position where it matters.

**Grammar (`docs/GRAMMAR.md`).** Written before further parser code, so
the parser's structure would be a direct translation of it rather than
something invented ad hoc. Covers sequencing, `if`/`else`, gate modifiers,
and `wait`; deliberately excludes boolean `and`/`or`, parenthesized
conditions, and loops.

**Parser and AST (`sentry/parser.py`, `sentry/ast_nodes.py`).** One method
per grammar rule. `FieldAccess` generalizes from a single-level
`(base, field)` pair (Phase 1) to an arbitrary `(root, path)` chain,
supporting access like `alert.host.ip` without changing the parsing
strategy from a loop to recursion. `ActionCall.gate` is the single field
that realizes the project's central idea: gating is literally a value
carried by the action-call node, not a wrapper around it.

**Symbol table and semantic analysis (`sentry/symbol_table.py`,
`sentry/semantics.py`).** Two flat dictionaries describe what's valid;
a separate tree-walking pass checks the AST against them, catching
undefined actions, undefined fields, argument type/count mismatches, and
malformed gate conditions — including a rule specific to this language
that string comparisons may only use `==`/`!=`, not ordering operators.

**Interpreter and audit log (`sentry/interpreter.py`,
`sentry/audit.py`).** The interpreter resolves every action's gate into
exactly one of three outcomes — unconditional execution, a comparison
evaluated against real alert data, or an unconditional refusal pending
human approval — and records each outcome as a structured, human-readable
audit entry explaining *why* the decision was made, not just what it was.

**Phase 3 additions:**

- *Source positions and diagnostics.* `ActionCall`, `FieldAccess`,
  `Comparison`, `IfElse`, and `WaitStmt` now carry `line`/`column`
  (excluded from equality comparisons so existing tests built around
  hand-constructed AST nodes were unaffected). `SemanticError` and
  `InterpreterError` gained optional position parameters, and semantic
  errors for unknown actions or fields now suggest the closest valid name
  via fuzzy string matching.
- *CLI (`sentry/cli.py`, `sentry/__main__.py`).* `python -m sentry run`
  and `python -m sentry trace` wrap the full pipeline behind `argparse`
  subcommands, with every `SentryError`, missing file, and malformed JSON
  input caught in one place and surfaced as a clean one-line message
  instead of a traceback.
- *Execution trace visualization (`sentry/trace.py`).* A fourth AST
  traversal builds a nested structure describing the full branching shape
  of an `on` block with execution results annotated on top — both branches
  of every `if`/`else` are kept in the output, with the untaken one
  visually dimmed, so what's produced is the AST with execution laid over
  it, not a flattened log.

## Chapter 9: Testing and Results

The test suite covers 65 tests across eight files, all passing:

| File | Tests | Covers |
|---|---|---|
| `test_lexer.py` | 14 | keywords, operators, literals, indentation, illegal input |
| `test_parser.py` | 11 (15 cases) | full playbook parsing, 5 malformed-input shapes |
| `test_semantics.py` | 12 | undefined actions/fields, type mismatches, malformed gates, suggestions, positions |
| `test_interpreter.py` | 6 | gate resolution, sequencing, missing alert data |
| `test_trace.py` | 4 | branch-taken/skipped marking, HTML output |
| `test_cli.py` | 7 | both subcommands, clean error paths, exit codes |
| `test_boundary_cases.py` | 10 | threshold equality, zero duration, multi-block dispatch, empty source, deep dedent mismatch |
| **Total** | **65** | |

**Testing matrix**, as required for Phase 3:

- *Valid inputs* — every sample playbook in `samples/`, plus the canonical
  playbook used throughout development.
- *Invalid inputs* — at least one deliberately malformed case per pipeline
  stage: an illegal character (lexer), a missing token (parser), an
  unknown action/field (semantic analysis), missing alert data
  (interpreter), a missing file or malformed JSON (CLI).
- *Boundary cases* — exact threshold equality on a `>=` gate, a
  zero-length `wait`, an `on` block containing only a single statement, a
  file with multiple `on` blocks, and empty source.
- *Error conditions* — every error type (`LexError`, `ParseError`,
  `SemanticError`, `InterpreterError`) confirmed to carry a specific,
  actionable message, and confirmed never to surface as a raw traceback
  at the CLI layer.
- *A genuinely complex playbook* — `samples/credential_compromise.sentry`,
  nesting `if`/`else` inside both branches of an outer `if`/`else`, mixing
  all three gate shapes in one file, with `wait` statements at two
  different nesting depths.

**Sample result**, `host_isolation.sentry` run against two different
alerts (`python -m sentry run`):

```
[EXECUTED] isolate_host('workstation-12') - gate satisfied: alert.confidence >= 0.9
[WAITED  ] wait - waited 5m (simulated, no real delay)
```
```
[REFUSED ] notify_soc('alert-1002') - requires manual approval
[WAITED  ] wait - waited 5m (simulated, no real delay)
```

Same playbook, two alerts, two different and correctly-reasoned gating
decisions — the project's central argument made visible in one command's
output.

**Performance** (full detail in `docs/PERFORMANCE.md`): the complete
pipeline, run 1000 times against the most complex sample playbook, averages
~119 microseconds per run with ~19 KB peak memory for a single run. Every
stage is a single linear pass over its input, so cost scales with playbook
size, not combinatorially — the gating mechanism itself introduces no
meaningful latency.

## Chapter 10: Conclusion

The central question this project set out to answer was whether a
language's own design could double as a safety mechanism, rather than
being just a way of writing syntax that some external system then has to
be trusted to enforce correctly. The answer, demonstrated across all three
phases, is yes, within the scope this project defined: because `require`
is a production in the grammar itself, and because Sentry is a standalone
interpreted language with no library surface to call around, there is no
path to executing a gated action that skips evaluating its gate. The audit
log is complete by construction — every decision the interpreter makes,
executed or refused, is logged with a reason, because logging is built into
the same code path that evaluates the gate, not bolted on afterward.

All six original objectives were met, and the three Phase 3 stretch goals
(line/column diagnostics, "did you mean" suggestions, and an AST-based
execution trace visualizer) were completed as well, on top of the required
CLI integration and testing matrix. The result is a small but complete
language: lexer, formal grammar, parser, symbol table, semantic analysis,
interpreter, audit log, CLI, and visualization, backed by 65 passing tests
spanning valid input, invalid input, boundary cases, and one genuinely
complex playbook.

## Chapter 11: Future Enhancements

Scope decisions made deliberately in Phase 1 and never revisited, since the
core language stayed the right size for this project:

- **Loops within playbooks** — not needed by any scenario in scope; adding
  them would require deciding how a loop interacts with gating (does a
  refused action inside a loop stop iteration, or just that one
  iteration?) — a real design question, not just more parser work.
- **Real integration with live security tools** — the interpreter
  currently logs decisions rather than calling real APIs; wiring actual
  actions to real systems is an infrastructure concern orthogonal to the
  language design this project is actually about.
- **A graphical interface** — the CLI and the HTML execution trace cover
  the practical need (run a playbook, see what happened) without the
  added complexity of a GUI framework.
- **Distributed execution** — out of scope; nothing about gating as a
  grammar construct requires or benefits from distribution.
- **A richer type system** — currently two flat types (`string`,
  `number`); a language with more action types might eventually want
  structured types (lists, nested objects) rather than a flat alert
  schema.
- **Boolean `and`/`or` and parenthesized conditions** — `comparison` is
  currently exactly one `expression comparator expression`; compound
  conditions (`alert.confidence >= 0.8 and alert.severity == "high"`)
  would be a natural, contained grammar extension if a future phase
  needed it.
- **String escape sequences** — not needed by any sample playbook, but a
  real gap if string literals ever need to contain a literal quote.

## References

1. Red Hat / Ansible Documentation — Playbooks and execution model.
2. Splunk SOAR Documentation — Playbook and approval workflow design.
3. Shuffle Automation — Visual workflow and approval node design.
4. Sigma Project Documentation — Detection rule DSL design.
5. Open Policy Agent — Rego Language Documentation.
6. Aho, Lam, Sethi, Ullman — *Compilers: Principles, Techniques, and
   Tools* (reference for lexical analysis, recursive-descent parsing, and
   symbol table design).
7. Python Software Foundation — `difflib`, `argparse`, `dataclasses`
   standard library documentation.

## Appendix A: Formal Grammar (EBNF)

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

## Appendix B: Sample Playbook Source

```
on credential_compromise:
    if alert.severity == "high":
        if alert.confidence >= 0.9:
            disable_user(alert.user) require alert.confidence >= 0.95
        else:
            disable_user(alert.user) require approval
        notify_soc(alert.id)
        wait 2m
    else:
        if alert.confidence >= 0.5:
            notify_soc(alert.id) require alert.confidence >= 0.6
        else:
            notify_soc(alert.id)
        wait 10m
    wait 1m
```
