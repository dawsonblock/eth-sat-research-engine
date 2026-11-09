import ModeCount.Valuation

/-!
# The parameter schedule and the size conditions of `precision_bound`

`eq:tensor-parameters`: `u_d = ⌊ελ/2^d⌋` with `ε = 1/131072`,
`a_d = 2 ∑_{j ≤ d} u_j`, `a_{d-1} = 2 ∑_{j < d} u_j`. The paper asserts the
size conditions "for sufficiently large `s`". Here:

* `depth_bound`: `M·8^d ≤ Cs` and `s ≤ M·r` with `r² ≤ λ` (a call above the
  leaf cutoff `H = ⌈s/⌊√λ⌋⌉`) give `(2^d)^6 ≤ C²λ`.
* `lam_lt_of_depth`: then `λ < 2^34 C² (u_d + 1)²`, so `u_d` grows with `λ`.
* `schedule_bound`: there is `λ₀`, depending only on `C`, such that for every
  `λ ≥ λ₀` and every such depth, `u_d ≥ 1` and `need C λ ≤ 2^{u_d}`.
* `size_conditions`: hence `A·u ≤ M·2^u` and `8(a+1)u ≤ 2^{a_{d-1}+u}` for
  every active call, with `A` the precision envelope of `path_precision`.
-/

open Finset Filter Topology

namespace ModeCount

def uSched (lam d : ℕ) : ℕ := lam / (131072 * 2 ^ d)

def aPrev (lam d : ℕ) : ℕ := 2 * ∑ j ∈ range d, uSched lam j

def aSched (lam d : ℕ) : ℕ := aPrev lam d + 2 * uSched lam d

theorem uSched_le (lam d : ℕ) : uSched lam d ≤ lam := Nat.div_le_self _ _

