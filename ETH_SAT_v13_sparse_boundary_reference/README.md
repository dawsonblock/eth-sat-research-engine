# ETH-SAT v1.3 sparse-boundary permanent reference

This Python 3.9+ standard-library prototype is an isolated reference for one exact subproblem:
computing all coefficients of

```text
Q(z) = per(B + z D)
```

when `B` is block diagonal and `D` has few nonzero cross-block entries.
It is **not integrated into the available ETH-SAT v0.3.0 checkout** and is
not a replacement for a missing v1.3.0 source archive.

For each subset `S` of nonzero entries of `D`, the algorithm skips `S` if
two selected entries share a row or column. Otherwise it removes those rows
and columns, computes each remaining block permanent by subset DP, and adds
the product to coefficient `z**len(S)`. Each permutation contributes once,
through its unique subset of cross-block entries, so the coefficient
identity is exact.

If `k` is the number of nonzero cross-block entries, `b` is the largest
diagonal block size, and block sizes are `b_1,...,b_g`, the conservative
subset-DP state-visit and column-scan bounds are respectively
`2**k * sum_i 2**b_i` and `2**k * sum_i b_i*2**b_i`. Including subset checks,
residual construction, and exact scalar arithmetic gives the looser bound
`O(2**k * (k + n*b*2**b))` arithmetic/loop work for this explicit algorithm.
The Python operation ledger reports exact scalar arithmetic, DP state visits,
and DP column scans separately; those counters are not wall-clock or bit-cost
measurements. When `k,b=O(sqrt(n))`, the stated operation bound is
subexponential; when either grows linearly with `n`, it gives no such result.
Coefficient bit lengths add their own cost.

The prototype separately caps matrix dimension, cross-entry count, masks,
DP-state visits, DP column scans, block size, and exact scalar arithmetic.
Conservative DP work estimates are checked before search; live ledgers enforce
the state, scan, and arithmetic caps during computation. Exhaustion raises an
exception without exposing partial coefficients. The scalar arithmetic count
includes exact multiplications and additions in subset DP and coefficient
accumulation. It does not count integer bit complexity, input copying, matrix
validation, all Python loop/control work, Python object overhead, or peak
bytes. Dimension and block caps bound some of these costs but do not make the
ledger a complete resource proof.

Run the full finite validation:

```console
python ETH_SAT_v13_sparse_boundary_reference.py --self-test
python -m unittest discover -s tests -v
```

The validation includes the 3x3 coefficient example, 330 deterministic
random differential cases against a separate permutation enumerator, and a
64x64 identity-plus-three-cycles example with eight cross-block entries.
The large example is also checked against the independent product of its
three cycle factors.

This work does not implement a general structured Taylor jet, nor does it
prove a cheap block decomposition for arbitrary matrices or a subexponential
algorithm for arbitrary SAT. Integration requires the exact v1.3.0 archive
and its existing permanent APIs.
