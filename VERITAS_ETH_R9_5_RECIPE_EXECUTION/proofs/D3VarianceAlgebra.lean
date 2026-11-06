import D3ClassAccounting

/-! Centered class-load variance and common padded-load bounds for the Lean
labeling construction. The final theorem assumes the first two numerical
packing conditions. It does not construct packets, establish port loads,
prove bit complexity, or refine the Python implementation. -/

set_option linter.unusedSimpArgs false

def d3ZSum {α : Type} : List α → (α → Int) → Int
  | [], _ => 0
  | x :: xs, f => f x + d3ZSum xs f

theorem d3ZSum_congr {α : Type} (xs : List α) (f g : α → Int)
    (h : ∀ x, x ∈ xs → f x = g x) : d3ZSum xs f = d3ZSum xs g := by
  induction xs with
  | nil => rfl
  | cons x xs ih =>
      simp only [d3ZSum]
      rw [h x (by simp), ih (by intro y hy; exact h y (by simp [hy]))]

theorem d3ZSum_add {α : Type} (xs : List α) (f g : α → Int) :
    d3ZSum xs (fun x => f x + g x) = d3ZSum xs f + d3ZSum xs g := by
  induction xs with
  | nil => simp [d3ZSum]
  | cons x xs ih => simp only [d3ZSum, ih]; omega

theorem d3ZSum_mul_left {α : Type} (xs : List α) (f : α → Int) (k : Int) :
    d3ZSum xs (fun x => k * f x) = k * d3ZSum xs f := by
  induction xs with
  | nil => simp [d3ZSum]
  | cons x xs ih => simp only [d3ZSum, ih, Int.mul_add]

theorem d3ZSum_constant {α : Type} (xs : List α) (k : Int) :
    d3ZSum xs (fun _ => k) = (xs.length : Int) * k := by
  induction xs with
  | nil => simp [d3ZSum]
  | cons x xs ih => simp only [d3ZSum, ih, List.length_cons, Int.natCast_succ, Int.add_mul, Int.one_mul]; omega

theorem d3ZSum_nat_cast {α : Type} (xs : List α) (f : α → Nat) :
    d3ZSum xs (fun x => (f x : Int)) = (sumBy xs f : Int) := by
  induction xs with
  | nil => rfl
  | cons x xs ih => simp [d3ZSum, sumBy, ih]

theorem d3_centered_scalar_identity (d x m : Int) :
    (d*x-m)*(d*x-m) + 2*d*m*x = d*d*(x*x) + m*m := by
  have h : 2*d*m*x = d*x*m + d*x*m := by
    calc
      _ = 2 * (d*x*m) := by ac_rfl
      _ = d*x*m + d*x*m := by omega
  rw [h]
  simp only [Int.sub_mul, Int.mul_sub]
  simp only [Int.mul_assoc, Int.mul_comm, Int.mul_left_comm]
  omega

theorem d3_centered_sum_identity {α : Type} (xs : List α) (f : α → Int)
    (d m : Int) :
    d3ZSum xs (fun x => (d * f x - m) * (d * f x - m)) +
      (2*d*m) * d3ZSum xs f =
    (d*d) * d3ZSum xs (fun x => f x * f x) + (xs.length : Int) * (m*m) := by
  have h := d3ZSum_congr xs
    (fun x => (d*f x-m)*(d*f x-m) + (2*d*m)*f x)
    (fun x => (d*d)*(f x*f x) + m*m)
    (by intro x hx; exact d3_centered_scalar_identity d (f x) m)
  simp only [d3ZSum_add, d3ZSum_mul_left, d3ZSum_constant] at h
  have hmul : (xs.length : Int) * (m*m) = m * ((xs.length : Int) * m) := by ac_rfl
  rw [hmul]
  exact h

