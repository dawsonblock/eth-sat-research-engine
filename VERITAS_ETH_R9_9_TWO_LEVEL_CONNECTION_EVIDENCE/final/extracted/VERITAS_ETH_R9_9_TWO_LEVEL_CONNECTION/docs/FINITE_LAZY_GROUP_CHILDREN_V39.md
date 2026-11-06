# v3.9 finite lazy group-child prototype

`veritas.research.eth_recursive_contraction_v39.lazy_children` translates one
checked v31 geometric-mode certificate and one retained exponent tuple into
group-local Boolean tensor networks. Each group child has the original
vertex factors assigned to that symbol group and one lazy packet tensor per
incident packet. A packet entry computes the coefficient of the prescribed
target-mode exponents in the product of its affine row factors, then
multiplies the source-mode linear forms to their exponents.

The child description is immutable. Its edges are the group-owned row and
column halfbits; each must meet one original vertex and one packet tensor.
The descriptor reports the resulting edge count and maximum degree. The
evaluator contracts each small child and sums products over the retained mode
tuples. The checker rebuilds the descriptions, replays their entries, and
compares the complete result with direct half-edge Cauchy contraction.

For packet `p` and group `g`, the implemented entry has the form

\[
P_{p,g,\beta}(Y,X)=
\left[\prod_{Z:\,\mathrm{target}(Z)=g} Z^{\beta_Z}\right]
\prod_{x:\,\mathrm{rowgroup}(x)=g}
\bigl(Y_x z_x+(1-Y_x)(1-z_x)\bigr)
\;\prod_{Z:\,\mathrm{source}(Z)=g} L_Z(X)^{\beta_Z},
\]

where coefficient extraction applies to the row-factor product,
`z_x = local_x(X) + sum_Z c_(x,Z) Z`, and
`L_Z(X) = sum_y j_y^b X_y`. Thus the `Y_x=0` case contributes `1-z_x`
and negates each mode coefficient; the `Y_x=1` case contributes `z_x`.
This sign distinction is checked by the direct-contraction tests. Every mode
belongs to one packet and has one source and one target, so the extracted
coefficient and source powers depend only on the bits in group `g`.

This is a finite prototype with the existing v31 limits (at most six parent
wires, small packet/radix parameters, bounded precision and extension degree).
It validates the local child formula and parent identity on tested examples.
An additional bounded path now reuses immutable creation-precision entries for
two experimental tapered recursion levels; see
[FINITE_TAPERED_RECURSION_V39.md](FINITE_TAPERED_RECURSION_V39.md). It does not
provide the manuscript's uniform `M/8` proof or a subexponential time or
space guarantee. Work counters exclude some precomputation and checker costs
and must not be used as a complete complexity ledger.
