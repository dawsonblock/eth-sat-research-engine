import ModeCount.TotalCost

/-!
# The subexponential closure of `subsec:tensor-cost`

`total_calls` bounds the recursion by `(n+1) Q^n exp(2^11 κ C s / √λ)`.
This file absorbs `(n+1) Q^n`, a leaf of `2^{⌈s/⌊√λ⌋⌉}` assignments and an entry
exponent `L (⌊log₂(s+1)⌋+1)` into `exp(O(s/√λ))`, and makes the schedule
threshold a closed term `lamZero C`. `exp(K s / √⌊log₂ s⌋)` is then `2^{o(s)}`.

The inequality needs `λ ≥ lamZero C`. For the precision constant `C = 34`
that threshold is far past every input the engine can run. Nothing here
proves the recursion identity, Hermite recovery, or that a concrete call
tree meets the branching hypothesis, so it does not prove a subexponential
algorithm and it does not bear on ETH.
-/

namespace ModeCount

open Real

set_option exponentiation.threshold 1024

theorem two_mul_pow (k : ℕ) : 2 * 2 ^ k = 2 ^ (k + 1) := by
  rw [Nat.pow_succ, Nat.mul_comm]

theorem two_le_exp_one : (2 : ℝ) ≤ exp 1 := by
  have h := add_one_le_exp (1 : ℝ)
  norm_num at h
  exact h

/-! ### An explicit `2^u` beats `B (u+1)^8` -/

theorem eight_k_le_pow (k : ℕ) (hk : 6 ≤ k) : 8 * k + 15 ≤ 2 ^ k := by
  induction k with
  | zero => omega
  | succ k ih =>
    cases Nat.lt_or_ge k 6 with
    | inl h =>
      have hk5 : k = 5 := by omega
      subst hk5
      decide
    | inr h =>
      have ih' := ih h
      have h8 : 8 ≤ 2 ^ k := by
        have : (2 : ℕ) ^ 3 ≤ 2 ^ k := Nat.pow_le_pow_right (by decide) (by omega)
        simpa using this
      calc 8 * (k + 1) + 15 = 8 * k + 15 + 8 := by ring
        _ ≤ 2 ^ k + 8 := Nat.add_le_add_right ih' _
        _ ≤ 2 ^ k + 2 ^ k := Nat.add_le_add_left h8 _
        _ = 2 ^ (k + 1) := by rw [← Nat.two_mul]; exact two_mul_pow k

theorem log_linear (S : ℕ) (hS : 64 ≤ S) : 8 * Nat.log2 (S + 1) + 15 ≤ S := by
  have hne : S ≠ 0 := by omega
  have hk : 6 ≤ S.log2 := (Nat.le_log2 hne).mpr (by omega : 2 ^ 6 ≤ S)
  by_cases hpow : S + 1 = 2 ^ (S.log2 + 1)
  · have hlog : (S + 1).log2 = S.log2 + 1 := by rw [hpow, Nat.log2_two_pow]
    rw [hlog]
    set k := S.log2
    have h8 : 8 * k + 23 ≤ 2 ^ (k + 1) - 1 := by
      have hbase := eight_k_le_pow k hk
      have h9 : 9 ≤ 2 ^ k := by
        have : (2 : ℕ) ^ 4 ≤ 2 ^ k := Nat.pow_le_pow_right (by decide) (by omega)
        omega
      calc 8 * k + 23 = 8 * k + 15 + 8 := by ring
        _ ≤ 2 ^ k + 8 := Nat.add_le_add_right hbase _
        _ ≤ 2 ^ (k + 1) - 1 := by
          have : 2 ^ k + 9 ≤ 2 ^ (k + 1) := by
            calc 2 ^ k + 9 ≤ 2 ^ k + 2 ^ k := Nat.add_le_add_left h9 _
              _ = 2 ^ (k + 1) := by rw [← Nat.two_mul]; exact two_mul_pow k
          omega
    have hS' : S = 2 ^ (k + 1) - 1 := by
      have : S + 1 = 2 ^ (k + 1) := by simpa [k] using hpow
      omega
    omega
  · have hlt : S + 1 < 2 ^ (S.log2 + 1) := by
      have hle : S + 1 ≤ 2 ^ (S.log2 + 1) := Nat.succ_le_of_lt (Nat.lt_log2_self (n := S))
      exact lt_of_le_of_ne hle hpow
    have hlog : (S + 1).log2 ≤ S.log2 :=
      Nat.le_of_lt_succ ((Nat.log2_lt (by omega)).mpr hlt)
    calc 8 * (S + 1).log2 + 15 ≤ 8 * S.log2 + 15 :=
          Nat.add_le_add_right (Nat.mul_le_mul_left _ hlog) _
      _ ≤ 2 ^ S.log2 := eight_k_le_pow _ hk
      _ ≤ S := Nat.log2_self_le hne

theorem eight_step (u : ℕ) (hu : 30 ≤ u) : (u + 2) ^ 8 ≤ 2 * (u + 1) ^ 8 := by
  have h32 : (32 : ℕ) ^ 8 ≤ 2 * 31 ^ 8 := by decide
  have hmul : (u + 2) * 31 ≤ (u + 1) * 32 := by omega
  have hpow : ((u + 2) * 31) ^ 8 ≤ ((u + 1) * 32) ^ 8 := Nat.pow_le_pow_left hmul 8
  have : (u + 2) ^ 8 * 31 ^ 8 ≤ (2 * (u + 1) ^ 8) * 31 ^ 8 := by
    calc (u + 2) ^ 8 * 31 ^ 8 = ((u + 2) * 31) ^ 8 := by rw [Nat.mul_pow]
      _ ≤ ((u + 1) * 32) ^ 8 := hpow
      _ = (u + 1) ^ 8 * 32 ^ 8 := by rw [Nat.mul_pow]
      _ ≤ (u + 1) ^ 8 * (2 * 31 ^ 8) := Nat.mul_le_mul_left _ h32
      _ = (u + 1) ^ 8 * 2 * 31 ^ 8 := by rw [← Nat.mul_assoc]
      _ = 2 * (u + 1) ^ 8 * 31 ^ 8 := by rw [Nat.mul_comm ((u + 1) ^ 8) 2]
      _ = (2 * (u + 1) ^ 8) * 31 ^ 8 := by rw [Nat.mul_assoc]
  exact Nat.le_of_mul_le_mul_right this (by decide)

theorem pow8_from (u : ℕ) (hu : 128 ≤ u) : (u + 1) ^ 8 ≤ 2 ^ (u - 64) := by
  induction u with
  | zero => omega
  | succ u ih =>
    cases Nat.lt_or_ge u 128 with
    | inl h =>
      have hu' : u = 127 := by omega
      subst hu'
      decide
    | inr h =>
      have ih' := ih h
      calc (u + 1 + 1) ^ 8 ≤ 2 * (u + 1) ^ 8 := eight_step u (by omega)
        _ ≤ 2 * 2 ^ (u - 64) := Nat.mul_le_mul_left _ ih'
        _ = 2 ^ (u - 64 + 1) := two_mul_pow _
        _ = 2 ^ ((u + 1) - 64) := by congr 1; omega

