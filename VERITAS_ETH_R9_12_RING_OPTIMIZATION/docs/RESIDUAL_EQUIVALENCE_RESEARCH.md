# Residual equivalence research (Exact Symbolic State Compression)

Engineering hypothesis (not a complexity theorem): **#SAT cost is driven by the
number of distinct residual problems** \(R(a)\) after partial assignment \(a\),
not by raw \(2^n\) assignment enumeration.

## Definition

For CNF \(F\) and partial assignment \(a\) on a subset of variables:

\[
a \sim b \iff R(a) = R(b)
\]

where \(R(a)\) is the count-preserving residual CNF after fixing literals in \(a\),
unit propagation, and variable reindexing (canonical SHA-256 fingerprint).

Then:

\[
\#F = \sum_{[r]} m(r)\,\#r
\]

with multiplicity \(m(r)\) of prefix assignments landing in residual class \(r\).

## Prototype module

| Operation | Module |
| --- | --- |
| Canonicalize | `residual_after_assignment`, `CNF.digest()` |
| Merge | `prefix_residual_table` (multiplicity buckets) |
| Factor | existing `structure_aware_count` component product |
| Eliminate | existing `gf2_xor_*`, `count_preserving_preprocess` |
| Verify | `exhaustive_count`, `exhaustive_mixed_count`, `count_dag` checker |

Code: `veritas.research.residual_equivalence` — `count_with_residual_memo`,
`prefix_residual_table`.

### Block example

\(F=(x\lor z)\land(y\lor z)\), prefix \((x,y)\): four assignments, **two** residual
fingerprints (three share forced-\(z\), one leaves \(z\) free) →
\(\#F = 3\cdot 1 + 1\cdot 2 = 5\).

```bash
pytest tests/test_residual_equivalence.py -q
```

## Connection to existing R9 / archive stack

| Existing piece | Relation |
| --- | --- |
| `boundary_dp` cache on factor signatures | Same *idea*; factor network not CNF residual |
| `count_dag` / weighted DAG | Certificates already carry residual formulas — verifier rebuilds \(R\) |
| `eth_recursive_bonds_v33` | Mode-level residual reuse + `cache_hits` |
| R9.13 `anthropic_signed_contraction` | Bit-cost of one-level rewrite — orthogonal economics |
| `cost_ledger` / `tree_ledger` | Measure memo reuse vs recursion (observational) |
| `gf2_xor_count` | Polynomial **elimination** class (rank), not Shannon residual |

**Upgrade path (research):** emit residual-equivalence statistics from recursive
counting (distinct \(R\), multiplicities, reuse ratio) alongside `tree_ledger`,
and compare growth curves on independent → coupled → adversarial families.

## Three parallel experiments (next)

1. **Residual-function equivalence classes** — `benchmarks/v34_residual_growth.py`
   (distinct residuals vs \(n\), clauses) on structured + random small CNFs.
2. **Algebraic compression** — extend R9.13 coefficient extraction with sparse
   merges when child jets share identical support (`manuscript/sparse_query.py`).
3. **Recursive merge + verify** — plug residual memo keys into boundary DP
   signature (`boundary_dp.py` comment at relabel-invariant signatures).

## Hard question (explicit)

If \(2^{96}\) assignments collapse to \(10^4\) distinct residuals on **your**
networks but stay near \(2^{96}\) on adversarial CNFs, we learn **instance
structure**, not universal subexponential worst case. The prototype is for
measuring that gap, not claiming a polynomial bound.
