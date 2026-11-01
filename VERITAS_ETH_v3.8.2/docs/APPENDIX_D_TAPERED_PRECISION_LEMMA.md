# Conditional tapered-recovery precision argument

This note derives the mathematical guard precision under the grid, degree,
integrality, and multiplicity hypotheses below. The bounded implementation
uses a separately checked rational Hermite system; this argument does not
establish its theorem-scale time or space bounds.

Let `L=2^a`, `alpha=2L`, `S={-L,...,L-1}` and `1<=u<=min(a,M)`.
Set `h=ceil(3M/u)` and, for `t!=0`,
`q_t=h max(0,u-v2(t))`. Suppose `F` has degree at most `M(2L-1)`,
`F(0)` is integral, and every shifted polynomial `F(t+alpha z)` has
integral coefficients in the stated truncated extension ring.

There are `L` odd points, each with multiplicity `hu`; consequently
`sum_t q_t >= Lhu >= 3ML > M(2L-1)`. Put

\[
E_t(T)=\prod_{q\in S\setminus\{0,t\}}
\left(\frac{T-q}{t-q}\right)^{q_q},\qquad
Q_t(z)=\left[\frac{F(t+\alpha z)}{E_t(t+\alpha z)}\right]_{<q_t}.
\]

Hermite interpolation gives `F(0)=sum_t E_t(0) Q_t(-t/alpha)`: each
summand matches the required jet at its own node and vanishes to the
required order at the other nodes. Its degree is below `sum_t q_t`, so the
difference from `F` is the zero polynomial. Every factor of
`E_t(t+alpha z)` is a power of `1+alpha z/(t-q)`, whose nonconstant
coefficient is integral because nonzero grid differences have valuation at
most `a`. Its truncated inverse is therefore integral and loses no precision.

Fix a retained node `t`, let `i=v2(t)` and `D=L/2^i`. Differences with
`v2(q)<i` contribute zero to the valuation of `E_t(0)`. For each
`1<=j<=a-i`, exactly `D/2^j` grid points have `v2(q)=i+j`; the same
number have `v2(t-q)=i+j`, and these have `v2(q)=i`. Therefore

\[
v_2(E_t(0))
=D\sum_{j=1}^{a-i}\frac{j}{2^j}\bigl(q(i+j)-q(i)\bigr)
\ge -6Dh,
\]

where `q(k)=h max(0,u-k)`, `q(i+j)-q(i)>=-hj`, and
`sum_{j>=1} j^2/2^j=6`. Since `M>=u`, `h<=4M/u` and hence
`q_t<=4M`. Evaluating the truncated quotient at `-t/alpha` loses at most
`4M(a+1)` additional powers of two. Thus input coefficients known modulo

\[
2^{p_t},\qquad p_t=p+8hD+8M(a+1),
\]

have sufficient guard bits for each node's contribution modulo `2^p`.
Every contribution's error is in `2^p` times the integral ring, so summing
them causes no further 2-adic loss. The conclusion applies coordinatewise
in the extension and truncated-polynomial bases.

The argument assumes the supplied local jets are the actual shifted
polynomials at their declared precisions. Finite oracle comparisons do not
prove that every recursive call supplies such jets or that the implementation
meets the claimed uniform resource bounds.
