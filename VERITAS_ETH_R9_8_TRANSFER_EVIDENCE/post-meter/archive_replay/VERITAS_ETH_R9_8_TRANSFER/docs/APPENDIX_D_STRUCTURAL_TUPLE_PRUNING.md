# Exact affine-degree pruning for mode tuples

Fix a packet and a target group. Its row-factor product before substituting
source forms is a polynomial over the current coefficient ring:

\[
P(Z)=\prod_{x\in R}\left(A_x+\sum_Z B_{xZ}Z\right).
\]

Each factor is affine in all target modes. For one mode `Z`, only the rows
with `B_(xZ) != 0` can contribute a `Z` factor. Therefore its exponent in
any monomial of `P` is at most the number of those rows. Let `R_active` be
the union of rows with a nonzero coefficient for at least one target mode.
The sum of all target-mode exponents in any monomial is at most
`|R_active|`: each active row factor contributes at most one mode variable.

These bounds hold over any commutative coefficient ring, including rings
with zero divisors. If a tuple violates either bound, its coefficient is
exactly zero. Later substitution of source linear forms and multiplication by
other group factors cannot change zero into a nonzero contribution.
Passing both bounds is only a necessary condition for a nonzero coefficient;
additional zero terms may remain.

The finite `structural_tuples` iterator enforces these bounds together with
the weighted cutoff. The point-mode certificate records the nominal weighted
tuple count and the smaller structural count separately. An exhaustive small
integer oracle checks the iterator, and complete point contractions are still
compared against direct half-edge sums. This pruning is exact but does not,
by itself, prove the manuscript's uniform runtime or space bound.