theorem d3ZSum_nonnegative {α : Type} (xs : List α) (f : α → Int)
    (h : ∀ x, x ∈ xs → 0 ≤ f x) : 0 ≤ d3ZSum xs f := by
  induction xs with
  | nil => simp [d3ZSum]
  | cons x xs ih =>
      have hx := h x (by simp)
      have ht := ih (by intro y hy; exact h y (by simp [hy]))
      simp only [d3ZSum]
      omega

theorem d3ZSum_member_le {α : Type} (xs : List α) (f : α → Int)
    (h : ∀ x, x ∈ xs → 0 ≤ f x) (x : α) (hx : x ∈ xs) :
    f x ≤ d3ZSum xs f := by
  induction xs with
  | nil => simp at hx
  | cons y ys ih =>
      simp only [List.mem_cons] at hx
      have htail : ∀ z, z ∈ ys → 0 ≤ f z := by intro z hz; exact h z (by simp [hz])
      have hhead := h y (by simp)
      have hrest := d3ZSum_nonnegative ys f htail
      simp only [d3ZSum]
      rcases hx with heq | hx
      · subst x; omega
      · have hmem := ih htail hx; omega

theorem d3_centered_class_square_bound {α : Type} (classes : List α)
    (load : α → Nat) (D M delta S : Nat)
    (hlen : classes.length = D)
    (hsum : sumBy classes load = M)
    (hsquare : sumBy classes (fun c => load c * load c) = S)
    (hbound : D*S ≤ M*M + 2*M*delta*D)
    (c : α) (hc : c ∈ classes) :
    ((D : Int) * (load c : Int) - (M : Int)) *
      ((D : Int) * (load c : Int) - (M : Int)) ≤
      2 * (M : Int) * (delta : Int) * (D : Int) * (D : Int) := by
  let z : α → Int := fun x => ((D : Int) * (load x : Int) - (M : Int)) *
    ((D : Int) * (load x : Int) - (M : Int))
  have hz : ∀ x, x ∈ classes → 0 ≤ z x := by
    intro x hx
    have h := Int.sq_nonneg ((D : Int) * (load x : Int) - (M : Int))
    simpa [z, Int.pow_succ] using h
  have hmember := d3ZSum_member_le classes z hz c hc
  have hsumZ : d3ZSum classes (fun x => (load x : Int)) = (M : Int) := by
    rw [d3ZSum_nat_cast, hsum]
  have hsqZ : d3ZSum classes (fun x => (load x : Int) * (load x : Int)) = (S : Int) := by
    have h := d3ZSum_nat_cast classes (fun x => load x * load x)
    simpa only [Int.natCast_mul, hsquare] using h
  have hid := d3_centered_sum_identity classes (fun x => (load x : Int)) (D : Int) (M : Int)
  rw [hsumZ, hsqZ, hlen] at hid
  have htwo : 2 * (D : Int) * (M : Int) * (M : Int) =
      (D : Int) * ((M : Int) * (M : Int)) + (D : Int) * ((M : Int) * (M : Int)) := by
    calc
      _ = 2 * ((D : Int) * ((M : Int) * (M : Int))) := by ac_rfl
      _ = _ := by omega
  rw [htwo] at hid
  have hInt : (D : Int)*(S : Int) ≤ (M : Int)*(M : Int) +
      2*(M : Int)*(delta : Int)*(D : Int) := by
    exact_mod_cast hbound
  have hm := Int.mul_le_mul_of_nonneg_left hInt (Int.natCast_nonneg D)
  rw [Int.mul_add] at hm
  have hprod : (D : Int) * ((D : Int) * (S : Int)) = (D : Int)*(D : Int)*(S : Int) := by ac_rfl
  have herr : (D : Int) * (2*(M : Int)*(delta : Int)*(D : Int)) =
      2*(M : Int)*(delta : Int)*(D : Int)*(D : Int) := by ac_rfl
  rw [hprod, herr] at hm
  change z c ≤ _
  change z c ≤ d3ZSum classes z at hmember
  change d3ZSum classes z + _ = _ at hid
  omega

