import ModeCount.Combined

/-!
# The divisibility argument of `subsec:tensor-modes`

Over any commutative ring `R` and any `q : R` (`q = 2` in the paper):

* `geometric_mode_expansion`: if `(1 - ρj)·v = 1`, `W = c·v`, `q ∣ c` and
  `q ∣ ρ`, then `W = ∑_{b<N} (c ρ^b) j^b + q^(N+1)·r` and `q^(b+1) ∣ c ρ^b`.
  This is `eq:tensor-mode-expansion`: mode `b` has weight `b+1` and the
  geometric remainder is divisible by `q^{p_t}` for `N + 1 = p_t`.
* `WDiv q w f`: every coefficient of `Z^β` in `f` is divisible by
  `q^(∑ w_Z β_Z)`. Affine forms whose `Z` coefficient is divisible by
  `q^(w_Z)` satisfy it, and it is closed under products.
* `eval_eq_budget_sum`: for such `f`, every substitution `Z ↦ L_Z` gives
  `f(L) = ∑_{∑ w_Z β_Z < p} coeff_β(f) ∏ L_Z^{β_Z} + q^p·s`. This is
  `eq:tensor-mode-budget` and "the omitted monomials vanish by their
  coefficient divisibility" in `eq:tensor-recursion-identity`.
* `budget_iff_enum`: the surviving exponents are exactly those `enum` lists.

The `p`-adic valuation estimates that give `q ∣ c` and `q ∣ ρ` (first
fraction of valuation at least `a + 1 - i`, `v₂(T - y₀ + x) ≤ i`) and the
factorization over groups into child contractions are not formalised here.
-/

open Finset

namespace ModeCount

section Geometric

variable {R : Type*} [CommRing R]

