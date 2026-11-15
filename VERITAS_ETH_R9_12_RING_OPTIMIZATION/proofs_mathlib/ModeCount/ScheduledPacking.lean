import ModeCount.ChildSize
import ModeCount.Schedule

/-!
# The packing conditions on the actual schedule

`eq:tensor-packing-conditions` is asserted "for all sufficiently large `s`".
Here it is derived from the schedule `eq:tensor-parameters` with an explicit
threshold, `λ ≥ 144`.

The inputs are the paper's own definitions, stated over `ℕ`:

* `λ = ⌈log₂ s⌉` enters as `2^λ ≤ 2s`;
* an active call (`M > H = ⌈s/⌊√λ⌋⌉`) enters as `s ≤ M·λ`;
* `Δ = ⌈s^{9/10}⌉` enters as `s⁹ ≤ Δ¹⁰` and `(Δ-1)¹⁰ < s⁹`;
* `r = 64`, `a = a_d`, `L = 2^a`, `D_arr = r^{2a} = (64^a)²`.

Results:

* `aSched_mul_le`: `32768·a_d ≤ λ`, the paper's `a ≤ 4ελ`.
* `aSched_eq_zero`: `a_d = 0` whenever `λ < 131072`. Below `s ≈ 2^131071` the
  schedule has no label coordinates at all, so the statements below are only
  non-vacuous beyond that size.
* `packing_of_schedule`: `M ≥ 2·D_arr²·Δ`, `M ≥ L·D_arr`, `2L ≤ Δ`.
* `scheduled_child_edges_le_eighth`: hence labels in `[64]^{a_d}` exist for
  which every group's child has at most `M/8` edges, and a new packet vertex
  (`2L` ports) respects the degree cap `Δ`. This is the inductive invariant of
  `subsec:tensor-children` with no packing hypothesis left.
-/

open Finset

namespace ModeCount

/-- `a ≤ 4ελ` with `ε = 1/131072`. -/
theorem aSched_mul_le (lam d : ℕ) : 32768 * aSched lam d ≤ lam := by
  have h : ∀ j, uSched lam j = lam / 131072 / 2 ^ j := fun j => by
    rw [uSched, Nat.div_div_eq_div_mul]
  have hs := sum_div_two_pow_le (lam / 131072) (d + 1)
  unfold aSched aPrev
  rw [sum_range_succ] at hs
  simp only [h] at hs ⊢
  omega

/-- Below `λ = 131072` every `u_j` is zero, so the label space `[r]^a` is a point. -/
theorem aSched_eq_zero {lam : ℕ} (h : lam < 131072) (d : ℕ) : aSched lam d = 0 := by
  have hu : ∀ j, uSched lam j = 0 := fun j => by
    unfold uSched
    exact Nat.div_eq_of_lt (lt_of_lt_of_le h (Nat.le_mul_of_pos_right _ (by positivity)))
  simp [aSched, aPrev, hu]

