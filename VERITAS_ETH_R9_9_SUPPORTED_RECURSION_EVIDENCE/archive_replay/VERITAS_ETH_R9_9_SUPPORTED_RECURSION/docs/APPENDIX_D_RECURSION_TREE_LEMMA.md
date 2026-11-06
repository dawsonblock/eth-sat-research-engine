# A conditional bound for the complete recursion tree

This lemma closes the abstract recurrence under explicit uniform hypotheses.
It does **not** prove that VERITAS constructs calls satisfying them. The
letter `s` is the manuscript's size parameter and `L_in` is the bit length
of the input description, not the packet length.

## Hypotheses

Let `lambda=ceil(log2(s))`, `s>=2`. Assume fixed positive constants
`C,c,rho`, with `rho sqrt(2)<1`, such that every active call at depth `d`
has at most `C s rho^d` wires and uses `u_d>=c lambda/2^d`. The total
number of active levels is at most `D=O(log lambda)`. Assume a single call
at depth `d` generates at most

\[
B_d \le P(s)\exp\!\left(K\frac{s}{\sqrt\lambda}
                                  (\rho\sqrt2)^d\right)
\]

children, where `P` is one fixed polynomial and `K` is a fixed constant.
This bound must already include all groups, retained tuples, and every
interpolation point. Finally assume that the local bit work at **each**
active call, and the full bit work at **each** leaf, are bounded by

\[
U(s,L_{in})\le Q(s+L_{in})
                 \exp(K' s/\sqrt\lambda),
\]

for one fixed polynomial `Q` and constant `K'`. This hypothesis includes
packet and mode generation, tensor-entry computation, interpolation,
precision changes, and direct leaf contraction; it is not implied by the
number of retained tuples alone.

## Conclusion and proof

At depth `d`, there are at most `prod_{j<d} max(1,B_j)` calls. Therefore the
work over **all** nodes and leaves is at most

\[
(D+1)U(s,L_{in})\prod_{j<D}\max(1,B_j).
\]

Since `rho sqrt(2)<1`, the geometric sum in the exponent is
`O(s/sqrt(lambda))`. The factors `P(s)` contribute
`exp(O(log(s) log(lambda)))`; the depth factor contributes only another
`exp(O(log(lambda)))`. Both are absorbed by
`exp(O(s/sqrt(lambda)))` for sufficiently large `s`. Thus

\[
W(s,L_{in})\le Q(s+L_{in})\exp\!\left(O(s/\sqrt{\log s})\right).
\]

The polynomial in `L_in` appears once in this argument because it is part
of the per-call work bound `U`, not a factor repeated in `B_d`. A proposed
branching bound containing an unrestricted polynomial in `L_in` at every
depth does not establish this same dependence.

This is a bound relative to the global size parameter `s`. It does not by
itself show that the overhead is `o(M_d)` for every individual call: a
polynomial in `s` can dominate the wire count of a small descendant. Nor
does it show an empirical speedup over direct contraction. Any local
criterion involving child work and reconstruction must first define whether
those costs are summed or multiplied and justify the resulting inequality.

For polynomial space, additionally require that each retained call frame,
precision lift, accumulator, and entry-evaluation state has polynomial bit
size; that children and tuples are produced sequentially and discarded; and
that no exponential intermediate table or cache is retained. A depth-first
evaluation then stores at most `O(D)` polynomial-sized frames. This is a
separate conclusion requiring separate implementation evidence.

The pinned manuscript proposes `rho=3/32`, a leaf cutoff near
`s/sqrt(lambda)`, and a mode bound of the displayed form. The present finite
code neither implements the full theorem schedule nor establishes these
hypotheses for its complete recursive execution. In particular, checking a
single tree or using a direct leaf outside a proven cutoff cannot supply the
uniform assumptions above.
