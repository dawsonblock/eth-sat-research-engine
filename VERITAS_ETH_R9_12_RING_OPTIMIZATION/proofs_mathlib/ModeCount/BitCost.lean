import ModeCount.Multiplicity

/-!
# Enumerating `eq:tensor-mode-budget` under a bit-size cost model

The enumerator tries `b = 0, 1, …` for each weight `w` with remaining budget
`r`. A try forms `w * b` from `w * (b - 1)` by one addition, compares it with
`r`, and on success subtracts it from `r`. Each operation is charged the bit
lengths (`Nat.size`) of its operands; the final failing try is also charged.
Every feasible partial choice extends by zeros, so the total charge is at most
`2 N (K + 1)` times a bit-length unit, where `N` is the number of tuples and
`K` the number of modes.
-/

open Real Finset

namespace ModeCount

/-- One add, one compare and one subtract, each charged by operand bit length. -/
def tryCost (w r b : ℕ) : ℕ := (Nat.size (w * b) + Nat.size w) + (Nat.size (w * b) + Nat.size r) +
  (Nat.size r + Nat.size (w * b))

/-- Charge of `enum ws r`: every try, including each failing one, and one unit per emitted tuple. -/
def cost : List ℕ → ℕ → ℕ
  | [], _ => 1
  | w :: ws, r => (∑ b ∈ range (feasible w r + 1), tryCost w r b) +
      ∑ b ∈ range (feasible w r), cost ws (r - w * b)

theorem size_add_le (a b : ℕ) : Nat.size (a + b) ≤ Nat.size a + Nat.size b + 1 := by
  rw [Nat.size_le]
  have ha := Nat.lt_size_self a
  have hb := Nat.lt_size_self b
  have h1 : 2 ^ Nat.size a ≤ 2 ^ (Nat.size a + Nat.size b) := Nat.pow_le_pow_right (by norm_num) (by omega)
  have h2 : 2 ^ Nat.size b ≤ 2 ^ (Nat.size a + Nat.size b) := Nat.pow_le_pow_right (by norm_num) (by omega)
  rw [pow_succ]
  omega

theorem tryCost_le {w r b R W : ℕ} (hw : 1 ≤ w) (hb : b ≤ feasible w r) (hr : r ≤ R) (hW : w ≤ W) :
    tryCost w r b ≤ 9 * (Nat.size R + Nat.size W + 1) := by
  have hwb : w * b ≤ r + w := by
    rcases Nat.eq_zero_or_pos b with rfl | hb0
    · simp
    · have := (lt_feasible_iff hw (r := r) (b := b - 1)).1 (by omega)
      have : w * b = w * (b - 1) + w := by
        rw [← Nat.mul_succ]; congr 1; omega
      omega
  have h1 : Nat.size (w * b) ≤ Nat.size R + Nat.size W + 1 :=
    (Nat.size_le_size (hwb.trans (Nat.add_le_add hr hW))).trans (size_add_le R W)
  have h2 : Nat.size r ≤ Nat.size R := Nat.size_le_size hr
  have h3 : Nat.size w ≤ Nat.size W := Nat.size_le_size hW
  unfold tryCost
  omega

theorem one_le_length_enum {ws : List ℕ} (hw : ∀ w ∈ ws, 1 ≤ w) {r : ℕ} (hr : 0 < r) :
    1 ≤ (enum ws r).length := by
  have hz : List.replicate ws.length 0 ∈ enum ws r := by
    rw [mem_enum hw]
    refine ⟨by simp, ?_⟩
    have : ∀ vs : List ℕ, wsum vs (List.replicate vs.length 0) = 0 := by
      intro vs; induction vs with
      | nil => rfl
      | cons v vs ih => simp [List.replicate_succ, wsum, ih]
    rw [this]; exact hr
  exact List.length_pos_of_mem hz