theorem d3_generated_centered_class_bound (r a : Nat) (hr : 0 < r)
    (edges : List PackingEdge) (delta : Nat)
    (hrow : ∀ vertex, rowDegreeOnList edges vertex ≤ delta)
    (hcol : ∀ vertex, columnDegreeOnList edges vertex ≤ delta)
    (c : D3EdgeColor) (hc : c ∈ allWordPairs r a) :
    let final := d3CanonicalRun r a hr edges (d3GraphVertices edges) emptyPackingAssignments
    let load := d3ClassLoad edges (d3PartialColor final a)
    (((r ^ (2*a) : Nat) : Int) * (load c : Int) - (edges.length : Int)) *
      (((r ^ (2*a) : Nat) : Int) * (load c : Int) - (edges.length : Int)) ≤
      2 * (edges.length : Int) * (delta : Int) * ((r ^ (2*a) : Nat) : Int) *
        ((r ^ (2*a) : Nat) : Int) := by
  let final := d3CanonicalRun r a hr edges (d3GraphVertices edges) emptyPackingAssignments
  let load := d3ClassLoad edges (d3PartialColor final a)
  let S := sumBy (allWordPairs r a) (fun c => load c * load c)
  have h := generated_class_accounting r a hr edges delta hrow hcol
  exact d3_centered_class_square_bound (allWordPairs r a) load (r ^ (2*a)) edges.length delta S
    h.1 h.2.1 rfl h.2.2.2 c hc

theorem d3_centered_bound_implies_load_bound (D M delta x : Nat)
    (hregime : 2 * D * D * delta ≤ M)
    (hvariance : ((D : Int)*(x : Int)-(M : Int))*((D : Int)*(x : Int)-(M : Int)) ≤
      2*(M : Int)*(delta : Int)*(D : Int)*(D : Int)) :
    D*x ≤ 2*M := by
  have hmul := Nat.mul_le_mul_right M hregime
  have hcomm : (2*D*D*delta)*M = 2*M*delta*D*D := by ac_rfl
  rw [hcomm] at hmul
  have hInt : 2*(M : Int)*(delta : Int)*(D : Int)*(D : Int) ≤ (M : Int)*(M : Int) := by
    exact_mod_cast hmul
  have hsq := Int.le_trans hvariance hInt
  by_cases hnot : D*x ≤ 2*M
  · exact hnot
  · exfalso
    have hgtNat : 2*M < D*x := Nat.lt_of_not_ge hnot
    have hgt : (M : Int) < (D : Int)*(x : Int)-(M : Int) := by
      have hgtInt : 2*(M : Int) < (D : Int)*(x : Int) := by exact_mod_cast hgtNat
      omega
    have hM : (0 : Int) ≤ M := Int.natCast_nonneg M
    have hz : (0 : Int) < (D : Int)*(x : Int)-(M : Int) := Int.lt_of_le_of_lt hM hgt
    have hle := Int.mul_le_mul_of_nonneg_right (Int.le_of_lt hgt) hM
    have hlt := Int.mul_lt_mul_of_pos_left hgt hz
    omega

theorem d3_generated_class_load_bound (r a : Nat) (hr : 0 < r)
    (edges : List PackingEdge) (delta : Nat)
    (hrow : ∀ vertex, rowDegreeOnList edges vertex ≤ delta)
    (hcol : ∀ vertex, columnDegreeOnList edges vertex ≤ delta)
    (hregime : 2 * (r ^ (2*a)) * (r ^ (2*a)) * delta ≤ edges.length)
    (c : D3EdgeColor) (hc : c ∈ allWordPairs r a) :
    let final := d3CanonicalRun r a hr edges (d3GraphVertices edges) emptyPackingAssignments
    r ^ (2*a) * d3ClassLoad edges (d3PartialColor final a) c ≤ 2*edges.length := by
  exact d3_centered_bound_implies_load_bound (r ^ (2*a)) edges.length delta _ hregime
    (d3_generated_centered_class_bound r a hr edges delta hrow hcol c hc)

