import ModeCount.Packing

/-!
# `eq:tensor-precision-bound`

`lem:tapered-hermite` creates an active node `t` with `i = v₂(t) < u`,
`D_t = L / 2^i`, `L = 2^a`, `a = a_{d-1} + 2u` and precision
`p_t = p + 8 h D_t + 8 M (a + 1)`, where `h = ⌈3M/u⌉ ≤ 4M/u`.

* `path_precision`: along a path, `p_d ≤ A_d · 2^{a_{d-1}}`, with the explicit
  envelope `A_{d+1} = A_d + 8 h_d + 8 M_d (a_d + 1)` (first assertion).
* `precision_bound`: `p_t · u ≤ 34 M D_t` (second assertion, `C = 34`), given
  the two size conditions the paper states as holding for sufficiently large
  `s`: `A · u ≤ M · 2^u` and `8 (a + 1) u ≤ 2^{a_{d-1} + u}`.
-/

namespace ModeCount

def nodePrecision (p h Dt M a : ℕ) : ℕ := p + 8 * h * Dt + 8 * M * (a + 1)

/-- `2^{a_{d-1}}` along a path, with `a_{-1} = 0`. -/
def prevExp (a : ℕ → ℕ) : ℕ → ℕ
  | 0 => 0
  | d + 1 => a d

/-- The explicit envelope `A_d`. -/
def envelope (A0 : ℕ) (h M a : ℕ → ℕ) : ℕ → ℕ
  | 0 => A0
  | d + 1 => envelope A0 h M a d + 8 * h d + 8 * M d * (a d + 1)

theorem path_precision {p h M a Dt : ℕ → ℕ} {A0 : ℕ} (hp0 : p 0 ≤ A0)
    (hstep : ∀ d, p (d + 1) = nodePrecision (p d) (h d) (Dt d) (M d) (a d))
    (hDt : ∀ d, Dt d ≤ 2 ^ a d) (hmono : ∀ d, a d ≤ a (d + 1)) :
    ∀ d, p d ≤ envelope A0 h M a d * 2 ^ prevExp a d := by
  have hprev : ∀ d, prevExp a d ≤ a d := fun d => by
    cases d with
    | zero => exact Nat.zero_le _
    | succ d => exact hmono d
  intro d
  induction d with
  | zero => simpa [prevExp, envelope] using hp0
  | succ d ih =>
    rw [hstep, nodePrecision]
    simp only [envelope, prevExp]
    have h1 : 2 ^ prevExp a d ≤ 2 ^ a d := Nat.pow_le_pow_right (by norm_num) (hprev d)
    have h2 : 1 ≤ 2 ^ a d := Nat.one_le_two_pow
    have e1 : p d ≤ envelope A0 h M a d * 2 ^ a d := ih.trans (Nat.mul_le_mul_left _ h1)
    have e2 : 8 * h d * Dt d ≤ 8 * h d * 2 ^ a d := Nat.mul_le_mul_left _ (hDt d)
    have e3 : 8 * M d * (a d + 1) ≤ 8 * M d * (a d + 1) * 2 ^ a d := Nat.le_mul_of_pos_right _ h2
    nlinarith

theorem Dt_ge {a' u i Dt : ℕ} (hi : i < u) (hD : Dt * 2 ^ i = 2 ^ (a' + 2 * u)) :
    2 ^ (a' + u) ≤ Dt := by
  have h : 2 ^ (a' + u) * 2 ^ u ≤ Dt * 2 ^ u := by
    calc 2 ^ (a' + u) * 2 ^ u = Dt * 2 ^ i := by rw [hD, ← pow_add]; ring_nf
      _ ≤ Dt * 2 ^ u := Nat.mul_le_mul_left _ (Nat.pow_le_pow_right (by norm_num) hi.le)
  exact Nat.le_of_mul_le_mul_right h (by positivity)

/-- `eq:tensor-precision-bound`: `p_t = O(M D_t / u)` with constant 34. -/
theorem precision_bound {p h M a' u i Dt A : ℕ} (hi : i < u) (hD : Dt * 2 ^ i = 2 ^ (a' + 2 * u))
    (hh : h * u ≤ 4 * M) (hp : p ≤ A * 2 ^ a') (hA : A * u ≤ M * 2 ^ u)
    (hlog : 8 * (a' + 2 * u + 1) * u ≤ 2 ^ (a' + u)) :
    nodePrecision p h Dt M (a' + 2 * u) * u ≤ 34 * M * Dt := by
  have hX := Dt_ge hi hD
  have e1 : p * u ≤ M * Dt := by
    calc p * u ≤ A * 2 ^ a' * u := Nat.mul_le_mul_right _ hp
      _ = A * u * 2 ^ a' := by ring
      _ ≤ M * 2 ^ u * 2 ^ a' := Nat.mul_le_mul_right _ hA
      _ = M * 2 ^ (a' + u) := by rw [pow_add]; ring
      _ ≤ M * Dt := Nat.mul_le_mul_left _ hX
  have e2 : 8 * h * Dt * u ≤ 32 * M * Dt := by
    calc 8 * h * Dt * u = 8 * Dt * (h * u) := by ring
      _ ≤ 8 * Dt * (4 * M) := Nat.mul_le_mul_left _ hh
      _ = 32 * M * Dt := by ring
  have e3 : 8 * M * (a' + 2 * u + 1) * u ≤ M * Dt := by
    calc 8 * M * (a' + 2 * u + 1) * u = M * (8 * (a' + 2 * u + 1) * u) := by ring
      _ ≤ M * 2 ^ (a' + u) := Nat.mul_le_mul_left _ hlog
      _ ≤ M * Dt := Nat.mul_le_mul_left _ hX
  have expand : nodePrecision p h Dt M (a' + 2 * u) * u =
      p * u + 8 * h * Dt * u + 8 * M * (a' + 2 * u + 1) * u := by
    unfold nodePrecision; ring
  rw [expand]
  nlinarith

end ModeCount
