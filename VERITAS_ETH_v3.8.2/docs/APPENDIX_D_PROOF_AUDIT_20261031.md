# Appendix D: proof obligations and conditional deductions

Source: OpenAI/math, commit `4eaee87548250b2682affda7d05d947c05554bae`, `preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026/build/quantitative-contraction.tex`. This note is an analysis of that source and the v3.8.2 implementation. It is not a complete independent proof or a verification of the Python implementation. Constants hidden in O and sufficiently-large thresholds are not extracted here.

## 1. Schedule and packing

Let λ=ceil(log₂ s), Δ=ceil(s^(9/10)), ε=1/131072, r=64, H=ceil(s/floor(sqrt λ)). At depth d the source sets u_d=floor(ελ/2^d), a_d=2 sum_{j=0}^d u_j, L_d=2^a_d, D_d=r^(2a_d). A node is active only above the leaf cutoff H.

Conditional on the child invariant M_{d+1}≤M_d/8 and root size M_0≤Cs, any active node satisfies H<M_d≤Cs/8^d. Thus 8^d<Cs/H≤C sqrt λ, so d≤(log₂ λ)/6+O_C(1). A deliberately loose explicit sufficient threshold, λ≥2^600 C^10, is derived in [APPENDIX_D_EXPLICIT_SCHEDULE_THRESHOLD.md](APPENDIX_D_EXPLICIT_SCHEDULE_THRESHOLD.md); under these invariants it implies the three numeric packing conditions and u_d≥λ^(4/5) at every active depth. The fixed finite range below that threshold requires the source's separate direct-summation treatment.

These inequalities do not themselves construct the labeling. The separate D.3 conditional-expectation packing lemma must establish a polynomial-time, polynomial-space labeling with its stated port and padding bounds for every eligible graph. The current bounded Python constructor and certificate checker do not establish this universal claim. The mathematical proof in the pinned source is a candidate proof; it has not been independently verified here.

The implicit labeler has now been changed to maintain one exact conditional-score contribution per unordered edge pair and update only pairs affected by a newly fixed endpoint label. Its operation estimate is `O(a r M^2)` with `O(M^2)` pair/update storage, and it checks the final state against the direct score calculation. This removes a repeated full pair scan per vertex from the constructor. It is a deterministic finite implementation improvement; the bit-operation estimate, source-to-code correspondence, and downstream theorem obligations are not validated by this change.

Correction to prior advice: if packing fails at an arbitrary large node, directly enumerating that node may take 2^M operations and does not preserve the stated subexponential bound. A fallback is complexity-safe only when M is bounded by the prescribed leaf threshold (or by another separately proved admissible bound).

## 2. Identity, pruning, and child size

