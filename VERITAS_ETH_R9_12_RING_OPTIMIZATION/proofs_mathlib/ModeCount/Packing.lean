import ModeCount.BitCost

/-!
# Packet count of `lem:tensor-packets`, item 1

Rows `α` and columns `β` receive labels in `K` (`[r]^a` in the paper, so
`D_arr = |K|²` pair labels). Averaged over all labelings,
`∑_γ (X_γ - M/D_arr)² ≤ 2MΔ`; hence some labeling attains it. Every load is
then at most `M/D_arr + √(2MΔ)`. Padding every class to a multiple `H_pad` of
`L` and cutting it into packets of `L` slots gives `P·L = H_pad·D_arr ≤ 3M`
under `eq:tensor-packing-conditions`.

Only existence is proved; the paper's deterministic conditional-expectation
search and its running time are not formalised here.
-/

open Finset Real

namespace ModeCount

variable {α β K : Type*} [Fintype α] [Fintype β] [Fintype K] [DecidableEq α] [DecidableEq β]
  [DecidableEq K]

/-- Number of edges with pair label `γ`. -/
def load (E : Finset (α × β)) (f : α → K) (g : β → K) (γ : K × K) : ℕ :=
  (E.filter fun e => (f e.1, g e.2) = γ).card

theorem sum_load (E : Finset (α × β)) (f : α → K) (g : β → K) : ∑ γ, load E f g γ = E.card :=
  (card_eq_sum_card_fiberwise (f := fun e : α × β => (f e.1, g e.2)) (s := E)
    (t := (univ : Finset (K × K))) (by simp)).symm

theorem sum_load_sq (E : Finset (α × β)) (f : α → K) (g : β → K) :
    ∑ γ, (load E f g γ : ℝ) ^ 2 =
      ∑ e ∈ E, ∑ e' ∈ E, if f e.1 = f e'.1 ∧ g e.2 = g e'.2 then 1 else 0 := by
  have h : ∀ γ, (load E f g γ : ℝ) = ∑ e ∈ E, if (f e.1, g e.2) = γ then 1 else 0 := by
    intro γ; simp only [load, card_filter, Nat.cast_sum, Nat.cast_ite, Nat.cast_one, Nat.cast_zero]
  simp_rw [h, sq, sum_mul_sum]
  rw [sum_comm]
  refine sum_congr rfl fun e _ => ?_
  rw [sum_comm]
  refine sum_congr rfl fun e' _ => ?_
  simp only [ite_zero_mul_ite_zero, mul_one]
  by_cases hq : f e.1 = f e'.1 ∧ g e.2 = g e'.2
  · rw [if_pos hq, sum_eq_single (f e.1, g e.2)]
    · simp [hq.1, hq.2]
    · intro γ _ hγ; rw [if_neg]; rintro ⟨h1, _⟩; exact hγ h1.symm
    · simp
  · rw [if_neg hq]
    refine sum_eq_zero fun γ _ => if_neg ?_
    rintro ⟨h1, h2⟩
    rw [← h2, Prod.mk.injEq] at h1
    exact hq h1