/-- Total bit charge is at most `2 N (K + 1)` bit-length units. -/
theorem cost_le {ws : List ℕ} {R W : ℕ} (hw : ∀ w ∈ ws, 1 ≤ w ∧ w ≤ W) {r : ℕ} (hr0 : 0 < r) (hr : r ≤ R) :
    cost ws r ≤ 2 * (enum ws r).length * (ws.length + 1) * (9 * (Nat.size R + Nat.size W + 1)) := by
  set B := 9 * (Nat.size R + Nat.size W + 1)
  induction ws generalizing r with
  | nil => simp [cost, enum, hr0, B]; omega
  | cons w ws ih =>
    have hw1 := (hw w (by simp)).1
    have hwW := (hw w (by simp)).2
    have hws : ∀ v ∈ ws, 1 ≤ v ∧ v ≤ W := fun v hv => hw v (by simp [hv])
    set n := feasible w r
    have hn : 1 ≤ n := by
      have := (lt_feasible_iff hw1 (r := r) (b := 0)).2 (by simpa using hr0); omega
    have hrb : ∀ b ∈ range n, 0 < r - w * b ∧ r - w * b ≤ R := fun b hb => by
      have := (lt_feasible_iff hw1).1 (mem_range.1 hb); omega
    set len := fun b => (enum ws (r - w * b)).length
    have hlen : ∀ b ∈ range n, 1 ≤ len b := fun b hb =>
      one_le_length_enum (fun v hv => (hws v hv).1) (hrb b hb).1
    have htotal : (enum (w :: ws) r).length = ∑ b ∈ range n, len b := length_enum_cons w ws r
    have htry : ∑ b ∈ range (n + 1), tryCost w r b ≤ (n + 1) * B := by
      calc ∑ b ∈ range (n + 1), tryCost w r b ≤ ∑ _b ∈ range (n + 1), B :=
            sum_le_sum fun b hb => tryCost_le hw1 (Nat.lt_succ_iff.1 (mem_range.1 hb)) hr hwW
        _ = (n + 1) * B := by simp
    have hrec : ∑ b ∈ range n, cost ws (r - w * b) ≤ ∑ b ∈ range n, 2 * len b * (ws.length + 1) * B :=
      sum_le_sum fun b hb => ih hws (hrb b hb).1 (hrb b hb).2
    have hcount : n ≤ ∑ b ∈ range n, len b := by
      simpa using (sum_le_sum hlen : ∑ _b ∈ range n, 1 ≤ ∑ b ∈ range n, len b)
    have hsplit : ∑ b ∈ range n, 2 * len b * (ws.length + 1) * B =
        2 * (∑ b ∈ range n, len b) * (ws.length + 1) * B := by
      rw [mul_sum, sum_mul, sum_mul]
    rw [cost, htotal, List.length_cons]
    nlinarith [htry, hrec, hcount, hsplit]

/-- Bit cost of enumerating every tuple of `eq:tensor-mode-budget` at the paper's parameters. -/
theorem paper_enumeration_cost {P i L M D p : ℕ} {u C : ℝ} {modes : List Tag} (hnd : modes.Nodup)
    (hrange : ∀ z ∈ modes, z.1 < P ∧ z.2.1 < 2 ^ (i + 1)) (hb : ∀ z ∈ modes, weight z < p)
    (hpack : P * L ≤ 3 * M) (hD : D * 2 ^ i = L) (hP : 0 < P) (hDpos : 0 < D) (hp : 0 < p)
    (hu : 0 < u) (hC : 0 ≤ C) (hprec : (p : ℝ) * u ≤ C * M * D) :
    (cost (modes.map weight) p : ℝ) ≤
      2 * exp (2 * π * √C * M / √u) * (modes.length + 1) * (9 * (2 * Nat.size p + 1)) := by
  have hw : ∀ w ∈ modes.map weight, 1 ≤ w ∧ w ≤ p := by
    intro w hw
    obtain ⟨z, hz, rfl⟩ := List.mem_map.1 hw
    exact ⟨by simp [weight], (hb z hz).le⟩
  have hc := cost_le hw hp le_rfl
  have hN := paper_tuple_count hnd hrange hpack hD hP hDpos hp hu hC hprec
  rw [List.length_map] at hc
  have hc' : (cost (modes.map weight) p : ℝ) ≤
      2 * ((enum (modes.map weight) p).length : ℝ) * (modes.length + 1) * (9 * (2 * Nat.size p + 1)) := by
    have : 9 * (Nat.size p + Nat.size p + 1) = 9 * (2 * Nat.size p + 1) := by ring
    rw [this] at hc
    exact_mod_cast hc
  refine hc'.trans ?_
  gcongr

end ModeCount