For S={-L,...,L-1}, C(T)=∏_{q∈S}(T-q), and x,y∈{0,...,L-1}, y-x is in S. Thus W_xy(T)=C(T)/(C'(0)(T-(y-x))) is a polynomial. For x=y, W_xx(0)=1, because C(T)/T evaluated at 0 is C'(0). For x≠y, the uncancelled factor T makes W_xy(0)=0. Hence W(0)=I and the source's multilinear wire deformation has F(0) equal to the original contraction.

In a ring modulo 2^p, if a mode coefficient is in 2^w R, its βth power is in 2^(wβ) R. Therefore a product indexed by β with sum wβ≥p is zero. Under the packet-orientation and unramified-ring hypotheses, [APPENDIX_D_POINT_MODE_VALUATION.md](APPENDIX_D_POINT_MODE_VALUATION.md) derives the geometric point expansion, its coefficient valuation, and the exact remainder cutoff. This does not prove that every recursive implementation state satisfies those hypotheses.

Conditional on the D.3 packing lemma, each symbol group has at most 3M/r real ports on each side. If the prescribed child has one edge for each such original half-port and no extra mode edges, it has at most 6M/r=3M/32<M/8 edges. Old degrees remain unchanged, while a new packet vertex has at most 2L ports, hence degree at most Δ. This is a structural deduction from the exact construction, not a claim that the finite v3.8.2 child representation satisfies the general theorem. The coefficient extraction, mode factorization, field-extension interpolation and implicit entry evaluation still require a full independent proof and implementation correspondence.

## 3. Conditional runtime calculation

Suppose all active nodes satisfy the invariants above; their complete branching factor, including interpolation nodes and groups, is at most poly(s) exp(K M_d/sqrt(u_d)); each local operation, packet construction, interpolation, and entry evaluation has the uniform costs claimed by the source; and all direct leaves have M≤H. Then

    M_d/sqrt(u_d) = O_C((s/sqrt λ)(sqrt(2)/8)^d).

The geometric sum over active depths is O_C(s/sqrt λ). The number of depths is O_C(log λ), so the accumulated poly(s) factors contribute exp(O(log s log log s)), absorbed by exp(O(s/sqrt(log s))). Direct leaves cost at most 2^H times the required entry-evaluation overhead, with H=O(s/sqrt(log s)). A uniform exp(O(s^(9/10))) entry cost is also absorbed asymptotically. Under these assumptions the total is poly(s+description length) exp(O(s/sqrt(log s))) bit operations.

The abstract weighted-tuple estimate and the multiplicity deduction from the packet-count and orientation hypotheses are derived in [APPENDIX_D_WEIGHTED_TUPLE_BOUND.md](APPENDIX_D_WEIGHTED_TUPLE_BOUND.md). A precision-path deduction under the stated root, shrinkage, schedule and increment invariants is given in [APPENDIX_D_PRECISION_PATH.md](APPENDIX_D_PRECISION_PATH.md); the conditional Hermite guard argument is in [APPENDIX_D_TAPERED_PRECISION_LEMMA.md](APPENDIX_D_TAPERED_PRECISION_LEMMA.md). Uniform validity of those hypotheses, proof that generating the tuples and all implicit entry evaluations obey the charged costs, and bounds on exact arithmetic and reconstruction remain necessary. The displayed geometric sum alone does not prove these inputs. Dependence on the input-description length must remain a fixed polynomial, rather than a polynomial factor multiplied once per recursion level with an exponent growing with depth.

The exact root-precision requirement for unweighted CNF counts and the
conditional recursion calculation with the sharper `3/32` child factor are
spelled out in [APPENDIX_D_COUNT_AND_RECURRENCE.md](APPENDIX_D_COUNT_AND_RECURRENCE.md).
An explicit bound on the sum of work over the entire tree, under separately
stated branching and per-call bit-cost assumptions, is given in
[APPENDIX_D_RECURSION_TREE_LEMMA.md](APPENDIX_D_RECURSION_TREE_LEMMA.md).

## 4. Conditional space calculation

Assume each active node's graph, immutable tensor descriptions, ring precision and all interpolation data occupy poly(s+description length) bits; children and exponent tuples are generated one at a time in polynomial space; tensor entries can be recomputed in polynomial space; and the recursion stack has O(log log s) levels. Depth-first evaluation holds one child, one product, one sum, the current interpolation data, and the descriptions along one path. The resulting space is polynomial in s+description length. This conclusion fails if all children, exponentially many modes, or exponentially large tables are materialized at once. It also requires a proof that descriptions and coefficient bit lengths remain polynomial and that entry procedures do not create unbounded nested computation state.

## Status

The elementary W(0) calculation, conditional point-mode valuation and identity, modular divisibility deduction, conditional mode multiplicity and weighted-tuple estimates, conditional precision-path and Hermite guard arguments, conditional child-size deduction, and conditional geometric runtime/space calculations above are supplied here. A separate [packing argument](APPENDIX_D_PACKING_ARGUMENT.md) derives the abstract collision, derandomization, padding, and port bounds. It does not remove the bounded constructor's size limits or establish source-to-code refinement. Uniform application of the packet and precision hypotheses and complete source-to-code refinement remain unproved here. No universal complexity claim is made for VERITAS-ETH v3.8.2. The existing finite experiment is not a formal proof of the manuscript.

The separate `veritas.research.appendix_d_schedule.schedule_preflight` now
checks the numerical schedule using exact integers, including the degree and
recursive edge-size limits. It permits a direct leaf only at or below H and
returns an inconclusive status when the active schedule or packing conditions
do not apply. `ACTIVE_NUMERIC_PRECONDITIONS_MET` certifies only those numerical
checks: the caller supplies the root-size constant and depth, and must verify
the actual ancestry and construct and check the packing separately. The
default 4096-bit input cap is far below the manuscript's active asymptotic
regime; changing the cap does not remove the computational cost of large
integer arithmetic or implement the recursion. Resource limits never yield a
count.
