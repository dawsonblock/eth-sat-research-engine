import ModeCount.Divisibility

/-!
# The 2-adic estimates behind `eq:tensor-mode-expansion`

The grid `S = {-L, …, L-1}` with `L = 2^a` is indexed by `m < 2^K`, `K = a+1`,
as `q_m = m - L`; the node `t = q_n` and `T = t + 2^K z`, so
`T - q_m = (n - m) + 2^K z`. The ring `R` stands for `𝒪 = ℤ_(2)[U]/(f)`; the
only property used is the paper's "every element nonzero modulo two is a
unit", in the form `IsUnit (o + 2r)` for odd integers `o`.

* `crossing_not_dvd`, `tile_bit`: a crossing row `x` and tile residue `y₀`
  (equal `i`-th bits) give `2^(i+1) ∤ t - y₀ + x` when `v₂(t) = i`.
* `factorization_prodAbs_eq`: `v₂(∏_{m≠n} |n-m|)` is the same for every `n`
  (`lem:tensor-integrality`, "`v₂(𝒞'(t)) = v₂(𝒞'(0))`"), via Kummer:
  `(2^K - 1).choose n` is odd.
* `first_fraction`: `𝒞(T) / (𝒞'(q_{n₀}) (T - q_{m₀}))` is an element of `R`
  divisible by `2^(K - v₂(n - m₀))`.
* `ratio_even`: `2^(i+1) / (T - q_{m₀})` is even when `v₂(n - m₀) ≤ i < K`,
  and `1 - ρ j` is a unit.
* `crossing_mode_expansion`: together with `geometric_mode_expansion`,
  `W_{xy}(T) = 𝒞(T)/(𝒞'(0)(T - (y - x)))` expands in modes `b` with
  coefficients divisible by `2^(b+1)` and remainder divisible by `2^N`.
-/

open Finset

namespace ModeCount

/-! ### Tile geometry -/

theorem tile_bit (i y₀ j : ℕ) : (y₀ + 2 ^ (i + 1) * j) / 2 ^ i % 2 = y₀ / 2 ^ i % 2 := by
  have : y₀ + 2 ^ (i + 1) * j = y₀ + 2 ^ i * (2 * j) := by rw [pow_succ]; ring
  rw [this, Nat.add_mul_div_left _ _ (by positivity), Nat.add_mul_mod_self_left]

theorem crossing_not_dvd {i : ℕ} {k : ℤ} {x y₀ : ℕ} (hbit : x / 2 ^ i % 2 = y₀ / 2 ^ i % 2) :
    ¬ (2 : ℤ) ^ (i + 1) ∣ 2 ^ i * (2 * k + 1) - y₀ + x := by
  set P := 2 ^ i with hP
  have hP0 : 0 < P := by positivity
  have split : ∀ m : ℕ, m = 2 * P * (m / (2 * P)) + P * (m / P % 2) + m % P := by
    intro m
    have h1 := Nat.div_add_mod m (P * 2)
    have h2 := Nat.div_add_mod (m % (P * 2)) P
    rw [Nat.mod_mul_right_div_self, Nat.mod_mul_right_mod] at h2
    rw [show 2 * P = P * 2 by ring]
    linarith
  rintro ⟨n, hn⟩
  have hx := split x
  have hy := split y₀
  have hrx := Nat.mod_lt x hP0
  have hry := Nat.mod_lt y₀ hP0
  have hPz : ((P : ℕ) : ℤ) = 2 ^ i := by rw [hP]; push_cast; ring
  have h2 : (2 : ℤ) ^ (i + 1) = 2 * P := by rw [pow_succ, hPz]; ring
  rw [h2, ← hPz] at hn
  set A := x / (2 * P); set B := y₀ / (2 * P); set b := x / P % 2
  set rx := x % P; set ry := y₀ % P
  have hb : y₀ / P % 2 = b := hbit.symm
  rw [hb] at hy
  have key : (P : ℤ) + rx - ry = 2 * P * (n - k - A + B) := by
    have hx' : (x : ℤ) = 2 * P * A + P * b + rx := by exact_mod_cast hx
    have hy' : (y₀ : ℤ) = 2 * P * B + P * b + ry := by exact_mod_cast hy
    push_cast at hn
    linear_combination hn - hx' + hy'
  have l1 : (0 : ℤ) < P + rx - ry := by omega
  have l2 : (P : ℤ) + rx - ry < 2 * P := by omega
  rcases le_or_gt (n - k - A + B) 0 with h | h
  · nlinarith
  · nlinarith

