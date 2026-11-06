# R9.8 follow-up mathematical corrections

The first review corrected the packet-index bound in commit `278ec33`. This
follow-up reviews that change and the R9.8 implementation beneath it. The
manuscript stays pinned at `4eaee87548250b2682affda7d05d947c05554bae`; none of
its formulas or source bytes are changed. New evidence is written to
`../VERITAS_ETH_R9_8_MATH_CORRECTIONS_EVIDENCE/`.

## Ring identity must survive recursion

The point-mode adapter previously passed only the extension degree. Its
underlying generator chose the first irreducible polynomial of that degree,
even when the parent's tensor references specified another valid polynomial.
The independent checker then rejected the valid call as a ring mismatch.

For example, the binary encodings 19 and 25 represent `U^4+U+1` and
`U^4+U^3+1`. Both are irreducible modulo two, but the coordinate reductions
of `U^4` are respectively `-U-1` and `-U^3-1`. Equal coordinate vectors do
not specify the same arithmetic merely because the degrees agree. One cannot
relabel tensor coordinates between these presentations without an explicit
map that also respects their creation-time representatives.

`make_point_modes` now accepts an explicit defining polynomial, validates its
degree and irreducibility, and uses it in both construction and replay.
R9.8 passes the parent's polynomial. The legacy default remains available
for callers that have not already specified a ring. Regression tests use
nonscalar interpolation points in multiple alternative irreducible rings,
nonzero cross modes, full weighted tuple sums and complete Hermite recovery.
The replay checker preserves resource-limit refusals from source validation;
missing or null polynomial metadata still fails validation.

## Child ancestry and canonical integer metadata

`ChildGraph.as_parent` previously accepted a different parent object and
borrowed its root context without checking the recorded parent digest. It
now requires that digest to match, depth to increase by one, the defining
polynomial to remain unchanged, and target precision to increase strictly.
These checks bind the recursive call; the separate child verifier still
establishes the actual port and coefficient correspondence.

Python treats `False == 0` and `True == 1`. The old metadata comparisons
therefore admitted Boolean half-edge indices, vertex identities and point
metadata in place of the specified integers. Child records now reject those
values, duplicate half-edge identities and noncanonical order at construction.
The packet audit and mode verifier likewise check arithmetic metadata types.
These are fixes to the executable representation, not new algebraic axioms.

## Correct packet bound and conditional child shrink

Let a packet pattern have a coordinates, of which k have equal symbols.
It contains `2^(a-k)` orientations, with `2^k` copies per directed class.
If each class has padded height H, the exact range is

\[
 0\le j<H/2^k.
\]

The total number of packets is

\[
 H\left(r/2+\binom r2\right)^a=Hr^{2a}/2^a.
\]

The earlier fix agrees with `D3FullPacketModel.encodeClass_bounds` and
`D3FinitePacketDomain.addresses`. The six-edge counterexample remains a
regression. That check compares independently evaluated generated children
with the half-edge point oracle at zeta=0; it does not claim an end-to-end
six-edge recursive run or source eligibility.

For group g, actual child wires satisfy `M_g=R_g+C_g`. The paper's separate
per-side hypotheses `R_g,C_g <= 3M/64` are **sufficient** to derive
`M_g <= 3M/32 < M/8`. They are not necessary for an arbitrary individual
child to satisfy that numerical shrink bound. Source packing still requires
the stated per-side conditions. Finite fixtures do not inherit them by default.

## Complete tuples over the specified basis

The mode generator removes zero modes before enumerating exponents. If all
target coefficients of a mode vanish at the working precision, the row
polynomial is independent of it and every positive-exponent coefficient is
zero. If its source form is identically zero, every positive power of that
form is zero. Empty packets and empty target groups are covered by the same
argument. The zero exponent always contributes a factor one.

Projecting away those coordinates therefore preserves the complete sum.
R9.8 enumerates every tuple of weight below `p_t` on the retained basis,
including structural zeros; no tuple is removed to satisfy a work budget.
It does not enumerate every formal tuple of the paper's larger basis.
Certificates and reports now bind this distinction explicitly:

- `mode_basis_scope = ZERO_REDUCED_GEOMETRIC_POINT_MODES`
- `tuple_domain = ALL_WEIGHTED_TUPLES_OVER_RETAINED_MODES`
- `paper_formal_mode_domain_enumerated = false`

A retained mode of weight w has target coefficients divisible by `2^w`.
Consequently a beta coefficient is divisible by `2^(sum w beta)`, which
justifies only the stated high-weight cutoff. Exact zero-mode reduction and
high-weight divisibility are distinct reasons for omission.

Leaf-only calls now return `PASS_FINITE_SCALED_LEAF`, with
`parent_child_recursion_performed = false`. Calls stopped at depth zero or
with no edges do not count as executed parent-to-child identities. In
particular, zero wires do not imply the unit value when isolated tensor
scalars remain.

## Local source checks do not certify descendants

The preflight report now explicitly says `CURRENT_NODE_NUMERICS_ONLY`, with
actual packing and descendant schedules unverified. It separately records
whether the node is above the leaf cutoff and whether u is positive.

The review's exact example survives: at `s=M=2^131080`, the root has `u_0=1`
and meets all three packing inequalities. A balanced abstract matching can
produce children of size `M/32`. Such a child exceeds `ceil(s/362)`, but
`u_1=0`. The existing path preflight correctly refuses the child; a regression
now checks that result. This is a numeric/abstract example, not a constructed
network at that scale, and not a contradiction of the paper's sufficiently
large-size theorem. Source qualification must cover every active call.

## Precision and the parent-to-child identity

For each packet P and group g, let `R_(P,g)` be the product of its row
affine factors, and define `R_P = product_g R_(P,g)`. Let `I_g` be the
product of the inherited tensors in group g, including isolated scalars.
The packet tensor is the coefficient of the beta exponents restricted to
the modes targeting `(P,g)`, multiplied by the beta powers of the modes
sourced there. Each mode has one target and one source; every X/Y half-edge
has one group owner. Distributivity then separates the sums over group bits
and gives the product of 64 child contractions for each beta. The geometric
decomposition and weighted divisibility give the full point identity modulo
`2^p_t`. Actual packing loads are a separate premise for shrinkage.

The creation-lift rule is a map of coordinate representatives, not a ring
homomorphism: reduce the entry recipe at its original creation precision,
then reuse those representatives at higher precision in the **same** ring
presentation. For example, `1-3 mod 4` is represented by 2, and inheriting
it modulo 512 still gives 2, rather than the recomputed value 510.

For tapered Hermite recovery, set

\[
 Q_t(z)=[F(t+\alpha z)/E_t(t+\alpha z)]_{<q_t}.
\]

The reciprocal series has integral coefficients. Its j-th quotient
coefficient is multiplied by `E_t(0)(-t/alpha)^j`, so the sufficient local
loss is

\[
 \max\{0,-v_2(E_t(0))+(a+1-i)(q_t-1)\}
 \le 6hD_t+4M(a+1).
\]

Thus the prescribed `p_t = p+8hD_t+8M(a+1)` is sufficient coefficientwise.
This is a sufficient bound, not a claim of minimal necessary precision.
No precision formula was changed. The independent rational audit from the
first review is rerun as corroboration; it is not promoted to a universal
executable proof.

The source executor remains unqualified, and bit-time and peak-space bounds
remain `COMPLEXITY_NOT_ESTABLISHED`. The separate finite boundary/elimination
engine remains the applicable exact route for practical 12–16-edge cases.
