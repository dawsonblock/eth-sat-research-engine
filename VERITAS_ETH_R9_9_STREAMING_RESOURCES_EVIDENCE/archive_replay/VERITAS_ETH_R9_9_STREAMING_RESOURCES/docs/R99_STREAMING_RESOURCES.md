# R9.9 finite streamed packet recursion

This development checkout preserves the sealed preflight release. It adds a
separate finite full-tapered executor; it does not complete the manuscript's
source-qualified algorithm or complexity proof.

## Corrections

- `basis.iter_packet_components` generates geometric modes lazily. An optional
  creation-bound constant-row certificate is independently verified before
  expansion. Cross-port topology remains recorded. All surviving mode orders
  and nonnegative supported exponents remain legal, including exponent two.
  The bounded child API still materializes the reduced inventory and support;
  it refuses overflow rather than truncating it.
- `resources.ExactCache` stores successful completed computations only, with an
  LRU payload cap and hit/miss/eviction measurements. Keys retain graph labels,
  ordered ports, complete tensor recipe bytes, original creation precision,
  evaluation precision, field, depth, root context and remaining schedule.
  Only the provenance ancestry digest is omitted: it is not an entry operand.
  Each reuse event still binds the actual ancestry. No isomorphism or value-
  based guessing is used. Cache overhead is not a hard process memory limit.
- `prepare_scalar_field` chooses enough residue classes (727 needs degree ten)
  and independently trial-divides the constructed polynomial. Scalar dense,
  equality and clause root recipes retain their creation precision. Non-scalar
  extension entries and generated packet recipes are refused; changing a
  polynomial is not a general extension-ring embedding.
- `StreamRecovery` consumes each complete prescribed grid in order, retains
  one node's Newton polynomial and basis, and accumulates the exact rational
  tapered functional with coefficientwise precision checks. It keeps the full
  degree bound; it does not substitute a constant-degree shortcut. Rational
  plan weights and reduced mode/support data remain resident and bounded.
- `contract_streaming` writes pre-order events depth-first. The independent
  single-pass consumer reconstructs children without the production constructor,
  computes leaves with separate entry arithmetic, checks all 64 children,
  checks shrinking, and reuses only previously verified values. Recovery replay
  uses separate ring arithmetic and a divided-difference recurrence. It checks
  ordering, completeness, precision, final digest and accounting.

## Usage

From this development checkout, with a new external output directory:

```sh
PYTHONPATH=src python3 -m veritas.research.parent_child_r99.stream_cli \
  examples/r98_general_matching22.json \
  --output-dir ../VERITAS_ETH_R9_9_STREAMING_RESOURCES_EVIDENCE/example \
  --verify
```

`--levels` supplies the finite a=u=1 schedule. `--max-work`, `--max-calls`,
`--max-seconds`, `--max-points`, and `--cache-bytes` are explicit limits.
No source-active call is redirected here. Failures have no result; incomplete
external event files are not valid certificates. Existing complete-weighted
and degree-certified entry points retain their previous behavior. The typed
`execute` API routes a tapered, certified-support request with an evidence sink
through this new engine.

## Workload accounting and remaining scope

The old recomputing call lower bounds do not apply to memoized executions.
New reports distinguish requests from actual cache-miss computations. No hit
rate is assumed in advance; every request consumes work and all arithmetic,
call and evidence limits still fail closed. Streaming does not remove the
full-grid point count, tuple explosion or expensive general Hermite weights.

Source-compliant padded packing, a source-qualified nonleaf executor,
universal Python refinement, recursive jets beyond the existing scalar-point
interface, and bit-time/peak-space proofs remain unfinished. The combined
connected, multi-slot, nonconstant, exponent-two, two-active-level full-tapered
acceptance case is not established by separate component tests.
