# Source-pinned calculations for recursive child entries

The [pinned OpenAI contraction manuscript](https://github.com/openai/math/blob/4eaee87548250b2682affda7d05d947c05554bae/preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026/build/quantitative-contraction.tex#L455-L518) describes each packet/group child entry as a coefficient of a product of affine row factors, multiplied by the source-mode powers. Its child identity and time/space analysis have not been independently established for this implementation.

For row factors indexed by `x` and target modes indexed by `i`, the exact coefficient calculation is

\[
[z^\beta]\prod_{x=1}^{q}\Bigl(a_x+\sum_{i=1}^{k}b_{xi}z_i\Bigr)
=\sum_{\substack{f:[q]\to\{0,\ldots,k\}\\|f^{-1}(i)|=\beta_i\ (1\le i\le k)}}
\prod_{x=1}^{q}c_{x,f(x)},\quad c_{x,0}=a_x,\ c_{x,i}=b_{xi}.
\]

Each selection chooses exactly one term from each affine factor. Consequently it can be generated and accumulated one at a time, without keeping a table indexed by all partial exponent vectors. For `q<=L` rows and `k` target modes, naive streaming uses at most `(k+1)^q` selections, with selection indices, counters, coefficients and ring accumulators retained. The source-mode contribution is then multiplied in as `product_i L_i(X)^beta_i`. Zero rows and exponent-zero source factors use the usual empty-product convention. The implementation's cooperative budget still controls this finite calculation.

The implementation prunes a partial selection when a mode's required exponent is exceeded or the remaining rows cannot supply the remaining degree. For one active mode with exponent one, the product rule computes the constant and linear coefficients in one pass, without dividing by any ring element. These improvements do not bound the number of feasible selections for general exponents. For `R` rows and `k` active modes, the selection tree has at most `(R+1)(k+1)^R` partial nodes; any asymptotic use of this bound must also charge construction of the row options and the bit costs of ring operations.

The work ledger now charges scans of packet inputs and coefficient descriptions that the former finite evaluator did not count. The eight-wire differential test explicitly requests a larger aggregate work budget to account for those additional observed operations; the default remains unchanged, individual subcalls retain their existing caps, and exhaustion continues to return an inconclusive status. This observed-work counter is not complete bit-operation or memory accounting.

Packet recipes reject negative mode exponents and malformed or duplicate port, row, column and mode references when constructed. A recursively inherited vertex can have new edge identifiers: its tensor recipe is bound by port position, so validation does not require the vertex's new port labels to equal the recipe's original labels.

The standalone exact Cauchy point evaluator also accepts packet sizes up to
256 under an explicit opt-in cap; its default remains 16. Independent tests
compare integer evaluation points with exact rational products. This extends
only the local finite evaluator: the recursive geometric mode builder still
has smaller supported packet and network limits.

The manuscript's polynomial-space conclusion additionally needs polynomial-size descriptions and ring elements, bounded mode multiplicity, the prescribed schedule, streaming at all other levels, and polynomial-space entry evaluation throughout the ancestry. The bounded implementation and finite tests do not prove those conditions uniformly.

## Related permanent-jet calculation

[Ryan O'Donnell's exposition, Lemma 3.1](https://www.cs.cmu.edu/~odonnell/some_eth_false_exposition.pdf) gives a separate calculation useful for the earlier permanent backend. Put `A0=A(t0)` and `Delta(z)=A(t0+z)-A0`. Then

\[
[z^j]\operatorname{per}(A(t_0+z))=
\sum_{a=0}^{\min(j,n)}\;\sum_{|S|=|T|=a}
\operatorname{per}(A_0[S^c,T^c])\,
[z^j]\operatorname{per}(\Delta(z)[S,T]).
\]

Each entry of `Delta` is divisible by `z`, so minors larger than `j` contribute zero. The ordinary derivative is `j!` times this coefficient. The large complementary minors must be evaluated with the available block-plus-low-rank structure, including unequal numbers of selected rows and columns inside individual blocks; the small perturbation minors can use exact truncated-polynomial permanent calculation. The formula is exact for arbitrary polynomial matrices but yields an asymptotic saving only when all the structured-minor, bit-cost and deformation hypotheses are met. This note does not claim that this permanent-jet backend has been implemented here.
