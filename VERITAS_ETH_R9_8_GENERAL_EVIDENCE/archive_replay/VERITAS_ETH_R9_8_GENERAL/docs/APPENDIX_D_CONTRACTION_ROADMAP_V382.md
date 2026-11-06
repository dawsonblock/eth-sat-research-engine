# Appendix D contraction: mathematical implementation roadmap

## Source and claim boundary

This maps the implementation work to the source-pinned Appendix D. The
source revision is OpenAI/math commit
[`4eaee87548250b2682affda7d05d947c05554bae`](https://github.com/openai/math/blob/4eaee87548250b2682affda7d05d947c05554bae/preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026/build/quantitative-contraction.tex).
The manuscript states the contraction theorem; the finite code here is not
an independent verification of that theorem. The related Lean scope file
records a weaker general counting exponent and does not claim to formalize
the sharper Appendix D contraction theorem:
[`lean/docs/378.md`](https://github.com/openai/math/blob/main/lean/docs/378.md).

## Exact route asserted by the manuscript

For a Boolean tensor network with `M` edges, the proof route is:

1. **Bounded-degree preparation and D.3 packet packing.** Let the size
   parameter be `s`, `lambda=ceil(log2(s))`, `r=64`,
   `epsilon=1/(128*1024)`, `Delta=ceil(s^(9/10))`, and
   `H=ceil(s/floor(sqrt(lambda)))`. At depth `d`, choose
   `u_d=floor(epsilon*lambda/2^d)`,
   `a_d=2*sum_{j=0}^d u_j`, and packet size `L=2^a_d`. The deterministic
   packing must establish the source's three conditions
   `M >= 2*D_arr^2*Delta`, `M >= L*D_arr`, and `2L <= Delta`, where
   `D_arr=r^(2a_d)`. A heuristic partition or a verified finite packing
   score is not a substitute for this certificate.
2. **Cauchy deformation.** For
   `C(T)=product_{q=-L}^{L-1}(T-q)`, use
   `W_xy(T)=C(T)/(C'(0)*(T-(y-x)))`, which obeys `W(0)=I`.
   Packet labels determine tile groups. Near a nonzero root
   `t in [-L,L-1]`, expand each affine Boolean row factor at
   `T=t+2^(a+1)z` into its within-group part and cross-group modes.
3. **Exact pruning and child factorization.** Each mode `Z` has a weight
   `w_Z` for which its coefficient is divisible by `2^(w_Z)`. At node
   precision `p_t`, retain exactly exponent tuples with
   `sum_Z w_Z*beta_Z < p_t`; all omitted terms vanish modulo `2^(p_t)`.
   For each retained tuple and each of the `r` groups, construct the
   prescribed packet-tensor child. The identity to verify is
   `F(t+alpha*z) = sum_beta product_g Z_(g,beta) mod 2^(p_t)`.
   The claimed child bound is `6M/r=3M/32<M/8` edges, with maximum degree
   at most `Delta`. Child factors must remain implicit and be computable
   from immutable descriptions.
4. **Tapered reconstruction.** For a nonzero node with
   `i=v2(t)`, let `h=ceil(3M/u)`,
   `q_t=h*max(0,u-i)`, and
   `p_t=p+8*h*D_t+8*M*(a+1)` with `D_t=2^(a-i)`. Reconstruct the value
   at zero from the first `q_t` local Taylor coefficients at all required
   nodes. The node multiplicities must exceed the degree bound, and the
   finite-ring precision loss must be covered coefficientwise.
5. **Recursion and total cost.** Regenerate every child with the inherited
   precision, degree, degree cap, and entry-description invariants. The
   proof then combines the weighted tuple bound
   `exp(O(sqrt(M*p_t/D_t)))=exp(O(M/sqrt(u)))`, geometric wire shrinkage,
   interpolation overhead, bounded leaf enumeration, and bit-cost/space
   accounting. None of these recurrence-wide bounds follows from a single
   finite contraction identity.

## Current implementation status

### Call contract

`research.appendix_d_contract` now binds a per-call immutable tensor
description digest to the source revision above. It checks the declared
description-bit ceiling, factor/table/entry-bit resource ceilings, the
one-call schedule and recursive edge-size hypotheses, and records canonical
integer lifts into `(Z/2^P Z)[V]/(V^ell)`. Resource exhaustion is
`INCONCLUSIVE_RESOURCE_LIMIT`; unsupported schedule or degree hypotheses are
rejected. The contract now requires a strictly increasing root-to-call
precision path and records each explicit integer tensor's creation precision.
It does not establish that the increments obey the manuscript's full
coefficientwise precision formula. A finite call-contract pass is not theorem
eligibility or a contraction result.

| Obligation | v3.8.2 status | What remains |
|---|---|---|
| Source-pinned call contract | Implemented as a finite per-call checker with immutable input digest, explicit resource ceilings, canonical residue lifts, and numeric one-call schedule checks. | Prove and enforce coefficientwise precision inheritance and bind local entry evaluators to a recursive theorem invariant. |
| Exact `W(0)=I` and small polynomial/Hermite recovery | Finite scalar testbed now reconstructs `F(0)` at 8 and 10 wires from nonzero L=2 roots with exact guard bits; independent half-edge evaluations check six 8-wire jet points. | Extend independent checks and use the manuscript's node multiplicities, local rings, and `p_t` schedule. |
| D.3 packing | Existing finite certificate/checker components plus an implicit active-packet view; a separate conditional schedule argument supplies an explicit sufficient threshold for numeric packing hypotheses. | Prove that the actual recursive constructor maintains the child and degree assumptions and remove finite construction caps. See [APPENDIX_D_EXPLICIT_SCHEDULE_THRESHOLD.md](APPENDIX_D_EXPLICIT_SCHEDULE_THRESHOLD.md). |
| Geometric-tile modes and finite packet coefficients | Bounded v31 mode generation, v31 scalar-child contraction, and v36 Boolean-multilinear packet coefficients now accept sparse packet views directly; differential checks compare explicit and implicit paths and direct contraction oracles. | Replace these finite references with the manuscript's exact recursive tile factors, retained-tuple child descriptions, and complete coefficientwise identity. |
| Exact child identity and `M/8` | v39 creates immutable finite group children with lazy packet-entry extraction and creation-precision lifts. Point-mode sums are checked against direct half-edge contraction. | Remove the finite 1..6 parent-wire and ring caps, implement the theorem schedule, and prove/recheck the uniform `M/8` bound. Finite child identities do not establish that bound. |
| Recursive regeneration | A bounded, scaled v39 reference regenerates packets and point modes through two tested levels, interpolates at distinct extension-ring points, and applies finite tapered recovery. | Replace scaled fixed parameters and direct finite leaves with the prescribed depth schedule, and prove the creation, precision, degree and shrinkage invariants inductively. See [FINITE_TAPERED_RECURSION_V39.md](FINITE_TAPERED_RECURSION_V39.md). |
| Total time and polynomial space | The abstract point valuation, per-weight tuple bound, and conditional precision-path estimate are documented. The finite work counters are incomplete. | Prove and connect all hypotheses to the implementation; account for every node, mode tuple, entry evaluation, bit operation, interpolation, retained object, and leaf. |

## Validation gates for the next implementation

Use small arbitrary bipartite networks, not just two dense full-scope
tables. For each supported network, retain a direct assignment oracle and
check, in this order:

1. D.3 packet coverage, endpoint consistency, group/tile conditions, and
   the exact numeric hypotheses.
2. Every local Cauchy entry and every cross-group mode coefficient,
   including its declared 2-adic valuation.
3. Every retained weighted tuple's lazily generated child network and the
   exact modular recursion identity at each interpolation node.
4. Nonzero-node Taylor jets, guard precision, and reconstruction of the
   original contraction at zero.
5. At least two recursive levels, checking child edge counts, maximum
   degrees, precision inheritance, and recomputed entry descriptions.
6. A deterministic whole-run ledger for work, bit lengths, and peak stored
   state. Resource exhaustion must return an inconclusive status, never a
   partial count.

Small tests can expose implementation mistakes. They cannot prove that the
packing hypotheses hold for every supported network or that the manuscript's
uniform asymptotic bounds are valid.
