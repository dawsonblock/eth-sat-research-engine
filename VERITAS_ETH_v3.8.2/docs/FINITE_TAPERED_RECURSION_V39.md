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

The tuple stream applies two exact affine-degree restrictions before forming
children: each mode exponent is at most the number of target rows containing
that mode, and the sum of exponents targeted at one packet/group is at most
the number of target rows containing any of those modes. Each target row
contributes at most one mode factor. Tuples excluded by either restriction
therefore have zero coefficient. The certificate retains the nominal weighted
tuple count as well as the smaller structural count; the tuple budget applies
to the latter. The argument and its limits are given in
[APPENDIX_D_STRUCTURAL_TUPLE_PRUNING.md](APPENDIX_D_STRUCTURAL_TUPLE_PRUNING.md).

The experiments use caller-selected small parameters, normally `r=2`, `a=1`,
and `u=1`; a caller may specify a separate `(a,u,r)` tuple per level. They do
not use the theorem's depth-dependent
`r=64` schedule or establish shrinking children. Limits include at most six
parent wires, extension degree at most eight, precision at most 1024 bits,
bounded interpolation points and mode tuples, and at most two requested
transformation levels. Direct leaf enumeration and independent oracles are
explicitly bounded. `run_tapered_finite` reports `INCONCLUSIVE_RESOURCE_LIMIT`
without a result when its supported work or precision budget is exhausted.

Work counters distinguish child work from direct oracle work, but omit some
packing, mode generation, interpolation, bit-operation and retained-memory
costs. They are not a complete ledger or a runtime/space proof. The theorem's
uniform packing, precision estimates, general child invariants, and
source-to-code correspondence remain open for this implementation.
