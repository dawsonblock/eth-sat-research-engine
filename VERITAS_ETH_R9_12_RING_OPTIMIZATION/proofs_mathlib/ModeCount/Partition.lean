import Mathlib

/-!
# The weighted mode-tuple count (`eq:tensor-mode-budget`, `eq:tensor-partition-count`)

`enum ws r` chooses the exponents of the modes with weights `ws` one at a time,
each subject to the remaining budget. It lists exactly the tuples `β` with
`∑ wᵢ βᵢ < r`, once each. Its length satisfies the paper's generating-product
bound and, when at most `m` modes share any one weight, `exp (π √(2 m r / 3))`.
-/

open Real Finset

namespace ModeCount

/-- Number of exponents `b` with `w * b < r`, for `1 ≤ w`. -/
def feasible (w r : ℕ) : ℕ := (r + w - 1) / w

/-- Successive choice of exponents subject to the remaining budget. -/
def enum : List ℕ → ℕ → List (List ℕ)
  | [], r => if 0 < r then [[]] else []
  | w :: ws, r => (List.range (feasible w r)).flatMap fun b => (enum ws (r - w * b)).map (b :: ·)

/-- `∑ wᵢ βᵢ` over the common prefix. -/
def wsum : List ℕ → List ℕ → ℕ
  | w :: ws, b :: bs => w * b + wsum ws bs
  | _, _ => 0

theorem lt_feasible_iff {w r b : ℕ} (hw : 1 ≤ w) : b < feasible w r ↔ w * b < r := by
  unfold feasible
  rw [← Nat.add_one_le_iff, Nat.le_div_iff_mul_le (by omega)]
  constructor <;> intro h <;> nlinarith [Nat.sub_add_cancel (show 1 ≤ r + w by omega)]

