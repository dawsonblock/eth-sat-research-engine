import ModeCount.Packing

/-!
# Child size of `lem:tensor-packets`, item 3

With every pair-label load at most `H_pad` and `P·L = H_pad·D_arr ≤ 3M`, a symbol in one coordinate
of `[r]^a` owns at most `3M/r` real ports on each side.  The child built for one group therefore has
at most `6M/r` edges, which is below `M/8` for `r = 64`.
-/

open Finset

namespace ModeCount

variable {α β K : Type*} [Fintype K] [DecidableEq K]

/-- Edges whose pair label lies in a class covering a `1/r` share of all pair labels. -/
theorem class_edges_le (E : Finset (α × β)) (f : α → K) (g : β → K) {Hpad r : ℕ}
    (hload : ∀ γ, load E f g γ ≤ Hpad) (φ : K × K → Prop) [DecidablePred φ]
    (hφ : (univ.filter φ).card * r = Fintype.card K ^ 2) :
    (E.filter fun e => φ (f e.1, g e.2)).card * r ≤ Hpad * Fintype.card K ^ 2 := by
  set t := univ.filter φ
  have hfib := card_eq_sum_card_fiberwise (f := fun e : α × β => (f e.1, g e.2))
    (s := E.filter fun e => φ (f e.1, g e.2)) (t := t) (by intro e he; simpa [t] using (mem_filter.1 he).2)
  have hle : (E.filter fun e => φ (f e.1, g e.2)).card ≤ t.card * Hpad := by
    rw [hfib]
    calc ∑ γ ∈ t, ((E.filter fun e => φ (f e.1, g e.2)).filter fun e => (f e.1, g e.2) = γ).card
        ≤ ∑ _γ ∈ t, Hpad := sum_le_sum fun γ _ =>
          (card_le_card (filter_subset_filter _ (filter_subset _ _))).trans (hload γ)
      _ = t.card * Hpad := by simp
  calc (E.filter fun e => φ (f e.1, g e.2)).card * r ≤ t.card * Hpad * r := Nat.mul_le_mul_right _ hle
    _ = Hpad * (t.card * r) := by ring
    _ = Hpad * Fintype.card K ^ 2 := by rw [hφ]

/-- Each symbol of a coordinate is taken by exactly `1/r` of the labels in `[r]^a`. -/
theorem card_fiber {a r : ℕ} (c : Fin a) (σ : Fin r) :
    (univ.filter fun k : Fin a → Fin r => k c = σ).card * r = Fintype.card (Fin a → Fin r) := by
  have hfib := card_eq_sum_card_fiberwise (f := fun k : Fin a → Fin r => k c)
    (s := univ) (t := univ) (by simp)
  have heq : ∀ σ' : Fin r, (univ.filter fun k : Fin a → Fin r => k c = σ').card =
      (univ.filter fun k : Fin a → Fin r => k c = σ).card := by
    intro σ'
    refine card_nbij' (fun k => Equiv.swap σ σ' ∘ k) (fun k => Equiv.swap σ σ' ∘ k) ?_ ?_ ?_ ?_
    · intro k hk; simp only [coe_filter, Set.mem_ofPred_eq, mem_univ, true_and] at hk ⊢
      simp [hk]
    · intro k hk; simp only [coe_filter, Set.mem_ofPred_eq, mem_univ, true_and] at hk ⊢
      simp [hk]
    · intro k _; funext j; simp
    · intro k _; funext j; simp
  rw [card_univ] at hfib
  rw [hfib]
  rw [sum_congr rfl fun σ' _ => heq σ', sum_const, card_univ, Fintype.card_fin, smul_eq_mul,
    mul_comm]

/-- `lem:tensor-packets`, item 3, and the child bound `6M/r` of `subsec:tensor-children`. -/
theorem child_edges (E : Finset (α × β)) {a r : ℕ} (f : α → Fin a → Fin r) (g : β → Fin a → Fin r)
    {Hpad P L : ℕ} (hload : ∀ γ, load E f g γ ≤ Hpad)
    (hPL : P * L = Hpad * Fintype.card (Fin a → Fin r) ^ 2) (h3 : P * L ≤ 3 * E.card)
    (c : Fin a) (σ : Fin r) :
    ((E.filter fun e => f e.1 c = σ).card + (E.filter fun e => g e.2 c = σ).card) * r
      ≤ 6 * E.card := by
  have hrow : (univ.filter fun γ : (Fin a → Fin r) × (Fin a → Fin r) => γ.1 c = σ).card * r = Fintype.card (Fin a → Fin r) ^ 2 := by
    have : (univ.filter fun γ : (Fin a → Fin r) × (Fin a → Fin r) => γ.1 c = σ) = (univ.filter fun k : Fin a → Fin r => k c = σ) ×ˢ univ := by
      ext γ; simp
    rw [this, card_product, card_univ, mul_right_comm, card_fiber, sq]
  have hcol : (univ.filter fun γ : (Fin a → Fin r) × (Fin a → Fin r) => γ.2 c = σ).card * r = Fintype.card (Fin a → Fin r) ^ 2 := by
    have : (univ.filter fun γ : (Fin a → Fin r) × (Fin a → Fin r) => γ.2 c = σ) = univ ×ˢ (univ.filter fun k : Fin a → Fin r => k c = σ) := by
      ext γ; simp
    rw [this, card_product, card_univ, mul_assoc, card_fiber, sq]
  have h1 := class_edges_le E f g hload (fun γ : (Fin a → Fin r) × (Fin a → Fin r) => γ.1 c = σ) hrow
  have h2 := class_edges_le E f g hload (fun γ : (Fin a → Fin r) × (Fin a → Fin r) => γ.2 c = σ) hcol
  simp only at h1 h2
  rw [add_mul]
  omega

/-- For `r = 64`, every child has at most `M/8` edges. -/
theorem child_edges_le_eighth (E : Finset (α × β)) {a : ℕ} (f : α → Fin a → Fin 64)
    (g : β → Fin a → Fin 64) {Hpad P L : ℕ} (hload : ∀ γ, load E f g γ ≤ Hpad)
    (hPL : P * L = Hpad * Fintype.card (Fin a → Fin 64) ^ 2) (h3 : P * L ≤ 3 * E.card)
    (c : Fin a) (σ : Fin 64) :
    ((E.filter fun e => f e.1 c = σ).card + (E.filter fun e => g e.2 c = σ).card) * 8 ≤ E.card := by
  have := child_edges E f g hload hPL h3 c σ
  omega

end ModeCount
