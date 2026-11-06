# v2.7 finite D.4.4 geometric tile modes — scope and proof obligations

This research module implements **one finite scalar-evaluation slice** of the geometric tiling argument in [the published October 25 proof, D.4.4](https://github.com/openai/math/blob/main/preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026/build/quantitative-contraction.tex). The original D.3 packing constructor/checker are preserved unchanged from v2.6.

## Mathematical construction

For a validated D.3 packet of width `L = 2^a`, a nonzero interpolation node `t` with `i = v2(t) < a`, and a small nonnegative integer `zeta`, set `T=t+2^(a+1) zeta`. In packet position `x` (row) and `y` (column), the Cauchy kernel is

`W_xy(T) = C(T) / (C'(0) (T-(y-x)))`, where `C(T) = product_{q=-L}^{L-1}(T-q)`.

Group ports by their D.3 symbol in coordinate `i`. Retain the kernel exactly for same-group pairs. For a cross-group column tile `y=y0+2^(i+1) j`, expand

`W_xy(T) = SUM_{b>=0} [ C(T)/(C'(0)*(T-y0+x)) ] * [2^(i+1)/(T-y0+x)]^b * j^b`

modulo `2^p`. For each packet/tile/degree `b`, the column mode `L_Z(X)` is the sum of `j^b X_y` over *real* columns in that tile. Its coefficient on row `x` has a **checked lower valuation** of at least `b+1`; the mode weight is `w=b+1`.

The mode-index set is pruned by `sum_Z w_Z beta_Z < p`, with lazy polynomial-space tuple enumeration. The executable checker independently reconstructs all cross entries of the original Cauchy matrix modulo `2^p` from the mode data, validates local terms, replays D.3, and rederives rational mode coefficients and 2-adic bounds. A separate small-network oracle verifies that the **full deformed contraction** agrees with expanding the row factors into weighted mode monomials (not merely matrix entries).

These claims are **finite exact identities only**. The code also computes mode multiplicities and checks the manuscript numerical multiplicity inequality `6M/D` (where `D=L/2^i`) per instance, separately from the D.3 theorem preconditions. A successful finite equality does not establish a uniform asymptotic complexity bound.

## Important exclusions

- `zeta` is currently a bounded integer; the manuscript uses **extension-ring interpolation points**, and the code does not implement their full polynomial/Taylor-jet mode expansion.
- No tapered Hermite schedule is connected to this exact mode engine.
- No source/target-group implicit child-tensor constructor has been implemented here.
- No recursive D.4.4 contraction or bit-complexity recurrence is implemented.
- Most practical finite examples fail the manuscript's enormous-parameter eligibility conditions. The experimental mode remains explicitly outside those theorem claims.

## Usage

```bash
python -m pip install -e '.[test]'
python -m pytest -q
python scripts/validate_v27.py
veritas-eth27 construct --edges-json '[[0,0],[1,1],[0,1],[1,0]]' --a 1 --node 1 --precision 6 --output mode-cert.json
veritas-eth27 check --certificate mode-cert.json
veritas-eth27 count-tuples --weights-json '[1,2,3]' --precision 8
```

API:
- `POST /v1/research/eth/d44/modes` — construct D.3, construct finite modes, verify independently.
- `POST /v1/research/eth/d44/check` — check a separately supplied mode certificate.
- `GET /v1/research/eth/d44/status` — exact implementation scope.

**Fail-closed:** Bad certificates and resource limits return explicit errors. No production SAT/#SAT endpoint selects this experimental backend by default.
