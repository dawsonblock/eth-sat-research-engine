# v1.2 mathematical design and scope: weighted modes -> child tensor boundaries

## Semiring

Use `R=(Z/2^p Z)[z]/(z^q)` with `1 <= p <= 128`, `1 <= q <= 20`. In this truncated polynomial ring, a product vanishes if its lowest nonzero `z` degrees add to at least `q`, or if the minimum two-adic coefficient valuations add to at least `p`. Both checks use exact residue arithmetic; no numerical thresholds.

## Cauchy mode stage

At node `t`, form the paper's exact small Cauchy kernel `W_{ij}(t+2Lz)`. Group rows and columns so every nonzero constant entry is within a common group. For each degree and cross-group coefficient block, compute an exact rational rank-one decomposition `M_k = sum_a u_a v_a^T`. A mode's valuation lower bound is `min_i v_2(u_i) + min_j v_2(v_j)` over nonzero entries. This is a lower bound on **every** entry of the outer product. Drop a whole mode only when that bound is at least `p`; otherwise preserve it. Check the modular reconstruction of each kernel coefficient against the original. Rational intermediate factors can have even denominators; convert **only the fully reconstructed integral coefficient** into the modular ring.

This is **not** the paper's D.4.4 efficiently packed symbol-mode decomposition: the grouping and rank basis are small-reference choices and their ranks need not obey the claimed asymptotic bounds.

## Explicit half-wire network

Let `Y_i` be a row half-wire, `X_j` a column half-wire, with original Boolean clause factors `A(Y)` and variable equality factors `B(X)`. For each row, construct a factor whose value is

`H_i(Y_i,X) = Y_i * Z_i + (1-Y_i)*(1-Z_i)`,

where `Z_i(z) = sum_{j in the same packet} W_ij(t+2Lz) X_j`.

Each factor is a polynomial-valued table over its actual Boolean ports. The complete contraction `sum_{X,Y} A(Y) B(X) prod_i H_i` is the jet of the original deformed expression, reduced in `R`.

## Child tensor recursion

Partition **factor vertices**, not half-wire values. For factor-subset `S`, define `boundary(S)` as the Boolean ports touched both inside and outside `S`. The child tensor is

`T_S(b) = sum_{all internal assignments} prod_{f in S} f(x|ports(f))`.

For disjoint factor subsets `S=L union R`, take the union `U = boundary(L) union boundary(R)` and compute

`T_S(b) = sum_{u in {0,1}^U : u|boundary(S)=b} T_L(u|boundary(L)) * T_R(u|boundary(R))`.

This identity holds because all variables internal to each child have already been summed out and all shared interface variables retain a consistent assignment. The implementation represents `T_S` explicitly as a table indexed by its boundary variables and uses deterministic balanced separator search with hard caps on boundary width, table sizes, work assignments, and wall-clock time. At the root, the boundary is empty, yielding the scalar polynomial jet. The recursion has exponential worst-case dependence on boundary width and does **not** reproduce D.4.4's specialized low-width child-network theorem.

## Verification

`tests/test_v12_weighted_children.py` and `scripts/validate_v12.py` test complete jets against the independent exhaustive half-wire calculation at random nodes, precision and group spans, including unsatisfiable and zero-occurrence cases. Negative tests force resource-limit exits. The API reports `RESEARCH_CROSS_CHECKED` only when this independent oracle actually runs and agrees; it otherwise reports `RESEARCH_ONLY`, never a proof of subexponential complexity.

## Reproduction commands

```bash
python -m pip install -e '.[test]'
python -m pytest -q
python scripts/validate_v12.py
veritas-cli cnf examples/example.cnf --weighted-children --packet-size 2 --node 1 --jet-order 4 --precision-bits 12
```

The research service is local-only; **no remote authentication or process sandbox is provided**. Never deploy the API to a public network without an external isolation and authentication layer.