/-- `v₂(t - y₀ + x) ≤ i` for a crossing row. -/
theorem crossing_valuation {i : ℕ} {k : ℤ} {x y₀ : ℕ} (hbit : x / 2 ^ i % 2 = y₀ / 2 ^ i % 2) :
    (2 ^ i * (2 * k + 1) - y₀ + x : ℤ) ≠ 0 ∧
      (2 ^ i * (2 * k + 1) - y₀ + x : ℤ).natAbs.factorization 2 ≤ i := by
  have hnd := crossing_not_dvd (k := k) hbit
  refine ⟨fun h => hnd (h ▸ dvd_zero _), ?_⟩
  by_contra hlt
  apply hnd
  have hd : 2 ^ (i + 1) ∣ (2 ^ i * (2 * k + 1) - y₀ + x : ℤ).natAbs :=
    (Nat.pow_dvd_pow 2 (by omega)).trans (Nat.ordProj_dvd _ _)
  exact Int.natAbs_dvd_natAbs.1 (by simpa using hd)

/-! ### Kummer: `v₂(n! (2^K - 1 - n)!)` does not depend on `n` -/

theorem odd_choose_two_pow_sub_one (K n : ℕ) (hn : n ≤ 2 ^ K - 1) :
    Odd ((2 ^ K - 1).choose n) := by
  have : Fact (Nat.Prime 2) := ⟨Nat.prime_two⟩
  rcases Nat.eq_zero_or_pos (2 ^ K - 1) with h0 | hpos
  · rw [h0] at hn ⊢; interval_cases n; simp
  have hlog : Nat.log 2 (2 ^ K - 1) < K + 1 :=
    (Nat.log_lt_of_lt_pow (by omega) (by have := Nat.one_le_two_pow (n := K); omega)).trans
      (Nat.lt_succ_self K)
  have hv := padicValNat_choose (p := 2) hn hlog
  have hempty : (Finset.Ico 1 (K + 1)).filter
      (fun i => 2 ^ i ≤ n % 2 ^ i + (2 ^ K - 1 - n) % 2 ^ i) = ∅ := by
    rw [Finset.filter_eq_empty_iff]
    intro i hi
    rw [Finset.mem_Ico] at hi
    set P := 2 ^ i
    have hP : 0 < P := by positivity
    obtain ⟨Q, hQ⟩ : P ∣ 2 ^ K := Nat.pow_dvd_pow 2 (by omega)
    have hQ1 : 1 ≤ Q := by
      rcases Nat.eq_zero_or_pos Q with h | h
      · rw [h, mul_zero] at hQ; exact absurd hQ (by positivity)
      · exact h
    set s := n % P + (2 ^ K - 1 - n) % P
    have hs : s % P = P - 1 := by
      have e1 : s % P = (n + (2 ^ K - 1 - n)) % P := (Nat.add_mod _ _ _).symm
      have hPQ : P * Q = P * (Q - 1) + P := by
        conv_lhs => rw [show Q = (Q - 1) + 1 by omega]
        ring
      have e2 : n + (2 ^ K - 1 - n) = P * (Q - 1) + (P - 1) := by
        generalize P * (Q - 1) = X at hPQ ⊢
        generalize P * Q = Y at hPQ hQ
        omega
      rw [e1, e2, Nat.mul_add_mod, Nat.mod_eq_of_lt (by omega)]
    have h1 := Nat.mod_lt n hP
    have h2 := Nat.mod_lt (2 ^ K - 1 - n) hP
    intro hge
    have e3 : s % P = (s - P) % P := Nat.mod_eq_sub_mod hge
    rw [Nat.mod_eq_of_lt (by omega : s - P < P)] at e3
    omega
  rw [hempty, Finset.card_empty] at hv
  have hne : (2 ^ K - 1).choose n ≠ 0 := Nat.choose_ne_zero hn
  rcases (padicValNat.eq_zero_iff).1 hv with h | h | h
  · exact absurd h (by norm_num)
  · exact absurd h hne
  · exact Nat.odd_iff.2 (Nat.two_dvd_ne_zero.1 h)