theorem sum_div_two_pow_le (n d : ℕ) : ∑ j ∈ range d, n / 2 ^ j ≤ 2 * n := by
  induction d generalizing n with
  | zero => simp
  | succ d ih =>
    rw [sum_range_succ']
    have h : ∀ j, n / 2 ^ (j + 1) = n / 2 / 2 ^ j := fun j => by
      rw [Nat.div_div_eq_div_mul, pow_succ']
    simp only [h, pow_zero, Nat.div_one]
    have := ih (n / 2)
    omega

theorem aSched_le (lam d : ℕ) : aSched lam d ≤ lam := by
  have h : ∀ j, uSched lam j = lam / 131072 / 2 ^ j := fun j => by
    rw [uSched, Nat.div_div_eq_div_mul]
  have hs := sum_div_two_pow_le (lam / 131072) (d + 1)
  unfold aSched aPrev
  rw [sum_range_succ] at hs
  simp only [h] at hs ⊢
  omega

theorem depth_bound {lam C s M r d : ℕ} (hs : 0 < s) (hM : M * 8 ^ d ≤ C * s) (hH : s ≤ M * r)
    (hr : r ^ 2 ≤ lam) : (2 ^ d) ^ 6 ≤ C ^ 2 * lam := by
  have h1 : s * 8 ^ d ≤ s * (C * r) := by
    calc s * 8 ^ d ≤ M * r * 8 ^ d := Nat.mul_le_mul_right _ hH
      _ = M * 8 ^ d * r := by ring
      _ ≤ C * s * r := Nat.mul_le_mul_right _ hM
      _ = s * (C * r) := by ring
  have h2 : 8 ^ d ≤ C * r := Nat.le_of_mul_le_mul_left h1 hs
  calc (2 ^ d) ^ 6 = (8 ^ d) ^ 2 := by
        rw [show (8 : ℕ) = 2 ^ 3 by norm_num, ← pow_mul, ← pow_mul, ← pow_mul]; ring_nf
    _ ≤ (C * r) ^ 2 := Nat.pow_le_pow_left h2 2
    _ = C ^ 2 * r ^ 2 := by ring
    _ ≤ C ^ 2 * lam := Nat.mul_le_mul_left _ hr

theorem lam_lt_of_depth {lam d C : ℕ} (h : (2 ^ d) ^ 6 ≤ C ^ 2 * lam) :
    lam < 2 ^ 34 * C ^ 2 * (uSched lam d + 1) ^ 2 := by
  set t := 2 ^ d
  set u := uSched lam d
  have ht : 1 ≤ t := Nat.one_le_two_pow
  have hq : (0 : ℕ) < 131072 * t := by positivity
  have hlt : lam < 131072 * t * (u + 1) := Nat.lt_mul_div_succ lam hq
  have h5 : t * t ^ 5 < t * (C ^ 2 * 131072 * (u + 1)) := by
    calc t * t ^ 5 = t ^ 6 := by ring
      _ ≤ C ^ 2 * lam := h
      _ < C ^ 2 * (131072 * t * (u + 1)) := by
        rcases Nat.eq_zero_or_pos C with hC | hC
        · subst hC; simp at h; exact absurd h (by positivity)
        · exact Nat.mul_lt_mul_of_pos_left hlt (by positivity)
      _ = t * (C ^ 2 * 131072 * (u + 1)) := by ring
  have h6 : t ^ 5 < C ^ 2 * 131072 * (u + 1) := Nat.lt_of_mul_lt_mul_left h5
  have h7 : t ≤ t ^ 5 := Nat.le_self_pow (by norm_num) t
  calc lam < 131072 * t * (u + 1) := hlt
    _ ≤ 131072 * (C ^ 2 * 131072 * (u + 1)) * (u + 1) := by
      apply Nat.mul_le_mul_right; apply Nat.mul_le_mul_left; omega
    _ = 2 ^ 34 * C ^ 2 * (u + 1) ^ 2 := by ring

theorem eventually_poly_le_two_pow (B k : ℕ) : ∃ U, ∀ u ≥ U, B * (u + 1) ^ k ≤ 2 ^ u := by
  have ht := tendsto_pow_const_div_const_pow_of_one_lt k (r := (2 : ℝ)) (by norm_num)
  have hpos : (0 : ℝ) < 1 / ((B : ℝ) * 2 ^ k + 1) := by positivity
  obtain ⟨U, hU⟩ := eventually_atTop.1 (ht.eventually (gt_mem_nhds hpos))
  refine ⟨max U 1, fun u hu => ?_⟩
  have hu1 : 1 ≤ u := le_of_max_le_right hu
  have h := hU u (le_of_max_le_left hu)
  have h2 : (0 : ℝ) < 2 ^ u := by positivity
  have hlt : (u : ℝ) ^ k * ((B : ℝ) * 2 ^ k + 1) < 2 ^ u := by
    rw [div_lt_div_iff₀ h2 (by positivity), one_mul] at h
    linarith
  have hsh : ((u : ℝ) + 1) ^ k ≤ 2 ^ k * (u : ℝ) ^ k := by
    rw [← mul_pow]; exact pow_le_pow_left₀ (by positivity) (by
      have : (1 : ℝ) ≤ u := by exact_mod_cast hu1
      linarith) k
  have hfin : (B : ℝ) * ((u : ℝ) + 1) ^ k ≤ 2 ^ u := by
    have hB : (0 : ℝ) ≤ B := Nat.cast_nonneg _
    have hk : (0 : ℝ) ≤ (u : ℝ) ^ k := by positivity
    nlinarith [mul_le_mul_of_nonneg_left hsh hB]
  exact_mod_cast hfin

/-- What both size conditions need from `2^u`. -/
def need (C lam : ℕ) : ℕ := (C + 8) ^ 3 * 50 * (lam + 1) ^ 4

theorem schedule_bound (C : ℕ) : ∃ lam₀, ∀ lam ≥ lam₀, ∀ d, (2 ^ d) ^ 6 ≤ C ^ 2 * lam →
    1 ≤ uSched lam d ∧ need C lam ≤ 2 ^ uSched lam d := by
  set B := (C + 8) ^ 3 * 50 * (2 ^ 34 * C ^ 2 + 1) ^ 4
  obtain ⟨U, hU⟩ := eventually_poly_le_two_pow B 8
  refine ⟨2 ^ 34 * C ^ 2 * (max U 1 + 1) ^ 2, fun lam hlam d hd => ?_⟩
  have hlt := lam_lt_of_depth hd
  set u := uSched lam d
  have hu : max U 1 < u := by
    by_contra hle
    push Not at hle
    have : 2 ^ 34 * C ^ 2 * (u + 1) ^ 2 ≤ 2 ^ 34 * C ^ 2 * (max U 1 + 1) ^ 2 :=
      Nat.mul_le_mul_left _ (Nat.pow_le_pow_left (by omega) 2)
    omega
  refine ⟨by omega, ?_⟩
  have hlam1 : lam + 1 ≤ (2 ^ 34 * C ^ 2 + 1) * (u + 1) ^ 2 := by
    have : 1 ≤ (u + 1) ^ 2 := Nat.one_le_pow _ _ (by omega)
    nlinarith
  calc need C lam = (C + 8) ^ 3 * 50 * (lam + 1) ^ 4 := rfl
    _ ≤ (C + 8) ^ 3 * 50 * ((2 ^ 34 * C ^ 2 + 1) * (u + 1) ^ 2) ^ 4 :=
      Nat.mul_le_mul_left _ (Nat.pow_le_pow_left hlam1 4)
    _ = B * (u + 1) ^ 8 := by ring
    _ ≤ 2 ^ u := hU u (by omega)

theorem envelope_le {A0 C s lam : ℕ} {h M a : ℕ → ℕ} (hA0 : A0 ≤ C * s)
    (hh : ∀ j, h j ≤ 4 * C * s) (hM : ∀ j, M j ≤ C * s) (ha : ∀ j, a j ≤ lam) (d : ℕ) :
    envelope A0 h M a d ≤ C * s * (1 + d * (40 + 8 * lam)) := by
  induction d with
  | zero => simpa [envelope] using hA0
  | succ d ih =>
    simp only [envelope]
    have e1 : 8 * h d ≤ 32 * (C * s) := by have := hh d; nlinarith
    have e2 : 8 * M d * (a d + 1) ≤ 8 * (C * s) * (lam + 1) :=
      Nat.mul_le_mul (Nat.mul_le_mul_left _ (hM d)) (by have := ha d; omega)
    nlinarith

/-- `precision_bound`'s size conditions, from the schedule, for all large `λ`. -/
theorem size_conditions (C : ℕ) (hC : 1 ≤ C) : ∃ lam₀, ∀ lam ≥ lam₀, ∀ d M s A : ℕ,
    (2 ^ d) ^ 6 ≤ C ^ 2 * lam → s ≤ M * lam → A ≤ C * s * (1 + d * (40 + 8 * lam)) →
      A * uSched lam d ≤ M * 2 ^ uSched lam d ∧
      8 * (aSched lam d + 1) * uSched lam d ≤ 2 ^ (aPrev lam d + uSched lam d) := by
  obtain ⟨lam₀, h⟩ := schedule_bound C
  refine ⟨lam₀, fun lam hlam d M s A hd hs hA => ?_⟩
  obtain ⟨_, hneed⟩ := h lam hlam d hd
  set u := uSched lam d
  have hu := uSched_le lam d
  have ha := aSched_le lam d
  have hdl : d ≤ C ^ 2 * lam :=
    (Nat.lt_two_pow_self.le.trans (Nat.le_self_pow (by norm_num) _)).trans hd
  have hC8 : C ≤ C + 8 := by omega
  have hc3 : C ^ 3 ≤ (C + 8) ^ 3 := Nat.pow_le_pow_left hC8 3
  have hl1 : (1 : ℕ) ≤ lam + 1 := by omega
  constructor
  · have hfac : 1 + d * (40 + 8 * lam) ≤ C ^ 2 * (50 * (lam + 1) ^ 2) := by
      have : d * (40 + 8 * lam) ≤ C ^ 2 * lam * (40 + 8 * lam) := Nat.mul_le_mul_right _ hdl
      have hC2 : 1 ≤ C ^ 2 := Nat.one_le_pow _ _ hC
      nlinarith
    calc A * u ≤ C * s * (1 + d * (40 + 8 * lam)) * lam := Nat.mul_le_mul hA hu
      _ ≤ C * (M * lam) * (C ^ 2 * (50 * (lam + 1) ^ 2)) * lam :=
        Nat.mul_le_mul_right _ (Nat.mul_le_mul (Nat.mul_le_mul_left _ hs) hfac)
      _ = M * (C ^ 3 * 50 * (lam ^ 2 * (lam + 1) ^ 2)) := by ring
      _ ≤ M * ((C + 8) ^ 3 * 50 * (lam + 1) ^ 4) := by
        apply Nat.mul_le_mul_left
        have : lam ^ 2 * (lam + 1) ^ 2 ≤ (lam + 1) ^ 4 := by
          have : lam ^ 2 ≤ (lam + 1) ^ 2 := Nat.pow_le_pow_left (by omega) 2
          nlinarith
        exact Nat.mul_le_mul (Nat.mul_le_mul_right _ hc3) this
      _ ≤ M * 2 ^ u := Nat.mul_le_mul_left _ hneed
  · calc 8 * (aSched lam d + 1) * u ≤ 8 * (lam + 1) * lam :=
          Nat.mul_le_mul (Nat.mul_le_mul_left _ (by omega)) hu
      _ ≤ need C lam := by
        unfold need
        have h8 : 8 ≤ (C + 8) ^ 3 := le_trans (by omega) (Nat.le_self_pow (by norm_num) _)
        have : lam ≤ (lam + 1) ^ 3 := le_trans (by omega) (Nat.le_self_pow (by norm_num) _)
        calc 8 * (lam + 1) * lam ≤ (C + 8) ^ 3 * 50 * (lam + 1) * (lam + 1) ^ 3 :=
              Nat.mul_le_mul (Nat.mul_le_mul_right _ (by omega)) this
          _ = _ := by ring
      _ ≤ 2 ^ u := hneed
      _ ≤ 2 ^ (aPrev lam d + u) := Nat.pow_le_pow_right (by norm_num) (by omega)

/-- `eq:tensor-precision-bound` on the actual schedule, for all large `λ`. -/
theorem scheduled_precision_bound (C : ℕ) (hC : 1 ≤ C) : ∃ lam₀, ∀ lam ≥ lam₀,
    ∀ d M s A p h i Dt : ℕ, (2 ^ d) ^ 6 ≤ C ^ 2 * lam → s ≤ M * lam →
      A ≤ C * s * (1 + d * (40 + 8 * lam)) → i < uSched lam d →
      Dt * 2 ^ i = 2 ^ aSched lam d → h * uSched lam d ≤ 4 * M → p ≤ A * 2 ^ aPrev lam d →
        nodePrecision p h Dt M (aSched lam d) * uSched lam d ≤ 34 * M * Dt := by
  obtain ⟨lam₀, h⟩ := size_conditions C hC
  refine ⟨lam₀, fun lam hlam d M s A p hh i Dt hd hs hA hi hD hhu hp => ?_⟩
  obtain ⟨hAu, hlog⟩ := h lam hlam d M s A hd hs hA
  unfold aSched at hD hlog ⊢
  exact precision_bound hi hD hhu hp hAu hlog

end ModeCount
