import Mathlib
import ModeCount.Schedule
import ModeCount.ChildSize

/-!
# Total cost over the recursion (`subsec:tensor-cost`)

The recursion is modelled as a rose tree of calls.  If every call at depth `j` has at most
`b j` children and `b n = 0`, the tree has at most `∑_{d ≤ n} ∏_{j < d} b j` calls.

On the schedule `u_j = ⌊λ / (2^17 2^j)⌋`, a call with `M_j 8^j ≤ C s` and `u_j ≥ 1` has
`M_j / √u_j ≤ 2^10 C s / √λ · (√2/8)^j`.  Summing the geometric series turns per-depth branching
`b j ≤ Q exp (κ M_j / √u_j)` into at most `(n+1) Q^n exp (2^11 κ C s / √λ)` calls.
-/

namespace ModeCount

open Finset Real

inductive CallTree
  | node : List CallTree → CallTree

namespace CallTree

def children : CallTree → List CallTree
  | node cs => cs

mutual
def size : CallTree → ℕ
  | node cs => 1 + sizeList cs
def sizeList : List CallTree → ℕ
  | [] => 0
  | c :: cs => size c + sizeList cs
end

theorem sizeList_le {S : ℕ} : ∀ {cs : List CallTree}, (∀ c ∈ cs, size c ≤ S) →
    sizeList cs ≤ cs.length * S
  | [], _ => by simp [sizeList]
  | c :: cs, h => by
    have := sizeList_le (cs := cs) fun c' hc' => h c' (List.mem_cons_of_mem _ hc')
    have hc := h c List.mem_cons_self
    simp only [sizeList, List.length_cons]
    nlinarith

/-- Every call at depth `j` (relative to the root) has at most `b j` children. -/
inductive Branch : (ℕ → ℕ) → CallTree → Prop
  | node {b : ℕ → ℕ} {cs : List CallTree} :
      cs.length ≤ b 0 → (∀ c ∈ cs, Branch (fun j => b (j + 1)) c) → Branch b (node cs)

