# Conditional precision-path estimate

This derives the source's `p_t=O_C(M D_t/u)` estimate from its stated path
invariants. It does not by itself prove the tapered Hermite recovery lemma or
that the finite implementation enforces these hypotheses at theorem scale.

Let `lambda=ceil(log2(s))`, `M_0<=Cs`, root precision `p_0<=Cs`, and
`M_k<=Cs 8^-k` along a path. Assume each active call has
`1<=u_k<=M_k`, `a_k<=lambda`, and the source increment

\[
p_{k+1}=p_k+8h_kD_k+8M_k(a_k+1),\qquad
h_k=\lceil3M_k/u_k\rceil,\quad D_k\le2^{a_k}.
\]

Because `h_k<=4M_k/u_k<=4M_k`, `a_k` is nondecreasing, and
`sum_k M_k <= (8/7)Cs`, summing the increments before depth `d` gives a
fixed constant `K` such that

\[
p_d\le K C s(\lambda+1)2^{a_{d-1}},\qquad a_{-1}=0.
\]

At an active call, assume `M_d>H>=s/sqrt(lambda)`,
`u_d>=lambda^(4/5)`, `u_d<=lambda`, and
`a_d=a_{d-1}+2u_d`. A retained node has `i=v2(t)<u_d`, so

\[
D_t=2^{a_d-i}\ge2^{a_{d-1}+u_d}.
\]

For each fixed `C`, `2^(lambda^(4/5))` eventually dominates
`C(lambda+1)lambda^(3/2)`. Thus the displayed path bound implies
`p_d=O_C(M_d D_t/u_d)`. The same domination gives
`M_d(a_d+1)=O(M_d D_t/u_d)`, and `h_d<=4M_d/u_d` gives
`h_d D_t<=4M_d D_t/u_d`. Substitution into the node-precision formula proves

\[
p_t=p_d+8h_dD_t+8M_d(a_d+1)
   =O_C(M_dD_t/u_d).
\]

The constants and sufficiently-large threshold here are not extracted as
an operational test. The proof assumes the indicated root, shrinkage,
schedule, and precision-increment conditions at every ancestor. The current
finite code checks only selected paths and uses bounded scaled parameters.
