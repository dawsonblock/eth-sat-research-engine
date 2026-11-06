# v1.0: Exact separator recursion and coefficient-wise grouped Cauchy modes

**Status: bounded, executable mathematical research. Not the October 25 manuscript's asymptotic algorithm.**

## 1. Exact recursive factor-separator contraction

`src/veritas/research/recursive_separator.py` recursively splits factor vertices into two groups. Let `E_cut` be the edges with one endpoint on each side. Fixing each `b in {0,1}^{E_cut}` leaves two independent factor networks, so

    Z(G) = sum_{b in {0,1}^{E_cut}} Z(G_left | b) * Z(G_right | b).

This is an exact identity over the integers and modulo any requested positive modulus. The implementation uses deterministic exhaustive balanced factor bipartition search, choosing minimum cut cardinality then minimum repeated cut-edge incidence and lexicographic tie breaking. It labels **incident_collisions** as the count of pairs of cut edges meeting the same factor. This is a *local heuristic diagnostic*, **not** the paper's specialized packet collision packing theorem or collision bound.

The recursive evaluator never silently truncates a separator assignment. A global time budget, recursion-call cap, maximum cut width, maximum leaf free-edge count, and factor/edge caps are enforced. Over-budget computation raises `ResourceLimit`, and the API returns `UNKNOWN` instead of a count. It also supports exact residues modulo `2^p`.

### Proof of reference identity

Each global Boolean edge assignment restricts uniquely to its bits on `E_cut`, `E_left`, and `E_right`. For fixed `b`, the product of all tensor factors splits into the product of the left and right factor products because no unfixed cross edge remains. Distributing the finite sums gives the identity above. The program checks at every recursive call that an edge with exactly one incident factor inside the subproblem has been fixed by an ancestor, so no boundary bit can be dropped.

**No speed guarantee.** A large balanced separator incurs `2^cut_width` branches; choosing minimum cut does not control the recursive complexity as in the ETH theorem. Worst-case complexity remains exponential. The algorithm does not create the manuscript's low-width mode-indexed child tensors and does not prove polynomial space for arbitrarily large inputs (it caches intermediate subproblems).

### Reproducible API example

    POST /v1/research/separator-contract
    {"n":3,"clauses":[[1,2],[-2,3]],"cross_check":true}

The response differentiates `EXACT_COUNT`, `COUNT_RESIDUE`, and `UNKNOWN` and records the measured number of recursion calls, separator assignments, leaf assignments, and maximum separator width. Independent exhaustive enumeration is available only with <=16 wires and `cross_check=true`; disabling the oracle marks the result `RESEARCH_ONLY`.

## 2. Exact rational grouped Cauchy rank modes

`src/veritas/research/grouped_cauchy.py` starts from the **same exact rational Cauchy kernel** `W_ij(T)` already implemented in v0.8 and its integer-shifted jet `W_ij(t+2L*z)`. At grid node `t`, every packet-local nonzero constant coefficient connects only `j-i=t`. Therefore, the group construction forces a matched row `i` and column `j` into the same group.

For each cross-group pair `(g,h)` and each Taylor order `k`, form the coefficient block

    A_(g,h,k) = [ [z^k] W_ij(t+2L*z) ]_(i in g, j in h).

`A_(g,h,0)=0` for every cross-group block. For every nonzero higher coefficient block, deterministic exact rational Gaussian-style pivot elimination constructs vectors `u_r` and `v_r` such that

    A_(g,h,k) = sum_(r=1)^rank u_r * transpose(v_r).

After every factorization, the code reconstitutes each coefficient and checks exact equality. Then the complete grouped kernel is used for exhaustive half-edge jet evaluation. The resulting coefficient residues modulo `2^p` are cross-checked against `shifted_cauchy_jet_mod` in the unchanged v0.8 implementation. Fractions use exact numerators/denominators and odd-denominator modular inversion. There is no floating-point rank threshold.

### Limitations that affect claims

- Factorization is performed separately **for each Taylor coefficient** over `Q`. It is not the original paper's weighted symbol-group mode factorization in the two-adic truncated ring.
- The evaluator still visits up to `4^M` half-edge assignments, even when the rank decomposition has only a few modes. The decomposition does not itself accelerate the complete count.
- Grouping is a deterministic node-matched reference, not a verified collision-packed schedule satisfying the source's quantitative collision bound.
- The stated `max_coefficient_rank` describes only the explicit finite coefficient blocks; it is not a bound on paper-specific mode monomials.

### Example

    POST /v1/research/grouped-cauchy
    {"n":3,"clauses":[[1,2],[-2,3]],"node":1,
     "packet_size":2,"group_span":1,"jet_order":5,
     "precision_bits":10,"cross_check":true}

`jet_coefficients_mod_2_power` are residue coefficients, not an exact model count unless a separate certified recovery process and adequate precision establish the count.

## 3. Validation and scope

- `PYTHONPATH=src python -m pytest`: inherited and new tests.
- `PYTHONPATH=src python scripts/validate_v10.py`: deterministic exact counting, modular and Cauchy jet differential tests.
- `PYTHONPATH=src python benchmarks/v10_separator.py`: tiny smoke benchmark, not an asymptotic timing claim.
- Every new API result is logged in the local hash-chained audit store; localhost-only protection remains necessary.

Main future work: source-correct D.3/D.4.4 packet collision packing, valuation-weighted symbol-group decomposition, proof of child network identity and complexity, and source D.5 tapered finite-ring recovery. Formalized theorem and manuscript's stronger runtime must remain separately identified.

Source: https://github.com/openai/math/blob/main/preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026/build/quantitative-reduction.tex
Formalization scope: https://github.com/openai/math/blob/main/lean/docs/378.md