theorem pow_slack_large (S u : ℕ) (hS : 64 ≤ S)
    (hu : S + 8 * ((S + 1).log2 + 2) ≤ u) : (u + 1) ^ 8 ≤ 2 ^ (u - S) := by
  let u0 := S + 8 * ((S + 1).log2 + 2)
  induction u with
  | zero => omega
  | succ u ih =>
    cases Nat.lt_or_ge u u0 with
    | inl h =>
      have hu0 : u + 1 = u0 := by omega
      rw [hu0]
      set k := (S + 1).log2
      have hlin : u0 + 1 ≤ 2 * (S + 1) := by
        have := log_linear S hS
        dsimp [u0, k]
        omega
      have hlt : 2 * (S + 1) < 2 ^ (k + 2) := by
        calc 2 * (S + 1) < 2 * 2 ^ ((S + 1).log2 + 1) :=
              Nat.mul_lt_mul_of_pos_left Nat.lt_log2_self (by decide)
          _ = 2 ^ (k + 2) := by
            rw [show (S + 1).log2 = k by rfl, show k + 2 = (k + 1) + 1 by omega]
            exact two_mul_pow (k + 1)
      have hle : u0 + 1 ≤ 2 ^ (k + 2) := le_of_lt (lt_of_le_of_lt hlin hlt)
      have hexp : u0 - S = 8 * (k + 2) := by dsimp [u0, k]; omega
      calc (u0 + 1) ^ 8 ≤ (2 ^ (k + 2)) ^ 8 := Nat.pow_le_pow_left hle 8
        _ = 2 ^ ((k + 2) * 8) := by rw [← Nat.pow_mul]
        _ = 2 ^ (8 * (k + 2)) := by ring_nf
        _ = 2 ^ (u0 - S) := by rw [hexp]
    | inr h =>
      have ih' := ih h
      calc (u + 1 + 1) ^ 8 ≤ 2 * (u + 1) ^ 8 := eight_step u (by omega)
        _ ≤ 2 * 2 ^ (u - S) := Nat.mul_le_mul_left _ ih'
        _ = 2 ^ (u - S + 1) := two_mul_pow _
        _ = 2 ^ ((u + 1) - S) := by congr 1; omega

/-- `B (u+1)^8 ≤ 2^u` once `u` passes an explicit function of `B`. -/
def polyU (B : ℕ) : ℕ :=
  let S := Nat.log2 B + 1
  max 128 (S + 8 * (Nat.log2 (S + 1) + 2))

