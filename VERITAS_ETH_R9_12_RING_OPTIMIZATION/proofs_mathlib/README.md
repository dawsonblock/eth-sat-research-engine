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

## Taken as hypotheses, not proved here

- Item 1 of `lem:tensor-packets`: at most `3M/L` packets (`P·L ≤ 3M`).
- `eq:tensor-precision-bound`: `p_t = O_C(M D_t / u)`, as `p·u ≤ C·M·D`.
- That the construction of `subsec:tensor-modes` produces modes tagged by
  distinct `(packet, tile, b)` with weight `b+1`. The tags are modelled, not
  derived from the tensor algebra.
- The divisibility argument that tuples outside the budget contribute zero.

## Not covered

- Child construction, child contraction, Hermite recovery, packing, entry
  evaluation and the recursion over depths; only tuple enumeration is costed.
- Any statement about the Python or C++ implementation.

## Reading the bound

`exp (2π √C M / √u)` is below `2^M` only when `u` is large. At `u = 1`, the
value used by every R9.12 finite schedule, it is `exp (O(M))`, which matches
the measured child-request growth in
`VERITAS_ETH_R9_12_RING_OPTIMIZATION_EVIDENCE/child_growth`. The source
schedule `u_0 = ⌊λ/131072⌋` reaches `u ≥ 1` only when `λ ≥ 131072`.
