# R9.9 finite streaming corrections

Implemented in a separate development worktree; the sealed preflight baseline is preserved.
Implementation source SHA-256: `8c573334553c18e65be712e85e1176e7dc1ffee32a0ba14dbf1693db8410002e`.

## Delivered behavior

Lazy geometric mode production can apply independently checked constant-row cancellation
before expansion. Surviving higher orders and higher beta exponents are preserved.
The bounded reduced inventory and support are still materialized, with explicit refusal on overflow.

A bounded exact cache binds full graph and tensor semantics, original creation precision,
evaluation precision, field, depth and remaining schedule. Ancestry provenance alone is
excluded from its key and is still checked on every replay event.

Scalar root recipes can be transported to a sufficiently large verified extension ring.
727 points require degree ten (1,024 residue classes). Non-scalar entries and generated
packet recipes require a separate embedding and are refused by this adapter.

Full tapered recovery consumes one ordered node grid at a time. Independent recursive
replay reconstructs all children, checks shrinking, recomputes leaves, verifies cache
reuse, and uses separate ring arithmetic and divided differences. No production oracle
substitutes an answer. All successful leaves have at most four edges.

## Fresh validation

- Full pytest: 1928 passed, 2 optional skips, no failures/errors.
- C++ Release build and self-test passed.
- 13 inherited/component validation commands passed, including the
  41-module Lean and axiom gate and the finite 12/14/16-edge matrix.
- 30 clean-wheel/Docker commands passed, including new streaming
  checks. Installed wheel and Docker source identities were checked explicitly.
  Stale same-version wheel results were excluded and rerun in a fresh environment.
  Full container pytest and hosted CI were not run.
- External 22-edge nonconstant matching: all 134 complete-grid points evaluated;
  8,577 requests, 135 actual computations, 8,442 cache hits, no evictions.
  Peak cache payload 142,501 bytes; evidence payload 8,293,909 bytes.
  Exact result `31^22 = 645590698195138073036733040138561`; independent streamed replay passed.
  All 134 production point values also matched a separate Cauchy closed-form calculation.
  The validation observer asserted equality and never supplied production answers.
- The 242-edge probe obtained the required degree-ten field but refused before expensive
  plan arithmetic under its explicit work cap. The full run was not launched.

The cache payload excludes Python object overhead. Host resource checks are cooperative;
no hard host memory limit was enforced; these measurements are not peak-space or bit-time proofs. Docker
portable checks used no network, two CPUs and a 1 GiB limit.

## Remaining obligations

The combined connected, multi-slot, nonconstant, nonzero exponent-two,
two-active-level full-tapered acceptance case remains unestablished. General large
mode inventories, support counts and interpolation work can still exhaust budgets.
Source-compliant padded packing, source-active nonleaf execution, arbitrary recursive
jet refinement, universal Python correspondence, arbitrary-density SAT reduction,
and bit-time/peak-space bounds remain unfinished. The inherited Lean gate does not
prove these new Python routines. Source qualification and theorem mode remain off.

See [usage and mathematical scope](docs/R99_STREAMING_RESOURCES.md).
Raw evidence is outside this checkout in `../VERITAS_ETH_R9_9_STREAMING_RESOURCES_EVIDENCE`.
`validation_summary.json` and `REVIEW_SHA256.json` bind the final checks; interrupted
preliminary directories are not release evidence.
