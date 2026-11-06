# v0.9.0: valuation-safe local mode expansion and finite-ring Hermite recovery

## What is implemented

Two **bounded reference algorithms** add rigorously testable components to the existing v0.8 source-derived Appendix D.4.3 Cauchy deformation. The complete ETH-breaking recursion is **NOT** implemented. There is no time-complexity improvement guarantee.

### (1) Node-matching cross-group expansion

File: `src/veritas/research/cauchy_modes.py`.

At grid node `t in S`, the Cauchy kernel satisfies `W_ij(t)=0` unless `j-i=t`. Group each row slot with its matched column (if present) and give unmatched columns separate groups. Consequently, every inter-group kernel coefficient vanishes at `z=0` in `W_ij(t+2L*z)`.

For row bit `Y_i`, write its linear factor as `l_{Y_i}(local_i + sum_j cross_ij)` with `l_0(x)=1-x` and `l_1(x)=x`. Exactly expand the product by selecting either a local factor or one cross mode per row. The algorithm computes the entire truncated jet modulo `2^p` and omits a branch **only** when at least one invariant holds:

- Its accumulated lower bound on 2-adic valuation is at least `p`. Every other factor is 2-adically integral, so its contribution is 0 modulo `2^p`.
- Its accumulated lower bound on polynomial degree in `z` is at least `jet_order`; it is zero in the truncated polynomial ring.

The lower bounds are computed from exact rational kernel coefficients with odd denominators; no float threshold is used. A second implementation evaluates the Cauchy jet by multiplying the full row factors without mode expansion, and randomized differential tests check agreement.

**Very important:** The grouping used here consists of node-matched **individual slots** and is *not* the paper's high-level collision-packed symbol grouping, low-rank cross-tiles, or bounded-mode factorization. All `X,Y` half-edge assignments are still explicitly enumerated (exponential worst case). This supports valuation-pruning logic only, not the full paper's mode-count/runtime theorem.

### (2) Precision-aware Hermite reconstruction

File: `src/veritas/research/hermite_ring.py`.

Given an upper bound `D` on the polynomial degree and local node jets `J_{t,j}=[z^j]F(t+alpha*z)`, compute exact rational weights `w_{t,j}` such that

```
F(0) = sum_{t,j} w_{t,j} * J_{t,j}
```

for every polynomial of degree at most `D`. The weights come from an exact rational confluent Vandermonde system, not numerical regression.

When only the residues `J_{t,j} modulo 2^P` are known, multiplying by rational recovery coefficients may LOSE powers of two. The required **sufficient guard bits** are

```
g = max(0, max_{nonzero weights w}(v2(denominator(w))-v2(numerator(w))))
```

The input precision must satisfy `P >= p+g` to recover `F(0) modulo 2^p`. Compute `sum(2^g * w * J) modulo 2^(p+g)` using only odd-denominator modular inverses; divide the sum by `2^g`. Reject a nondivisible result, insufficient precision, invalid samples, or singular systems.

In the end-to-end Cauchy endpoint, local jets are calculated at **nonzero** nodes, avoiding a trivial direct read of `F(0)`. The resulting count residue is compared against an independent original tensor contraction. The endpoint has hard wire and degree bounds. The algorithm is not the manuscript's full Lemma D.5 schedule (node multiplicities/precision accounting for the asymptotic recursion are not implemented).

### Caution about proof status

- Randomized or independent test agreement is evidence, **not** an asymptotic algorithm proof or a formal proof of the upstream paper.
- Guard-bit safety is mathematically justified for the stated linear reconstruction and integral target; the submitted jets are not intrinsically authenticated.
- This code has not compiled the original Lean theorem or reproduced its dependency closure.
- `COUNT_RESIDUE` means a residue modulo `2^p`, not automatically the full count. When p>n and the count is bounded by 2^n, exact recovery is possible; the current endpoint still names the result a residue to avoid ambiguous guarantees.

## Usage

```bash
python -m pip install -e '.[test]'
python -m pytest
python scripts/validate_v09.py
veritas-api
```

Then visit `http://127.0.0.1:8080` or the interactive API docs at `/docs`.

### API endpoints

`POST /v1/research/cauchy-modes`

```json
{"n":3,"clauses":[[1,2],[-2]],"packet_size":2,"node":1,"precision_bits":8,"jet_order":6,"cross_check":true}
```

`POST /v1/research/cauchy-hermite`

```json
{"n":3,"clauses":[[1,2],[-2]],"packet_size":2,"precision_bits":8,"cross_check":true}
```

Both return audited, explicitly research-only data. Production proof/check statuses remain separate.

### CLI

```bash
veritas-cli cnf examples/example.cnf --cauchy-modes --packet-size 2 --node 1 --jet-order 6 --precision-bits 8
veritas-cli cnf examples/example.cnf --cauchy-hermite --packet-size 2 --precision-bits 8
```

## Main remaining work

1. Construct and validate the **actual** collision-packing schedule with its quantitative collision bounds.
2. Derive the manuscript's low-rank, symbol-grouped valuation modes and check the exact child-tensor identity.
3. Add the paper's recursive contraction and entry representation, including complexity accounting.
4. Implement the precise finite-ring recovery schedule and Lean correspondence, then independently reproduce all key theorems.
5. Determine practical crossover through meaningful benchmarks rather than substituting asymptotic notation for evidence.

Primary paper: https://github.com/openai/math/blob/main/preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026/build/quantitative-reduction.tex
