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
=\frac{K\pi^2}{6\theta}.
\]

For `K > 0`, the minimizing choice `theta = pi sqrt(K/(6p))` gives

\[
N\le\exp\!\left(\pi\sqrt{2Kp/3}\right).
\]

For `K=0`, `N=1`. For a safe integer-only binary bound, use `pi < 22/7`
and `ln 2 > 2/3`; the latter follows from the positive-term expansion
`ln 2 = 2(1/3 + (1/3)^3/3 + ...)`. These inequalities imply
`pi sqrt(2/3)/ln 2 < 4`. Thus, for `K>0`,

\[
\log_2 N < 4\sqrt{Kp},\qquad
N\le 2^{\lceil\sqrt{16Kp}\rceil}.
\]

The function `weighted_tuple_upper_exponent` calculates the displayed
exponent using integer square roots and exact rational input `K`, with no
floating-point rounding. It proves only the abstract counting implication:
the caller must establish the per-weight multiplicity hypothesis separately.

For the pinned manuscript's modes at a node, suppose the packet construction
has at most `3M/L` packets and each packet has one fixed unordered symbol
pair in coordinate `i`. A column tile is specified by `y0` in
`0,...,2^(i+1)-1` and has one source symbol. If the pair's symbols agree,
there is no cross-group target; otherwise the target symbol is the other
member of that pair. Thus each packet has at most `2^(i+1)` modes of any
one nominal weight `b+1`. Writing `D_t=L/2^i`, the multiplicity is at most
`(3M/L) 2^(i+1) = 6M/D_t`. Taking the real bound `K=6M/D_t` gives
`N=exp(O(sqrt(M p_t/D_t)))`. The finite auditor keeps `6M/D_t` as a
rational when calculating its power-of-two bound. The further simplification to
`exp(O(M/sqrt(u)))` requires the separate precision estimate
`p_t=O(M D_t/u)` and its hypotheses.

`audit_point_mode_multiplicity` checks the per-weight inequality for one
finite point-mode certificate and reports the loose power-of-two bound. Its
result is an instance check. The scaled finite experiments do not prove the
uniform packing, precision estimate, recursion-tree cost, or space bound.

## Cost of streaming a finite tuple set

Let `k` be the number of explicitly supplied positive weights, `p` the
precision, and `N` the number of retained tuples. Every feasible prefix of
length `d` extends to a retained tuple by choosing zero for every remaining
coordinate. Distinct prefixes at the same depth have distinct such
extensions. Thus there are at most `N` prefixes at each depth and at most
`(k+1)N` prefixes in the complete search tree. The iterative depth-first
enumerator therefore uses `O(kN)` state transitions and `O(kN)` additional
work to emit its tuples, in a unit-cost model. The work to produce each
child or evaluate its entries is separate.

The bounded reference first counts tuples using a dynamic program with
`O(kp)` integer operations and `O(p)` stored counters; it refuses to emit
any tuple if its finite tuple-count cap is exceeded. The iterative traversal
retains `O(k)` weights, exponent counters and remaining-weight values, plus
one output tuple at a time. Its arithmetic and storage costs must also
include the bit lengths of weights, counters and the precision. A caller
that collects all outputs, or downstream construction that retains all
children, does not obtain the streaming space bound. The current precision
cap and tuple cap make this an implementation-level finite result, not a
proof that the complete solver has polynomial space or subexponential time.
