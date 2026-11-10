import ModeCount.Precision

/-!
# Tuple count and enumeration cost at an active node, without assumed bounds

`paper_tuple_count` and `paper_enumeration_cost` took `P·L ≤ 3M` and
`p·u ≤ C·M·D` as hypotheses. Here the first comes from `packet_count`
(`M = |E|`, `D_arr = |K|²`, `L = 2^(a'+2u)`) and the second from
`precision_bound` (`C = 34`), so the remaining assumptions are the packing
conditions, the tapered-Hermite inputs `h·u ≤ 4M`, `p ≤ A·2^{a'}`, and the two
size conditions `A·u ≤ M·2^u`, `8(a+1)u ≤ 2^{a'+u}`.
-/

open Finset Real

namespace ModeCount

variable {α β K : Type*} [Fintype α] [Fintype β] [Fintype K] [DecidableEq α] [DecidableEq β]
  [DecidableEq K]

theorem active_node_bounds (E : Finset (α × β)) [Nonempty K] {Δ a' u i Dt p h A : ℕ}
    (hrow : ∀ x, (E.filter fun e => e.1 = x).card ≤ Δ)
    (hcol : ∀ y, (E.filter fun e => e.2 = y).card ≤ Δ)
    (hM1 : 2 * (Fintype.card K ^ 2) ^ 2 * Δ ≤ E.card)
    (hM2 : 2 ^ (a' + 2 * u) * Fintype.card K ^ 2 ≤ E.card) (hE : 0 < E.card)
    (hi : i < u) (hD : Dt * 2 ^ i = 2 ^ (a' + 2 * u)) (hh : h * u ≤ 4 * E.card)
    (hp : p ≤ A * 2 ^ a') (hA : A * u ≤ E.card * 2 ^ u)
    (hlog : 8 * (a' + 2 * u + 1) * u ≤ 2 ^ (a' + u)) :
    ∃ (f : α → K) (g : β → K) (Hpad P : ℕ), 2 ^ (a' + 2 * u) ∣ Hpad ∧
      (∀ γ, load E f g γ ≤ Hpad) ∧ P * 2 ^ (a' + 2 * u) = Hpad * Fintype.card K ^ 2 ∧
      ∀ modes : List Tag, modes.Nodup → (∀ z ∈ modes, z.1 < P ∧ z.2.1 < 2 ^ (i + 1)) →
        ((enum (modes.map weight) (nodePrecision p h Dt E.card (a' + 2 * u))).length : ℝ) ≤
            exp (2 * π * √34 * E.card / √u) ∧
        ((∀ z ∈ modes, weight z < nodePrecision p h Dt E.card (a' + 2 * u)) →
          (cost (modes.map weight) (nodePrecision p h Dt E.card (a' + 2 * u)) : ℝ) ≤
            2 * exp (2 * π * √34 * E.card / √u) * (modes.length + 1) *
              (9 * (2 * Nat.size (nodePrecision p h Dt E.card (a' + 2 * u)) + 1))) := by
  obtain ⟨f, g, Hpad, P, hdvd, hload, hPL, hpack⟩ :=
    packet_count (K := K) E (L := 2 ^ (a' + 2 * u)) (by positivity) hrow hcol hM1 hM2
  refine ⟨f, g, Hpad, P, hdvd, hload, hPL, fun modes hnd hrange => ?_⟩
  have hHpad : 0 < Hpad := by
    by_contra h0
    have hz : ∀ γ, load E f g γ = 0 := fun γ => by have := hload γ; omega
    have := sum_load E f g
    simp [hz] at this
    omega
  have hP : 0 < P := by
    have : 0 < P * 2 ^ (a' + 2 * u) := by
      rw [hPL]; exact Nat.mul_pos hHpad (pow_pos Fintype.card_pos 2)
    exact Nat.pos_of_mul_pos_right this
  have hDpos : 0 < Dt := lt_of_lt_of_le (by positivity) (Dt_ge hi hD)
  have hpt : 0 < nodePrecision p h Dt E.card (a' + 2 * u) := by
    have h8 : 0 < 8 * E.card * (a' + 2 * u + 1) :=
      Nat.mul_pos (Nat.mul_pos (by norm_num) hE) (Nat.succ_pos _)
    unfold nodePrecision; omega
  have hu : (0 : ℝ) < u := by exact_mod_cast (Nat.zero_lt_of_lt hi)
  have hprec : (nodePrecision p h Dt E.card (a' + 2 * u) : ℝ) * u ≤ 34 * E.card * Dt := by
    exact_mod_cast precision_bound hi hD hh hp hA hlog
  exact ⟨paper_tuple_count hnd hrange hpack hD hP hDpos hpt hu (by norm_num) hprec,
    fun hb => paper_enumeration_cost hnd hrange hb hpack hD hP hDpos hpt hu (by norm_num) hprec⟩

end ModeCount
