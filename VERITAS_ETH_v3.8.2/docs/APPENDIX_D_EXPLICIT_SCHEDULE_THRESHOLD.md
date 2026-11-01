# A sufficient uniform schedule threshold

This gives a deliberately loose explicit threshold for the numeric packing
inequalities in the pinned schedule. It is conditional on the inductive
network invariants; it does not implement the packing constructor at this
scale or establish the solver's complexity.

Let `C >= 1` be an integer, `lambda = ceil(log2(s))`,
`epsilon=2^-17`, `r=64`, `H=ceil(s/floor(sqrt(lambda)))`, and
`Delta=ceil(s^(9/10))`. Suppose the root has at most `C s` edges, every
child has at most one eighth of its parent's edges, and every call has
maximum degree at most `Delta`. Set

\[
\lambda \ge 2^{600} C^{10}.
\]

At an active depth `d`, `H < M_d <= C s 8^-d`. Since
`H >= s/sqrt(lambda)`, it follows that
`2^d < C^(1/3) lambda^(1/6)`. Therefore, for
`z=epsilon lambda / 2^d`,

\[
z>2^{-17}C^{-1/3}\lambda^{5/6}
 \ge 8\lambda^{4/5}.
\]

The last inequality uses `lambda^(1/30) >= 2^20 C^(1/3)`. Hence
`u_d=floor(z) >= lambda^(4/5) >= 1`, and `u_d=Theta_C(lambda/2^d)`.
Also `a_d=2 sum_{j<=d} u_j <= 4 epsilon lambda=lambda/32768`, while
`a_d >= 2u_d`. For this threshold, `M_d>H>lambda>=u_d` as well.

Write `L=2^a` and `D=64^(2a)=2^(12a)`. Since
`2^(lambda-1) < s <= 2^lambda`,

\[
L\le 2^{\lambda/32768},\quad
D\le 2^{3\lambda/8192},\quad
\Delta\le 2^{1+9\lambda/10},\quad
H\ge 2^{\lambda-1}/\sqrt\lambda.
\]

For integer `lambda >= 128`, `log2(lambda) <= lambda/16`; for example,
on `2^k <= lambda < 2^(k+1)`, `k>=7` implies
`k+1 <= 2^k/16`. Thus `H >= 2^(31 lambda/32-1)`. The preceding estimates
give

\[
2D^2\Delta\le2^{2+(9/10+3/4096)\lambda}<H,\qquad
LD\le2^{13\lambda/32768}<H,
\]

and `2L <= Delta`. The first strict inequality follows because
`31/32 - 9/10 - 3/4096 > 1/16` and `lambda >= 128`. Hence every active
call meets `M >= 2D^2 Delta`, `M >= LD`, and `2L <= Delta`. The same
estimates give `L,D <= s^(1/1000)` at this threshold.

The function `uniform_schedule_lemma` checks this sufficient condition
using `lambda` and `C` without constructing the astronomically large `s`.
It reports the required root, child-shrinkage, and degree assumptions. The
threshold is not a practical recommendation or a proof that the current
bounded Python code can execute at theorem scale. The finitely many smaller
sizes require a separate direct-summation treatment for a uniform theorem.
