# R9.8 mathematical review and correction

Reviewed 2026-11-04. Baseline: sealed R9.8 commit `b40e45c`; manuscript commit
`4eaee87548250b2682affda7d05d947c05554bae`. The contraction source SHA-256 is
`671642d7b53154d92344e8c4be0240f18929632ebcfdf73b07c3e9939b873860`.

**Result:** one reproducible packet-index error in the R9.8 checker, corrected
in the separate `review/r9.8-math` worktree. The conditional coefficient
identity, creation-lift rule, and tapered Hermite error estimate survive this
review. Root-only source eligibility is insufficient. No source-qualified
execution or complexity result is established by these checks.

The sealed R9.7 and R9.8 trees are preserved. The correction lives at
`/Users/dawsonblock/MATH SPEED/VERITAS_ETH_R9_8_MATH_REVIEW`.
Commit: `278ec33947630b7a082ef1055b99de3108b904db`. This is a reviewed
development correction, not a newly sealed release archive.

## 1. Confirmed implementation error: packet index capacity

In `parent_child_r98/packing.py`, the checker bounded every packet index by
`H_pad / L`. That is correct only for patterns whose symbols agree in every
coordinate.

Let a pattern have `k` equal coordinates and `a-k` unequal coordinates.
The unequal bits encode the orientations of the directed label classes;
the equal bits provide `2^k` copies from each class per packet. Each class
has `H_pad` padded positions. The correct range is therefore

\[
 0\le\operatorname{index}<H_{\rm pad}/2^k.
\]

This also recovers the paper's *total* packet count:

\[
 \sum_{\text{patterns}}\frac{H_{\rm pad}}{2^{k(\text{pattern})}}
 =H_{\rm pad}\left(\frac r2+\binom r2\right)^a
 =\frac{H_{\rm pad}r^{2a}}{2^a}
 =H_{\rm pad}D_{\rm arr}/L.
\]

A concrete counterexample has three parallel edges between one vertex pair
and three between another. The canonical packer returns `a=2`, `L=4`,
`H_pad=4`. One pattern is `((0,1),(0,0))`, with `k=1`; its legitimate packet
indices are 0 and 1. The sealed R9.8 checker rejects index 1. The older
independent packing checker accepts the same layout. The corrected R9.8
checker accepts it and still rejects index 2.

`packet_counterexample.json` records both executions. Five added regression
tests cover the real six-edge layout, every equal/unequal pattern of width
two, out-of-range indices, and the six-edge full point at zeta=0 through
64 actual group children and independent half-edge elimination. The source
load/shrink failures of this scaled fixture remain reported.

This was a false rejection of a valid finite layout. It is not evidence of
a wrong count previously returned, or an error in the manuscript's packing
formula. The existing `packet_bijection.py` already uses the correct range.
So does the compiled theorem `D3FullPacketModel.encodeClass_bounds` and
the domain enumeration `D3FinitePacketDomain.addresses`. The defect was in
the new R9.8 checker, illustrating the remaining model-to-executable gap.

## 2. The parent-to-child algebra, with its premises exposed

Work in the commutative ring at precision `p_t`, after fixing the actual
packet layout, interpolation value, tensor creation representatives, and
complete mode decomposition. For packet P and group g, write

\[
 R_{P,g}(Y_g,X_g,Z)
 =\prod_{x\in P,\ g(x)=g}
 l_{Y_x}\!\left(\operatorname{local}_x(X_g)
                    +\sum_{Z:\operatorname{target}(Z)=g}c_{xZ}Z\right).
\]

Every mode has exactly one target packet/group and one source group. Define
the packet tensor

\[
 K_{P,g,\beta}(Y_g,X_g)
 =[Z_{\rm target}^{\beta}]R_{P,g}
   \prod_{Z\in P:\operatorname{source}(Z)=g}L_Z(X_g)^{\beta_Z}.
\]

Expanding the product of the row polynomials selects each global beta
coefficient exactly once. Substituting the source forms places each
remaining factor in its source group. All X and Y half-edge variables now
belong to disjoint groups. Distributivity of finite sums gives

\[
 \sum_{X,Y} A(Y)B(X)\prod_P R_P(Y,X,L(X))
 =\sum_\beta\prod_{g=1}^{64}
   \left(\sum_{X_g,Y_g}I_g(Y_g,X_g)\prod_P K_{P,g,\beta}\right).
\]

