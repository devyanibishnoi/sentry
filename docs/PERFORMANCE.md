# Sentry, Performance Note

Measured on the most complex sample playbook (`credential_compromise.sentry`,
nested `if`/`else`, three distinct gate shapes, three `wait` statements),
run through the full pipeline (lex, parse, semantic analysis, interpret)
1000 times via `time.perf_counter()`:

- **Total for 1000 full pipeline runs:** ~390 ms
- **Average per run:** ~390 microseconds
- **Peak memory for one full run** (measured via `tracemalloc`): ~19 KB

These figures are machine-dependent (re-running the same benchmark on this
same machine across different sessions produced total times ranging from
roughly 120 ms to 390 ms for 1000 runs, depending on background system
load), so treat them as an order-of-magnitude indication, not a precise
claim.

None of this is surprising, and that's the actual point worth noting: every
stage is a single linear pass over its input (the lexer scans the source
once, the parser consumes the token stream once, semantic analysis and the
interpreter each walk the AST once), so cost is expected to scale linearly
with playbook size, not combinatorially. This hasn't been measured on a
larger playbook, only reasoned about from the single-pass structure of each
stage. For a language whose actual job is deciding whether to gate a
security action, this matters less as a speed claim and more as evidence
that the gating mechanism itself introduces no meaningful latency: a
confidence check or an approval gate costs the same single dictionary
lookup and comparison as any other part of evaluating the playbook.

No formal profiling tooling was used beyond the standard library
(`time`, `tracemalloc`), appropriate for a project at this scale, where
the interesting engineering question is correctness of the gating logic,
not throughput.
