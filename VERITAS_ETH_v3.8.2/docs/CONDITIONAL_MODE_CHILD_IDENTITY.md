# Exact conditional point-mode factorization

This is a uniform algebraic identity for a *supplied* valid mode expansion.
It does not construct that expansion, establish the packet load hypotheses,
or bound the work needed to evaluate its terms. It holds over any commutative
ring, including a truncated polynomial ring over an unramified extension of
`Z/2^p Z`.

The factorization follows the construction in the pinned [Appendix D child
network description](https://github.com/openai/math/blob/4eaee87548250b2682affda7d05d947c05554bae/preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026/build/quantitative-contraction.tex#L455-L518).

Assign each row half-wire `Y_e` and each column half-wire `X_e` to exactly
one group. Suppose each deformed packet row `e` in target group `g` has the
exact expression

\[
 H_e(X,Y)= (1-Y_e)+(2Y_e-1)
       \left(\operatorname{local}_e(X)+\sum_{Z:\,t(Z)=g} b_{eZ}L_Z(X)\right).
\]

Here the `X` variables in `local_e` belong to `g`, and the linear form
`L_Z` belongs entirely to mode `Z`'s source group `s(Z)`. The formula
follows by checking `Y_e=0` and `Y_e=1`; it makes no division in the ring.
The supplied packet mode identity is the assumption that this expression
really equals the deformed row factor for every Boolean assignment.

Introduce a formal variable `z_Z` for each mode and replace every `L_Z`
above by `z_Z`. Let `A_g(z)` be the product of those row factors in group
`g`, over every packet. For a nonnegative mode-exponent vector `beta`, let
`beta_g` be its restriction to modes targeted at `g`. Finite polynomial
expansion and substitution then give the exact identity

\[
 \prod_e H_e =\sum_{\beta}
 \prod_g \left([z^{\beta_g}]A_g(z)\right)
            \prod_{Z:\,s(Z)=g}L_Z(X)^{\beta_Z}.
\]

Only finitely many terms occur because each row factor is affine in its
formal mode variables. Multiply by the inherited tensor entries and sum
over all half-wire assignments. Every variable and every inherited entry
belongs to one group, so each summand separates into a product of group
contractions. Distributing finite sums over finite products proves the
parent-to-children identity for the supplied modes and the specified child
factors, regardless of whether any child is small.

If each coefficient `b_eZ` lies in the ideal `2^w_Z R`, then every monomial
contributing to `[z^beta_g]A_g` contains exactly `beta_Z` copies of a
coefficient from each target mode `Z`. Therefore the complete term lies in
`2^(sum_Z w_Z beta_Z) R`. In `R=(Z/2^p Z)[...]`, a term with total weight
at least `p` is exactly zero. Also, if a group has `q` target row factors,
the coefficient is identically zero whenever its total target exponent
exceeds `q`. Neither assertion requires a field or divides by an even value.

The current engine verifies bounded concrete mode data and compares some
child identities with an independent oracle. Its finite tests do not prove
that all inputs yield the required modes, that all resulting children
shrink, that coefficient generation is cheap, or that reconstruction and
the full recursion have the manuscript's resource bounds.