/-- `#{f : α → K | f x = f x'} · |K| = |K|^|α|` for `x ≠ x'`. -/
theorem sum_eq_pair {x x' : α} (hx : x ≠ x') :
    (∑ f : α → K, if f x = f x' then (1 : ℝ) else 0) * Fintype.card K =
      (Fintype.card K : ℝ) ^ Fintype.card α := by
  let e := Equiv.piSplitAt x' (fun _ : α => K)
  have hsplit : ∑ f : α → K, (if f x = f x' then (1 : ℝ) else 0) =
      ∑ q : K × ({j // j ≠ x'} → K), if q.2 ⟨x, hx⟩ = q.1 then 1 else 0 := by
    refine Fintype.sum_equiv e _ _ fun f => ?_
    simp [e, Equiv.piSplitAt]
  rw [hsplit, Fintype.sum_prod_type, sum_comm]
  simp only [sum_ite_eq, mem_univ, ite_true, sum_const, card_univ, nsmul_eq_mul, mul_one]
  rw [Fintype.card_fun, Fintype.card_subtype_compl, Fintype.card_subtype_eq]
  push_cast
  rw [← pow_succ, Nat.sub_add_cancel (Fintype.card_pos_iff.2 ⟨x⟩)]

theorem sum_pair_le (x x' : α) :
    ∑ f : α → K, (if f x = f x' then (1 : ℝ) else 0) ≤ (Fintype.card K : ℝ) ^ Fintype.card α := by
  calc ∑ f : α → K, (if f x = f x' then (1 : ℝ) else 0) ≤ ∑ _f : α → K, (1 : ℝ) :=
        sum_le_sum fun f _ => by split_ifs <;> norm_num
    _ = _ := by simp

/-- Averaged over all labelings, the squared pair-label count is at most `M²/D + 2MΔ`. -/
theorem sum_labelings_load_sq (E : Finset (α × β)) {Δ : ℕ} [Nonempty K]
    (hrow : ∀ x, (E.filter fun e => e.1 = x).card ≤ Δ)
    (hcol : ∀ y, (E.filter fun e => e.2 = y).card ≤ Δ) :
    ∑ f : α → K, ∑ g : β → K, ∑ γ, (load E f g γ : ℝ) ^ 2 ≤
      (Fintype.card K : ℝ) ^ Fintype.card α * (Fintype.card K : ℝ) ^ Fintype.card β *
        ((E.card : ℝ) ^ 2 / (Fintype.card K : ℝ) ^ 2 + 2 * E.card * Δ) := by
  set k : ℝ := (Fintype.card K : ℝ)
  set N := k ^ Fintype.card α * k ^ Fintype.card β
  have hk : (1 : ℝ) ≤ k := by
    simp only [k]; exact_mod_cast Nat.succ_le_of_lt (Fintype.card_pos (α := K))
  have hN : 0 ≤ N := by positivity
  simp_rw [sum_load_sq]
  have reorder : (∑ f : α → K, ∑ g : β → K, ∑ e ∈ E, ∑ e' ∈ E,
      (if f e.1 = f e'.1 ∧ g e.2 = g e'.2 then (1 : ℝ) else 0)) =
      ∑ e ∈ E, ∑ e' ∈ E, ∑ f : α → K, ∑ g : β → K,
        (if f e.1 = f e'.1 ∧ g e.2 = g e'.2 then (1 : ℝ) else 0) := by
    calc _ = ∑ f : α → K, ∑ e ∈ E, ∑ e' ∈ E, ∑ g : β → K,
          (if f e.1 = f e'.1 ∧ g e.2 = g e'.2 then (1 : ℝ) else 0) := by
          refine sum_congr rfl fun f _ => ?_
          rw [sum_comm]; exact sum_congr rfl fun e _ => sum_comm
      _ = _ := by
          rw [sum_comm]; exact sum_congr rfl fun e _ => sum_comm
  rw [reorder]
  have term : ∀ e ∈ E, ∀ e' ∈ E,
      ∑ f : α → K, ∑ g : β → K, (if f e.1 = f e'.1 ∧ g e.2 = g e'.2 then (1 : ℝ) else 0) ≤
        N * ((if e.1 = e'.1 then 1 else 0) + (if e.2 = e'.2 then 1 else 0) + 1 / k ^ 2) := by
    intro e _ e' _
    have hprod : ∑ f : α → K, ∑ g : β → K,
        (if f e.1 = f e'.1 ∧ g e.2 = g e'.2 then (1 : ℝ) else 0) =
        (∑ f : α → K, if f e.1 = f e'.1 then (1 : ℝ) else 0) *
          ∑ g : β → K, if g e.2 = g e'.2 then (1 : ℝ) else 0 := by
      rw [sum_mul_sum]
      refine sum_congr rfl fun f _ => sum_congr rfl fun g _ => ?_
      by_cases ha : f e.1 = f e'.1 <;> by_cases hb : g e.2 = g e'.2 <;> simp [ha, hb]
    rw [hprod]
    have hA := sum_pair_le (K := K) e.1 e'.1
    have hB := sum_pair_le (K := K) e.2 e'.2
    have hA0 : 0 ≤ ∑ f : α → K, (if f e.1 = f e'.1 then (1 : ℝ) else 0) :=
      sum_nonneg fun _ _ => by split_ifs <;> norm_num
    by_cases h1 : e.1 = e'.1
    · rw [if_pos h1]
      calc _ ≤ k ^ Fintype.card α * k ^ Fintype.card β := mul_le_mul hA hB
              (sum_nonneg fun _ _ => by split_ifs <;> norm_num) (by positivity)
        _ ≤ N * (1 + (if e.2 = e'.2 then 1 else 0) + 1 / k ^ 2) := by
            have h0 : (0:ℝ) ≤ 1 / k ^ 2 := by positivity
            have : (1:ℝ) ≤ 1 + (if e.2 = e'.2 then 1 else 0) + 1 / k ^ 2 := by
              split_ifs <;> linarith
            nlinarith
    by_cases h2 : e.2 = e'.2
    · rw [if_pos h2, if_neg h1]
      calc _ ≤ k ^ Fintype.card α * k ^ Fintype.card β := mul_le_mul hA hB
              (sum_nonneg fun _ _ => by split_ifs <;> norm_num) (by positivity)
        _ ≤ N * (0 + 1 + 1 / k ^ 2) := by
            have : (0:ℝ) ≤ 1 / k ^ 2 := by positivity
            nlinarith
    · rw [if_neg h1, if_neg h2]
      have eA := sum_eq_pair (K := K) h1
      have eB := sum_eq_pair (K := K) h2
      have hk0 : k ≠ 0 := by positivity
      have hA' : ∑ f : α → K, (if f e.1 = f e'.1 then (1 : ℝ) else 0) = k ^ Fintype.card α / k := by
        rw [eq_div_iff hk0]; exact eA
      have hB' : ∑ g : β → K, (if g e.2 = g e'.2 then (1 : ℝ) else 0) = k ^ Fintype.card β / k := by
        rw [eq_div_iff hk0]; exact eB
      rw [hA', hB']
      apply le_of_eq
      field_simp
      ring
  refine (sum_le_sum fun e he => sum_le_sum fun e' he' => term e he e' he').trans ?_
  have hdeg : ∀ e ∈ E, ∑ e' ∈ E, ((if e.1 = e'.1 then (1 : ℝ) else 0) + (if e.2 = e'.2 then 1 else 0))
      ≤ 2 * Δ := by
    intro e _
    rw [sum_add_distrib]
    have r1 : ∑ e' ∈ E, (if e.1 = e'.1 then (1 : ℝ) else 0) ≤ Δ := by
      have := hrow e.1
      rw [card_filter] at this
      calc ∑ e' ∈ E, (if e.1 = e'.1 then (1 : ℝ) else 0)
          = ((∑ e' ∈ E, if e'.1 = e.1 then 1 else 0 : ℕ) : ℝ) := by
            push_cast; exact sum_congr rfl fun e' _ => by simp [eq_comm]
        _ ≤ Δ := by exact_mod_cast this
    have r2 : ∑ e' ∈ E, (if e.2 = e'.2 then (1 : ℝ) else 0) ≤ Δ := by
      have := hcol e.2
      rw [card_filter] at this
      calc ∑ e' ∈ E, (if e.2 = e'.2 then (1 : ℝ) else 0)
          = ((∑ e' ∈ E, if e'.2 = e.2 then 1 else 0 : ℕ) : ℝ) := by
            push_cast; exact sum_congr rfl fun e' _ => by simp [eq_comm]
        _ ≤ Δ := by exact_mod_cast this
    linarith
  calc ∑ e ∈ E, ∑ e' ∈ E, N * ((if e.1 = e'.1 then (1 : ℝ) else 0) + (if e.2 = e'.2 then 1 else 0)
          + 1 / k ^ 2)
      = N * ∑ e ∈ E, (∑ e' ∈ E, ((if e.1 = e'.1 then (1 : ℝ) else 0) + (if e.2 = e'.2 then 1 else 0))
          + (E.card : ℝ) * (1 / k ^ 2)) := by
        rw [mul_sum]; refine sum_congr rfl fun e _ => ?_
        rw [← mul_sum, sum_add_distrib, sum_const, nsmul_eq_mul]
    _ ≤ N * ∑ _e ∈ E, (2 * Δ + (E.card : ℝ) * (1 / k ^ 2)) :=
        mul_le_mul_of_nonneg_left (sum_le_sum fun e he => by linarith [hdeg e he]) hN
    _ = N * ((E.card : ℝ) ^ 2 / k ^ 2 + 2 * E.card * Δ) := by rw [sum_const, nsmul_eq_mul]; ring

theorem variance_eq (E : Finset (α × β)) (f : α → K) (g : β → K) [Nonempty K] :
    ∑ γ, ((load E f g γ : ℝ) - E.card / (Fintype.card K : ℝ) ^ 2) ^ 2 =
      ∑ γ, (load E f g γ : ℝ) ^ 2 - (E.card : ℝ) ^ 2 / (Fintype.card K : ℝ) ^ 2 := by
  have hs : ∑ γ, (load E f g γ : ℝ) = E.card := by exact_mod_cast sum_load E f g
  have hk : (0 : ℝ) < Fintype.card K := by exact_mod_cast Fintype.card_pos
  set μ := (E.card : ℝ) / (Fintype.card K : ℝ) ^ 2 with hμ
  have expand : ∀ γ, ((load E f g γ : ℝ) - μ) ^ 2 = (load E f g γ : ℝ) ^ 2 - 2 * μ * load E f g γ + μ ^ 2 :=
    fun γ => by ring
  simp_rw [expand]
  rw [sum_add_distrib, sum_sub_distrib, ← mul_sum, hs, sum_const, card_univ, Fintype.card_prod,
    nsmul_eq_mul]
  push_cast
  rw [hμ]
  field_simp
  ring

/-- Some labeling has `∑_γ (X_γ - M/D_arr)² ≤ 2MΔ`. -/
theorem exists_labeling (E : Finset (α × β)) {Δ : ℕ} [Nonempty K]
    (hrow : ∀ x, (E.filter fun e => e.1 = x).card ≤ Δ)
    (hcol : ∀ y, (E.filter fun e => e.2 = y).card ≤ Δ) :
    ∃ (f : α → K) (g : β → K),
      ∑ γ, ((load E f g γ : ℝ) - E.card / (Fintype.card K : ℝ) ^ 2) ^ 2 ≤ 2 * E.card * Δ := by
  by_contra h
  push Not at h
  have hsum := sum_labelings_load_sq (K := K) E hrow hcol
  have hlt : ∑ _f : α → K, ∑ _g : β → K, (2 * (E.card : ℝ) * Δ) <
      ∑ f : α → K, ∑ g : β → K, ∑ γ, ((load E f g γ : ℝ) - E.card / (Fintype.card K : ℝ) ^ 2) ^ 2 :=
    sum_lt_sum_of_nonempty univ_nonempty fun f _ =>
      sum_lt_sum_of_nonempty univ_nonempty fun g _ => h f g
  simp_rw [variance_eq, sum_sub_distrib, sum_const, card_univ, nsmul_eq_mul, Fintype.card_fun] at hlt
  push_cast at hlt
  nlinarith [hsum, hlt]

/-- `lem:tensor-packets`, item 1: a labeling and padding with `P·L = H_pad·D_arr ≤ 3M`. -/
theorem packet_count (E : Finset (α × β)) {Δ L : ℕ} [Nonempty K] (hL : 0 < L)
    (hrow : ∀ x, (E.filter fun e => e.1 = x).card ≤ Δ)
    (hcol : ∀ y, (E.filter fun e => e.2 = y).card ≤ Δ)
    (hM1 : 2 * (Fintype.card K ^ 2) ^ 2 * Δ ≤ E.card) (hM2 : L * Fintype.card K ^ 2 ≤ E.card) :
    ∃ (f : α → K) (g : β → K) (Hpad P : ℕ), L ∣ Hpad ∧ (∀ γ, load E f g γ ≤ Hpad) ∧
      P * L = Hpad * Fintype.card K ^ 2 ∧ P * L ≤ 3 * E.card := by
  obtain ⟨f, g, hv⟩ := exists_labeling (K := K) E hrow hcol
  set k := Fintype.card K
  set M := E.card
  have hk : (0 : ℝ) < k := by exact_mod_cast Fintype.card_pos
  set μ : ℝ := M / (k : ℝ) ^ 2
  have hload : ∀ γ, (load E f g γ : ℝ) ≤ μ + √(2 * M * Δ) := by
    intro γ
    have h1 : ((load E f g γ : ℝ) - μ) ^ 2 ≤ 2 * M * Δ :=
      (single_le_sum (fun γ _ => sq_nonneg (((load E f g γ : ℕ) : ℝ) - μ)) (mem_univ γ)).trans hv
    have := abs_le_sqrt h1
    linarith [le_abs_self ((load E f g γ : ℝ) - μ)]
  set mx := univ.sup (load E f g)
  obtain ⟨γ0, -, hγ0⟩ := exists_mem_eq_sup univ univ_nonempty (load E f g)
  set q := (mx + L - 1) / L
  have hdm := Nat.div_add_mod (mx + L - 1) L
  have hmod := Nat.mod_lt (mx + L - 1) hL
  have hq1 : mx ≤ L * q := by
    have : L * q + (mx + L - 1) % L = mx + L - 1 := hdm
    omega
  have hq2 : L * q ≤ mx + L - 1 := by
    have : L * q + (mx + L - 1) % L = mx + L - 1 := hdm
    omega
  refine ⟨f, g, L * q, q * k ^ 2, Dvd.intro q rfl, fun γ => (le_sup (mem_univ γ)).trans hq1,
    by ring, ?_⟩
  have hmx : (mx : ℝ) ≤ μ + √(2 * M * Δ) := by rw [show mx = load E f g γ0 from hγ0]; exact hload γ0
  have hsq : √(2 * (M : ℝ) * Δ) ≤ μ := by
    rw [sqrt_le_left (by positivity)]
    have : (2 * (k : ℝ) ^ 4 * Δ) ≤ M := by
      have := hM1; rw [← pow_mul] at this; exact_mod_cast this
    simp only [μ]
    rw [div_pow, le_div_iff₀ (by positivity)]
    have hM0 : (0 : ℝ) ≤ M := Nat.cast_nonneg _
    nlinarith [mul_le_mul_of_nonneg_left this hM0]
  have hLμ : (L : ℝ) ≤ μ := by
    simp only [μ]; rw [le_div_iff₀ (by positivity)]; exact_mod_cast hM2
  have hpad : ((L * q : ℕ) : ℝ) ≤ 3 * μ := by
    have : ((L * q : ℕ) : ℝ) ≤ mx + L := by
      have : L * q ≤ mx + L := by omega
      exact_mod_cast this
    linarith
  have : ((q * k ^ 2 * L : ℕ) : ℝ) ≤ 3 * M := by
    have e1 : ((q * k ^ 2 * L : ℕ) : ℝ) = ((L * q : ℕ) : ℝ) * (k : ℝ) ^ 2 := by push_cast; ring
    rw [e1]
    calc ((L * q : ℕ) : ℝ) * (k : ℝ) ^ 2 ≤ 3 * μ * (k : ℝ) ^ 2 :=
          mul_le_mul_of_nonneg_right hpad (by positivity)
      _ = 3 * M := by simp only [μ]; field_simp
  exact_mod_cast this

end ModeCount
