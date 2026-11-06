# v0.7 split-wire deformation: mathematical specification and exact scope

## Definition

Let `G` be a Boolean tensor network with an edge `e` connecting two tensor ports. Replace each original wire bit by two independent **half-edge** bits `a_e` and `b_e`. Introduce the coupling matrix

```
             b=0  b=1
    a=0        1    T
    a=1        T    1
```

Equivalently `K_T(a,b) = 1 if a==b else T`.

The polynomial associated to the network is

```
D_G(T) = sum_{a,b in {0,1}^E} [product_v T_v(bits incident to v)]
                                  * product_e K_T(a_e,b_e).
```

This has degree at most `E`, the number of wires. Every coefficient is an exact integer (or a residue in `Z/(2**p)Z` if explicitly requested). For integer tensors, each coefficient is the sum of tensor contributions from half-edge assignments with **exactly that many mismatched wires**. It is not a probability distribution, nor a clause-violation polynomial.

### Three exact invariants

1. `D_G(0) = contract(G)`: at `T=0` the coupling forces `a_e == b_e` and restores the original wire identification.
2. `D_G(1) = product_v sum_{local bits} T_v(bits)`: at `T=1` the coupling is identically one and all tensor vertices become independent.
3. `D_G(-1) = product_v sum_{local bits} (-1)**(popcount(bits)) * T_v(bits)`: because `K_-1(a,b) = (-1)**(a+b)`, the interaction is a rank-one outer product.

The two factorized-node values are computed by a path **independent** of the polynomial-semiring bucket eliminator. A fourth oracle enumerates all `4**E` assignments to half-edges and directly constructs the histogram for small networks. For CNF-derived networks the degree-zero coefficient is also cross-checked against independent variable enumeration where feasible.

Integer finite differences independently recover `D_G(0)` from `D_G(1),...,D_G(E+1)` as a further algebraic identity. This reconstruction gives **no computational advantage**: evaluating the nonzero nodes generically is expensive.

### Method

`research/wire_deformation.py` constructs a new factor graph with `2E` half-edge variables, original vertex tables, and `E` two-port coupling tables. It performs polynomial-semiring bucket elimination with a deterministic min-fill heuristic. All products have degree at most `E` and may be reduced modulo `2**p`. Only products provably zero under that exact quotient ring are discarded. No floating-point approximation is used.

By contrast, the paper's *Cauchy deformation* produces specially constructed interactions and uses valuation-based mode pruning to obtain an asymptotic recurrence. **Neither this construction nor the ETH tensor recurrence is implemented here**. The v0.7 deformation is a testbed for polynomial identities and cross-check infrastructure, not a faithful paper reproduction or asymptotic solver.

### Resource, status, and ambiguity

- Method bounds: `max_edges <= 12`, default 10, `max_table_entries <= 65,536`, default 8,192; timeout <=30 seconds.
- The API also bounds declared variables to 40 and original literal occurrences to 12; independent direct enumeration only happens with `E <= 7`.
- Endpoint `/v1/research/wire-deformation` accepts `n`, `clauses`, `precision_bits` (optional 1..64), `max_edges`, `max_table_entries`, `timeout_s`, `cross_check`.
- `coefficients` are JSON decimal **strings**; under modular mode they are **residues**, not exact integers.
- Since the CNF solution count lies in `[0,2**n]`, the constant coefficient uniquely determines that count from its residue modulo `2**p` only when `p > n`.
- Cross-checking an algebraic invariant alone does not independently certify the entire coefficient vector. `RESEARCH_CROSS_CHECKED` is used only when a separate exhaustive CNF count or full half-edge histogram agrees.
- Do not expose this network service publicly. It has no remote authentication or OS-level solver worker isolation.

### Reproducible local tests

```bash
python -m pytest tests/test_wire_deformation.py tests/test_v07_api.py
python scripts/validate_v07.py
python scripts/verify_manifest.py
```

Expected from seeded validation: 250 full small-network histogram comparisons, and 750 modular coefficient-vector comparisons. These are **small example checks**, not evidence for the ETH theorem.

### Upstream reference

OpenAI (2026), *The Exponential Time Hypothesis is False*, October 25 manuscript:
https://github.com/openai/math/tree/main/preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026

Formalized theorem description:
https://github.com/openai/math/blob/main/lean/docs/378.md

Neither the preprint nor its Lean repository is embedded or claimed rebuilt in this archive.
