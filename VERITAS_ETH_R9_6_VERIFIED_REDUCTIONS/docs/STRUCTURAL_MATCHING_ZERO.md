# A conditional zero certificate for a packet coefficient

The optional `certify_structural_tuple_matching` utility in
`eth_recursive_contraction_v39/mode_matching.py` checks a stronger necessary
condition than the existing per-mode and total-row capacity bounds. The
finite recursor can opt in with `RecursionPolicy(enable_hall_pruning=True)`;
the default tuple stream and default execution remain unchanged.

For one packet and target group, consider its product of affine row factors

\[
  \prod_{j\in J}\left(a_j+\sum_i b_{ji}z_i\right).
\]

To obtain the coefficient of `z^beta`, each row can contribute at most one
mode. Build a bipartite graph with a mode vertex `i` and a row vertex `j`
whenever the supplied mode metadata says `b_ji` may be nonzero. Mode `i`
needs `beta_i` distinct rows. If a set of modes `S` has

\[
  \sum_{i\in S}\beta_i > |N(S)|,
\]

then no selection of affine factors can yield the monomial, so its
coefficient is exactly zero over **any commutative coefficient ring**.
This is a pigeonhole argument and does not depend on 2-adic divisibility.
The utility uses an integral augmenting-path matching and, on failure,
returns the particular mode set, its neighboring rows, and the two integers
in the displayed inequality. For the conclusion to apply to a real child,
the supplied support must include every nonzero mode-row coefficient. This
utility deliberately reports `support_provenance_verified=false`: the
caller must independently check the actual mode certificate first.

For example, if modes 0 and 1 both touch only row 0, and mode 2 touches rows
1 and 2, then `beta=(1,1,0)` passes the existing aggregate bound of two
selections among three total rows. It is nevertheless zero because modes
`{0,1}` demand two selections from their sole neighboring row `{0}`.

A feasible matching proves only that this combinatorial obstruction is
absent. Different selections can cancel, and listed coefficients can be
zero in the ring. A failed cooperative work budget returns
`INCONCLUSIVE_RESOURCE_LIMIT` without a partial witness. The utility uses a
stream of iterative augmenting-path searches and has polynomial worst-case
work in the explicitly supplied support graph, but its counters are not
complete bit-operation or hard-memory accounting. When enabled in the finite
recursor, the actual mode certificate is checked first, matching and an
independent Hall-witness replay are charged to the shared cooperative budget,
and only verified zero tuples are omitted from child construction. The
transcript records the witness. Some mode verification, allocation and
bit-arithmetic costs remain unmeasured. This does not establish a uniform
tuple bound, child-size theorem, or subexponential solver.

For actual finite point-mode certificates, the opt-in
`certify_point_mode_matching_zero` wrapper first replays `check_point_modes`,
which checks the finite packet source and the mode expansion, before using
the certified support. On a deficiency it returns a certificate bound by a
SHA-256 digest to the exact mode certificate and exponent tuple. The separate
`replay_point_mode_matching_zero` routine rechecks the mode certificate and
the mode set's neighboring rows and demand directly; it does not trust or
rerun the augmenting-path implementation. Tampering with the mode data,
tuple, digest, or Hall witness is rejected. A feasible matching still proves
no nonzero claim. The declared work budget covers matching and Hall witness
checks, **not** the existing mode-certificate replay, hashing, wall time, or
all bit and allocation costs. Resource exhaustion returns an inconclusive
result without a zero certificate. These standalone finite certificates make
no uniform complexity claim.
