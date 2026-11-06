# Exact coefficient identity and scope

Let an `n x n` matrix be partitioned into diagonal blocks indexed by `g`.
Write `A = B + zD`, where `B` contains exactly the entries whose row and
column belong to the same block, and `D` contains the nonzero entries between
different blocks. Let `E` be the set of those `k` cross-block entries.

For a subset `S` of `E`, call `S` a matching when no two entries share a row
or a column. Let `R_g(S)` and `C_g(S)` be the rows and columns in block `g`
used by `S`. Define `B_g[S]` as the submatrix of block `g` left after removing
those rows and columns. Its permanent is zero if the residual row and column
counts differ. The exact identity is

```text
per(B + zD) =
  sum over matching S subset E of
    z^|S| * (product of D entries in S)
    * (product over g of per(B_g[S])).
```

## Proof

Expand the permanent as a sum over permutations, then expand each product
using `A[i,j] = B[i,j] + zD[i,j]`. Every nonzero expanded term has a unique
set `S` of rows where its selected factor came from `zD`. Since a permutation
uses each row and column once, `S` is a matching. All remaining selected
factors come from `B`, so they match the unused rows and columns independently
inside each diagonal block. Summing those within-block choices gives exactly
the product of residual block permanents in the formula. Conversely, any
matching `S` together with one residual permutation per block forms one
permutation of the full matrix, counted once. Grouping terms by `|S|` gives
the coefficient of each power of `z`.

This proof also explains the implementation's checks: conflicting edge
subsets contribute nothing, and a block with unequal residual row and column
counts cannot complete a permutation.

## Operation bound

For block sizes `b_1,...,b_g` with `sum b_i=n`, the implementation visits at
most `2^k * sum_i 2^b_i` subset-DP states and at most
`2^k * sum_i b_i*2^b_i` DP column transitions. It also inspects at most `k`
cross-edge bits per mask and constructs residual blocks. A conservative
arithmetic/loop bound is

```text
O(2^k * (k + n*b*2^b)), where b = max_i b_i.
```

This is a bound for this explicit coefficient algorithm in scalar arithmetic
operations, with separately tracked state visits and column scans. The
prototype does not account for big-integer bit operations, allocation bytes,
or interpreter overhead, so its runtime counters are not a complete resource
certificate. It has finite caps and fails closed when a cap is reached.

When `k` and `b` are both `O(sqrt(n))`, this particular bound is
subexponential in `n`. This is a parameterized result for an already-given
block partition. The method does not find a useful partition for every matrix,
does not reduce arbitrary dense permanents, and does not establish a
subexponential algorithm for arbitrary SAT.
