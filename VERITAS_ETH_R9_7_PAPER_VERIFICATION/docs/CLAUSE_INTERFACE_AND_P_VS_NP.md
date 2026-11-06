# Clause-interface rank and the P versus NP research gate

The [Clay Mathematics Institute's official problem description](https://www.claymath.org/wp-content/uploads/2022/02/MPPc.pdf)
asks whether `P=NP`. A deterministic algorithm that decides every 3-CNF
formula in time polynomial in the encoded input length, together with a
correctness and worst-case bit-cost proof, would establish equality. An
exact polynomial-time counter would be stronger than the decision algorithm
needed for this implication. A Lean formalization and independent review
would strengthen verification, but neither is a logical prerequisite for a
valid mathematical proof.

The following lemma examines the clause-compatibility matrix described in
the request. It does not assert that a particular unprovided v1.5.0 archive
has been inspected in this workspace.

## Exact rank lemma

For `s,t` in `{0,1}^c`, let `K_c(s,t)=1` when `s OR t` is all ones and
zero otherwise. If `K_1=[[0,1],[1,1]]`, then, after a consistent bit order,

\[
K_c=K_1^{\otimes c}.
\]

The determinant of `K_1` is `-1`, and its inverse has integer entries:

\[
K_1^{-1}=\begin{pmatrix}-1&1\\1&0\end{pmatrix}.
\]

Therefore `K_c` is invertible over the integers, with inverse
`(K_1^{-1})^(tensor c)`. In particular it has rank `2^c` over the rationals
and over every field, including `F_2`. Equivalently, complementing the row
mask turns the compatibility condition into subset containment; ordering
subsets by size gives a triangular matrix with diagonal entries one.

Over a field, a sum of `R` rank-one matrices has rank at most `R`.
Consequently an exact flat rank-one representation of the **full**
compatibility matrix requires `R>=2^c`. This conclusion also applies to a
change of invertible linear basis. It does not imply a lower bound for every
algorithm that evaluates a join: the actual reachable masks may be a proper
subset, and a structured computation may avoid materializing a rank-one
expansion.

For example, the tensor-product structure itself permits multiplying `K_c`
by an explicitly supplied `2^c`-entry vector using `c` passes of two-entry
updates, in `O(c 2^c)` arithmetic operations instead of a dense `4^c`
matrix-vector multiplication. This is fast in the length of the explicit
vector, but that vector is already exponential in `c`; it is not a
polynomial-time SAT algorithm or a bound on producing the histograms.

`audit_clause_interface_rank` builds this matrix only for `c<=6` under an
explicit entry budget and independently computes its ranks over the
rationals and `F_2`. These finite calculations check examples; the
tensor-inverse argument above proves the stated rank for every `c`.

## Gate for a P=NP claim

No current ETH-SAT or tapered-v4 result in this workspace supplies a
polynomial worst-case decision algorithm. Finite tests, compact
representations with unbounded construction or evaluation cost, and a
subexponential (but superpolynomial) upper bound do not establish `P=NP`.
For any proposed representation, the research gate is a uniform proof of
correctness and termination on **all** 3-CNF inputs, with polynomial total
construction, evaluation, arithmetic bit cost, and space in the encoded input
length. A fallback with exponential worst-case work does not close that gate.