theorem factorization_factorial_mul (K n : ℕ) (hn : n ≤ 2 ^ K - 1) :
    (n.factorial * (2 ^ K - 1 - n).factorial).factorization 2 = (2 ^ K - 1).factorial.factorization 2 := by
  have h := Nat.choose_mul_factorial_mul_factorial hn
  have hodd := odd_choose_two_pow_sub_one K n hn
  have hc : ((2 ^ K - 1).choose n).factorization 2 = 0 :=
    Nat.factorization_eq_zero_of_not_dvd (fun h2 => (Nat.not_even_iff_odd.2 hodd) (even_iff_two_dvd.2 h2))
  rw [← h, mul_assoc, Nat.factorization_mul (Nat.choose_ne_zero hn)
    (Nat.mul_ne_zero (Nat.factorial_ne_zero _) (Nat.factorial_ne_zero _)),
    Finsupp.add_apply, hc, zero_add]

/-- `∏_{m < N, m ≠ n} |n - m|`. -/
def prodAbs (N n : ℕ) : ℕ := ∏ m ∈ (range N).erase n, ((n : ℤ) - m).natAbs

theorem prodAbs_eq (N n : ℕ) (hn : n < N) : prodAbs N n = n.factorial * (N - 1 - n).factorial := by
  have hsplit : (range N).erase n = range n ∪ Ico (n + 1) N := by
    ext m; simp only [mem_erase, mem_range, mem_union, mem_Ico]; omega
  have hdisj : Disjoint (range n) (Ico (n + 1) N) := by
    rw [Finset.disjoint_left]; intro m h1 h2; simp only [mem_range, mem_Ico] at h1 h2; omega
  unfold prodAbs
  rw [hsplit, prod_union hdisj]
  congr 1
  · rw [← Finset.prod_range_add_one_eq_factorial, ← Finset.prod_range_reflect]
    refine prod_congr rfl fun m hm => ?_
    rw [mem_range] at hm; omega
  · rw [prod_Ico_eq_prod_range, ← Finset.prod_range_add_one_eq_factorial]
    rw [show N - (n + 1) = N - 1 - n by omega]
    refine prod_congr rfl fun m _ => ?_
    omega

/-- `v₂(𝒞'(q_n))` is the same for every grid point (`lem:tensor-integrality`). -/
theorem factorization_prodAbs_eq (K n n₀ : ℕ) (hn : n < 2 ^ K) (hn₀ : n₀ < 2 ^ K) :
    (prodAbs (2 ^ K) n).factorization 2 = (prodAbs (2 ^ K) n₀).factorization 2 := by
  rw [prodAbs_eq _ _ hn, prodAbs_eq _ _ hn₀, factorization_factorial_mul K n (by omega),
    factorization_factorial_mul K n₀ (by omega)]

/-! ### Odd parts -/

/-- `v₂(d)` and the odd part of a nonzero integer. -/
def val2 (d : ℤ) : ℕ := d.natAbs.factorization 2

def oddPart (d : ℤ) : ℤ := d / 2 ^ val2 d

theorem pow_val2_dvd (d : ℤ) : (2 : ℤ) ^ val2 d ∣ d := by
  have := Nat.ordProj_dvd d.natAbs 2
  exact Int.natAbs_dvd_natAbs.1 (by simpa [val2] using this)

