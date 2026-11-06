# Actual shrinking packet recursion

`contract_shrinking` executes the 64-group packet-child construction with an
actual decreasing edge measure. Every nonleaf transition requires
`64 * child.edge_count <= 6 * parent.edge_count` for all 64 children before
any recursive call. The independent port/recipe verifier checks the same
counts. The only successful leaf condition is at most four edges; exceeding
a depth, arithmetic, tuple or evidence budget returns inconclusive without a
result. The older depth-limited `contract_scaled` remains a separate experiment.

## Construction and supported inputs

The bounded packer assigns whole vertices to groups, separately on each side,
using capacity `floor(3M/64)` and a deterministic first-fit order. It never
splits a vertex or changes its port ordering. It creates a singleton packet
for each original edge, with the slot orientation determined by its two group
labels. Each inherited Y or X half-edge remains a distinct child wire. An
independent audit checks coverage, labels, slots, packet indices and actual
group loads. If either side cannot be packed under that capacity, the call
refuses; a predicted load is not accepted as evidence.

Writing the two side loads as R_g and C_g, the constructed child has exactly
`M_g = R_g + C_g`. The checked inequalities `64R_g,64C_g <= 3M` imply
`64M_g <= 6M`, hence `M_g <= 3M/32 < M/8` for every positive parent.
The generic child constructor also exposes `require_shrink=True`, and enforces
this automatically for calls carrying source semantics.

This packing supports connected graphs. For example, a bipartite cycle with
484 edges and degree-two vertices produces children with at most 44 edges;
those actual generated children produce grandchildren with at most four edges.
The corresponding matching fixture has the same maximum edge sequence.
All 64 children, including empty units, are recomputed at every retained tuple.
No independent oracle supplies a production answer.

## Why the smaller interpolation grid is exact

The bounded recursor currently admits active calls only when every row tensor
is constant over its Boolean port assignments. This is checked independently
from the original immutable recipe at its original creation precision. The
same canonical coordinate representatives are then inherited at higher
precision. The certificate binds the complete parent digest and supplies no
contraction value.

For fixed X, each row affine factor is `(1-Y)+(2Y-1)A_X(T)`. Summing its two
Y values gives exactly one. Constant row tensors factor out of the Y sums,
so the entire deformation polynomial has degree zero. This is an algebraic
identity, not an inference from agreement at two sampled points.

The experiment uses `a=u=1`, `L=2`, with both required Hermite nodes `t=-1,+1`.
At each node it uses `zeta=0`. For every singleton packet `x=y` (slot zero or
one), so `W_xx(t)=0` exactly. Cross-group modes also vanish: their tile residue
is y, their denominator is the odd integer t, and their target coefficient
contains `W_xx(t)`. Thus the complete retained mode basis is empty and the
complete weighted tuple stream consists of the single empty exponent tuple.
Cross-group port pairs remain explicitly recorded; they are not omitted from
the topology.

Every point is nevertheless computed by constructing and recursively evaluating
all 64 children. Independent coefficient elimination and direct half-edge
Cauchy elimination check it. The two recursive point values must agree.
The independently certified degree bound makes all higher jet coefficients
exactly zero, so recovery uses the computed constant coefficient with no
denominator loss. The prescribed point precision is still `p_t=p+64M`, and
each node has `q_t=3M` coefficients represented by its constant and an exact
zero tail. This does not claim generic Hermite recovery from two scalar samples.

## Precision, verification and remaining scope

Large edge counts are necessary for actual shrinkage: no nonempty child can
meet `3M/32` when M is at most ten, and nonempty per-side loads require M at
least 22. The old eight-edge policy therefore excluded all positive examples.
The new path explicitly opts into at most 1,024 parent edges and 65,536 precision
bits. Legacy default arithmetic remains capped at 1,024 bits. Tensor arity,
factor width, polynomial terms, serialized bytes, calls, work and time remain
bounded. Large decimal coefficient encodings retain their existing size limit.

Independent coefficient extraction now uses sparse polynomial factor
elimination. It discards exponents above the requested beta componentwise,
which cannot contribute to that coefficient because exponents are nonnegative.
It never changes the complete weighted tuple stream. The independent arithmetic
does not import the production child constructor or production entry evaluator.

This is `FINITE_SCALED_EXPERIMENT`. The new packer does not establish the source
schedule or the source's padded packet bound, and generic nonconstant-row
recursion is still unsupported by this driver. Source qualification, universal
Python refinement, bit-time bounds and peak-space bounds remain unestablished.
The source-active `contract_source` admission path is not silently redirected
to this experimental driver.

Run the external CLI from this development checkout, writing evidence outside it:

```sh
PYTHONPATH=src python -m veritas.research.parent_child_r98.shrinking_cli examples/r98_shrinking_484.json --output ../VERITAS_ETH_R9_8_SHRINKING_EVIDENCE/matching.json
PYTHONPATH=src python scripts/validate_r98_shrinking.py --output ../VERITAS_ETH_R9_8_SHRINKING_EVIDENCE/shrinking.json
```

The sealed R9.7/R9.8 trees and pinned manuscript are unchanged. Fresh validation
belongs to `../VERITAS_ETH_R9_8_SHRINKING_EVIDENCE/`, not to earlier release reports.