The inner sum is precisely the constructed child contraction. This argument
requires neither shrinkage nor an asymptotic schedule. Those are separate
conditions needed for source recursion and its resource estimates.

If each `c_xZ` is divisible by `2^w_Z`, a coefficient of `Z^beta` is
divisible by `2^(sum w_Z beta_Z)`. Thus deleting terms of weight at least
`p_t` is valid modulo `2^p_t`. A work limit alone never justifies deletion.
No rows means a target coefficient is 1 for the all-zero exponent and 0
otherwise; an empty source form has `0^0=1` and `0^b=0` for positive b.
An edge-free child is a unit only if its inherited scalar tensors also
multiply to one. The evaluator correctly retains isolated scalar vertices.

R9.8 removes modes with identically zero source forms or all-zero target
coefficients before enumerating tuples. This is an algebraically valid
reduction: any positive exponent in a removed mode gives zero. Its stream
is complete over that reduced basis, not a literal enumeration of every
zero-contributing formal variable introduced in the paper. This distinction
must accompany the reported 245-tuple fixture count.

The construction has exactly one child wire per inherited half-edge.
Consequently

\[
 M_g=R_g+C_g,\qquad \sum_gM_g=2M.
\]

Only if the *actual* per-side group loads obey `R_g,C_g <= 3M/64` can one
deduce `M_g <= 6M/64 = 3M/32 < M/8`. The new packet degree is at most
`2L`; inherited degrees are unchanged. For `12 <= M <= 16`, even a
nonempty per-side group cannot satisfy `3M/64 < 1`, so the prescribed
source load hypotheses cannot hold at those finite sizes.

## 3. Cauchy coefficients and Hermite precision

The Cauchy numerator cancels the factor at `y-x`, so W is a rational
polynomial of degree `2L-1` and `W(0)=I`. On the complete residue grid,
the content of `C'(t)` equals that of `C'(0)`. After substituting
`T=t+2Lz`, cancellation leaves integral coefficients. When `y-x != t`,
their valuations are at least `a+1-v2(t-y+x)`.

For a crossing tile `y=y0+2^(i+1)j`, orientation gives
`v2(t-y0+x) <= i`. Hence the geometric ratio has valuation at least one;
the leading fraction has valuation at least `a+1-i`. Its b-th mode
coefficient has valuation at least `b+1`. The remainder of the retained
geometric expansion is therefore zero modulo `2^p_t`.

For Hermite recovery, let

\[
 Q_t(z)=\left[F(t+\alpha z)/E_t(t+\alpha z)\right]_{<q_t}.
\]

The reciprocal series of E is integral with constant term one, so this
operation preserves coefficientwise precision. The contribution from
coefficient j has multiplier valuation

\[
 v_2(E_t(0))+j(i-a-1).
\]

Thus a sufficient loss allowance at that node is

\[
 \max\{0,-v_2(E_t(0))+(a+1-i)(q_t-1)\}.
\]

Using the level-count identity in `eq:tensor-hermite-loss` gives
`v2(E_t(0)) >= -6D_t h`; also `q_t <= 4M`. The loss is at most
`6D_t h + 4M(a+1)`. The paper's prescribed increment
`8D_t h + 8M(a+1)` covers it. Summation causes no further 2-adic loss.
This is a coefficientwise argument, not a test of one scalar value.

An independent exact Gauss-Jordan solution of the confluent Vandermonde
systems of orders 6, 12, 12, 30, 24 and 60 agrees with the implementation's
product-form Hermite weights. A rational polynomial
`W_00(T)^M + 3 W_01(T)^M - 5`, whose value at zero is -4, recovers as
124 modulo 128 from canonical shifted coefficient residues in all six cases.
These are independent finite corroborations of the displayed argument.
The source precision schedule was not reduced or changed.

## 4. Creation precision is part of the tensor's definition

For an entry recipe R created at `p_c`, the inherited entry at any higher
precision is

\[
 \operatorname{embed}_{p_c\to p}(\operatorname{can}(R\bmod2^{p_c})).
\]