def d3MaxClassLoad {α : Type} : List α → (α → Nat) → Nat
  | [], _ => 0
  | c :: cs, load => max (load c) (d3MaxClassLoad cs load)

theorem d3MaxClassLoad_zero {α : Type} (cs : List α) :
    d3MaxClassLoad cs (fun _ => 0) = 0 := by
  induction cs with
  | nil => rfl
  | cons c cs ih => simp only [d3MaxClassLoad, ih, Nat.max_zero]

theorem d3_class_load_le_max {α : Type} (classes : List α) (load : α → Nat)
    (c : α) (hc : c ∈ classes) : load c ≤ d3MaxClassLoad classes load := by
  induction classes with
  | nil => simp at hc
  | cons head tail ih =>
      simp only [List.mem_cons] at hc
      simp only [d3MaxClassLoad]
      rcases hc with heq | ht
      · subst c; exact Nat.le_max_left _ _
      · exact Nat.le_trans (ih ht) (Nat.le_max_right _ _)

theorem d3_max_class_load_scaled_bound {α : Type} (classes : List α) (load : α → Nat)
    (D M : Nat) (h : ∀ c, c ∈ classes → D * load c ≤ 2 * M) :
    D * d3MaxClassLoad classes load ≤ 2 * M := by
  induction classes with
  | nil => simp [d3MaxClassLoad]
  | cons head tail ih =>
      have hh := h head (by simp)
      have ht := ih (by intro c hc; exact h c (by simp [hc]))
      simp only [d3MaxClassLoad]
      by_cases hmax : load head ≤ d3MaxClassLoad tail load
      · rw [Nat.max_eq_right hmax]; exact ht
      · rw [Nat.max_eq_left (Nat.le_of_not_ge hmax)]; exact hh

def d3PaddedClassLoad (L maximum : Nat) : Nat := ((maximum + L - 1) / L) * L

theorem d3_padded_class_load_bounds (L maximum : Nat) (hL : 0 < L) :
    maximum ≤ d3PaddedClassLoad L maximum ∧
    d3PaddedClassLoad L maximum ≤ maximum + L ∧
    L ∣ d3PaddedClassLoad L maximum := by
  unfold d3PaddedClassLoad
  have hrem := Nat.mod_lt (maximum + L - 1) hL
  have hdecomp := Nat.mod_add_div (maximum + L - 1) L
  rw [Nat.mul_comm L ((maximum + L - 1) / L)] at hdecomp
  have hupper := Nat.div_mul_le_self (maximum + L - 1) L
  refine ⟨by omega, by omega, Nat.dvd_mul_left _ _⟩

theorem d3_generated_padded_load_bound (r a : Nat) (hr : 0 < r)
    (edges : List PackingEdge) (delta : Nat)
    (hrow : ∀ vertex, rowDegreeOnList edges vertex ≤ delta)
    (hcol : ∀ vertex, columnDegreeOnList edges vertex ≤ delta)
    (hregime : 2 * (r ^ (2*a)) * (r ^ (2*a)) * delta ≤ edges.length)
    (hwidth : (2^a) * (r ^ (2*a)) ≤ edges.length) :
    let final := d3CanonicalRun r a hr edges (d3GraphVertices edges) emptyPackingAssignments
    let load := d3ClassLoad edges (d3PartialColor final a)
    let maximum := d3MaxClassLoad (allWordPairs r a) load
    let H := d3PaddedClassLoad (2^a) maximum
    (∀ c, c ∈ allWordPairs r a → load c ≤ H) ∧
    (2^a) ∣ H ∧ r ^ (2*a) * H ≤ 3 * edges.length := by
  let final := d3CanonicalRun r a hr edges (d3GraphVertices edges) emptyPackingAssignments
  let load := d3ClassLoad edges (d3PartialColor final a)
  let maximum := d3MaxClassLoad (allWordPairs r a) load
  let H := d3PaddedClassLoad (2^a) maximum
  change (∀ c, c ∈ allWordPairs r a → load c ≤ H) ∧
    (2^a) ∣ H ∧ r ^ (2*a) * H ≤ 3 * edges.length
  have hmax : r ^ (2*a) * maximum ≤ 2 * edges.length := by
    apply d3_max_class_load_scaled_bound
    intro c hc
    exact d3_generated_class_load_bound r a hr edges delta hrow hcol hregime c hc
  have hL : 0 < 2^a := Nat.pow_pos (by decide)
  have hpad := d3_padded_class_load_bounds (2^a) maximum hL
  change maximum ≤ H ∧ H ≤ maximum + 2^a ∧ (2^a) ∣ H at hpad
  have hmul := Nat.mul_le_mul_left (r ^ (2*a)) hpad.2.1
  have hwidth' : r ^ (2*a) * 2^a ≤ edges.length := by
    simpa [Nat.mul_comm] using hwidth
  refine ⟨?_, hpad.2.2, ?_⟩
  · intro c hc
    exact Nat.le_trans (d3_class_load_le_max _ load c hc) hpad.1
  · rw [Nat.mul_add] at hmul
    omega

