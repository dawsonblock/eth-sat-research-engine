# Exact independent-component optimization

This candidate extends only the explicit optimized counting route. The original
`count`, source sparse-query construction, finite recursive schedule, paper,
independent replay checker, and all earlier sealed checkpoints remain unchanged.
It does not establish source qualification, executable refinement, or an
asymptotic improvement for general instances.

## Algorithm and scope

After exact normalization, constraints are connected only when their variable
supports overlap. Every clause or polynomial equation belongs wholly to one
component. Components are renumbered locally and evaluated with the existing
exact counter. Their counts multiply; each declared but unused variable adds a
factor of two. Transitive overlaps are included. Duplicate literals, tautologies,
empty clauses, zero equations, constant-one equations, repeated monomials, and
unused variables retain their original semantics.

An invocation-local cache reuses an already completed exact count only for an
identical locally renumbered component. It has no persistent state, does not
cache resource failures, and never trusts a digest instead of equality. All
component work shares one Budget. A component refusal returns no product/count;
limits apply to the combined calculation rather than restarting per component.
A zero factor can finish the count immediately.

Certificate-producing CNF calls retain their historical dispatcher and trace;
no existing certificate schema was widened. Equation event-sink calls likewise
retain their historical construction. The original reference APIs are unchanged.
`count-optimized` is the CLI entry; ordinary `count` remains the reference.

Files: `src/veritas/research/manuscript/optimizations.py` and
`tests/test_manuscript_components.py`. The package binding is resealed separately.
The historical optimization policy string is retained for certificate
compatibility; component-result receipts explicitly identify
`EXACT_INDEPENDENT_COMPONENT_PRODUCT` and list component sizes, unused variables,
and reused-component count.

## Reproducible evidence

Sibling directory `VERITAS_ETH_R9_12_COMPONENT_OPTIMIZATION_EVIDENCE` contains
`benchmark_components.py`, three-repetition baseline/candidate JSON, cProfile
summaries, `stress_components.py`, source/wheel checks and validation logs.
Benchmark baseline is the untouched ZERO_BRANCH source. The reported work-unit
counts are cooperative instrumentation, not complete bit-operation accounting.
Benchmarks ran on the same Mac with other validation work active; microsecond
values and ratios are fixture-specific, not general performance guarantees.

- 18-variable nine-pair CNF: median 0.710381 seconds before and 0.000075 seconds
  after; measured work units 2,201,859 versus 105. Both return 3^9 exactly.
- Equivalent sparse equations: 0.706611 versus 0.000062 seconds; work units
  3,171,703 versus 106. Both return 3^9 exactly.
- 40-variable twenty-pair CNF: baseline exhausts its 10-million-work allowance;
  candidate returns 3^20 in 0.000152 seconds. This is a completion improvement,
  not a speedup ratio for equal completed work.
- Connected 14-variable control: 0.055113 versus 0.055668 seconds. No speedup.
- 20,000-variable, 10,000-identical-pair stress input: exact 3^10000, 9,999 cache
  hits, 0.354 seconds including tracemalloc overhead; 3,894,596 traced peak bytes
  and 31,145,984 process peak RSS bytes. These are observations, not memory bounds.

The new tests contain 250 seeded CNF and 250 seeded polynomial-system comparisons
against separately written exhaustive original-input Boolean oracles, plus
constant/zero/cancellation, transitive connectivity, repeated-component reuse,
shared work/time/item/integer limits, and late-failure no-partial-count tests.

## Remaining limits

Connected difficult inputs and finite recursive tensor arithmetic retain their
existing exponential behavior and practical caps. No native arithmetic rewrite
is included. Independent profiling determines follow-on candidates; a benchmark
of disconnected instances is not evidence that recursive arithmetic got faster.
Docker validation is not run because the previous permission denial remains in
force. Optional pybind11 coverage, complete release gates, and any unrun checks
must be disclosed separately. Passing tests do not prove the paper's theorem.

## Lean test invocation

When using elan, resolve the pinned executable inside this checkout before
running tests: `LEAN_BIN="$(elan which lean)" PYTHONPATH=src python3 -m pytest`.
The shim alone may have no default toolchain when a fault-injection test starts
Lean in a temporary directory. Passing the resolved executable avoids changing
global Lean settings or downloading a toolchain. Use only an already installed
pinned version; the observed gate used Lean 4.35.0.
