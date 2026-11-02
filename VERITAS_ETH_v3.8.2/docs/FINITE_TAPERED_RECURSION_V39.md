# Finite tapered recursion with creation-time entries

This bounded research path uses immutable bipartite vertex descriptions.
An original table or packet-entry recipe is evaluated modulo its own creation
precision. Each coordinate is then lifted by its canonical representative
to the current precision. In particular, a packet entry is **not** recomputed
using higher-precision arithmetic: canonical lifting does not preserve sums or
products. A regression case distinguishes a creation-time residue of `2`
modulo `8` from the incorrect recomputation `26` modulo `32`.

`make_point_modes` evaluates the geometric modes at
`T=t+2^(a+1)*zeta`, cancelling known powers of two before inverting a unit.
The point evaluator uses a product of individually normalized factors, so it
does not construct the full Cauchy matrix of rational polynomials. A separate
bounded polynomial evaluator checks its values. It reconstructs every finite
Cauchy matrix entry and checks each mode's nominal `b+1` valuation.
`contract_point_child_expansion` builds group-local
children from existing descriptions and checks the full retained-tuple sum
against an independent half-edge contraction at the same point.

`contract_tapered_finite` evaluates the prescribed nonzero nodes at enough
residue-distinct extension-ring points, interpolates each truncated-polynomial
coordinate, and applies the finite tapered Hermite recovery. With
`max_recursive_levels=2`, its children can themselves use the same finite
recovery before direct leaf contraction. A one-wire signed example is
checked through precision `5 -> 69 -> 197`; a separate test carries nonzero
extension and truncated-polynomial coordinates across both levels. A two-wire
example exercises cross-group modes and recovers count `3` modulo `8`. An
additional two-level test changes the packet exponent from `a=1` to `a=2`
and reaches 309-bit working precision.

The eight-wire experiment in `scripts/validate_tapered_v4.py` observes about
2.13 million charged work units, so it pins `max_work=3_000_000` explicitly.
The `RecursionPolicy` default of 2 million is just below what the current
tree charges, and a run at the default fails closed with
`INCONCLUSIVE_RESOURCE_LIMIT` and no count. `--write` and `--replay` both
use the pinned cap; a transcript written under a smaller cap replays as
inconclusive and reports its `recorded_max_work`.

Zero-wire networks take a separate direct leaf path. This handles an empty
CNF on zero variables, empty clauses, and isolated declared variables. A
certificate binds the immutable zero-wire tensor descriptions, their lifted
entries, and the result; the checker replays each entry and independently
multiplies its extension-jet coordinates. For a network with no vertices,
the default return ring has extension degree one and jet length one. The
certificate verifies the supplied tensor network, not the correctness of an
arbitrary CNF-to-network reduction.

The tuple stream applies two exact affine-degree restrictions before forming
children: each mode exponent is at most the number of target rows containing
that mode, and the sum of exponents targeted at one packet/group is at most
the number of target rows containing any of those modes. Each target row
contributes at most one mode factor. Tuples excluded by either restriction
therefore have zero coefficient. The certificate retains the nominal weighted
tuple count as well as the smaller structural count; the tuple budget applies
to the latter. The argument and its limits are given in
[APPENDIX_D_STRUCTURAL_TUPLE_PRUNING.md](APPENDIX_D_STRUCTURAL_TUPLE_PRUNING.md).
For a verified completed scalar residue of a count-preserving `n`-variable
CNF contraction, `recover_boolean_count` enforces `precision >= n+1` and
checks the residue's canonical and Boolean-count ranges. The helper does not
verify which network produced the residue; these remain caller obligations.

Each point-child expansion now records the mode valuations, retained tuples,
each child contraction and its actual edge count and maximum degree, the
tuple products, and the independently evaluated half-edge result. The
point-certificate checker replays those fields against the input network and
mode certificate. The opt-in `require_one_eighth_shrink=True` rejects a
branch if a child is not strictly smaller than `M/8` or violates `6M/r`;
`run_tapered_finite` then reports `INCONCLUSIVE_CHILD_SIZE_INVARIANT` with no
count. Scaled examples can fail this check: checking an actual child is not a
proof that all theorem-schedule children satisfy the bound.
The tapered result also aggregates finite child counts, maximum actual edge
count and degree, size-check outcomes, and minimum valuation slack across
visited recursive calls. This summary is instance evidence, not a verified
whole-run arithmetic or memory ledger.

The experiments use caller-selected small parameters, normally `r=2`, `a=1`,
and `u=1`; a caller may specify a separate `(a,u,r)` tuple per level. They do
not use the theorem's depth-dependent
`r=64` schedule or establish shrinking children. Limits include at most six
parent wires, extension degree at most eight, precision at most 1024 bits,
bounded interpolation points and mode tuples, and at most two requested
transformation levels; the zero-wire leaf is also supported. Requests above
the finite wire cap return `INCONCLUSIVE_RESOURCE_LIMIT` through
`run_tapered_finite`. Direct leaf enumeration and independent oracles are
explicitly bounded. `run_tapered_finite` reports `INCONCLUSIVE_RESOURCE_LIMIT`
without a result when its supported work or precision budget is exhausted.
Its explicitly capped 512-bit target-precision option supports a two-wire
example through two recursive levels; that example does not satisfy the
one-eighth child-size invariant. Insufficient extension-field interpolation
points also return an inconclusive resource status rather than a partial count.

Work counters distinguish child work from direct oracle work, but omit some
packing, mode generation, interpolation, bit-operation and retained-memory
costs. They are not a complete ledger or a runtime/space proof. The theorem's
uniform packing, precision estimates, general child invariants, and
source-to-code correspondence remain open for this implementation.
