# Exact Appendix D.4.3 Cauchy-deformation reference (v0.8.0)

## Paper correspondence

Primary source: OpenAI, *The Exponential Time Hypothesis is False*, 25 October 2026, Appendix D.4.3, **equations (76)–(77)**. The local kernel is reproduced, rather than invented, and all calculations here use exact rational arithmetic (or valid residues of rationals whose denominators are odd).

For packet width `L=2**a` with `L in {1,2,4,8}` define

```
S = [-L, ..., L-1]
C(T) = PRODUCT_{t in S} (T-t)
W[x,y](T) = C(T) / (C'(0) * (T-(y-x)))
```

The apparent quotient is a polynomial because `(y-x)` belongs to `S` and thus divides `C(T)`.

For an `M`-wire bipartite network with row-side tensor product `A(Y)` and column-side product `B(X)`, define

```
F(T) = SUM_{X,Y in {0,1}^M} A(Y) B(X)
                    PRODUCT_{row slot x} l_{Y[x]}( SUM_{column slot y} W[x,y](T) X[y] ),
l_0(z) = 1-z, l_1(z) = z
```

Entries of `W` between separate packets are zero. This tiny reference groups consecutive wires into packets of size at most `L`; unused packet slots are padded with zero-valued column bits. Its CNF networks have clause vertices on the row side and variable equality vertices on the column side. **This is the exact local formula but not the paper's collision-packing choice of packets.**

### Checked mathematical identities

1. `W(0) = I`, therefore `F(0)` equals the original exact contraction.
2. At every integer node `t in S`, each row has nonzero entries only when `y-x=t` (within a packet), enabling independently evaluated special-node checks.
3. `degree W[x,y] = 2L-1` and `degree F <= M*(2L-1)`.
4. Let `alpha=2L`. The coefficients of `W(t+alpha*z)` are **2-adic integers**. They need **not** be ordinary integers: fractions like `49/9` are valid, because their denominator is odd and invertible modulo `2**p`. Requiring literal integer coefficients would reject a correct kernel.
5. `F(t+alpha*z)` is computed separately in the truncated residue ring `Z/(2**p)[z]/(z**jet_order)` and cross-checked against an independently shifted full exact rational polynomial. Both methods apply modular inverses to odd denominators, never approximate rounding.

### Algorithms and output

- `research/cauchy_deformation.py`: exact kernel generation, exact polynomial computation by direct half-edge enumeration, special-node oracle, shifted 2-adic jets, coefficient valuations.
- `POST /v1/research/cauchy-deformation`: accepts `n`, `clauses`, `packet_size`, `max_edges`, `node`, `precision_bits`, `jet_order`, `timeout_s`, `cross_check`.
- CLI: `veritas-cli cnf examples/example.cnf --cauchy-deformation --packet-size 2 --node 0 --precision-bits 8` (needs at most 6 literal occurrences).
- The `rational_coefficients` JSON array is made of exact fraction strings such as `"19/4"`; do not attempt floating point coercion.
- `shifted_jet.coefficients_mod_2_power` is an array of decimal residue strings, not an exact ordinary-integer Taylor expansion.
- `coefficient_valuations` reports `ZERO_MOD_PRECISION` for a zero residue, not an assertion that the original integer is zero.

### Explicit constraints

- Strictly at most 6 wires and small dense CNF tensors; `L=8` is additionally capped to 3 wires in the HTTP API.
- Exponential `4**M` assignment pairs *before zero-factor pruning*. Larger cases are intentionally rejected.
- Rational coefficient growth can be steep; the API is a bounded, local-only research tool.
- A correct local deformation does not imply that the full recursive ETH contraction algorithm is implemented.
- Unimplemented: manuscript-specific packet collision packing, 2-adic weighted cross-group mode decomposition, child tensor creation and recursion, polynomial-space bound, finite ring Hermite recovery, end-to-end asymptotic performance.
- No Lean theorem statement or its dependency closure has been compiled by this release.

### Verification

```bash
python -m pip install -e '.[test]'
python -m pytest
python scripts/validate_v08.py
python scripts/verify_manifest.py
```

## Sources

- OpenAI manuscript: https://github.com/openai/math/blob/main/preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026/build/quantitative-reduction.tex
- OpenAI Lean scope: https://github.com/openai/math/blob/main/lean/docs/378.md
- For exact D.4.3 equations (76)–(77), see source manuscript appendices, not the weaker Lean scope description.


## v0.9.0 addendum

The previously listed finite-ring Hermite recovery is now implemented as a **bounded reference** (`research/hermite_ring.py`), with rational recovery weights, explicit sufficient precision guard bits and small nonzero-node jet tests. A **separate node-matching** Cauchy mode expansion with 2-adic/z-order-certified pruning is implemented in `research/cauchy_modes.py`. Neither implements the manuscript's actual collision packing, low-rank D.4.4 group mode count, recursive child networks, or D.5 asymptotic schedule. See `docs/MODES_HERMITE_V09.md`.