theorem poly_le_two_pow (B u : ℕ) (hu : polyU B ≤ u) : B * (u + 1) ^ 8 ≤ 2 ^ u := by
  set S := Nat.log2 B + 1
  have hB : B ≤ 2 ^ S := le_of_lt (by simpa [S] using (Nat.lt_log2_self (n := B)))
  have hslack : (u + 1) ^ 8 ≤ 2 ^ (u - S) := by
    by_cases hS : 64 ≤ S
    · exact pow_slack_large S u hS (by
        have : S + 8 * ((S + 1).log2 + 2) ≤ polyU B := by
          dsimp [polyU, S]
          exact le_max_right _ _
        omega)
    · have hu' : 128 ≤ u := by
        have : 128 ≤ polyU B := by dsimp [polyU]; exact le_max_left _ _
        omega
      have hS' : S < 64 := Nat.not_le.mp hS
      calc (u + 1) ^ 8 ≤ 2 ^ (u - 64) := pow8_from u hu'
        _ ≤ 2 ^ (u - S) := Nat.pow_le_pow_right (by decide)
            (Nat.sub_le_sub_left (Nat.le_of_lt hS') u)
  calc B * (u + 1) ^ 8 ≤ 2 ^ S * (u + 1) ^ 8 := Nat.mul_le_mul_right _ hB
    _ ≤ 2 ^ S * 2 ^ (u - S) := Nat.mul_le_mul_left _ hslack
    _ = 2 ^ (S + (u - S)) := by rw [← Nat.pow_add]
    _ = 2 ^ u := by
      have hSu : S ≤ u := by
        have : S ≤ polyU B := by
          dsimp [polyU, S]
          exact le_trans (Nat.le_add_right S _) (le_max_right _ _)
        omega
      congr 1
      omega

/-! ### `λ₀(C)` as a term -/

def scheduleB (C : ℕ) : ℕ := (C + 8) ^ 3 * 50 * (2 ^ 34 * C ^ 2 + 1) ^ 4

/-- Every active depth of every `λ ≥ lamZero C` has `u_d ≥ 1` and `need C λ ≤ 2^{u_d}`. -/
def lamZero (C : ℕ) : ℕ := 2 ^ 34 * C ^ 2 * (polyU (scheduleB C) + 1) ^ 2

theorem schedule_bound_explicit (C lam d : ℕ) (hlam : lamZero C ≤ lam)
    (hd : (2 ^ d) ^ 6 ≤ C ^ 2 * lam) :
    1 ≤ uSched lam d ∧ need C lam ≤ 2 ^ uSched lam d := by
  set B := scheduleB C
  have hlt := lam_lt_of_depth hd
  set u := uSched lam d
  have hU : polyU B < u := by
    by_contra hle
    have hle' : u ≤ polyU B := by omega
    have : 2 ^ 34 * C ^ 2 * (u + 1) ^ 2 ≤ lamZero C := by
      dsimp [lamZero, B]
      exact Nat.mul_le_mul_left _ (Nat.pow_le_pow_left (by omega : u + 1 ≤ polyU B + 1) 2)
    omega
  refine ⟨by omega, ?_⟩
  have hlam1 : lam + 1 ≤ (2 ^ 34 * C ^ 2 + 1) * (u + 1) ^ 2 := by
    have : 1 ≤ (u + 1) ^ 2 := Nat.one_le_pow _ _ (by omega)
    nlinarith
  calc need C lam = (C + 8) ^ 3 * 50 * (lam + 1) ^ 4 := rfl
    _ ≤ (C + 8) ^ 3 * 50 * ((2 ^ 34 * C ^ 2 + 1) * (u + 1) ^ 2) ^ 4 :=
      Nat.mul_le_mul_left _ (Nat.pow_le_pow_left hlam1 4)
    _ = B * (u + 1) ^ 8 := by
      simp only [B, scheduleB, Nat.mul_pow]
      rw [← Nat.pow_mul]
      ring_nf
    _ ≤ 2 ^ u := poly_le_two_pow B u (by omega)

/-! ### The polynomial prefactor and the depth -/

/-- Nodes, residue values and groups at one call: `2L · (M(2L-1)+1) · r`. -/
def callFactor (L M r : ℕ) : ℕ := 2 * L * (M * (2 * L - 1) + 1) * r

theorem callFactor_le {L M r s C : ℕ} (hL : L ^ 1000 ≤ s) (hM : M ≤ C * s) (hr : r ≤ 64)
    (hs : 1 ≤ s) : callFactor L M r ≤ 128 * (2 * C + 1) * s ^ 3 := by
  have hLs : L ≤ s := le_trans (Nat.le_pow (by decide : 0 < 1000)) hL
  have hterm : M * (2 * L - 1) + 1 ≤ (2 * C + 1) * s ^ 2 := by
    have hsub : 2 * L - 1 ≤ 2 * L := Nat.sub_le _ _
    calc M * (2 * L - 1) + 1 ≤ M * (2 * L) + 1 :=
          Nat.add_le_add_right (Nat.mul_le_mul_left _ hsub) _
      _ ≤ C * s * (2 * s) + 1 :=
          Nat.add_le_add_right (Nat.mul_le_mul hM (Nat.mul_le_mul_left _ hLs)) _
      _ = 2 * C * s ^ 2 + 1 := by ring
      _ ≤ 2 * C * s ^ 2 + s ^ 2 := Nat.add_le_add_left (Nat.one_le_pow 2 s (by omega)) _
      _ = (2 * C + 1) * s ^ 2 := by ring
  calc callFactor L M r = 2 * L * (M * (2 * L - 1) + 1) * r := rfl
    _ ≤ 2 * s * ((2 * C + 1) * s ^ 2) * 64 :=
      Nat.mul_le_mul (Nat.mul_le_mul (Nat.mul_le_mul_left _ hLs) hterm) hr
    _ = 128 * (2 * C + 1) * s ^ 3 := by ring

theorem callFactor_small {L M r s lam C : ℕ} (hL : L ^ 1000 ≤ s) (hM : M ≤ C * s)
    (hr : r ≤ 64) (hs : 1 ≤ s) (hsz : s ≤ 2 ^ lam) (hCl : C ≤ 2 ^ lam)
    (hlam : 8 ≤ lam) : callFactor L M r ≤ 2 ^ (8 * lam) := by
  have hpoly := callFactor_le hL hM hr hs
  have hC1 : 2 * C + 1 ≤ 2 ^ (lam + 2) := by
    have hpow : 2 * 2 ^ lam = 2 ^ (lam + 1) := two_mul_pow lam
    calc 2 * C + 1 ≤ 2 * 2 ^ lam + 1 := Nat.add_le_add_right (Nat.mul_le_mul_left _ hCl) _
      _ ≤ 2 ^ (lam + 1) + 2 ^ (lam + 1) := by
        have : 1 ≤ 2 ^ (lam + 1) := Nat.one_le_pow _ _ (by decide)
        omega
      _ = 2 ^ (lam + 2) := by rw [← Nat.two_mul]; exact two_mul_pow (lam + 1)
  have hs3 : s ^ 3 ≤ 2 ^ (3 * lam) := by
    calc s ^ 3 ≤ (2 ^ lam) ^ 3 := Nat.pow_le_pow_left hsz 3
      _ = 2 ^ (lam * 3) := by rw [← Nat.pow_mul]
      _ = 2 ^ (3 * lam) := by ring_nf
  calc callFactor L M r ≤ 128 * (2 * C + 1) * s ^ 3 := hpoly
    _ ≤ 2 ^ 7 * 2 ^ (lam + 2) * 2 ^ (3 * lam) := by
      refine Nat.mul_le_mul (Nat.mul_le_mul ?_ hC1) hs3
      decide
    _ = 2 ^ (4 * lam + 9) := by
      rw [← Nat.pow_add, ← Nat.pow_add]
      congr 1
      omega
    _ ≤ 2 ^ (8 * lam) := Nat.pow_le_pow_right (by decide) (by omega)

theorem cube_le_pow (lam : ℕ) (hlam : 32 ≤ lam) : 256 * lam ^ 3 ≤ 2 ^ (lam - 2) := by
  induction lam with
  | zero => omega
  | succ lam ih =>
    cases Nat.lt_or_ge lam 32 with
    | inl h =>
      have hlam31 : lam = 31 := by omega
      subst hlam31
      decide
    | inr h =>
      have ih' := ih h
      have hmul : (lam + 1) ^ 3 ≤ 2 * lam ^ 3 := by
        have hcoef : (lam + 1) * 4 ≤ 5 * lam := by omega
        have hpow : ((lam + 1) * 4) ^ 3 ≤ (5 * lam) ^ 3 := Nat.pow_le_pow_left hcoef 3
        have : (lam + 1) ^ 3 * 64 ≤ 125 * lam ^ 3 := by simpa [Nat.mul_pow] using hpow
        have h125 : 125 * lam ^ 3 ≤ 128 * lam ^ 3 := Nat.mul_le_mul_right _ (by decide)
        have htwo : (lam + 1) ^ 3 * 64 ≤ (2 * lam ^ 3) * 64 := by
          calc (lam + 1) ^ 3 * 64 ≤ 125 * lam ^ 3 := this
            _ ≤ 128 * lam ^ 3 := h125
            _ = (2 * lam ^ 3) * 64 := by ring
        exact Nat.le_of_mul_le_mul_right htwo (by decide)
      calc 256 * (lam + 1) ^ 3 ≤ 256 * (2 * lam ^ 3) := Nat.mul_le_mul_left _ hmul
        _ = 2 * (256 * lam ^ 3) := by ring
        _ ≤ 2 * 2 ^ (lam - 2) := Nat.mul_le_mul_left _ ih'
        _ = 2 ^ (lam - 2 + 1) := two_mul_pow _
        _ = 2 ^ ((lam + 1) - 2) := by congr 1; omega

/-- An active depth obeying `(2^j)^6 ≤ C^2 λ` with `C ≤ λ` is `O(log λ)`. -/
theorem depth_is_logarithmic {C lam j : ℕ} (hC : C ≤ lam) (_hlam : 64 ≤ lam)
    (h : (2 ^ j) ^ 6 ≤ C ^ 2 * lam) : j ≤ 8 * Nat.log2 (lam + 1) + 8 := by
  have h6 : 2 ^ (6 * j) ≤ C ^ 2 * lam := by
    calc 2 ^ (6 * j) = 2 ^ (j * 6) := by ring_nf
      _ = (2 ^ j) ^ 6 := by rw [Nat.pow_mul]
      _ ≤ C ^ 2 * lam := h
  have hbox : C ^ 2 * lam ≤ (lam + 1) ^ 3 := by
    calc C ^ 2 * lam ≤ lam ^ 2 * lam := Nat.mul_le_mul_right _ (Nat.pow_le_pow_left hC 2)
      _ = lam ^ 3 := by ring
      _ ≤ (lam + 1) ^ 3 := Nat.pow_le_pow_left (by omega) _
  have htop : (lam + 1) ^ 3 ≤ 2 ^ (3 * ((lam + 1).log2 + 1)) := by
    calc (lam + 1) ^ 3 ≤ (2 ^ ((lam + 1).log2 + 1)) ^ 3 :=
          Nat.pow_le_pow_left (le_of_lt Nat.lt_log2_self) _
      _ = 2 ^ (((lam + 1).log2 + 1) * 3) := by rw [← Nat.pow_mul]
      _ = 2 ^ (3 * ((lam + 1).log2 + 1)) := by ring_nf
  have : 2 ^ (6 * j) ≤ 2 ^ (3 * ((lam + 1).log2 + 1)) := le_trans (le_trans h6 hbox) htop
  have hj : 6 * j ≤ 3 * ((lam + 1).log2 + 1) :=
    (Nat.pow_le_pow_iff_right (by decide : 1 < 2)).mp this
  omega

/-! ### Absorbing `(n+1) Q^n` -/

theorem eight_lam_le_pow (lam : ℕ) (h : 6 ≤ lam) : 8 * lam + 9 ≤ 2 ^ lam := by
  induction lam with
  | zero => omega
  | succ lam ih =>
    cases Nat.lt_or_ge lam 6 with
    | inl hlt =>
      have hlam5 : lam = 5 := by omega
      subst hlam5
      decide
    | inr hge =>
      have ih' := ih hge
      have h8 : 8 ≤ 2 ^ lam := by
        have : (2 : ℕ) ^ 3 ≤ 2 ^ lam := Nat.pow_le_pow_right (by decide) (by omega)
        simpa using this
      calc 8 * (lam + 1) + 9 = 8 * lam + 9 + 8 := by ring
        _ ≤ 2 ^ lam + 2 ^ lam := Nat.add_le_add ih' h8
        _ = 2 ^ (lam + 1) := by rw [← Nat.two_mul]; exact two_mul_pow lam

theorem prefactor_exponent {lam n : ℕ} (hlam : 64 ≤ lam)
    (hn : n ≤ 8 * Nat.log2 (lam + 1) + 8) :
    lam * (8 * n + 1) ≤ 2 ^ (lam - 2) / (lam + 1) := by
  set a := Nat.log2 (lam + 1) + 2
  have hlog : Nat.log2 (lam + 1) ≤ lam := by
    have hlt : (lam + 1).log2 < lam + 1 :=
      (Nat.log2_lt (by omega)).mpr (Nat.lt_two_pow_self (n := lam + 1))
    omega
  have hn8 : 8 * n + 1 ≤ 64 * a := by dsimp [a]; omega
  have ha : a ≤ 2 * lam := by dsimp [a]; omega
  have hb : lam + 1 ≤ 2 * lam := by omega
  have hgrow : 64 * a * (lam + 1) * lam ≤ 256 * lam ^ 3 := by
    have h1 : 64 * a ≤ 64 * (2 * lam) := Nat.mul_le_mul_left _ ha
    have h2 : 64 * a * (lam + 1) ≤ 64 * (2 * lam) * (2 * lam) := Nat.mul_le_mul h1 hb
    calc 64 * a * (lam + 1) * lam ≤ 64 * (2 * lam) * (2 * lam) * lam :=
          Nat.mul_le_mul_right _ h2
      _ = 256 * lam ^ 3 := by ring
  have hmul : lam * (8 * n + 1) * (lam + 1) ≤ 2 ^ (lam - 2) := by
    calc lam * (8 * n + 1) * (lam + 1) ≤ lam * (64 * a) * (lam + 1) :=
          Nat.mul_le_mul_right _ (Nat.mul_le_mul_left _ hn8)
      _ = 64 * a * (lam + 1) * lam := by ring
      _ ≤ 256 * lam ^ 3 := hgrow
      _ ≤ 2 ^ (lam - 2) := cube_le_pow lam (by omega)
  exact (Nat.le_div_iff_mul_le (by omega)).mpr hmul

theorem two_rpow_le_exp {x : ℝ} (hx : 0 ≤ x) : (2 : ℝ) ^ x ≤ exp x := by
  rw [Real.rpow_def_of_pos (by norm_num : (0 : ℝ) < 2)]
  refine exp_le_exp.mpr ?_
  have hlog : Real.log 2 ≤ 1 :=
    (Real.log_le_iff_le_exp (by norm_num)).mpr two_le_exp_one
  calc Real.log 2 * x ≤ 1 * x := mul_le_mul_of_nonneg_right hlog hx
    _ = x := by rw [one_mul]

theorem natPow_le_exp {e s lam : ℕ} (hlam : 1 ≤ lam) (hs : 2 ^ (lam - 1) ≤ s)
    (he : e ≤ 2 ^ (lam - 2) / (lam + 1)) :
    (2 ^ e : ℝ) ≤ exp ((s : ℝ) / √(lam : ℝ)) := by
  have hdiv : (e : ℝ) ≤ (2 ^ (lam - 2) : ℝ) / (lam + 1) := by
    have hmul : e * (lam + 1) ≤ 2 ^ (lam - 2) := (Nat.le_div_iff_mul_le (by omega)).mp he
    have : (e : ℝ) * (lam + 1) ≤ (2 ^ (lam - 2) : ℝ) := by exact_mod_cast hmul
    exact (le_div_iff₀ (by positivity)).mpr this
  have hroot : √(lam : ℝ) ≤ lam + 1 := by
    rw [← Real.sqrt_sq (by positivity : (0 : ℝ) ≤ (lam : ℝ) + 1)]
    exact Real.sqrt_le_sqrt (by nlinarith : (lam : ℝ) ≤ ((lam : ℝ) + 1) ^ 2)
  have hlow : (2 ^ (lam - 2) : ℝ) / (lam + 1) ≤ (s : ℝ) / √(lam : ℝ) := by
    have hs' : (2 ^ (lam - 1) : ℝ) ≤ s := by exact_mod_cast hs
    have htwo : (2 ^ (lam - 2) : ℝ) ≤ 2 ^ (lam - 1) := by
      exact_mod_cast Nat.pow_le_pow_right (by decide : 0 < 2) (by omega : lam - 2 ≤ lam - 1)
    have hsqrt : (0 : ℝ) < √(lam : ℝ) := Real.sqrt_pos.2 (by exact_mod_cast (by omega : 0 < lam))
    calc (2 ^ (lam - 2) : ℝ) / (lam + 1) ≤ (2 ^ (lam - 1) : ℝ) / (lam + 1) := by
          gcongr
      _ ≤ (s : ℝ) / (lam + 1) := by gcongr
      _ ≤ (s : ℝ) / √(lam : ℝ) :=
          div_le_div_of_nonneg_left (by exact_mod_cast (Nat.zero_le s)) hsqrt hroot
  have hle : (e : ℝ) ≤ (s : ℝ) / √(lam : ℝ) := le_trans hdiv hlow
  calc (2 ^ e : ℝ) = (2 : ℝ) ^ (e : ℕ) := by norm_cast
    _ = (2 : ℝ) ^ (e : ℝ) := (Real.rpow_natCast 2 e).symm
    _ ≤ (2 : ℝ) ^ ((s : ℝ) / √(lam : ℝ)) :=
      Real.rpow_le_rpow_of_exponent_le (by norm_num) hle
    _ ≤ exp ((s : ℝ) / √(lam : ℝ)) := two_rpow_le_exp (by positivity)

theorem prefactor_le_exp {lam n Q : ℕ} (hlam : 64 ≤ lam)
    (hn : n ≤ 8 * Nat.log2 (lam + 1) + 8) (hQ : Q ≤ 2 ^ (8 * lam)) {s : ℕ}
    (hs : 2 ^ (lam - 1) ≤ s) :
    ((n + 1) * Q ^ n : ℝ) ≤ exp ((s : ℝ) / √(lam : ℝ)) := by
  have hlog : Nat.log2 (lam + 1) ≤ lam := by
    have hlt : (lam + 1).log2 < lam + 1 :=
      (Nat.log2_lt (by omega)).mpr (Nat.lt_two_pow_self (n := lam + 1))
    omega
  have hone : n + 1 ≤ 2 ^ lam := by
    have hn' : n + 1 ≤ 8 * lam + 9 := by omega
    exact hn'.trans (eight_lam_le_pow lam (by omega))
  have hQn : Q ^ n ≤ 2 ^ (8 * lam * n) := by
    calc Q ^ n ≤ (2 ^ (8 * lam)) ^ n := Nat.pow_le_pow_left hQ _
      _ = 2 ^ ((8 * lam) * n) := by rw [← Nat.pow_mul]
  have hexp : (n + 1) * Q ^ n ≤ 2 ^ (lam * (8 * n + 1)) := by
    calc (n + 1) * Q ^ n ≤ 2 ^ lam * 2 ^ (8 * lam * n) := Nat.mul_le_mul hone hQn
      _ = 2 ^ (lam + 8 * lam * n) := by rw [← Nat.pow_add]
      _ = 2 ^ (lam * (8 * n + 1)) := by ring_nf
  exact (natPow_le_exp (by omega) hs (prefactor_exponent hlam hn)).trans' (by exact_mod_cast hexp)

/-- `subsec:tensor-cost`: the `(n+1) Q^n` factor is absorbed for `λ ≥ 64` and `2^{λ-1} ≤ s`. -/
theorem contraction_calls_bound {lam n Q : ℕ} {C s κ : ℝ} (hlam0 : 0 < lam) (hκ : 0 ≤ κ)
    (hCs : 0 ≤ C * s) (t : CallTree) (b M : ℕ → ℕ) (hb : CallTree.Branch b t) (hbn : b n = 0)
    (hb1 : ∀ j < n, 1 ≤ b j) (hu : ∀ j < n, 1 ≤ uSched lam j)
    (hM : ∀ j < n, (M j : ℝ) * 8 ^ j ≤ C * s)
    (hbQ : ∀ j < n, (b j : ℝ) ≤ Q * exp (κ * (M j / √(uSched lam j))))
    (hlam : 64 ≤ lam) (hn : n ≤ 8 * Nat.log2 (lam + 1) + 8) (hQ : Q ≤ 2 ^ (8 * lam))
    {sN : ℕ} (hsN : s = sN) (hs : 2 ^ (lam - 1) ≤ sN) :
    (t.size : ℝ) ≤ exp ((2 ^ 11 * κ * C + 1) * s / √(lam : ℝ)) := by
  have hcalls := total_calls hlam0 hκ hCs t b M hb hbn hb1 hu hM hbQ
  have hpre := prefactor_le_exp hlam hn hQ hs
  calc (t.size : ℝ) ≤ (n + 1) * Q ^ n * exp (2 ^ 11 * κ * C * s / √(lam : ℝ)) := hcalls
    _ ≤ exp ((sN : ℝ) / √(lam : ℝ)) * exp (2 ^ 11 * κ * C * s / √(lam : ℝ)) := by
      refine mul_le_mul_of_nonneg_right ?_ (exp_pos _).le
      simpa using hpre
    _ = exp ((2 ^ 11 * κ * C + 1) * s / √(lam : ℝ)) := by
      rw [← exp_add, hsN]
      congr 1
      ring

/-! ### Leaf, entry, and the total -/

theorem direct_leaf_le {s lam : ℕ} (hlam : 4 ≤ lam) (hs : 2 ≤ s) (hu : Nat.sqrt lam ≤ s) :
    (2 ^ (s / Nat.sqrt lam + 1) : ℝ) ≤ exp (3 * (s : ℝ) / √(lam : ℝ)) := by
  set u := Nat.sqrt lam
  have hu2 : 2 ≤ u := by
    by_contra h
    have h1 : u ≤ 1 := by omega
    have hsq : (u + 1) * (u + 1) ≤ 4 := by interval_cases u <;> decide
    have hlt : lam < (u + 1) * (u + 1) := by
      simpa [u, Nat.succ_eq_add_one] using Nat.lt_succ_sqrt lam
    omega
  have h2exp : (2 : ℝ) ≤ exp 1 := two_le_exp_one
  have hnat : (2 ^ (s / u + 1) : ℝ) ≤ exp (↑(s / u + 1)) := by
    calc (2 ^ (s / u + 1) : ℝ) = (2 : ℝ) ^ (s / u + 1) := by norm_cast
      _ ≤ (exp 1) ^ (s / u + 1) := pow_le_pow_left₀ (by norm_num) h2exp _
      _ = exp (↑(s / u + 1) * 1) := (Real.exp_nat_mul (1 : ℝ) _).symm
      _ = exp (↑(s / u + 1)) := by rw [mul_one]
  have hsq : (u : ℝ) ≤ √(lam : ℝ) := by
    have hnat_sq : u * u ≤ lam := by simpa [u] using Nat.sqrt_le lam
    rw [← Real.sqrt_mul_self (by positivity : (0 : ℝ) ≤ (u : ℝ))]
    exact Real.sqrt_le_sqrt (by exact_mod_cast hnat_sq)
  have hlt : √(lam : ℝ) < (u : ℝ) + 1 := by
    have hnat_lt : lam < (u + 1) * (u + 1) := by
      simpa [u, Nat.succ_eq_add_one] using Nat.lt_succ_sqrt lam
    have hcast : (lam : ℝ) < ((u : ℝ) + 1) * ((u : ℝ) + 1) := by exact_mod_cast hnat_lt
    have := (Real.sqrt_lt_sqrt_iff (by positivity)).2 hcast
    rwa [Real.sqrt_mul_self (by positivity : (0 : ℝ) ≤ (u : ℝ) + 1)] at this
  have hu0 : (0 : ℝ) < u := by exact_mod_cast (by omega : 0 < u)
  have hsqrt : (0 : ℝ) < √(lam : ℝ) := Real.sqrt_pos.2 (by exact_mod_cast (by omega : 0 < lam))
  have hratio : √(lam : ℝ) / u ≤ (3 / 2 : ℝ) := by
    rw [div_le_iff₀ hu0]
    have hu2' : (2 : ℝ) ≤ u := by exact_mod_cast hu2
    linarith
  have hhalf : (s : ℝ) / u ≤ (3 / 2) * ((s : ℝ) / √(lam : ℝ)) := by
    have hs0 : (0 : ℝ) ≤ (s : ℝ) / √(lam : ℝ) := by positivity
    calc (s : ℝ) / u = ((s : ℝ) / √(lam : ℝ)) * (√(lam : ℝ) / u) := by field_simp
      _ ≤ ((s : ℝ) / √(lam : ℝ)) * (3 / 2) := mul_le_mul_of_nonneg_left hratio hs0
      _ = (3 / 2) * ((s : ℝ) / √(lam : ℝ)) := by ring
  have hone : (1 : ℝ) ≤ (3 / 2) * ((s : ℝ) / √(lam : ℝ)) := by
    have hsqrt_le : √(lam : ℝ) ≤ (3 / 2) * s := by
      have hu_le : (u : ℝ) ≤ s := by exact_mod_cast hu
      have hs2' : (2 : ℝ) ≤ s := by exact_mod_cast hs
      linarith
    rw [show (3 / 2) * ((s : ℝ) / √(lam : ℝ)) = ((3 / 2) * s) / √(lam : ℝ) by ring]
    exact (one_le_div hsqrt).mpr hsqrt_le
  have hlin : (↑(s / u + 1) : ℝ) ≤ 3 * (s : ℝ) / √(lam : ℝ) := by
    have hdiv : (↑(s / u) : ℝ) ≤ (s : ℝ) / u := Nat.cast_div_le (m := s) (n := u)
    calc (↑(s / u + 1) : ℝ) = (↑(s / u) : ℝ) + 1 := by norm_cast
      _ ≤ (s : ℝ) / u + 1 := by linarith
      _ ≤ (3 / 2) * ((s : ℝ) / √(lam : ℝ)) + (3 / 2) * ((s : ℝ) / √(lam : ℝ)) := by
        linarith
      _ = 3 * (s : ℝ) / √(lam : ℝ) := by ring
  exact hnat.trans (exp_le_exp.mpr hlin)

theorem sq_half_exp (n : ℕ) (hn : 32 ≤ n) : (2 * n + 3) ^ 2 ≤ 2 ^ (n - 2) := by
  induction n with
  | zero => omega
  | succ n ih =>
    cases Nat.lt_or_ge n 32 with
    | inl h =>
      have hn31 : n = 31 := by omega
      subst hn31
      decide
    | inr h =>
      have ih' := ih h
      have hstep : (2 * (n + 1) + 3) ^ 2 ≤ 2 * (2 * n + 3) ^ 2 := by
        have hdiff : 4 * (2 * n + 3) + 4 ≤ (2 * n + 3) ^ 2 := by
          have hge : 4 ≤ 2 * n + 3 := by omega
          have hmul : 4 * (2 * n + 3) ≤ (2 * n + 3) * (2 * n + 3) :=
            Nat.mul_le_mul_right (2 * n + 3) hge
          have hgap : 4 * (2 * n + 3) + 4 ≤ (2 * n + 3) * (2 * n + 3) := by
            have hsub : (2 * n + 3) * 4 + 4 ≤ (2 * n + 3) * (2 * n + 3) := by
              have hrest : 4 ≤ (2 * n + 3) * ((2 * n + 3) - 4) := by
                have hone : 1 ≤ 2 * n + 3 - 4 := by omega
                exact le_trans hge (by
                  simpa using Nat.mul_le_mul_left (2 * n + 3) hone)
              have hsplit : (2 * n + 3) * 4 + (2 * n + 3) * (2 * n + 3 - 4) =
                  (2 * n + 3) * (2 * n + 3) := by
                have : 4 + (2 * n + 3 - 4) = 2 * n + 3 := by omega
                rw [← Nat.mul_add, this]
              omega
            simpa [Nat.mul_comm] using hsub
          exact hgap.trans (by rw [Nat.pow_two])
        calc (2 * (n + 1) + 3) ^ 2 = (2 * n + 5) ^ 2 := by ring
          _ = (2 * n + 3) ^ 2 + 4 * (2 * n + 3) + 4 := by ring
          _ ≤ (2 * n + 3) ^ 2 + (2 * n + 3) ^ 2 := Nat.add_le_add_left hdiff _
          _ = 2 * (2 * n + 3) ^ 2 := by ring
      calc (2 * (n + 1) + 3) ^ 2 ≤ 2 * (2 * n + 3) ^ 2 := hstep
        _ ≤ 2 * 2 ^ (n - 2) := Nat.mul_le_mul_left _ ih'
        _ = 2 ^ (n - 2 + 1) := two_mul_pow _
        _ = 2 ^ ((n + 1) - 2) := by congr 1; omega

/-- `L^1000 ≤ s ≤ 2^λ` makes the entry exponent `L(⌊log₂(s+1)⌋+1)` fit under `s/√λ`. -/
theorem entry_exponent_le {L s lam : ℕ} (hL : L ^ 1000 ≤ s) (hs : s ≤ 2 ^ lam) (hlam : 64 ≤ lam)
    (hs0 : 1 ≤ s) : L * ((s + 1).log2 + 1) ≤ 2 ^ (lam - 2) / (lam + 1) := by
  set k := (lam + 999) / 1000
  have hmod : (lam + 999) % 1000 < 1000 := Nat.mod_lt _ (by decide)
  have heq : k * 1000 + (lam + 999) % 1000 = lam + 999 := by
    simpa [k] using Nat.div_add_mod' (lam + 999) 1000
  have hk : lam ≤ k * 1000 := by omega
  have hLle : L ≤ 2 ^ k := by
    have hpow : 2 ^ lam ≤ (2 ^ k) ^ 1000 := by
      calc 2 ^ lam ≤ 2 ^ (k * 1000) := Nat.pow_le_pow_right (by decide) hk
        _ = (2 ^ k) ^ 1000 := by rw [Nat.pow_mul]
    exact (Nat.pow_le_pow_iff_left (by decide)).mp (le_trans hL (le_trans hs hpow))
  have hlog : (s + 1).log2 + 1 ≤ lam + 2 := by
    have hs1 : s + 1 ≤ 2 ^ (lam + 1) := by
      calc s + 1 ≤ 2 ^ lam + 1 := Nat.add_le_add_right hs _
        _ ≤ 2 ^ lam + 2 ^ lam := Nat.add_le_add_left (Nat.one_le_pow _ _ (by decide)) _
        _ = 2 ^ (lam + 1) := by rw [← Nat.two_mul]; exact two_mul_pow lam
    have hlt : s + 1 < 2 ^ (lam + 2) :=
      lt_of_le_of_lt hs1 (Nat.pow_lt_pow_right (by decide) (by omega))
    have : (s + 1).log2 < lam + 2 := (Nat.log2_lt (by omega)).mpr hlt
    omega
  have hk2 : k ≤ lam / 2 := by
    have h499 : 1499 ≤ 499 * lam := by
      calc 1499 ≤ 31936 := by decide
        _ = 499 * 64 := by decide
        _ ≤ 499 * lam := Nat.mul_le_mul_left _ hlam
    have hlin : lam + 999 ≤ 500 * (lam - 1) := by omega
    have hmod2 : lam % 2 ≤ 1 := by
      have := Nat.mod_lt lam (by decide : 0 < 2)
      omega
    have heq2 : lam = 2 * (lam / 2) + lam % 2 := (Nat.div_add_mod lam 2).symm
    have h2mul : lam - 1 ≤ 2 * (lam / 2) := by omega
    have hhalf : lam + 999 ≤ 1000 * (lam / 2) := by
      calc lam + 999 ≤ 500 * (lam - 1) := hlin
        _ ≤ 500 * (2 * (lam / 2)) := Nat.mul_le_mul_left _ h2mul
        _ = 1000 * (lam / 2) := by ring
    have hmul : k * 1000 ≤ lam + 999 := by
      simpa [k, Nat.mul_comm] using Nat.div_mul_le_self (lam + 999) 1000
    have : 1000 * k ≤ 1000 * (lam / 2) := by
      rw [Nat.mul_comm]
      exact hmul.trans hhalf
    exact Nat.le_of_mul_le_mul_left this (by decide)
  have hhalf : (lam + 2) ^ 2 ≤ 2 ^ (lam / 2 - 2) := by
    have hn : 32 ≤ lam / 2 := (Nat.le_div_iff_mul_le (by decide)).mpr (by omega)
    have hsq := sq_half_exp (lam / 2) hn
    have hmod2 : lam % 2 ≤ 1 := by
      have := Nat.mod_lt lam (by decide : 0 < 2)
      omega
    have heq2 : lam = 2 * (lam / 2) + lam % 2 := (Nat.div_add_mod lam 2).symm
    have hle : lam + 2 ≤ 2 * (lam / 2) + 3 := by omega
    calc (lam + 2) ^ 2 ≤ (2 * (lam / 2) + 3) ^ 2 := Nat.pow_le_pow_left hle 2
      _ ≤ 2 ^ (lam / 2 - 2) := hsq
  have hprod : 2 ^ (lam / 2) * (lam + 2) * (lam + 1) ≤ 2 ^ (lam - 2) := by
    have hexp : lam / 2 + (lam / 2 - 2) ≤ lam - 2 := by
      have hself : lam / 2 * 2 ≤ lam := Nat.div_mul_le_self lam 2
      have htwo : 2 ≤ lam / 2 := by omega
      have happ : lam / 2 + (lam / 2 - 2) = lam / 2 * 2 - 2 := by omega
      have hsub : lam / 2 * 2 - 2 ≤ lam - 2 := Nat.sub_le_sub_right hself 2
      omega
    calc 2 ^ (lam / 2) * (lam + 2) * (lam + 1) ≤ 2 ^ (lam / 2) * (lam + 2) * (lam + 2) :=
          Nat.mul_le_mul_left _ (by omega : lam + 1 ≤ lam + 2)
      _ = 2 ^ (lam / 2) * (lam + 2) ^ 2 := by ring
      _ ≤ 2 ^ (lam / 2) * 2 ^ (lam / 2 - 2) := Nat.mul_le_mul_left _ hhalf
      _ = 2 ^ (lam / 2 + (lam / 2 - 2)) := by rw [← Nat.pow_add]
      _ ≤ 2 ^ (lam - 2) := Nat.pow_le_pow_right (by decide) hexp
  have : L * ((s + 1).log2 + 1) * (lam + 1) ≤ 2 ^ (lam - 2) := by
    calc L * ((s + 1).log2 + 1) * (lam + 1) ≤ 2 ^ k * (lam + 2) * (lam + 1) := by
          refine Nat.mul_le_mul_right _ (Nat.mul_le_mul hLle ?_)
          omega
      _ ≤ 2 ^ (lam / 2) * (lam + 2) * (lam + 1) :=
          Nat.mul_le_mul_right _ (Nat.mul_le_mul_right _
            (Nat.pow_le_pow_right (by decide) hk2))
      _ ≤ 2 ^ (lam - 2) := hprod
  exact (Nat.le_div_iff_mul_le (by omega)).mpr this

/-- Bit-work of one recursion whose branching, leaf sum and entry routine have the paper's shape. -/
theorem contraction_time_bound {lam n Q L : ℕ} {C s κ : ℝ} (hlam0 : 0 < lam) (hκ : 0 ≤ κ)
    (hCs : 0 ≤ C * s) (t : CallTree) (b M : ℕ → ℕ) (hb : CallTree.Branch b t) (hbn : b n = 0)
    (hb1 : ∀ j < n, 1 ≤ b j) (hu : ∀ j < n, 1 ≤ uSched lam j)
    (hM : ∀ j < n, (M j : ℝ) * 8 ^ j ≤ C * s)
    (hbQ : ∀ j < n, (b j : ℝ) ≤ Q * exp (κ * (M j / √(uSched lam j))))
    (hlam : 64 ≤ lam) (hn : n ≤ 8 * Nat.log2 (lam + 1) + 8) (hQ : Q ≤ 2 ^ (8 * lam))
    {sN : ℕ} (hsN : s = sN) (hslo : 2 ^ (lam - 1) ≤ sN) (hshi : sN ≤ 2 ^ lam)
    (hs2 : 2 ≤ sN) (hsqrt : Nat.sqrt lam ≤ sN) (hL : L ^ 1000 ≤ sN) :
    (t.size : ℝ) * (sN + 1) ^ 8 * (2 : ℝ) ^ (sN / Nat.sqrt lam + 1) *
        (2 : ℝ) ^ (L * ((sN + 1).log2 + 1)) ≤
      exp ((2 ^ 11 * κ * C + 6) * s / √(lam : ℝ)) := by
  have hcalls := contraction_calls_bound hlam0 hκ hCs t b M hb hbn hb1 hu hM hbQ hlam hn hQ hsN hslo
  have hleaf := direct_leaf_le (by omega) hs2 hsqrt
  have hentry := natPow_le_exp (by omega) hslo (entry_exponent_le hL hshi hlam (by omega))
  have hpoly : (sN + 1 : ℝ) ^ 8 ≤ exp ((sN : ℝ) / √(lam : ℝ)) := by
    have hpos : (0 : ℝ) < (sN + 1 : ℝ) := by positivity
    have hs1 : (sN + 1 : ℝ) ≤ (2 : ℝ) ^ (lam + 1) := by
      have : sN + 1 ≤ 2 ^ (lam + 1) := by
        calc sN + 1 ≤ 2 ^ lam + 1 := Nat.add_le_add_right hshi _
          _ ≤ 2 ^ lam + 2 ^ lam := Nat.add_le_add_left (Nat.one_le_pow _ _ (by decide)) _
          _ = 2 ^ (lam + 1) := by rw [← Nat.two_mul]; exact two_mul_pow lam
      exact_mod_cast this
    have hlog : Real.log (sN + 1) ≤ (lam + 1 : ℕ) * Real.log 2 := by
      have hy : (0 : ℝ) < (2 : ℝ) ^ (lam + 1) := by positivity
      have hle := (Real.log_le_log_iff hpos hy).mpr hs1
      rwa [Real.log_pow] at hle
    have hlog2 : Real.log 2 ≤ 1 :=
      (Real.log_le_iff_le_exp (by norm_num)).mpr two_le_exp_one
    have hlog' : Real.log (sN + 1) ≤ (lam + 1 : ℝ) := by
      calc Real.log (sN + 1) ≤ (lam + 1 : ℕ) * Real.log 2 := hlog
        _ = ((lam : ℝ) + 1) * Real.log 2 := by norm_cast
        _ ≤ ((lam : ℝ) + 1) * 1 := mul_le_mul_of_nonneg_left hlog2 (by positivity)
        _ = lam + 1 := mul_one _
    have h8n : 8 * (lam + 1) ^ 2 ≤ 2 ^ (lam - 1) := by
      have h2 : lam + 1 ≤ 2 * lam := by omega
      calc 8 * (lam + 1) ^ 2 ≤ 8 * (2 * lam) ^ 2 :=
            Nat.mul_le_mul_left _ (Nat.pow_le_pow_left h2 2)
        _ = 32 * lam ^ 2 := by ring
        _ ≤ 256 * lam ^ 3 := by
          calc 32 * lam ^ 2 = 32 * lam ^ 2 * 1 := by ring
            _ ≤ 32 * lam ^ 2 * (8 * lam) := Nat.mul_le_mul_left _ (by omega)
            _ = 256 * lam ^ 3 := by ring
        _ ≤ 2 ^ (lam - 2) := cube_le_pow lam (by omega)
        _ ≤ 2 ^ (lam - 1) := Nat.pow_le_pow_right (by decide) (by omega)
    have hdiv : (8 * (lam + 1) : ℝ) ≤ (2 ^ (lam - 1) : ℝ) / (lam + 1) := by
      have hmul : 8 * (lam + 1) * (lam + 1) ≤ 2 ^ (lam - 1) := by
        simpa [Nat.pow_two, Nat.mul_assoc] using h8n
      have : (8 * (lam + 1) : ℝ) * (lam + 1) ≤ (2 ^ (lam - 1) : ℝ) := by exact_mod_cast hmul
      exact (le_div_iff₀ (by positivity)).mpr this
    have hroot : √(lam : ℝ) ≤ (lam : ℝ) + 1 := by
      rw [← Real.sqrt_sq (by positivity : (0 : ℝ) ≤ (lam : ℝ) + 1)]
      exact Real.sqrt_le_sqrt (by nlinarith : (lam : ℝ) ≤ ((lam : ℝ) + 1) ^ 2)
    have hlow : (2 ^ (lam - 1) : ℝ) / (lam + 1) ≤ (sN : ℝ) / √(lam : ℝ) := by
      have hs' : (2 ^ (lam - 1) : ℝ) ≤ sN := by exact_mod_cast hslo
      have hsqrt : (0 : ℝ) < √(lam : ℝ) := Real.sqrt_pos.2 (by exact_mod_cast (by omega : 0 < lam))
      calc (2 ^ (lam - 1) : ℝ) / (lam + 1) ≤ (sN : ℝ) / (lam + 1) := by gcongr
        _ ≤ (sN : ℝ) / √(lam : ℝ) :=
          div_le_div_of_nonneg_left (by exact_mod_cast (Nat.zero_le sN)) hsqrt hroot
    have h8 : 8 * Real.log (sN + 1) ≤ (sN : ℝ) / √(lam : ℝ) := by
      have : 8 * Real.log (sN + 1) ≤ (8 * (lam + 1) : ℝ) := by nlinarith
      exact le_trans this (le_trans hdiv hlow)
    calc (sN + 1 : ℝ) ^ 8 = exp (Real.log ((sN + 1 : ℝ) ^ 8)) := by
          rw [Real.exp_log (by positivity)]
      _ = exp (8 * Real.log (sN + 1)) := by rw [Real.log_pow]; norm_cast
      _ ≤ exp ((sN : ℝ) / √(lam : ℝ)) := exp_le_exp.mpr h8
  have hpos_leaf : (0 : ℝ) ≤ (2 : ℝ) ^ (sN / Nat.sqrt lam + 1) := by positivity
  have hpos_entry : (0 : ℝ) ≤ (2 : ℝ) ^ (L * ((sN + 1).log2 + 1)) := by positivity
  have hpos_poly : (0 : ℝ) ≤ (sN + 1 : ℝ) ^ 8 := by positivity
  calc (t.size : ℝ) * (sN + 1) ^ 8 * (2 : ℝ) ^ (sN / Nat.sqrt lam + 1) *
          (2 : ℝ) ^ (L * ((sN + 1).log2 + 1))
      ≤ exp ((2 ^ 11 * κ * C + 1) * s / √(lam : ℝ)) *
          exp ((sN : ℝ) / √(lam : ℝ)) * exp (3 * (sN : ℝ) / √(lam : ℝ)) *
          exp ((sN : ℝ) / √(lam : ℝ)) := by
        refine mul_le_mul (mul_le_mul (mul_le_mul hcalls hpoly hpos_poly (exp_pos _).le)
          hleaf hpos_leaf (by positivity)) hentry hpos_entry (by positivity)
    _ = exp ((2 ^ 11 * κ * C + 6) * s / √(lam : ℝ)) := by
      rw [← exp_add, ← exp_add, ← exp_add, hsN]
      congr 1
      ring

/-- `exp(K s / √⌊log₂ s⌋)` is `2^{o(s)}`. -/
theorem subexponential_bound {K : ℝ} (hK : 0 ≤ K) {ε : ℝ} (hε : 0 < ε) :
    ∃ S : ℕ, ∀ s ≥ S, exp (K * (s : ℝ) / √(Nat.log2 s : ℝ)) ≤ (2 : ℝ) ^ (ε * s) := by
  have hlog2 : 0 < Real.log 2 := Real.log_pos (by norm_num)
  let t : ℝ := K / (ε * Real.log 2)
  have ht0 : 0 ≤ t := div_nonneg hK (mul_pos hε hlog2).le
  let tsq : ℝ := t * t
  let N : ℕ := max 1 (Nat.ceil tsq)
  refine ⟨2 ^ N, fun s hs => ?_⟩
  have hNpos : 1 ≤ N := le_max_left _ _
  have hspos : s ≠ 0 := by
    exact Nat.ne_of_gt (lt_of_lt_of_le (Nat.two_pow_pos N) hs)
  have hlam : N ≤ Nat.log2 s := (Nat.le_log2 hspos).mpr hs
  have hNreal : tsq ≤ (N : ℝ) := by
    calc tsq ≤ (Nat.ceil tsq : ℝ) := Nat.le_ceil _
      _ ≤ (N : ℝ) := by exact_mod_cast le_max_right 1 (Nat.ceil tsq)
  have hsqrt : t ≤ √(Nat.log2 s : ℝ) := by
    have hlog : (N : ℝ) ≤ Nat.log2 s := by exact_mod_cast hlam
    have hsq : t ^ 2 ≤ (Nat.log2 s : ℝ) := by
      simpa [tsq, sq] using le_trans hNreal hlog
    rw [← Real.sqrt_sq ht0]
    exact Real.sqrt_le_sqrt hsq
  have hdiv : K / √(Nat.log2 s : ℝ) ≤ ε * Real.log 2 := by
    have hroot : 0 < √(Nat.log2 s : ℝ) := by
      have : (0 : ℕ) < Nat.log2 s := by omega
      exact Real.sqrt_pos.2 (by exact_mod_cast this)
    rw [div_le_iff₀ hroot]
    have hKt : K = t * (ε * Real.log 2) := by
      simp only [t]
      field_simp
    rw [hKt]
    calc t * (ε * Real.log 2) ≤ √(Nat.log2 s : ℝ) * (ε * Real.log 2) :=
          mul_le_mul_of_nonneg_right hsqrt (mul_pos hε hlog2).le
      _ = ε * Real.log 2 * √(Nat.log2 s : ℝ) := by ring
  have hle : K * (s : ℝ) / √(Nat.log2 s : ℝ) ≤ ε * s * Real.log 2 := by
    calc K * (s : ℝ) / √(Nat.log2 s : ℝ) = (K / √(Nat.log2 s : ℝ)) * s := by ring
      _ ≤ (ε * Real.log 2) * s := mul_le_mul_of_nonneg_right hdiv (by positivity)
      _ = ε * s * Real.log 2 := by ring
  calc exp (K * (s : ℝ) / √(Nat.log2 s : ℝ)) ≤ exp (ε * s * Real.log 2) := exp_le_exp.mpr hle
    _ = (2 : ℝ) ^ (ε * s) := by
      rw [Real.rpow_def_of_pos (by norm_num : (0 : ℝ) < 2)]
      congr 1
      ring

end ModeCount
