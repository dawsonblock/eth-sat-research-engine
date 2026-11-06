# Shared linear summaries: the counting and construction halves

`src/veritas/research/eth_counting_v39/` implements `sec:counting` and
`sec:construction` of the pinned OpenAI preprint — the polynomial-construction
half of the algorithm. The older `eth_recursive_contraction_v39` package
implements the other half, `app:tensor`.

Both are finite references. Neither establishes the paper's subexponential
running-time bound.

## What is implemented

| Module | Paper object | What it does |
|---|---|---|
| `parameters.py` | `eq:parameter-QR`, `lem:incidence-parameters` | The schedule `r, Q, R, tau, epsilon, D` and the interval `I`, with every numerical hypothesis evaluated exactly |
| `auxiliary.py` | `subsec:incidence-layout`, `lem:swaps-matrix`, `lem:swaps-support`, `eq:swaps-row` | The label set `B = ([r]^Q)^2`, the swaps `Pi_s`, `V_0`, `W_0`, `f_I`, the matrix `M_0`, the measurements `C^B`, and the rows `P_u(T)` |
| `labels.py` | `lem:incidence-labels` | The deterministic schedules `a_v, d_f`, chosen greedily to minimise `Phi/(M(b+w)) + Xi/(Qn)` |
| `embedding.py` | `subsec:embedding` | `h` copies of `B`, the placement `c(f,v)`, the rows `P_{f,v}`, the group matrices `C_{t,g}` |
| `layout.py` | `def:layout` | Replays all five required properties, including the kernel condition |
| `separation.py` | `lem:measurement-separation` | The group-sum identity `Z_E = sum_y prod_g Sigma_g(y)` |
| `taylor.py` | `lem:boolean-differences`, `eq:full-taylor-sum` | `H(t+z) mod z^J` from fixed substitutions `X = 1_U` and restrictions `x_i = 1` |
| `count.py` | `eq:general-count-polynomial`, `eq:hasse-order` | Solves the rational Taylor system for the coefficients of `H` and returns `H(0)` |

`instance.py` supplies the factor representation: general rational polynomials
over a scope, the clause indicator `Phi_e = 1 - prod_v (1 - L_{e,v})`, and the
paper's normalisations (drop tautologies, collapse repeated literals, one
dummy clause per unused variable).

## The pipeline

```python
from veritas.research.eth_counting_v39 import count_cnf

result = count_cnf([[1, 2], [-1, 3], [2, -3]], n=4, r=2, Q=2, R=2)
assert result.value == 6          # exhaustive enumeration agrees
```

Steps, in the paper's order:

1. **Schedules** (`lem:incidence-labels`). Fix `a_v` and `d_f` one at a time,
   choosing the value that does not increase the conditional expectation of
   `Phi/(M(b+w)) + Xi/(Qn)`.
2. **Auxiliary rows** (`eq:swaps-row`). `M_0 = V_0 f_I(W_0)` is expanded in
   the commuting swaps by a Walsh--Hadamard transform of `j -> f_I(j)`. Only
   `|S| <= R-1` coefficients are nonzero, which is exactly `lem:swaps-support`.
   The rows are `P_u = delta_u + M_0[u,y](phi_{u,y}(T) - 1)`.
3. **Embedding** (`subsec:embedding`). Place each incidence in a copy at its
   label, then push rows and measurements onto the original variables by
   summing the coefficients of positions holding the same variable.
4. **Design check** (`def:layout`). Verify the kernel condition
   `C_{t,g} xi = 0 => <P_{f,v}(t), xi> = 0` by exact row-space containment.
5. **Taylor data** (`eq:full-taylor-sum`). At each `t`, sum
   `(-1)^{|E|-|U|} Z_{t,E,U}(z)` over `|E| <= q`, `U` a subset of `E`, with
   values in `Q[z]/(z^J)`.
6. **Recovery** (`eq:hasse-order`). Solve the `QJ` linear equations
   `[z^j] H(t+z) = data` for the coefficients of `H` and read off `H(0)`.

## What the finite reference establishes

- **Correctness.** For every bounded-occurrence CNF the pipeline executes, the
  returned integer equals exhaustive enumeration. This is checked on a battery
  of fixed cases, on randomised cases, and per component: the separation
  identity against a direct sum, the Taylor data against a direct expansion,
  the Boolean-difference identity against direct substitution, and the
  auxiliary rows against the paper's worked Remark.
- **Formula conformance.** `parameters.theorem_parameters_from_lambda` computes
  `eq:parameter-QR` at theorem scale (`lambda = 2**34`) and every numerical
  hypothesis of `lem:incidence-parameters` holds there.

### Degenerate inputs

Three cases are outside the paper's `n >= 20` regime and are handled
explicitly rather than rejected:

- **`d = 0`.** A CNF with no clauses, or only tautologies, has a constant
  factor product. Then `d_H = 0`, `q = 0`, `J = 1`, and the count is `2^n`.
  `FormParameters` accepts `d >= 0`; requiring `d >= 1` would break these
  instances even though their counts are trivial.
- **`n = 1`.** `lambda = ceil(log2 1) = 0`, so the paper's `tau = 1/(r*lambda)`
  is undefined. `tau` and `epsilon` are cost parameters that never enter the
  counting identity, so the scale is clamped to one instead of dividing by
  zero. `theorem_parameters` reports `INCONCLUSIVE_PARAMETERS` for `n = 1`
  rather than raising.
- **Empty clause.** An empty clause gives `constant_zero`, and `count_instance`
  returns zero without building a design.

A separate soundness point: the theorem-scale balance report compares
`2Qr^2` and `2(b+w)D^2` against `lambda - 1`, not `lambda`, because
`lambda = ceil(log2 n)` only guarantees `n > 2**(lambda-1)`. Comparing against
`lambda` would accept parameter tuples for which `2Qr^2 > n` still holds.

## What it does not establish

- **The running-time bound.** At the sizes a finite reference can execute
  (`n <= 6`, `r = 2..3`, `Q <= 3`), the balance hypotheses
  `2(b+w)D^2 <= M` and `2Qr^2 <= n` fail, and `R >= 32` / `6R <= Q` are far
  from satisfied. `FormParameters.check()` reports exactly which fail, and
  `CountingResult.layout['cost_hypotheses_hold']` is usually `False`. The
  counting identity does not depend on those hypotheses; only the cost
  estimate does.
- **Uniform applicability.** Nothing here proves that the schedules,
  the `M_0` support bound, or the measurement count hold for every input.
  Each certificate is an instance check.
- **Space.** The pipeline materialises `D`-sized arrays per copy and enumerates
  restriction pairs; it is not the paper's polynomial-space traversal.

## Verification

```sh
PYTHONPATH=src python -m pytest -o addopts="" -q tests/test_counting_v39.py
PYTHONPATH=src python scripts/validate_counting_v39.py
```

The script prints a JSON report with every case's count against enumeration,
one full `def:layout` certificate, and the theorem-scale parameter schedule.

## Naming

`eth_counting_v39` covers `sec:counting` and `sec:construction`. It does not
replace `eth_recursive_contraction_v39`, which covers `app:tensor`; the two
packages implement different halves of the same paper and share no state.
