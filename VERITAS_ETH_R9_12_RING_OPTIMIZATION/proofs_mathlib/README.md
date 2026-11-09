# Mode-tuple count and enumeration cost (Lean 4.35.0 + Mathlib v4.35.0)

Separate from the 41-module core-Lean gate in `proofs/`. Run
`bash scripts/check_mode_count_lean.sh`; it builds, rejects `sorry`, and
requires every listed theorem to depend only on `propext`,
`Classical.choice` and `Quot.sound`.

## Proved

| Theorem | Statement | Paper label |
| --- | --- | --- |
| `mem_enum`, `nodup_enum` | `enum ws r` lists exactly the tuples with `∑ wᵢβᵢ < r`, once each (all `wᵢ ≥ 1`) | `eq:tensor-mode-budget` |
| `length_enum_le_product` | count `≤ e^{θr} ∏ (1 - e^{-θw})⁻¹` for every `θ > 0` | generating product |
| `length_enum_le` | if at most `m` weights equal any value, count `≤ exp (π √(2mr/3))` | `eq:tensor-partition-count` |
| `count_weight_le`, `mode_multiplicity` | distinct `(packet < P, tile < 2^(i+1), b)` modes of weight `b+1`: at most `P·2^(i+1)` per weight; with `P·L ≤ 3M` and `D·2^i = L`, `count·D ≤ 6M` | `eq:tensor-mode-multiplicity` |
| `paper_tuple_count` | with `p·u ≤ C·M·D` as well: count `≤ exp (2π √C M / √u)` | `eq:tensor-partition-count` |
| `cost_le`, `paper_enumeration_cost` | enumeration charge `≤ 2 N (K+1) · 9(2·size p + 1)` bit operations, so `≤ 2 exp (2π √C M/√u) (K+1) · 9(2·size p + 1)` | "polynomial delay" claim |

Cost model: each try of an exponent performs one addition (`w·b` from
`w·(b-1)`), one comparison with the remaining budget and one subtraction,
each charged the sum of its operands' `Nat.size`; the final failing try of
every loop is charged too, and each emitted tuple costs one unit.

| `sum_labelings_load_sq`, `exists_labeling` | averaged over all row/column labelings, `∑_γ X_γ² ≤ M²/D_arr + 2MΔ`; some labeling has `∑_γ (X_γ - M/D_arr)² ≤ 2MΔ` | `lem:tensor-packets` proof |
| `packet_count` | under `M ≥ 2D_arr²Δ`, `M ≥ L·D_arr`: a labeling and `H_pad` with `L ∣ H_pad`, every load `≤ H_pad`, and `P·L = H_pad·D_arr ≤ 3M` | `lem:tensor-packets`, item 1 |
| `path_precision` | along a path, `p_d ≤ A_d·2^{a_{d-1}}` with `A_{d+1} = A_d + 8h_d + 8M_d(a_d+1)` | `eq:tensor-precision-bound`, first part |
| `precision_bound` | `i < u`, `D_t·2^i = 2^{a'+2u}`, `h·u ≤ 4M`, `p ≤ A·2^{a'}` ⇒ `p_t·u ≤ 34·M·D_t` | `eq:tensor-precision-bound`, second part (`C = 34`) |
| `active_node_bounds` | the two previous rows discharged: tuple count `≤ exp (2π √34 M/√u)` and the matching bit-cost bound, from the packing conditions alone | combined |

| `geometric_mode_expansion` | if `(1-ρj)v = 1`, `W = cv`, `q ∣ c`, `q ∣ ρ`: `W = ∑_{b<N} cρ^b j^b + q^(N+1) r`, and `q^(b+1) ∣ cρ^b` | `eq:tensor-mode-expansion` |
| `WDiv.affine_product` | a product of affine forms `c₀ + ∑ c_Z Z` with `q^(w_Z) ∣ c_Z` has `q^(∑ w_Z β_Z) ∣ coeff_β` | "every coefficient of `Z^β` is divisible by `2^{∑ w_Z β_Z}`" |
| `eq_budget_add`, `eval_eq_budget_sum` | then `f = ∑_{∑ w_Z β_Z < p} coeff_β Z^β + q^p g`, and after any substitution `Z ↦ L_Z` the same holds with `∏ L_Z^{β_Z}` | `eq:tensor-mode-budget`; omitted monomials in `eq:tensor-recursion-identity` |
| `budget_iff_enum` | the kept exponents are exactly the tuples `enum` lists | links the budget to the count |