It is not `R mod 2^p`. For example, at creation precision 2, `1-3`
represents 2. Inheriting that entry at precision 9 still gives 2; recomputing
the expression gives 510 and changes the tensor. The canonical coordinates
are below `2^p_c`, so all later reductions at precisions at least `p_c`
preserve them. This explains why the local identity can be composed down
the recursion: each child contracts exactly the entries created by its
parent, even when the child's own deformation uses larger precisions.

The existing lift-chain Lean lemmas establish this coordinate statement.
They do not establish the entire Python recipe evaluator or recursion.

## 5. Source qualification must cover descendants

Positive `u_0` and the three packing inequalities at the root do not imply
that every later active call has positive u. For an exact example, take

\[
 s=M=2^{131080},\quad C=1,\quad
 \Delta=2^{117972},\quad H=\lceil s/362\rceil.
\]

The root has `u_0=1`, `a_0=2`, `L=4`, `D_arr=2^24` and satisfies all
three packing inequalities. Abstractly, a matching with equal occupancy
of every directed label class admits a fully occupied balanced packing:
each group has `M/64` ports on each side and its child has `M/32` wires.
That child is still above H, yet `u_1=0`. All three numerical packing
inequalities still hold at the child. The Hermite construction cannot be
invoked there with u=0.

`math_checks.json` checks the integer inequalities; it does not construct
that enormous network. The matching argument establishes the abstract
layout, not an executable source-qualified test. This example is **not**
a contradiction of the manuscript's *sufficiently large s* theorem: the
paper separately treats a fixed finite range by direct summation. It
does rule out qualification based only on a successful root check.

The existing sufficient threshold `lambda >= 2^600 C^10`, together with
the inductive edge and degree bounds, supplies positive schedules at every
active depth. It is far beyond execution here. Separately, R9.8's
`ParentCall` restricts root s to 4096 bits, hence lambda <= 4096 and
u_0=0 throughout that API's domain. Its source-active output flags must
remain false. The large-integer schedule checker and the bounded executor
are different capabilities.

## 6. The correct deliverable and the remaining proof boundary

For practical 12–16-edge inputs, ordinary contraction, certified factor
elimination and conditioned boundary summation provide the applicable
exact algorithm. At 16 edges, original contraction enumerates 65,536
assignments; unrestricted half-edge deformation enumerates 4,294,967,296.
An elimination oracle needs its own width/resource limit.

For the source recurrence, the correct mathematical route is the explicit
packet bijection and load proof, weighted coefficient factorization above,
creation-time entry preservation, complete per-point evaluation, and exact
Hermite recovery, composed with a valid schedule at every active depth.
The edge measure then decreases by the conditional `3/32` bound. The
branching, bit-operation and space bounds require all of these hypotheses
and uniform costs; they do not follow from a larger finite wire cap.

No counterexample to the reviewed conditional coefficient identity or
Hermite lemma was found. This review covers the contraction appendix and
its implementation boundary, not all reductions in the full manuscript
or a rebuild of its upstream Lean formalization. Verification of all
Python executions and source-scale complexity remains open. Theorem mode
stays off.

The reproducible bounded arithmetic audit is `review_math.py`, with results
in `math_checks.json`. Final results in `verification.json` record 1,511
passing tests and two skips for the optional pybind11 extension; the
standalone C++ self-test passed. All 41 Lean modules passed their required
axiom audits, as did all 11 R9.4-R9.8 validator commands. Clean Python
3.10.19 wheel and Linux Python 3.12.14 Docker checks passed the packet-index
regression, two-level generated-child recursion, and finite 16-edge workflow.
All environments report source binding
`8325c93fccb8d37b99f85f79ee6e6b804c04e4c7cf9ae5b79e1bd821f5e1e67e`.
The full pytest suite was run natively; full container pytest and hosted CI
were not run. The original sealed manifests still verify, with 1,051 R9.7
and 1,068 R9.8 file entries.

Primary source: [pinned contraction manuscript](https://github.com/openai/math/blob/4eaee87548250b2682affda7d05d947c05554bae/preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026/build/quantitative-contraction.tex),
especially `lem:tensor-packets`, `eq:tensor-mode-expansion`,
`eq:tensor-recursion-identity`, `lem:tapered-hermite`, and
`eq:tensor-hermite-loss`.
