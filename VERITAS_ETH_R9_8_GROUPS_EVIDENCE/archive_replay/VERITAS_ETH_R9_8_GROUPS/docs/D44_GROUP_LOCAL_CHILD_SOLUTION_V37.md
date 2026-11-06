# D.4.4 group-local child tensor solution: finite reference implementation

## Original mathematical definition
Source: OpenAI/math, `preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026/build/quantitative-contraction.tex`, subsection **The child networks and their descriptions** (manuscript Appendix D.4.4). Review and pin a source commit before claiming source-faithful reproduction.

For a fixed global mode exponent tuple `beta`, group `g` and packet `P`:

1. Keep original vertices in group `g` with their original ports on one side of a new bipartite child network.
2. Put one new tensor vertex per relevant packet on the opposite side.
3. Each original half-port owned by `g` is one **child edge**, connecting its old vertex to its new packet vertex.
4. Evaluate a packet tensor by taking the coefficient of **targeted** formal mode powers from the product of the packet's group-`g` row factors. Multiply the resulting coefficient by all **source** linear forms raised to the exponents in `beta`.
5. There are no geometric mode-index edges *inside* an individual fixed-beta child. Mode exponents are frozen metadata; cross-group coupling survives only in the outer sum over `beta`.

Let `R(P,g)` and `C(P,g)` be row/column half-ports for this packet/group, and `M_{P,g}^{in}` and `M_{P,g}^{out}` the target/source mode indices. Over the exact extension-jet ring:

```
  A_x = (1-Y_x) + (2*Y_x-1) * sum_{y in C(P,g)} W[x,y](T)*X_y
  B_x(Z) = (2*Y_x-1) * sum_{m in M_in} c[x,m](T)*Z_m
  K[P,g,beta](Y_g,X_g)
     = coefficient_(Z_m**beta_m for m in M_in) product_(x in R(P,g)) (A_x+B_x(Z))
       * product_(m in M_out) L_m(X_g)**beta_m
```

The full parent identity is the exact congruence

```
  F(T) = sum_(beta: sum_m weight_m * beta_m < p_t)
             product_(g = 1..r) Contract(Child[g,beta])  (mod 2**p_t).
```

The coefficient extraction works because all targeted mode factors are local to their target group, while each source form `L_m` depends only on bits in its source group. This is an **exact separation**, not an approximation.

## Why this construction is different from v3.5/v3.6

- v3.5 counted mode bonds in child scopes and could not claim an `M/8` child bound.
- v3.6 built entire Boolean-multilinear packet coefficient tables, but without selecting a global mode tuple and specializing to group-local packet tensors.
- This reference fixes `beta` and keeps only group-local half-port wires. It counts original half-ports on both sides precisely once across all children. The resulting child wire count for group `g` is `number of original half-ports owned by g`, *not* that count plus number of incident mode variables.

Under **all** the manuscript D.3 hypotheses with `r=64`, its packet-symbol load bound implies at most `3M/64` ports on each side, hence at most `6M/64=3M/32<M/8` edges per child. The implementation's scaled examples use `r=2`; passing a small finite example does **not** prove the theorem or validate the full-size parameter regime.

## Implemented exactly in the finite reference

`src/veritas/research/eth_d44_child_reference/children.py`:

- Validates the D.3 packing and geometric mode certificate; obtains local coefficients and weighted modes from existing v3.1 components.
- Enumerates global nonnegative exponent tuples with weighted sum strictly less than precision.
- Computes each group-local packet tensor by sparse targeted-mode coefficient extraction (no full global mode-index factor table).
- Substitutes source linear forms after target coefficient extraction.
- Defines the child incidence graph with one edge per owned original half-port; original vertices and packet vertices lie on opposite sides.
- Calculates each child's exact finite contraction and checks the outer-sum identity against independent direct Cauchy half-edge enumeration.
- Rejects altered proof artifacts, unexpected input graph incidences, and computations exceeding finite budgets.

The child-entry calculations are lazy and carried out at fixed finite precision. The reference contraction still sums group-local Boolean assignments exhaustively, so it may require exponential time. It is not an implementation of the manuscript's recursive reentry into the same algorithm.

## Still required for an authentic subexponential implementation

1. Replace finite leaf/group enumeration with recursive contraction of the implicit child-network graph, retaining the *creation-time* tensor description and precision for all inherited tensors.
2. Implement the full tapered-Hermite node/precision schedule (`p_t`, `q_t`, `alpha`, residue-field interpolation nodes), and do not substitute the toy scaled node/precision values.
3. Check all manuscript preconditions: `r=64`, degree, symbol load, packet bound, `2L<=Delta`, child edge counts, and exact ring/bit complexity.
4. Verify inherited entry-evaluation costs on every recursive level and prove (rather than experimentally extrapolate) the mode tuple and total recurrence bounds.
5. Audit the pinned manuscript version against the implementation. Formal source-to-code correspondence has not been demonstrated.

**Scope:** An exact finite constructive/reference solution for the missing *child-tensor definition and factorization identity*. No claim that ETH has been refuted by this implementation, nor that its runtime is subexponential.

## Reproduce

```bash
python -m pip install -e '.[test]'
veritas-eth37 construct --n 2 --clauses-json '[[1,2]]' --output d44-child.json
veritas-eth37 check --certificate d44-child.json
pytest -q tests/test_v37_d44_group_local_children.py
```