theorem eq_pow_mul_oddPart (d : ℤ) : d = 2 ^ val2 d * oddPart d := by
  rw [oddPart, Int.mul_ediv_cancel' (pow_val2_dvd d)]

theorem odd_oddPart {d : ℤ} (hd : d ≠ 0) : Odd (oddPart d) := by
  have hco := Nat.coprime_ordCompl Nat.prime_two (Int.natAbs_ne_zero.2 hd)
  have habs : (oddPart d).natAbs = ordCompl[2] d.natAbs := by
    rw [oddPart, Int.natAbs_ediv_of_dvd (pow_val2_dvd d)]; simp [val2]
  rw [← Int.natAbs_odd, habs]
  exact Nat.coprime_two_left.1 hco

theorem val2_lt {d : ℤ} {K : ℕ} (hd : d ≠ 0) (hK : d.natAbs < 2 ^ K) : val2 d < K := by
  have h := Nat.le_of_dvd (Int.natAbs_pos.2 hd) (Nat.ordProj_dvd d.natAbs 2)
  exact (Nat.pow_lt_pow_iff_right (by norm_num)).1 (lt_of_le_of_lt h hK)

/-! ### Ring estimates -/

variable {R : Type*} [CommRing R]

/-- The paper's unit criterion in `𝒪`: an odd integer plus an even element is a unit. -/
def OddUnits (R : Type*) [CommRing R] : Prop := ∀ o : ℤ, Odd o → ∀ r : R, IsUnit ((o : R) + 2 * r)

/-- The hypothesis holds in the computation ring `ℤ/2^p`. -/
theorem oddUnits_zmod (p : ℕ) : OddUnits (ZMod (2 ^ p)) := by
  intro o ho r
  obtain ⟨l, rfl⟩ := ho
  have hnil : IsNilpotent (2 * ((l : ZMod (2 ^ p)) + r)) :=
    ⟨p, by rw [mul_pow, show (2 : ZMod (2 ^ p)) ^ p = ((2 ^ p : ℕ) : ZMod (2 ^ p)) by push_cast; rfl,
      ZMod.natCast_self, zero_mul]⟩
  have := hnil.isUnit_one_add
  convert this using 1
  push_cast; ring

/-- `T - q_m` for the node `q_n`, with `T = q_n + 2^K z`. -/
def shifted (K n m : ℕ) (z : R) : R := (((n : ℤ) - m : ℤ) : R) + 2 ^ K * z

theorem shifted_eq {K n m : ℕ} (hnm : n ≠ m) (hK : ((n : ℤ) - m).natAbs < 2 ^ K) (z : R) :
    shifted K n m z = 2 ^ val2 ((n : ℤ) - m) *
      (((oddPart ((n : ℤ) - m)) : R) + 2 ^ (K - val2 ((n : ℤ) - m)) * z) := by
  have hv := val2_lt (d := (n : ℤ) - m) (by omega) hK
  have hd := congrArg (fun d : ℤ => (d : R)) (eq_pow_mul_oddPart ((n : ℤ) - m))
  simp only [Int.cast_mul, Int.cast_pow, Int.cast_ofNat] at hd
  rw [shifted, hd, mul_add, ← mul_assoc, ← pow_add, Nat.add_sub_cancel' hv.le]

/-- `𝒞(T)/(𝒞'(q_{n₀}) (T - q_{m₀}))` lies in `R` and is divisible by `2^(K - v₂(n - m₀))`. -/
theorem first_fraction (hR : OddUnits R) {K n n₀ m₀ : ℕ} (hn : n < 2 ^ K) (hn₀ : n₀ < 2 ^ K)
    (hm₀ : m₀ < 2 ^ K) (hne : m₀ ≠ n) (z : R) :
    ∃ c : R, (2 : R) ^ (K - val2 ((n : ℤ) - m₀)) ∣ c ∧
      c * (((∏ m ∈ (range (2 ^ K)).erase n₀, ((n₀ : ℤ) - m) : ℤ) : R) * shifted K n m₀ z) =
        ∏ m ∈ range (2 ^ K), shifted K n m z := by
  classical
  set s := ((range (2 ^ K)).erase n).erase m₀
  set v : ℕ → ℕ := fun m => val2 ((n : ℤ) - m)
  set g : ℕ → R := fun m => ((oddPart ((n : ℤ) - m)) : R) + 2 ^ (K - v m) * z
  have hbound : ∀ m : ℕ, m < 2 ^ K → ((n : ℤ) - m).natAbs < 2 ^ K := fun m hm => by omega
  have hrest : ∏ m ∈ s, shifted K n m z = 2 ^ (∑ m ∈ s, v m) * ∏ m ∈ s, g m := by
    rw [← prod_pow_eq_pow_sum, ← prod_mul_distrib]
    refine prod_congr rfl fun m hm => ?_
    simp only [s, mem_erase, mem_range] at hm
    exact shifted_eq (Ne.symm hm.2.1) (hbound m hm.2.2) z
  have hn_mem : n ∈ range (2 ^ K) := mem_range.2 hn
  have hm_mem : m₀ ∈ (range (2 ^ K)).erase n := mem_erase.2 ⟨hne, mem_range.2 hm₀⟩
  have hC : ∏ m ∈ range (2 ^ K), shifted K n m z =
      2 ^ K * z * shifted K n m₀ z * (2 ^ (∑ m ∈ s, v m) * ∏ m ∈ s, g m) := by
    rw [← mul_prod_erase _ _ hn_mem, ← mul_prod_erase _ _ hm_mem, hrest]
    simp [shifted]; ring
  have hsum : ∑ m ∈ (range (2 ^ K)).erase n, v m = (prodAbs (2 ^ K) n).factorization 2 := by
    unfold prodAbs
    rw [Nat.factorization_prod fun m hm => by simp only [mem_erase] at hm; omega]
    simp [v, val2]
  have hsum' : v m₀ + ∑ m ∈ s, v m = (prodAbs (2 ^ K) n).factorization 2 := by
    rw [← hsum, ← add_sum_erase _ _ hm_mem]
  set Cp : ℤ := ∏ m ∈ (range (2 ^ K)).erase n₀, ((n₀ : ℤ) - m)
  have hCp0 : Cp ≠ 0 := prod_ne_zero_iff.2 fun m hm => by simp only [mem_erase] at hm; omega
  have hCpabs : Cp.natAbs = prodAbs (2 ^ K) n₀ := map_prod Int.natAbsHom _ _
  have hV : val2 Cp = v m₀ + ∑ m ∈ s, v m := by
    rw [hsum', val2, hCpabs, factorization_prodAbs_eq K n₀ n hn₀ hn]
  obtain ⟨O, hO⟩ := hR (oddPart Cp) (odd_oddPart hCp0) 0
  rw [mul_zero, add_zero] at hO
  have hvK : v m₀ ≤ K := (val2_lt (by omega) (hbound m₀ hm₀)).le
  refine ⟨(2 : R) ^ (K - v m₀) * z * (∏ m ∈ s, g m) * ((O⁻¹ : Rˣ) : R), ⟨z * (∏ m ∈ s, g m) * ((O⁻¹ : Rˣ) : R), by ring⟩, ?_⟩
  have hCpR : ((Cp : ℤ) : R) = 2 ^ val2 Cp * (oddPart Cp : R) := by
    conv_lhs => rw [eq_pow_mul_oddPart Cp]
    push_cast; ring
  rw [hC, hCpR, hV, ← hO]
  have hinv : ((O⁻¹ : Rˣ) : R) * O = 1 := Units.inv_mul O
  have hpow : (2 : R) ^ (K - v m₀) * 2 ^ (v m₀ + ∑ m ∈ s, v m) = 2 ^ K * 2 ^ (∑ m ∈ s, v m) := by
    rw [← pow_add, ← pow_add]; congr 1; omega
  calc (2 : R) ^ (K - v m₀) * z * (∏ m ∈ s, g m) * ((O⁻¹ : Rˣ) : R) *
        (2 ^ (v m₀ + ∑ m ∈ s, v m) * (O : R) * shifted K n m₀ z)
      = ((2 : R) ^ (K - v m₀) * 2 ^ (v m₀ + ∑ m ∈ s, v m)) * z * shifted K n m₀ z *
          (∏ m ∈ s, g m) * (((O⁻¹ : Rˣ) : R) * O) := by ring
    _ = _ := by rw [hpow, hinv]; ring

/-- `ρ = 2^(i+1)/(T - q_{m₀})` is even and `1 - ρ j` is a unit. -/
theorem ratio_even (hR : OddUnits R) {K n m₀ i : ℕ} (hne : n ≠ m₀)
    (hK : ((n : ℤ) - m₀).natAbs < 2 ^ K) (hvi : val2 ((n : ℤ) - m₀) ≤ i) (hiK : i + 1 ≤ K) (z : R) :
    ∃ ρ : R, (2 : R) ∣ ρ ∧ ρ * shifted K n m₀ z = 2 ^ (i + 1) ∧ ∀ j : R, IsUnit (1 - ρ * j) := by
  set v := val2 ((n : ℤ) - m₀)
  have hodd := odd_oddPart (d := (n : ℤ) - m₀) (by omega)
  obtain ⟨w, hw⟩ := hR _ hodd (2 ^ (K - v - 1) * z)
  have hsh : shifted K n m₀ z = 2 ^ v * (w : R) := by
    rw [shifted_eq hne hK, hw]
    congr 2
    rw [← mul_assoc, ← pow_succ']; congr 2; omega
  refine ⟨(2 : R) ^ (i + 1 - v) * ((w⁻¹ : Rˣ) : R), ?_, ?_, fun j => ?_⟩
  · exact dvd_mul_of_dvd_left (dvd_pow_self 2 (by omega)) _
  · rw [hsh]
    calc (2 : R) ^ (i + 1 - v) * ((w⁻¹ : Rˣ) : R) * (2 ^ v * (w : R)) =
        2 ^ (i + 1 - v) * 2 ^ v * (((w⁻¹ : Rˣ) : R) * w) := by ring
      _ = _ := by rw [Units.inv_mul, mul_one, ← pow_add]; congr 1; omega
  · have := hR 1 odd_one (-((2 : R) ^ (i - v) * ((w⁻¹ : Rˣ) : R) * j))
    convert this using 1
    push_cast
    rw [show i + 1 - v = (i - v) + 1 by omega, pow_succ]
    ring

/-- Item 1 assembled: the crossing entry `W_{xy}(T)` expands in modes of weight `b+1`. -/
theorem crossing_mode_expansion (hR : OddUnits R) {K n n₀ m₀ i : ℕ} (hn : n < 2 ^ K)
    (hn₀ : n₀ < 2 ^ K) (hm₀ : m₀ < 2 ^ K) (hne : m₀ ≠ n)
    (hvi : val2 ((n : ℤ) - m₀) ≤ i) (hiK : i + 1 ≤ K) (z j : R) (N : ℕ) :
    ∃ W c ρ : R,
      W * (((∏ m ∈ (range (2 ^ K)).erase n₀, ((n₀ : ℤ) - m) : ℤ) : R) *
        (shifted K n m₀ z - 2 ^ (i + 1) * j)) = ∏ m ∈ range (2 ^ K), shifted K n m z ∧
      (2 : R) ^ (K - i) ∣ c ∧
      (∃ r, W = ∑ b ∈ range N, c * ρ ^ b * j ^ b + 2 ^ (N + 1) * r) ∧
      ∀ b, (2 : R) ^ (b + 1) ∣ c * ρ ^ b := by
  obtain ⟨c, hc, hcC⟩ := first_fraction hR hn hn₀ hm₀ hne z
  obtain ⟨ρ, hρ2, hρ, hunit⟩ := ratio_even hR (Ne.symm hne) (by omega) hvi hiK z
  obtain ⟨u, hu⟩ := hunit j
  have hc' : (2 : R) ^ (K - i) ∣ c := (pow_dvd_pow 2 (by omega)).trans hc
  have hc2 : (2 : R) ∣ c := (dvd_pow_self 2 (by omega)).trans hc'
  have hv : (1 - ρ * j) * ((u⁻¹ : Rˣ) : R) = 1 := by rw [← hu, Units.mul_inv]
  obtain ⟨hexp, hcoef⟩ := geometric_mode_expansion N hv rfl hc2 hρ2
  refine ⟨c * ((u⁻¹ : Rˣ) : R), c, ρ, ?_, hc', hexp, hcoef⟩
  set Cp : R := (((∏ m ∈ (range (2 ^ K)).erase n₀, ((n₀ : ℤ) - m)) : ℤ) : R)
  have : shifted K n m₀ z - 2 ^ (i + 1) * j = shifted K n m₀ z * (1 - ρ * j) := by
    rw [← hρ]; ring
  rw [this, ← hcC]
  calc c * ((u⁻¹ : Rˣ) : R) * (Cp * (shifted K n m₀ z * (1 - ρ * j)))
      = c * (Cp * shifted K n m₀ z) * ((1 - ρ * j) * ((u⁻¹ : Rˣ) : R)) := by ring
    _ = c * (Cp * shifted K n m₀ z) := by rw [hv, mul_one]

/-- `crossing_mode_expansion` in the paper's variables: node `t = q_n = 2^i(2k+1)` with
`i < a`, row slot `x < L`, tile residue `y₀ < 2^(i+1)` with the crossing bit condition,
column `y = y₀ + 2^(i+1) j`. The first fraction is divisible by `2^(a+1-i)`. -/
theorem crossing_entry_expansion (hR : OddUnits R) {a i n n₀ x y₀ : ℕ} {k : ℤ} (hia : i < a)
    (hn : n < 2 ^ (a + 1)) (hn₀ : n₀ < 2 ^ (a + 1)) (ht : (n : ℤ) - 2 ^ a = 2 ^ i * (2 * k + 1))
    (hx : x < 2 ^ a) (hy : y₀ < 2 ^ (i + 1)) (hbit : x / 2 ^ i % 2 = y₀ / 2 ^ i % 2)
    (z j : R) (N : ℕ) :
    ∃ W c ρ : R,
      W * (((∏ m ∈ (range (2 ^ (a + 1))).erase n₀, ((n₀ : ℤ) - m) : ℤ) : R) *
        (shifted (a + 1) n (y₀ + 2 ^ a - x) z - 2 ^ (i + 1) * j)) =
          ∏ m ∈ range (2 ^ (a + 1)), shifted (a + 1) n m z ∧
      (2 : R) ^ (a + 1 - i) ∣ c ∧
      (∃ r, W = ∑ b ∈ range N, c * ρ ^ b * j ^ b + 2 ^ (N + 1) * r) ∧
      ∀ b, (2 : R) ^ (b + 1) ∣ c * ρ ^ b := by
  have hyL : 2 ^ (i + 1) ≤ 2 ^ a := Nat.pow_le_pow_right (by norm_num) hia
  have hpow : 2 ^ (a + 1) = 2 * 2 ^ a := by ring
  have hd : (n : ℤ) - ((y₀ + 2 ^ a - x : ℕ) : ℤ) = 2 ^ i * (2 * k + 1) - y₀ + x := by
    rw [Nat.cast_sub (by omega)]; push_cast; linarith
  obtain ⟨hne0, hv⟩ := crossing_valuation (k := k) hbit
  rw [← hd] at hne0 hv
  exact crossing_mode_expansion hR hn hn₀ (by omega) (fun h => hne0 (by rw [h]; ring)) hv
    (by omega) z j N

end ModeCount