`active_node_bounds` no longer assumes `P·L ≤ 3M` or `p·u ≤ C·M·D`.

| `crossing_not_dvd`, `crossing_valuation` | for `t = 2^i(2k+1)` and a crossing column, `v₂(T - y₀ + x) ≤ i` | `eq:tensor-mode-expansion` inputs |
| `odd_choose_two_pow_sub_one`, `factorization_prodAbs_eq` | `C(2^a - 1, n)` is odd; `∏_{m ≠ n} |n - m| = n!(N-1-n)!` has the matching 2-adic valuation | Kummer step |
| `first_fraction`, `ratio_even` | in any ring where odd integers plus even elements are units (`OddUnits`, e.g. `ZMod (2^p)`, `oddUnits_zmod`): the first fraction is `2^(a+1-i)` times an element, and `2^(i+1)/(T - y₀ + x)` is even | the two valuation facts |
| `crossing_entry_expansion` | both facts in the paper's variables (`i < a`, `x < 2^a`, `y₀ < 2^(i+1)`, crossing bit), feeding `geometric_mode_expansion` | `eq:tensor-mode-expansion` |
| `depth_bound` | `M·8^d ≤ C·s`, `s ≤ M·r`, `r² ≤ λ` ⇒ `(2^d)^6 ≤ C²λ` | `d ≤ log λ/6 + O_C(1)` |
| `schedule_bound` | on `u_d = ⌊λ/(2^17 2^d)⌋`, for all `λ ≥ λ₀(C)` and all active depths: `u_d ≥ 1` and `u_d` is large enough | `eq:tensor-parameter-bounds` |
| `size_conditions` | for all `λ ≥ λ₀(C)`: `A·u ≤ M·2^u` and `8(a+1)u ≤ 2^{a_{d-1}+u}` on the schedule, with `A` the envelope of `path_precision` (`envelope_le`) | the two size conditions |
| `scheduled_precision_bound` | `precision_bound` on the schedule with both size conditions discharged | `eq:tensor-precision-bound` |
| `child_edges`, `child_edges_le_eighth` | with loads `≤ H_pad` and `P·L = H_pad·D_arr ≤ 3M`, a symbol of one coordinate of `[r]^a` owns `≤ 3M/r` real ports per side, so a group's child has `≤ 6M/r` edges, `≤ M/8` for `r = 64` | `lem:tensor-packets`, item 3; `subsec:tensor-children` |
| `path_edges` | children with `≤ M/8` edges ⇒ `M_j·8^j ≤ M_0` | `M ≤ Cs·8^{-d}` |
| `CallTree.size_le` | a call tree with `≤ b_j` children per depth-`j` call and `b_n = 0` has `≤ ∑_{d ≤ n} ∏_{j<d} b_j` calls | "multiplying these bounds over the depths" |
| `depth_exponent` | `M_j·8^j ≤ Cs`, `u_j ≥ 1` ⇒ `M_j/√u_j ≤ 2^10 Cs/√λ · (√2/8)^j` | per-depth exponent |
| `total_calls` | if `b_j ≤ Q·exp(κ M_j/√u_j)` at every active depth: at most `(n+1)·Q^n·exp(2^11 κ C s/√λ)` calls | `subsec:tensor-cost`, call count |

With `κ = 2π√34` from `active_node_bounds`, `total_calls` is the paper's
call count `exp(O_C(s/√λ))·Q^n`. No gap was found in the assembly: the
per-depth exponents form a geometric series with ratio `√2/8`, so their sum
is `O_C(s/√λ)` independent of the depth.

## Taken as hypotheses, not proved here