theorem geometric_mode_expansion {q c ρ j v W : R} (N : ℕ) (hv : (1 - ρ * j) * v = 1)
    (hW : W = c * v) (hc : q ∣ c) (hρ : q ∣ ρ) :
    (∃ r, W = ∑ b ∈ range N, c * ρ ^ b * j ^ b + q ^ (N + 1) * r) ∧
      ∀ b, q ^ (b + 1) ∣ c * ρ ^ b := by
  refine ⟨?_, fun b => ?_⟩
  · obtain ⟨c', rfl⟩ := hc
    obtain ⟨ρ', rfl⟩ := hρ
    refine ⟨c' * ρ' ^ N * j ^ N * v, ?_⟩
    have tele : (∑ b ∈ range N, (q * ρ' * j) ^ b) * (1 - q * ρ' * j) = 1 - (q * ρ' * j) ^ N := by
      rw [geom_sum_mul_neg]
    have hsum : ∑ b ∈ range N, q * c' * (q * ρ') ^ b * j ^ b =
        q * c' * ∑ b ∈ range N, (q * ρ' * j) ^ b := by
      rw [mul_sum]; refine sum_congr rfl fun b _ => by ring
    rw [hsum, hW]
    have : q * c' * v = q * c' * v * ((∑ b ∈ range N, (q * ρ' * j) ^ b) * (1 - q * ρ' * j)) +
        q * c' * v * (q * ρ' * j) ^ N := by rw [tele]; ring
    calc q * c' * v = _ := this
      _ = q * c' * (∑ b ∈ range N, (q * ρ' * j) ^ b) * ((1 - q * ρ' * j) * v) +
          q * c' * v * (q * ρ' * j) ^ N := by ring
      _ = _ := by rw [hv]; ring
  · obtain ⟨c', rfl⟩ := hc
    obtain ⟨ρ', rfl⟩ := hρ
    exact ⟨c' * ρ' ^ b, by ring⟩

end Geometric

section Weighted

variable {R σ : Type*} [CommRing R] (q : R) (w : σ → ℕ)

/-- Every coefficient of `Z^β` is divisible by `q^(∑ w_Z β_Z)`. -/
def WDiv (f : MvPolynomial σ R) : Prop :=
  ∀ d : σ →₀ ℕ, q ^ Finsupp.weight w d ∣ f.coeff d

variable {q w}

theorem WDiv.add {f g : MvPolynomial σ R} (hf : WDiv q w f) (hg : WDiv q w g) :
    WDiv q w (f + g) := fun d => by rw [MvPolynomial.coeff_add]; exact dvd_add (hf d) (hg d)

theorem WDiv.C (r : R) : WDiv q w (MvPolynomial.C r : MvPolynomial σ R) := fun d => by
  classical
  rw [MvPolynomial.coeff_C]
  split_ifs with h
  · subst h; simp
  · exact dvd_zero _

theorem WDiv.mode {Z : σ} {c : R} (hc : q ^ w Z ∣ c) :
    WDiv q w (MvPolynomial.C c * MvPolynomial.X Z) := fun d => by
  classical
  rw [MvPolynomial.coeff_C_mul, MvPolynomial.coeff_X']
  split_ifs with h
  · subst h; simpa [Finsupp.weight_apply, Finsupp.sum_single_index] using hc
  · simp

theorem WDiv.mul {f g : MvPolynomial σ R} (hf : WDiv q w f) (hg : WDiv q w g) :
    WDiv q w (f * g) := fun d => by
  classical
  rw [MvPolynomial.coeff_mul]
  refine dvd_sum fun x hx => ?_
  rw [HasAntidiagonal.mem_antidiagonal] at hx
  rw [← hx, map_add, pow_add]
  exact mul_dvd_mul (hf x.1) (hg x.2)

theorem WDiv.sum {ι : Type*} (s : Finset ι) {f : ι → MvPolynomial σ R}
    (h : ∀ x ∈ s, WDiv q w (f x)) : WDiv q w (∑ x ∈ s, f x) := by
  classical
  induction s using Finset.induction_on with
  | empty => simpa using WDiv.C (q := q) (w := w) (σ := σ) 0
  | insert a s ha ih =>
    rw [sum_insert ha]
    exact (h a (mem_insert_self a s)).add (ih fun x hx => h x (mem_insert_of_mem hx))

theorem WDiv.prod {ι : Type*} (s : Finset ι) {f : ι → MvPolynomial σ R}
    (h : ∀ x ∈ s, WDiv q w (f x)) : WDiv q w (∏ x ∈ s, f x) := by
  classical
  induction s using Finset.induction_on with
  | empty => simpa using WDiv.C (q := q) (w := w) (σ := σ) 1
  | insert a s ha ih =>
    rw [prod_insert ha]
    exact (h a (mem_insert_self a s)).mul (ih fun x hx => h x (mem_insert_of_mem hx))

/-- An affine row form `c₀ + ∑_Z c_Z Z` with `q^(w_Z) ∣ c_Z`. -/
theorem WDiv.affine (s : Finset σ) (c₀ : R) {c : σ → R} (hc : ∀ Z ∈ s, q ^ w Z ∣ c Z) :
    WDiv q w (MvPolynomial.C c₀ + ∑ Z ∈ s, MvPolynomial.C (c Z) * MvPolynomial.X Z) :=
  (WDiv.C c₀).add (WDiv.sum s fun Z hZ => WDiv.mode (hc Z hZ))

/-- The product of the affine factors `l_{Y_x}((W(T)X)_x)`. -/
theorem WDiv.affine_product {ι : Type*} (rows : Finset ι) (s : ι → Finset σ) (c₀ : ι → R)
    {c : ι → σ → R} (hc : ∀ x ∈ rows, ∀ Z ∈ s x, q ^ w Z ∣ c x Z) :
    WDiv q w (∏ x ∈ rows, (MvPolynomial.C (c₀ x) +
      ∑ Z ∈ s x, MvPolynomial.C (c x Z) * MvPolynomial.X Z)) :=
  WDiv.prod rows fun x hx => WDiv.affine (s x) (c₀ x) (hc x hx)

/-- The monomials inside the budget `∑ w_Z β_Z < p`. -/
noncomputable def budget (w : σ → ℕ) (p : ℕ) (f : MvPolynomial σ R) : Finset (σ →₀ ℕ) :=
  by classical exact f.support.filter fun d => Finsupp.weight w d < p

theorem exists_eq_C_mul {h : MvPolynomial σ R} {a : R} (hd : ∀ d, a ∣ h.coeff d) :
    ∃ g, h = MvPolynomial.C a * g := by
  classical
  choose k hk using hd
  refine ⟨∑ d ∈ h.support, MvPolynomial.monomial d (k d), ?_⟩
  rw [mul_sum]
  conv_lhs => rw [h.as_sum]
  refine sum_congr rfl fun d _ => ?_
  rw [MvPolynomial.C_mul_monomial, ← hk]

theorem eq_budget_add {f : MvPolynomial σ R} (hf : WDiv q w f) (p : ℕ) :
    ∃ g, f = ∑ d ∈ budget w p f, MvPolynomial.monomial d (f.coeff d) +
      MvPolynomial.C (q ^ p) * g := by
  classical
  set T := ∑ d ∈ budget w p f, MvPolynomial.monomial d (f.coeff d)
  have hT : ∀ d, T.coeff d = if Finsupp.weight w d < p then f.coeff d else 0 := by
    intro d
    simp only [T, MvPolynomial.coeff_sum, MvPolynomial.coeff_monomial, budget]
    rw [sum_ite_eq']
    by_cases hw : Finsupp.weight w d < p <;> by_cases hs : d ∈ f.support <;>
      simp_all [MvPolynomial.notMem_support_iff]
  obtain ⟨g, hg⟩ := exists_eq_C_mul (h := f - T) (a := q ^ p) fun d => by
    rw [MvPolynomial.coeff_sub, hT]
    split_ifs with hw
    · simp
    · rw [sub_zero]
      exact (pow_dvd_pow q (not_lt.1 hw)).trans (hf d)
  exact ⟨g, by rw [← hg]; ring⟩

/-- Substituting `Z ↦ L_Z` leaves only the in-budget monomials modulo `q^p`. -/
theorem eval_eq_budget_sum {f : MvPolynomial σ R} (hf : WDiv q w f) (p : ℕ) (L : σ → R) :
    ∃ s, MvPolynomial.eval L f =
      ∑ d ∈ budget w p f, f.coeff d * d.prod (fun Z e => L Z ^ e) + q ^ p * s := by
  obtain ⟨g, hg⟩ := eq_budget_add hf p
  refine ⟨MvPolynomial.eval L g, ?_⟩
  conv_lhs => rw [hg]
  simp [map_sum, MvPolynomial.eval_monomial]

end Weighted

theorem wsum_ofFn {n : ℕ} (w b : Fin n → ℕ) :
    wsum (List.ofFn w) (List.ofFn b) = ∑ k, w k * b k := by
  induction n with
  | zero => simp [wsum]
  | succ n ih =>
    rw [List.ofFn_succ, List.ofFn_succ, wsum, ih, Fin.sum_univ_succ]

/-- The tuples kept by `eval_eq_budget_sum` are exactly those `enum` lists. -/
theorem budget_iff_enum {n : ℕ} {w : Fin n → ℕ} (hw : ∀ k, 1 ≤ w k) (p : ℕ) (d : Fin n →₀ ℕ) :
    Finsupp.weight w d < p ↔ List.ofFn d ∈ enum (List.ofFn w) p := by
  rw [mem_enum (by simpa [List.mem_ofFn, forall_exists_index, forall_apply_eq_imp_iff] using hw),
    List.length_ofFn, List.length_ofFn, wsum_ofFn, Finsupp.weight_apply,
    Finsupp.sum_fintype _ _ (by simp)]
  simp [smul_eq_mul, mul_comm]

end ModeCount
