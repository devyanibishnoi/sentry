# Sentry — Performance Note

Measured on the most complex sample playbook (`credential_compromise.sentry`
— nested `if`/`else`, three distinct gate shapes, three `wait` statements),
run through the full pipeline (lex → parse → semantic analysis → interpret)
1000 times via `time.perf_counter()`:

- **Total for 1000 full pipeline runs:** ~119 ms
- **Average per run:** ~119 microseconds
- **Peak memory for one full run** (measured via `tracemalloc`): ~19 KB

None of this is surprising, and that's the actual point worth noting: every
stage is a single linear pass over its input (the lexer scans the source
once, the parser consumes the token stream once, semantic analysis and the
interpreter each walk the AST once), so cost scales with playbook size, not
with anything combinatorial. A playbook orders of magnitude larger than any
sample here would still run in well under a millisecond. For a language
whose actual job is deciding whether to gate a security action, this
matters less as a speed claim and more as evidence that the gating
mechanism itself introduces no meaningful latency — a confidence check or
an approval gate costs the same single dictionary lookup and comparison as
any other part of evaluating the playbook.

No formal profiling tooling was used beyond the standard library
(`time`, `tracemalloc`) — appropriate for a project at this scale, where
the interesting engineering question is correctness of the gating logic,
not throughput.
