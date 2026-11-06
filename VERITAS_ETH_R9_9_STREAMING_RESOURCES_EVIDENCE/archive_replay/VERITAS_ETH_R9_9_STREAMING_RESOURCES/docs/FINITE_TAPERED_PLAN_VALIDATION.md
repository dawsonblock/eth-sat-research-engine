# Independent finite tapered-plan validation

`validate_tapered_plan` checks the mathematical recovery plan independently
of the linear-system solver that produced it. For a finite plan with `M`
wires, packet size `L=2^a`, precision `p`, and `h=ceil(3M/u)`, it recomputes
every active node `t`, its multiplicity and working precision:

\[
q_t=h\max(0,u-v_2(t)),\qquad
p_t=p+8h\frac{L}{2^{v_2(t)}}+8M(a+1).
\]

It checks the node set, the interpolation scale `2L`, the bound
`deg F <= M(2L-1)`, and that the multiplicities exceed the degree. It then
checks each exact rational recovery weight on every polynomial-basis
monomial. For `k=0,...,deg F`, the required identity is

\[
\sum_{(t,j)} w_{t,j}\binom{k}{j}t^{k-j}(2L)^j=[k=0].
\]

This proves that the supplied functional recovers `F(0)` for every
polynomial within the finite degree bound, by linearity. The verifier also
recomputes the common 2-adic guard and coefficient-wise sufficient precision
from the exact weights, and rejects a plan whose prescribed node precision
is too small. The test suite mutates node precisions, multiplicities, scale,
samples, weights, guards, and scope claims and confirms rejection.

This check validates one bounded recovery plan only. It does not establish
that a caller actually produced its jet residues at the declared precision,
that those residues came from a correct mode-to-child contraction, or that
the full recursive implementation satisfies the asymptotic runtime and
memory theorem. The precise `p_t` and `q_t` formulas are from the pinned
[tapered Hermite recovery lemma](https://github.com/openai/math/blob/4eaee87548250b2682affda7d05d947c05554bae/preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026/build/quantitative-contraction.tex).