/-- A concrete polynomial-versus-exponential bound: `(2m+1)^10 ≤ 2^m` from `m = 72` on. -/
theorem pow_ten_le_two_pow : ∀ m ≥ 72, (2 * m + 1) ^ 10 ≤ 2 ^ m := by
  intro m hm
  induction m, hm using Nat.le_induction with
  | base => norm_num
  | succ m hm ih =>
    have h1 : 72 * (2 * (m + 1) + 1) ≤ 73 * (2 * m + 1) := by omega
    have h2 : (72 * (2 * (m + 1) + 1)) ^ 10 ≤ (73 * (2 * m + 1)) ^ 10 :=
      Nat.pow_le_pow_left h1 10
    have h3 : (73 : ℕ) ^ 10 ≤ 2 * 72 ^ 10 := by norm_num
    have h4 : 72 ^ 10 * (2 * (m + 1) + 1) ^ 10 ≤ 72 ^ 10 * (2 * 2 ^ m) := by
      calc 72 ^ 10 * (2 * (m + 1) + 1) ^ 10 = (72 * (2 * (m + 1) + 1)) ^ 10 := (mul_pow _ _ _).symm
        _ ≤ (73 * (2 * m + 1)) ^ 10 := h2
        _ = 73 ^ 10 * (2 * m + 1) ^ 10 := mul_pow _ _ _
        _ ≤ 2 * 72 ^ 10 * 2 ^ m := Nat.mul_le_mul h3 ih
        _ = 72 ^ 10 * (2 * 2 ^ m) := by ring
    have h5 : (2 * (m + 1) + 1) ^ 10 ≤ 2 * 2 ^ m :=
      Nat.le_of_mul_le_mul_left h4 (by norm_num)
    calc (2 * (m + 1) + 1) ^ 10 ≤ 2 * 2 ^ m := h5
      _ = 2 ^ (m + 1) := (pow_succ' 2 m).symm

/-- `eq:tensor-packing-conditions` from `eq:tensor-parameters`, for every `λ ≥ 144`. -/
theorem packing_of_schedule {lam d M s Δ : ℕ} (hlam : 144 ≤ lam) (hs : 2 ^ lam ≤ 2 * s)
    (hM : s ≤ M * lam) (hΔ1 : s ^ 9 ≤ Δ ^ 10) (hΔ2 : (Δ - 1) ^ 10 < s ^ 9) :
    2 * ((64 ^ aSched lam d) ^ 2) ^ 2 * Δ ≤ M ∧
      2 ^ aSched lam d * (64 ^ aSched lam d) ^ 2 ≤ M ∧ 2 * 2 ^ aSched lam d ≤ Δ := by
  have ha : 32768 * aSched lam d ≤ lam := aSched_mul_le lam d
  generalize aSched lam d = a at ha ⊢
  have hs0 : 0 < s := by
    rcases Nat.eq_zero_or_pos s with h | h
    · subst h
      have : 0 < 2 ^ lam := by positivity
      omega
    · exact h
  have hΔ0 : 0 < Δ := by
    rcases Nat.eq_zero_or_pos Δ with h | h
    · subst h
      have h9 : 0 < s ^ 9 := pow_pos hs0 9
      have h0 : (0 : ℕ) ^ 10 = 0 := by norm_num
      omega
    · exact h
  have hΔup : Δ ^ 10 ≤ 2 ^ 10 * s ^ 9 := by
    have h2 : Δ ≤ 2 * (Δ - 1) ∨ Δ ≤ 1 := by omega
    rcases h2 with h2 | h2
    · calc Δ ^ 10 ≤ (2 * (Δ - 1)) ^ 10 := Nat.pow_le_pow_left h2 10
        _ = 2 ^ 10 * (Δ - 1) ^ 10 := mul_pow _ _ _
        _ ≤ 2 ^ 10 * s ^ 9 := Nat.mul_le_mul_left _ hΔ2.le
    · calc Δ ^ 10 ≤ 1 ^ 10 := Nat.pow_le_pow_left h2 10
        _ = 1 := one_pow 10
        _ ≤ 2 ^ 10 * s ^ 9 := Nat.succ_le_of_lt (Nat.mul_pos (by norm_num) (pow_pos hs0 9))
  have hm : 72 ≤ lam / 2 := by omega
  have hpoly : lam ^ 10 ≤ 2 ^ (lam / 2) :=
    (Nat.pow_le_pow_left (by omega : lam ≤ 2 * (lam / 2) + 1) 10).trans
      (pow_ten_le_two_pow _ hm)
  have hkey : 2 * 2 ^ (20 + 240 * a) * lam ^ 10 ≤ 2 ^ lam := by
    calc 2 * 2 ^ (20 + 240 * a) * lam ^ 10 = 2 ^ (20 + 240 * a + 1) * lam ^ 10 := by
          rw [pow_succ' 2 (20 + 240 * a)]
      _ ≤ 2 ^ (20 + 240 * a + 1) * 2 ^ (lam / 2) := Nat.mul_le_mul_left _ hpoly
      _ = 2 ^ (20 + 240 * a + 1 + lam / 2) := (pow_add 2 _ _).symm
      _ ≤ 2 ^ lam := Nat.pow_le_pow_right (by norm_num) (by omega)
  have hs1 : 2 ^ (20 + 240 * a) * lam ^ 10 ≤ s := by
    have h2s : 2 * (2 ^ (20 + 240 * a) * lam ^ 10) ≤ 2 * s := by
      calc 2 * (2 ^ (20 + 240 * a) * lam ^ 10) = 2 * 2 ^ (20 + 240 * a) * lam ^ 10 := by ring
        _ ≤ 2 ^ lam := hkey
        _ ≤ 2 * s := hs
    exact Nat.le_of_mul_le_mul_left h2s (by norm_num)
  have h64 : ((64 ^ a) ^ 2) ^ 2 = 2 ^ (24 * a) := by
    rw [show (64 : ℕ) = 2 ^ 6 by norm_num, ← pow_mul, ← pow_mul, ← pow_mul]
    congr 1; ring
  have h13 : 2 ^ a * (64 ^ a) ^ 2 = 2 ^ (13 * a) := by
    rw [show (64 : ℕ) = 2 ^ 6 by norm_num, ← pow_mul, ← pow_mul, ← pow_add]
    congr 1; ring
  have hX : (2 * 2 ^ (24 * a) * Δ * lam) ^ 10 ≤ s ^ 10 := by
    calc (2 * 2 ^ (24 * a) * Δ * lam) ^ 10 = 2 ^ (10 + 240 * a) * lam ^ 10 * Δ ^ 10 := by ring
      _ ≤ 2 ^ (10 + 240 * a) * lam ^ 10 * (2 ^ 10 * s ^ 9) := Nat.mul_le_mul_left _ hΔup
      _ = 2 ^ (20 + 240 * a) * lam ^ 10 * s ^ 9 := by ring
      _ ≤ s * s ^ 9 := Nat.mul_le_mul_right _ hs1
      _ = s ^ 10 := by ring
  have hXs : 2 * 2 ^ (24 * a) * Δ * lam ≤ s := (Nat.pow_le_pow_iff_left (by norm_num)).1 hX
  have h1 : 2 * 2 ^ (24 * a) * Δ ≤ M :=
    Nat.le_of_mul_le_mul_right (hXs.trans hM) (by omega)
  have hs2 : 2 ^ (lam - 1) ≤ s := by
    have e : 2 ^ lam = 2 * 2 ^ (lam - 1) := by
      rw [← pow_succ']; congr 1; omega
    rw [e] at hs
    exact Nat.le_of_mul_le_mul_left hs (by norm_num)
  refine ⟨by rw [h64]; exact h1, ?_, ?_⟩
  · rw [h13]
    have hmono : 2 ^ (13 * a) ≤ 2 ^ (24 * a) := Nat.pow_le_pow_right (by norm_num) (by omega)
    have hpad : 2 ^ (24 * a) * 1 ≤ 2 * 2 ^ (24 * a) * Δ :=
      Nat.mul_le_mul (Nat.le_mul_of_pos_left _ (by norm_num)) hΔ0
    rw [mul_one] at hpad
    exact hmono.trans (hpad.trans h1)
  · have h10 : (2 * 2 ^ a) ^ 10 ≤ Δ ^ 10 := by
      calc (2 * 2 ^ a) ^ 10 = 2 ^ (10 + 10 * a) := by ring
        _ ≤ 2 ^ ((lam - 1) * 9) := Nat.pow_le_pow_right (by norm_num) (by omega)
        _ = (2 ^ (lam - 1)) ^ 9 := pow_mul 2 _ _
        _ ≤ s ^ 9 := Nat.pow_le_pow_left hs2 9
        _ ≤ Δ ^ 10 := hΔ1
    exact (Nat.pow_le_pow_iff_left (by norm_num)).1 h10

/-- The inductive invariant of `subsec:tensor-children` on the actual schedule: at an active call
with `λ ≥ 144` there are labels in `[64]^{a_d}` for which every group's child has at most `M/8`
edges, and a new packet vertex, with `2L` ports, stays within the degree cap `Δ`. -/
theorem scheduled_child_edges_le_eighth {α β : Type*} [Fintype α] [Fintype β] [DecidableEq α]
    [DecidableEq β] {lam d s Δ : ℕ} (hlam : 144 ≤ lam) (hs : 2 ^ lam ≤ 2 * s)
    (E : Finset (α × β)) (hM : s ≤ E.card * lam) (hΔ1 : s ^ 9 ≤ Δ ^ 10)
    (hΔ2 : (Δ - 1) ^ 10 < s ^ 9)
    (hrow : ∀ x, (E.filter fun e => e.1 = x).card ≤ Δ)
    (hcol : ∀ y, (E.filter fun e => e.2 = y).card ≤ Δ) :
    2 * 2 ^ aSched lam d ≤ Δ ∧
      ∃ (f : α → Fin (aSched lam d) → Fin 64) (g : β → Fin (aSched lam d) → Fin 64),
        ∀ (c : Fin (aSched lam d)) (σ : Fin 64),
          ((E.filter fun e => f e.1 c = σ).card + (E.filter fun e => g e.2 c = σ).card) * 8
            ≤ E.card := by
  obtain ⟨h1, h2, h3⟩ := packing_of_schedule (d := d) hlam hs hM hΔ1 hΔ2
  have hc : Fintype.card (Fin (aSched lam d) → Fin 64) = 64 ^ aSched lam d := by simp
  refine ⟨h3, child_edges_le_eighth_of_packing (L := 2 ^ aSched lam d) (by positivity) E hrow hcol
    ?_ ?_⟩
  · rw [hc]; exact h1
  · rw [hc]; exact h2

end ModeCount
