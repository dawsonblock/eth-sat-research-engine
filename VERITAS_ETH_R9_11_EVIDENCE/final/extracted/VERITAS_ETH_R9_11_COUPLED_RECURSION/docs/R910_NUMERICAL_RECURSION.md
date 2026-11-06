# R9.10 finite two-level numerical recursion

This development branch extends R9.9 commit `8a10b85`. Its immediate target is
an executed and independently replayed numerical dependency tree. The R9.11–R10.0
mathematical and complexity obligations remain open. `source_qualified` and
`theorem_mode_enabled` remain false.

## Exact transformation

The pinned manuscript is `paper/quantitative-contraction.tex`, SHA-256
`671642d7b53154d92344e8c4be0240f18929632ebcfdf73b07c3e9939b873860`.
The new module uses `eq:tensor-mode-expansion`, `eq:tensor-recursion-identity`,
and `eq:tensor-hermite-origin` with the explicit **finite** schedule a=u=1.
This is not the manuscript-active schedule: its positive a_d values are even.
The truncated coefficient ring is restricted here to ell=1, with exact
2-adic extension coordinates and creation-time canonical lifts.

For a constant row tensor, summing its Y bit in
`(1-Y)+(2Y-1)A` gives one. Thus only ports on nonconstant row tensors contribute
deformation degree. If their number is b, d=3b bounds the degree when a=1.
The producer checks all row entries at their inherited creation semantics;
the consumer checks them with a separate entry evaluator. The Taylor tail
above d is exactly zero. It is not an estimated small numerical tail.

The original Hermite nodes remain -1 and +1, each with q=3M, alpha=4, and
precision p+64M. Only d+1 residue-distinct samples per node are required to
recover the polynomial in z. For j<min(q,d+1), the original weight at -1 is

    lambda[-1,j] = 2^(-q-2j) sum[k=0..q-1-j] binom(q+k-1,k)/2^k.
    lambda[+1,j] = (-1)^j lambda[-1,j].

`recovery.py` computes these by integer cumulative sums. Its consumer computes
the reciprocal-series rational formula directly, and checks the functional
on every monomial up to the certified degree. Each weight's denominator loss
is checked against the unchanged node precision. The omitted weights multiply
certified zeros. Newton residual interpolation in the producer and divided
differences with independent extension arithmetic in the consumer recover
the same Taylor coefficients. The old full-grid executor is preserved.

## Fixture and dependency evidence

`examples/r910_matching235.json` has one edge with row [2,3], column [5,7],
and 234 edges with both tensors [1,1]. Its exact independent sum is
`31 * 2^234`, below 2^256. The reference reads and checks the actual tensor
tables; it does not assume these factors from the filename.

The supplied layout crosses endpoint groups, with 21 groups of 22 half-edges
and eight groups of one half-edge. Each 22-edge active child is packable into
two-edge leaves. Every generated child is checked against `64*M_child<=6*M`
and strict decrease. The root and some depth-one calls have nonzero deformation
degree. A topology-only run cannot satisfy the numerical gate.

Under this 64-group per-side load condition, a nonempty active node needs
M>=22. Its parent must have M>=ceil(64*22/6)=235. This lower bound explains
the fixture size; it is not a universal minimality claim for other algorithms.

Events record the full local/folded mode coefficients, independently checked
affine support, each retained exponent tuple, all 64 child identities and wire
counts, child precisions and values, the product contribution, point sum and
Hermite result. Coefficients are incorporated into packet entries; there is
no omitted external scalar multiplier. Full child descriptions are reconstructed
from the root, layout, mode and tuple records by the independent constructor.
Ancestry and computational reuse have separate bindings. A hash alone is
never treated as a mathematical verification.

## Reproduction

```sh
PYTHONPATH=src python3 scripts/validate_r910.py --output-dir ../fresh-r910
PYTHONPATH=src python3 -m veritas.research.parent_child_r910.cli \
  examples/r910_matching235.json \
  --layout-file examples/r910_matching235_layout.json \
  --replay-dir ../fresh-r910/run --output-dir ../fresh-r910-replay
```

Use a new external output directory for each command. For the inherited
242-edge fixture, use `examples/r99_nonconstant_matching242.json` and its
corresponding layout, with `--preflight-only` first. Its generic degree bound
is 726 but its actual certified degree is three. Inspection
of the tables finds one edge [1,3]/[2,5] and 241 constant [1,1]/[1,1] edges,
so its independent exact answer is `17 * 2^241`. Its filename does not mean
that every edge is nonconstant. CLI preflight alone cannot complete this benchmark.

## Accounting and qualification

Preflight records root generic and certified point counts, the old rational
plan admission allowance, and the new cumulative-binomial step count. It also
projects descendant topology independently. Descendant degrees require numerical
recipes and are checked at runtime; no total recursive work estimate is
presented as a proved bound. Each active call records predicted and actual
local point counts, including computations avoided by exact bounded caching.

Exclusive stage work charges sum to the reported work counter. They include
charged setup/preflight work and are policy units, not measured bit operations.
The report explicitly sets `bit_operations=null` and `NOT_INSTRUMENTED`.
Process peak RSS includes imports, Python overhead and any prior process work;
the CLI validation uses a fresh process for its run. This is a measurement,
not a hard memory cap or a polynomial-space proof. Cache payload limits exclude
Python object overhead. Event bytes are capped and streamed to disk; per-call
summary metadata remains in memory within the finite call/evidence policies.

The independent checker rederives all numerical contributions, support coverage,
call/depth/point/tuple/transition counts and cache behavior. Producer work-stage
charges receive an internal sum check; they are not independently reconstructed
bit costs. Independent arithmetic has its own separately reported work counter.

## Remaining obligations

- Arbitrary ell and manuscript-active schedules; full node-specific tapering.
- General connected, multi-slot, exponent-two two-level acceptance fixture.
- General all-nonconstant large-network calculations and resumable checkpoints.
- Complete bit-operation instrumentation and independently reconciled total cost.
- General CNF/density reduction, solver comparisons and performance ablations.
- General mode bounds, precision/termination/space proofs and executable refinement.

The existing Lean gate proves its existing mathematical models; it does not
prove the new Python module. Passing finite tests cannot qualify any of these
remaining obligations. The complete R9.10 resource contract and R10.0 release
qualification therefore remain **partial** even when the numerical gates pass.