- `λ₀(C)` in `schedule_bound` and `size_conditions` is shown to exist but is
  not computed. With `λ = ⌈log₂ s⌉` it corresponds to astronomically large `s`.
- The tapered-Hermite inputs `h·u ≤ 4M` (true for `h = ⌈3M/u⌉` when `u ≤ M`)
  and `D_t·2^i = L`.
- Only existence of a good labeling is proved; the deterministic
  conditional-expectation search and its running time are not.
- That the construction of `subsec:tensor-modes` produces modes tagged by
  distinct `(packet, tile, b)` with weight `b+1`. The tags are modelled, not
  derived from the tensor algebra.
- That the coefficient ring is `OddUnits`. This is proved for `ZMod (2^p)`;
  the paper's `𝒜_p` is a Galois ring with maximal ideal `(2)`, so it holds
  there too, but that instance is not formalised.
- That the coefficient extraction factors over groups into the child
  contractions `Z_{g,β}` of `eq:tensor-recursion-identity`.
- Correctness of the tapered-Hermite recovery (`lem:tapered-hermite`).
- The polynomial factor `Q` in `total_calls`: that interpolation nodes,
  values and groups per call are polynomially many in `s`. The `(n+1)·Q^n`
  factor with `Q = s^{O(1)}` and `n = O(log λ)` is `exp(O(λ log λ))`; its
  absorption into `exp(O(s/√λ))` is not formalised.
- The leaf cost `2^H` times entry evaluation `exp(O(L log s))`, and the
  per-call work being polynomial apart from those.

## Runtime checks

`veritas.research.parent_child_r912.conformance` evaluates these hypotheses
on the engine's actual objects. Pass `conformance='report'` to
`parent_child_r910.engine.contract` (or `--conformance report` to
`parent_child_r912.cli`) to attach a `theorem_conformance` record per active
call. Pass `'strict'` to refuse with `INCONCLUSIVE_THEOREM_HYPOTHESIS` at the
first unmet hypothesis. A proved conclusion that fails while its hypotheses
hold raises an error. `layout_factory=derandomized_layout` (`--layout
derandomized`) uses the conditional-expectation labeler, with no repair.

| Check | Hypotheses evaluated | Conclusion evaluated |
| --- | --- | --- |
| `packet_count` | `M ≥ 2D_arr²Δ`, `M ≥ L·D_arr`, spread `≤ 2MΔ`, `L ∣ H_pad`, loads `≤ H_pad`, `P·L ≤ 3M` | minimal padding gives `P·L ≤ 3M` |
| `mode_multiplicity` | distinct `(packet, tile, b)` tags, `packet < P`, `tile < 2^(i+1)`, weight `b+1`, `D_t·2^i = L`, packing held | per weight `≤ P·2^(i+1)` and `·D_t ≤ 6M` |
| `precision_bound` | `a ≥ 2u`, `i < u`, `h·u ≤ 4M`, both size conditions, `p_t` as in `lem:tapered-hermite` | `p_t·u ≤ 34·M·D_t` |
| `tuple_count` | all of the above, support inside the weight budget | count `≤ exp (2π √34 M/√u)` |

On every parent the engine can run, these fail: the packing conditions
need `M ≥ 2·64^(4a)·Δ`, the finite schedules use `a < 2u` or `u = 1`, and the
bound beats `2^M` only for `u ≥ 2794`. A conforming run would still not be
source qualification or evidence for the recursion bound.

## Not covered

- Child construction and contraction as tensor algebra, Hermite recovery,
  entry evaluation, and the running time of each call; the recursion is
  costed by counting calls only.
- Any statement about the Python or C++ implementation.

## Reading the bound

`exp (2π √C M / √u)` is below `2^M` only when `u` is large. At `u = 1`, the
value used by every R9.12 finite schedule, it is `exp (O(M))`, which matches
the measured child-request growth in
`VERITAS_ETH_R9_12_RING_OPTIMIZATION_EVIDENCE/child_growth`. The source
schedule `u_0 = ⌊λ/131072⌋` reaches `u ≥ 1` only when `λ ≥ 131072`.
