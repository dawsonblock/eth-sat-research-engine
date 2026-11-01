# Weighted mode tuples: an abstract bound

This note proves the counting step under an explicit multiplicity hypothesis.
It does not prove that the implementation's packing satisfies that
hypothesis uniformly, nor does it establish the complete solver runtime.

Let the modes have positive integer weights, with at most `K` modes of each
weight, where `K >= 0` may be real. For `p > 0`, let `N` be the number of nonnegative exponent tuples
with total weight less than `p`. For any real `theta > 0`, the generating
function gives

\[
N \le e^{\theta p}\prod_{w\ge1}(1-e^{-\theta w})^{-K}.
\]

All coefficients are nonnegative, so extending the finite product to all
positive weights can only increase the bound. Expanding the logarithm and
using `exp(x)-1 >= x` yields

\[
\log\!\prod_{w\ge1}(1-e^{-\theta w})^{-K}
=K\sum_{j\ge1}\frac{1}{j(e^{j\theta}-1)}
\le\frac{K}{\theta}\sum_{j\ge1}\frac{1}{j^2}
<\frac{2K}{\theta}.
\]

For `K > 0`, set `theta = sqrt(2K/p)`. Then
`log N < 2 sqrt(2 K p) < 3 sqrt(K p)`. For `K=0`, `N=1`.
Since `exp(3) < 2^5`, an integer-only loose bound is
`N <= 2^(5 ceil(sqrt(K p)))`.

For the pinned manuscript's modes at a node, suppose the packet construction
has at most `3M/L` packets and each packet has one fixed unordered symbol
pair in coordinate `i`. A column tile is specified by `y0` in
`0,...,2^(i+1)-1` and has one source symbol. If the pair's symbols agree,
there is no cross-group target; otherwise the target symbol is the other
member of that pair. Thus each packet has at most `2^(i+1)` modes of any
one nominal weight `b+1`. Writing `D_t=L/2^i`, the multiplicity is at most
`(3M/L) 2^(i+1) = 6M/D_t`. Taking the real bound `K=6M/D_t` gives
`N=exp(O(sqrt(M p_t/D_t)))`. The finite integer-only auditor uses the
slightly looser ceiling. The further simplification to
`exp(O(M/sqrt(u)))` requires the separate precision estimate
`p_t=O(M D_t/u)` and its hypotheses.

`audit_point_mode_multiplicity` checks the per-weight inequality for one
finite point-mode certificate and reports the loose power-of-two bound. Its
result is an instance check. The scaled finite experiments do not prove the
uniform packing, precision estimate, recursion-tree cost, or space bound.