theorem mem_enum {ws : List ℕ} (hw : ∀ w ∈ ws, 1 ≤ w) {r : ℕ} {β : List ℕ} :
    β ∈ enum ws r ↔ β.length = ws.length ∧ wsum ws β < r := by
  induction ws generalizing r β with
  | nil =>
    cases β <;> by_cases h : 0 < r <;> simp [enum, wsum, h]
  | cons w ws ih =>
    have hw1 : 1 ≤ w := hw w (by simp)
    have ih' := fun {r} {β} => ih (fun x hx => hw x (by simp [hx])) (r := r) (β := β)
    cases β with
    | nil => simp [enum]
    | cons b γ =>
      simp only [enum, List.mem_flatMap, List.mem_range, List.mem_map, List.length_cons, wsum]
      constructor
      · rintro ⟨c, hc, δ, hδ, hcons⟩
        obtain ⟨rfl, rfl⟩ := List.cons.inj hcons
        rw [lt_feasible_iff hw1] at hc
        rw [ih'] at hδ
        exact ⟨by simp [hδ.1], by omega⟩
      · rintro ⟨hlen, hsum⟩
        refine ⟨b, (lt_feasible_iff hw1).2 (by omega), γ, ih'.2 ⟨by simpa using hlen, by omega⟩, rfl⟩

theorem nodup_enum (ws : List ℕ) (r : ℕ) : (enum ws r).Nodup := by
  induction ws generalizing r with
  | nil => by_cases h : 0 < r <;> simp [enum, h]
  | cons w ws ih =>
    simp only [enum]
    rw [List.nodup_flatMap]
    refine ⟨fun b _ => (ih _).map (List.cons_injective), ?_⟩
    refine (List.pairwise_lt_range).imp fun {a b} hab => ?_
    show List.Disjoint _ _
    rw [List.disjoint_left]
    intro x hxa hxb
    simp only [List.mem_map] at hxa hxb
    obtain ⟨_, _, rfl⟩ := hxa
    obtain ⟨_, _, h⟩ := hxb
    exact absurd (List.cons.inj h).1 (by omega)

theorem length_enum_cons (w : ℕ) (ws : List ℕ) (r : ℕ) :
    (enum (w :: ws) r).length = ∑ b ∈ range (feasible w r), (enum ws (r - w * b)).length := by
  simp only [enum, List.length_flatMap, List.length_map]
  generalize feasible w r = n
  induction n with
  | zero => simp
  | succ n ihn => rw [List.range_succ, List.map_append, List.sum_append, ihn, sum_range_succ]; simp

/-- The generating-product bound, by induction on the modes. -/
theorem length_enum_le_product {θ : ℝ} (hθ : 0 < θ) {ws : List ℕ} (hw : ∀ w ∈ ws, 1 ≤ w) (r : ℕ) :
    ((enum ws r).length : ℝ) ≤ exp (θ * r) * (ws.map fun w : ℕ => (1 - exp (-θ * w))⁻¹).prod := by
  induction ws generalizing r with
  | nil =>
    by_cases h : 0 < r
    · simp only [enum, h, ite_true, List.length_singleton, List.map_nil, List.prod_nil, mul_one,
        Nat.cast_one]
      exact one_le_exp (by positivity)
    · simp only [enum, h, ite_false, List.length_nil, Nat.cast_zero, List.map_nil, List.prod_nil, mul_one]
      positivity
  | cons w ws ih =>
    have hw1 : 1 ≤ w := hw w (by simp)
    have ih' := ih (fun x hx => hw x (by simp [hx]))
    set Q := (ws.map fun w : ℕ => (1 - exp (-θ * w))⁻¹).prod
    set x := exp (-θ * w)
    have hx0 : 0 ≤ x := (exp_pos _).le
    have hx1 : x < 1 := exp_lt_one_iff.2 (by have : (1:ℝ) ≤ w := (by exact_mod_cast hw1); nlinarith)
    rw [length_enum_cons, Nat.cast_sum, List.map_cons, List.prod_cons]
    calc ∑ b ∈ range (feasible w r), ((enum ws (r - w * b)).length : ℝ)
        ≤ ∑ b ∈ range (feasible w r), exp (θ * r) * Q * x ^ b := by
          refine sum_le_sum fun b hb => ?_
          have hb' : w * b < r := (lt_feasible_iff hw1).1 (mem_range.1 hb)
          refine (ih' _).trans (le_of_eq ?_)
          rw [Nat.cast_sub hb'.le, ← exp_nat_mul, Nat.cast_mul]
          rw [mul_comm (exp _) Q, mul_comm (exp (θ * r)) Q, mul_assoc, ← exp_add]
          ring_nf
      _ = exp (θ * r) * Q * ∑ b ∈ range (feasible w r), x ^ b := by rw [mul_sum]
      _ ≤ exp (θ * r) * Q * (1 - x)⁻¹ := by
          gcongr
          · exact mul_nonneg (exp_pos _).le (List.prod_nonneg fun y hy => by
              obtain ⟨v, _, rfl⟩ := List.mem_map.1 hy
              exact inv_nonneg.2 (sub_nonneg.2 (exp_le_one_iff.2
                (by have := (Nat.cast_nonneg v : (0:ℝ) ≤ v); nlinarith))))
          · rw [range_eq_Ico]
            simpa [div_eq_mul_inv] using geom_sum_Ico_le_of_lt_one hx0 hx1 (m := 0) (n := feasible w r)
      _ = exp (θ * r) * ((1 - x)⁻¹ * Q) := by ring

/-- `∑ⱼ -log (1 - e^{-θ j}) ≤ π²/(6θ)` over any finite set of positive weights. -/
theorem prod_inv_one_sub_exp_le {θ : ℝ} (hθ : 0 < θ) (S : Finset ℕ) (hS : ∀ j ∈ S, 1 ≤ j) :
    ∏ j ∈ S, (1 - exp (-θ * j))⁻¹ ≤ exp (π ^ 2 / 6 / θ) := by
  have hx : ∀ j ∈ S, |exp (-θ * j)| < 1 := fun j hj => by
    rw [abs_of_pos (exp_pos _), exp_lt_one_iff]
    have : (1:ℝ) ≤ j := by exact_mod_cast hS j hj
    nlinarith
  have hfactor : ∀ j ∈ S, (1 - exp (-θ * j))⁻¹ = exp (-log (1 - exp (-θ * j))) := fun j hj => by
    rw [exp_neg, exp_log (by linarith [abs_lt.1 (hx j hj)])]
  rw [prod_congr rfl hfactor, ← exp_sum]
  refine exp_le_exp.2 ?_
  have hsum : HasSum (fun n : ℕ => ∑ j ∈ S, exp (-θ * j) ^ (n + 1) / (n + 1))
      (∑ j ∈ S, -log (1 - exp (-θ * j))) :=
    hasSum_sum fun j hj => hasSum_pow_div_log_of_abs_lt_one (hx j hj)
  have hzeta : HasSum (fun n : ℕ => 1 / θ * (1 / ((n : ℝ) + 1) ^ 2)) (1 / θ * (π ^ 2 / 6)) := by
    have := (hasSum_nat_add_iff' 1).2 hasSum_zeta_two
    simp only [range_one, sum_singleton, Nat.cast_zero, ne_eq, OfNat.ofNat_ne_zero,
      not_false_eq_true, zero_pow, div_zero, sub_zero, Nat.cast_add, Nat.cast_one] at this
    exact this.mul_left _
  have key : ∀ n : ℕ, ∑ j ∈ S, exp (-θ * j) ^ (n + 1) / (n + 1) ≤ 1 / θ * (1 / ((n : ℝ) + 1) ^ 2) := by
    intro n
    set t : ℝ := θ * (n + 1)
    have ht : 0 < t := by positivity
    set y := exp (-t)
    have hy0 : 0 ≤ y := (exp_pos _).le
    have hy1 : y < 1 := exp_lt_one_iff.2 (by linarith)
    have hpow : ∀ j : ℕ, exp (-θ * j) ^ (n + 1) = y ^ j := fun j => by
      rw [← exp_nat_mul, ← exp_nat_mul]; congr 1; push_cast; ring
    simp_rw [hpow, ← sum_div]
    have hsub : S ⊆ Ico 1 (S.sup id + 1) := fun j hj =>
      mem_Ico.2 ⟨hS j hj, Nat.lt_succ_of_le (le_sup (f := id) hj)⟩
    have hgeom : ∑ j ∈ S, y ^ j ≤ y / (1 - y) :=
      (sum_le_sum_of_subset_of_nonneg hsub fun _ _ _ => pow_nonneg hy0 _).trans
        (by simpa using geom_sum_Ico_le_of_lt_one hy0 hy1 (m := 1) (n := S.sup id + 1))
    have hbound : y / (1 - y) ≤ 1 / t := by
      rw [div_le_div_iff₀ (by linarith) ht]
      have h1 : y * exp t = 1 := by rw [← exp_add]; simp
      nlinarith [add_one_le_exp t, exp_pos t]
    have hn : (0:ℝ) < n + 1 := by positivity
    calc (∑ j ∈ S, y ^ j) / (n + 1) ≤ 1 / t / (n + 1) := by gcongr; exact hgeom.trans hbound
      _ = 1 / θ * (1 / ((n : ℝ) + 1) ^ 2) := by field_simp [t]; ring
  have := hasSum_le key hsum hzeta
  calc ∑ j ∈ S, -log (1 - exp (-θ * j)) ≤ 1 / θ * (π ^ 2 / 6) := this
    _ = π ^ 2 / 6 / θ := by ring

/-- `∏ (1 - e^{-θ w})⁻¹ ≤ exp (m π² / (6θ))` when at most `m` weights equal any one value. -/
theorem prod_le_of_multiplicity {θ : ℝ} (hθ : 0 < θ) {ws : List ℕ} (hw : ∀ w ∈ ws, 1 ≤ w) {m : ℕ}
    (hm : ∀ k, ws.count k ≤ m) :
    (ws.map fun w : ℕ => (1 - exp (-θ * w))⁻¹).prod ≤ exp (m * (π ^ 2 / 6 / θ)) := by
  have hge : ∀ j ∈ ws.toFinset, 1 ≤ (1 - exp (-θ * j))⁻¹ := fun j hj => by
    have : (1:ℝ) ≤ j := by exact_mod_cast hw j (List.mem_toFinset.1 hj)
    have h0 : 0 < exp (-θ * j) := exp_pos _
    have h1 : exp (-θ * j) < 1 := exp_lt_one_iff.2 (by nlinarith)
    exact one_le_inv₀ (by linarith) |>.2 (by linarith)
  rw [Finset.prod_list_map_count]
  calc ∏ j ∈ ws.toFinset, (1 - exp (-θ * j))⁻¹ ^ ws.count j
      ≤ ∏ j ∈ ws.toFinset, (1 - exp (-θ * j))⁻¹ ^ m :=
        Finset.prod_le_prod₀ (fun j hj => pow_nonneg (zero_le_one.trans (hge j hj)) _)
          fun j hj => pow_le_pow_right₀ (hge j hj) (hm j)
    _ = (∏ j ∈ ws.toFinset, (1 - exp (-θ * j))⁻¹) ^ m := prod_pow _ _ _
    _ ≤ exp (π ^ 2 / 6 / θ) ^ m := by
        gcongr
        · exact prod_nonneg fun j hj => zero_le_one.trans (hge j hj)
        · exact prod_inv_one_sub_exp_le hθ _ fun j hj => hw j (List.mem_toFinset.1 hj)
    _ = exp (m * (π ^ 2 / 6 / θ)) := by rw [← exp_nat_mul]

/-- The counting estimate for every `θ > 0`. -/
theorem length_enum_le_theta {θ : ℝ} (hθ : 0 < θ) {ws : List ℕ} (hw : ∀ w ∈ ws, 1 ≤ w) {m : ℕ}
    (hm : ∀ k, ws.count k ≤ m) (r : ℕ) :
    ((enum ws r).length : ℝ) ≤ exp (θ * r + m * (π ^ 2 / 6 / θ)) := by
  rw [exp_add]
  exact (length_enum_le_product hθ hw r).trans
    (mul_le_mul_of_nonneg_left (prod_le_of_multiplicity hθ hw hm) (exp_pos _).le)

/-- `eq:tensor-partition-count` with the optimal `θ`: at most `exp (π √(2 m r / 3))` tuples. -/
theorem length_enum_le {ws : List ℕ} (hw : ∀ w ∈ ws, 1 ≤ w) {m : ℕ} (hm0 : 0 < m)
    (hm : ∀ k, ws.count k ≤ m) {r : ℕ} (hr : 0 < r) :
    ((enum ws r).length : ℝ) ≤ exp (π * √(2 * m * r / 3)) := by
  set s := √((m : ℝ) * r / 6)
  have hs : 0 < s := sqrt_pos.2 (by positivity)
  have hs2 : s ^ 2 = m * r / 6 := sq_sqrt (by positivity)
  have hr' : (0:ℝ) < r := by exact_mod_cast hr
  have hθ : 0 < π * s / r := by positivity
  refine (length_enum_le_theta hθ hw hm r).trans (exp_le_exp.2 (le_of_eq ?_))
  have h4 : √(2 * (m : ℝ) * r / 3) = 2 * s := by
    rw [show 2 * (m : ℝ) * r / 3 = 2 ^ 2 * (m * r / 6) by ring, sqrt_mul (by norm_num), sqrt_sq (by norm_num)]
  rw [h4]
  field_simp
  nlinarith [hs2, pi_pos]

end ModeCount
