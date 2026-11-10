import ModeCount.Partition

/-!
# Modes of one weight (`eq:tensor-mode-multiplicity`) and the paper-parameter count

In `subsec:tensor-modes` a mode is determined by its packet, its tile
`y₀ < 2^(i+1)` and its geometric index `b`, and has weight `b + 1`. Any
duplicate-free family of such tags therefore has at most `P * 2^(i+1)` modes of
each weight. With item 1 of `lem:tensor-packets` (`P * L ≤ 3M`, taken here as a
hypothesis) and `D = L / 2^i`, this is `6M/D`. Combined with
`eq:tensor-precision-bound` (`p_t u ≤ C M D`, also a hypothesis), the number of
tuples in `eq:tensor-mode-budget` is at most `exp (2π √C M / √u)`.
-/

open Real Finset

namespace ModeCount

/-- `(packet, tile, b)`. -/
abbrev Tag := ℕ × ℕ × ℕ

def weight (z : Tag) : ℕ := z.2.2 + 1

theorem count_weight_le {P i : ℕ} {modes : List Tag} (hnd : modes.Nodup)
    (hrange : ∀ z ∈ modes, z.1 < P ∧ z.2.1 < 2 ^ (i + 1)) (k : ℕ) :
    (modes.map weight).count k ≤ P * 2 ^ (i + 1) := by
  set F := modes.filter (fun z => weight z = k)
  have hcount : (modes.map weight).count k = F.length := by
    rw [List.count_eq_countP, List.countP_eq_length_filter, List.filter_map, List.length_map]
    congr 1
  have hinj : (F.map fun z : Tag => (z.1, z.2.1)).Nodup := by
    refine (hnd.filter _).map_on fun x hx y hy h => ?_
    have hx' : x.2.2 + 1 = k := by simpa [weight] using of_decide_eq_true (List.mem_filter.1 hx).2
    have hy' : y.2.2 + 1 = k := by simpa [weight] using of_decide_eq_true (List.mem_filter.1 hy).2
    obtain ⟨h1, h2⟩ := Prod.mk.inj h
    exact Prod.ext h1 (Prod.ext h2 (by omega))
  have hsub : (F.map fun z : Tag => (z.1, z.2.1)).toFinset ⊆ range P ×ˢ range (2 ^ (i + 1)) := by
    intro q hq
    obtain ⟨z, hz, rfl⟩ := List.mem_map.1 (List.mem_toFinset.1 hq)
    have := hrange z (List.mem_filter.1 hz).1
    simp [this.1, this.2]
  rw [hcount, ← List.length_map (f := fun z : Tag => (z.1, z.2.1)), ← List.toFinset_card_of_nodup hinj]
  simpa using card_le_card hsub

/-- `eq:tensor-mode-multiplicity`: at most `6M/D` variables of any one weight. -/
theorem mode_multiplicity {P i L M D : ℕ} {modes : List Tag} (hnd : modes.Nodup)
    (hrange : ∀ z ∈ modes, z.1 < P ∧ z.2.1 < 2 ^ (i + 1))
    (hpack : P * L ≤ 3 * M) (hD : D * 2 ^ i = L) (k : ℕ) :
    (modes.map weight).count k * D ≤ 6 * M := by
  calc (modes.map weight).count k * D ≤ P * 2 ^ (i + 1) * D :=
        Nat.mul_le_mul_right _ (count_weight_le hnd hrange k)
    _ = 2 * (P * L) := by rw [← hD, pow_succ]; ring
    _ ≤ 6 * M := by omega

/-- `eq:tensor-partition-count` at the paper's parameters. -/
theorem paper_tuple_count {P i L M D p : ℕ} {u C : ℝ} {modes : List Tag} (hnd : modes.Nodup)
    (hrange : ∀ z ∈ modes, z.1 < P ∧ z.2.1 < 2 ^ (i + 1))
    (hpack : P * L ≤ 3 * M) (hD : D * 2 ^ i = L) (hP : 0 < P) (hDpos : 0 < D) (hp : 0 < p)
    (hu : 0 < u) (hC : 0 ≤ C) (hprec : (p : ℝ) * u ≤ C * M * D) :
    ((enum (modes.map weight) p).length : ℝ) ≤ exp (2 * π * √C * M / √u) := by
  set m := P * 2 ^ (i + 1)
  have hw : ∀ w ∈ modes.map weight, 1 ≤ w := by
    intro w hw; obtain ⟨z, _, rfl⟩ := List.mem_map.1 hw; simp [weight]
  have hm0 : 0 < m := by positivity
  refine (length_enum_le hw hm0 (count_weight_le hnd hrange) hp).trans (exp_le_exp.2 ?_)
  have hmD : (m : ℝ) * D ≤ 6 * M := by
    have : m * D = 2 * (P * L) := by show P * 2 ^ (i + 1) * D = _; rw [← hD, pow_succ]; ring
    exact_mod_cast (show m * D ≤ 6 * M by omega)
  have hDr : (0 : ℝ) < D := by exact_mod_cast hDpos
  have hM : (0 : ℝ) ≤ M := Nat.cast_nonneg _
  have hmp : 2 * (m : ℝ) * p / 3 ≤ (2 * √C * M / √u) ^ 2 := by
    rw [div_pow, mul_pow, mul_pow, sq_sqrt hC, sq_sqrt hu.le, le_div_iff₀ hu]
    have h1 : (m : ℝ) * (p * u) ≤ m * (C * M * D) := mul_le_mul_of_nonneg_left hprec (Nat.cast_nonneg _)
    have h2 : C * M * ((m : ℝ) * D) ≤ C * M * (6 * M) := mul_le_mul_of_nonneg_left hmD (by positivity)
    nlinarith
  have hroot : √(2 * (m : ℝ) * p / 3) ≤ 2 * √C * M / √u :=
    (sqrt_le_sqrt hmp).trans_eq (sqrt_sq (by positivity))
  calc π * √(2 * (m : ℝ) * p / 3) ≤ π * (2 * √C * M / √u) := by gcongr
    _ = 2 * π * √C * M / √u := by ring

end ModeCount