theorem size_le {n : ℕ} : ∀ {b : ℕ → ℕ} {t : CallTree}, Branch b t → b n = 0 →
    size t ≤ ∑ d ∈ range (n + 1), ∏ j ∈ range d, b j := by
  induction n with
  | zero =>
    intro b t hb hb0
    cases hb with
    | @node _ cs hlen _ =>
      have : cs = [] := List.eq_nil_of_length_eq_zero (by omega)
      subst this; simp [size, sizeList]
  | succ n ih =>
    intro b t hb hbn
    cases hb with
    | @node _ cs hlen hcs =>
      set S := ∑ d ∈ range (n + 1), ∏ j ∈ range d, b (j + 1)
      have hc : ∀ c ∈ cs, size c ≤ S := fun c hc => ih (hcs c hc) hbn
      have hsum := sizeList_le hc
      have hrhs : ∑ d ∈ range (n + 1 + 1), ∏ j ∈ range d, b j = 1 + b 0 * S := by
        rw [sum_range_succ', mul_sum]
        simp only [prod_range_succ', prod_range_zero]
        rw [add_comm]; congr 1
        refine sum_congr rfl fun d _ => ?_
        ring
      rw [hrhs, size]
      have : cs.length * S ≤ b 0 * S := Nat.mul_le_mul_right _ hlen
      omega

end CallTree

theorem sum_prod_le {b : ℕ → ℕ} {n : ℕ} (hb : ∀ j < n, 1 ≤ b j) :
    ∑ d ∈ range (n + 1), ∏ j ∈ range d, b j ≤ (n + 1) * ∏ j ∈ range n, b j := by
  calc ∑ d ∈ range (n + 1), ∏ j ∈ range d, b j ≤ ∑ _d ∈ range (n + 1), ∏ j ∈ range n, b j := by
        refine sum_le_sum fun d hd => ?_
        have hd : d ≤ n := Nat.lt_succ_iff.1 (mem_range.1 hd)
        exact prod_le_prod_of_subset_of_one_le (range_subset_range.2 hd)
          (fun j hj _ => hb j (mem_range.1 hj))
    _ = (n + 1) * ∏ j ∈ range n, b j := by simp

theorem geom_sqrt_two_div_eight (n : ℕ) : ∑ j ∈ range n, (√2 / 8) ^ j ≤ 2 := by
  have h2 : √2 < 2 := by
    rw [show (2 : ℝ) = √4 by rw [show (4 : ℝ) = 2 ^ 2 by norm_num, sqrt_sq (by norm_num)]]
    exact sqrt_lt_sqrt (by norm_num) (by norm_num)
  have h0 : 0 ≤ √2 / 8 := by positivity
  have h1 : √2 / 8 < 1 := by linarith
  calc ∑ j ∈ range n, (√2 / 8) ^ j ≤ (√2 / 8) ^ 0 / (1 - √2 / 8) := by
        rw [← Nat.Ico_zero_eq_range]; exact geom_sum_Ico_le_of_lt_one h0 h1
    _ ≤ 2 := by rw [pow_zero, div_le_iff₀ (by linarith)]; linarith

/-- A floor quotient that is at least one is at least half the real quotient. -/
theorem uSched_ge {lam j : ℕ} (hu : 1 ≤ uSched lam j) :
    (lam : ℝ) ≤ 2 ^ 18 * 2 ^ j * uSched lam j := by
  have hk : 0 < 131072 * 2 ^ j := by positivity
  have h := Nat.lt_mul_div_succ lam hk
  have : lam ≤ 2 ^ 18 * 2 ^ j * uSched lam j := by
    unfold uSched at hu ⊢
    nlinarith
  exact_mod_cast this

/-- The per-depth exponent of `eq:tensor-partition-count` on the schedule. -/
theorem depth_exponent {lam j M : ℕ} {C s : ℝ} (hlam : 0 < lam) (hu : 1 ≤ uSched lam j)
    (hM : (M : ℝ) * 8 ^ j ≤ C * s) :
    (M : ℝ) / √(uSched lam j) ≤ 2 ^ 10 * C * s / √lam * (√2 / 8) ^ j := by
  set u := (uSched lam j : ℝ)
  have hu0 : (0 : ℝ) < u := by simp only [u]; exact_mod_cast hu
  have hl0 : (0 : ℝ) < lam := by exact_mod_cast hlam
  have hlu := uSched_ge hu
  have hCs : 0 ≤ C * s := le_trans (by positivity) hM
  rw [div_le_iff₀ (sqrt_pos.2 hu0)]
  have hs2 : √((2 : ℝ) ^ j) = √2 ^ j := by
    rw [show (2 : ℝ) ^ j = (√2 ^ j) ^ 2 by rw [pow_right_comm, sq_sqrt (by norm_num)]]
    exact sqrt_sq (by positivity)
  have hsq : √(2 ^ j * u / lam) = √2 ^ j * √u / √lam := by
    rw [sqrt_div (by positivity), sqrt_mul (by positivity), hs2]
  have hl : 0 < √(lam : ℝ) := sqrt_pos.2 hl0
  have e : 2 ^ 10 * C * s / √lam * (√2 / 8) ^ j * √u =
      C * s / 8 ^ j * (2 ^ 10 * √(2 ^ j * u / lam)) := by
    rw [hsq, div_pow]; field_simp
  rw [e]
  have h8 : (0 : ℝ) < 8 ^ j := by positivity
  have hM' : (M : ℝ) ≤ C * s / 8 ^ j := by rw [le_div_iff₀ h8]; exact hM
  have hroot : 1 ≤ 2 ^ 10 * √(2 ^ j * u / lam) := by
    have : (1 / 2 ^ 18 : ℝ) ≤ 2 ^ j * u / lam := by
      rw [le_div_iff₀ hl0]; linarith
    have hs : (1 / 2 ^ 9 : ℝ) ≤ √(2 ^ j * u / lam) := by
      rw [show (1 / 2 ^ 9 : ℝ) = √(1 / 2 ^ 18) by
        rw [show (1 / 2 ^ 18 : ℝ) = (1 / 2 ^ 9) ^ 2 by norm_num, sqrt_sq (by norm_num)]]
      exact sqrt_le_sqrt this
    nlinarith
  calc (M : ℝ) ≤ C * s / 8 ^ j := hM'
    _ = C * s / 8 ^ j * 1 := (mul_one _).symm
    _ ≤ C * s / 8 ^ j * (2 ^ 10 * √(2 ^ j * u / lam)) :=
        mul_le_mul_of_nonneg_left hroot (div_nonneg hCs h8.le)

/-- Children with at most `M/8` edges give `M_j 8^j ≤ M_0` along every path. -/
theorem path_edges {M : ℕ → ℕ} (h : ∀ j, M (j + 1) * 8 ≤ M j) (j : ℕ) : M j * 8 ^ j ≤ M 0 := by
  induction j with
  | zero => simp
  | succ j ih => calc M (j + 1) * 8 ^ (j + 1) = M (j + 1) * 8 * 8 ^ j := by ring
      _ ≤ M j * 8 ^ j := Nat.mul_le_mul_right _ (h j)
      _ ≤ M 0 := ih

/-- `subsec:tensor-cost`: the number of calls in the recursion. -/
theorem total_calls {lam n Q : ℕ} {C s κ : ℝ} (hlam : 0 < lam) (hκ : 0 ≤ κ) (hCs : 0 ≤ C * s)
    (t : CallTree)
    (b M : ℕ → ℕ) (hb : CallTree.Branch b t) (hbn : b n = 0) (hb1 : ∀ j < n, 1 ≤ b j)
    (hu : ∀ j < n, 1 ≤ uSched lam j) (hM : ∀ j < n, (M j : ℝ) * 8 ^ j ≤ C * s)
    (hbQ : ∀ j < n, (b j : ℝ) ≤ Q * exp (κ * (M j / √(uSched lam j)))) :
    (t.size : ℝ) ≤ (n + 1) * Q ^ n * exp (2 ^ 11 * κ * C * s / √lam) := by
  have hsize : (t.size : ℝ) ≤ (n + 1) * ∏ j ∈ range n, (b j : ℝ) := by
    exact_mod_cast (CallTree.size_le hb hbn).trans (sum_prod_le hb1)
  refine hsize.trans ?_
  rw [mul_assoc]
  refine mul_le_mul_of_nonneg_left ?_ (by positivity : (0 : ℝ) ≤ n + 1)
  set G := 2 ^ 10 * C * s / √lam
  have hG : 0 ≤ G := by simp only [G]; rw [mul_assoc]; positivity
  calc ∏ j ∈ range n, (b j : ℝ) ≤ ∏ j ∈ range n, ((Q : ℝ) * exp (κ * (G * (√2 / 8) ^ j))) := by
        refine prod_le_prod₀ (fun _ _ => by positivity) (fun j hj => (hbQ j (mem_range.1 hj)).trans ?_)
        have hQ : (0 : ℝ) ≤ Q := Nat.cast_nonneg _
        gcongr
        exact depth_exponent hlam (hu j (mem_range.1 hj)) (hM j (mem_range.1 hj))
    _ = Q ^ n * exp (κ * G * ∑ j ∈ range n, (√2 / 8) ^ j) := by
        rw [prod_mul_distrib, prod_const, card_range, ← exp_sum, mul_sum]
        congr 2; refine sum_congr rfl fun j _ => ?_; ring
    _ ≤ Q ^ n * exp (κ * G * 2) := by
        have := mul_nonneg hκ hG
        gcongr
        exact geom_sqrt_two_div_eight n
    _ = Q ^ n * exp (2 ^ 11 * κ * C * s / √lam) := by
        congr 2; simp only [G]; ring

end ModeCount