#print axioms d3_centered_scalar_identity
#print axioms d3_centered_sum_identity
#print axioms d3ZSum_member_le
#print axioms d3_centered_class_square_bound
#print axioms d3_generated_centered_class_bound
#print axioms d3_centered_bound_implies_load_bound
#print axioms d3_generated_class_load_bound
#print axioms d3_class_load_le_max
#print axioms d3_max_class_load_scaled_bound
#print axioms d3_padded_class_load_bounds
/-- `lem:tensor-packets`(1): there are at most `3M/L` packets.  The bound is
stated division-free: `L * packets <= 3M`, which is exactly
`H_pad * D_arr <= 3M` regrouped, because `L` divides `H_pad`. -/
theorem d3_generated_packet_count_bound (r a : Nat) (hr : 0 < r)
    (edges : List PackingEdge) (delta : Nat)
    (hrow : ∀ vertex, rowDegreeOnList edges vertex ≤ delta)
    (hcol : ∀ vertex, columnDegreeOnList edges vertex ≤ delta)
    (hregime : 2 * (r ^ (2*a)) * (r ^ (2*a)) * delta ≤ edges.length)
    (hwidth : (2^a) * (r ^ (2*a)) ≤ edges.length) :
    let final := d3CanonicalRun r a hr edges (d3GraphVertices edges) emptyPackingAssignments
    let load := d3ClassLoad edges (d3PartialColor final a)
    let maximum := d3MaxClassLoad (allWordPairs r a) load
    let H := d3PaddedClassLoad (2^a) maximum
    (2^a) * (r ^ (2*a) * (H / 2^a)) ≤ 3 * edges.length := by
  let final := d3CanonicalRun r a hr edges (d3GraphVertices edges) emptyPackingAssignments
  let load := d3ClassLoad edges (d3PartialColor final a)
  let maximum := d3MaxClassLoad (allWordPairs r a) load
  let H := d3PaddedClassLoad (2^a) maximum
  change (2^a) * (r ^ (2*a) * (H / 2^a)) ≤ 3 * edges.length
  have hb := d3_generated_padded_load_bound r a hr edges delta hrow hcol hregime hwidth
  change (∀ c, c ∈ allWordPairs r a → load c ≤ H) ∧ (2^a) ∣ H ∧
    r ^ (2*a) * H ≤ 3 * edges.length at hb
  calc
    (2^a) * (r ^ (2*a) * (H / 2^a)) = r ^ (2*a) * ((2^a) * (H / 2^a)) := by ac_rfl
    _ = r ^ (2*a) * H := by rw [Nat.mul_div_cancel' hb.2.1]
    _ ≤ 3 * edges.length := hb.2.2

#print axioms d3_generated_packet_count_bound
#print axioms d3_generated_padded_load_bound
