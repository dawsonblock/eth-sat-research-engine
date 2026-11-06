import Init

/-! Least representatives of coordinates, not a ring homomorphism.
This models the creation-precision rule in subsec:tensor-children. It does
not verify Python, the packet-entry formula, or recursive reconstruction. -/
namespace SourceCreationPrecision

def capture (p x : Nat) : Nat := x % 2^p

theorem capture_lt (p x : Nat) : capture p x < 2^p :=
  Nat.mod_lt x (Nat.two_pow_pos p)

theorem lift_unchanged (p P x : Nat) (h : p ≤ P) :
    capture P (capture p x) = capture p x := by
  apply Nat.mod_eq_of_lt
  exact Nat.lt_of_lt_of_le (capture_lt p x) (Nat.pow_le_pow_right (by decide) h)

theorem reduce_capture (p P x : Nat) (h : p ≤ P) :
    capture p (capture P x) = capture p x :=
  Nat.mod_mod_of_dvd x (Nat.pow_dvd_pow 2 h)

theorem lift_roundtrip (p P x : Nat) (h : p ≤ P) :
    capture p (capture P (capture p x)) = capture p x := by
  rw [lift_unchanged p P x h]
  exact lift_unchanged p p x (Nat.le_refl p)

def captureCoordinates (p : Nat) (xs : List Nat) := xs.map (capture p)

theorem coordinates_lift_unchanged (p P : Nat) (h : p ≤ P) (xs : List Nat) :
    captureCoordinates P (captureCoordinates p xs) = captureCoordinates p xs := by
  simp only [captureCoordinates, List.map_map]
  apply List.map_congr_left
  intro x _
  exact lift_unchanged p P x h

/- Every later precision is compared with the immutable creation precision.
   This is a coordinate-model theorem, not a Python execution theorem. -/
def liftChain : List Nat → List Nat → List Nat
  | [], xs => xs
  | p :: ps, xs => liftChain ps (captureCoordinates p xs)

theorem coordinates_lift_chain (pc : Nat) (ps xs : List Nat)
    (h : ∀ p ∈ ps, pc ≤ p) :
    liftChain ps (captureCoordinates pc xs) = captureCoordinates pc xs := by
  induction ps with
  | nil => rfl
  | cons p ps ih =>
    simp only [liftChain]
    rw [coordinates_lift_unchanged pc p (h p (by simp)) xs]
    exact ih (fun q hq => h q (by simp [hq]))

theorem coordinates_two_levels (pc p₁ p₂ : Nat) (xs : List Nat)
    (h₁ : pc ≤ p₁) (h₂ : pc ≤ p₂) :
    captureCoordinates p₂ (captureCoordinates p₁ (captureCoordinates pc xs)) =
      captureCoordinates pc xs := by
  rw [coordinates_lift_unchanged pc p₁ h₁ xs]
  exact coordinates_lift_unchanged pc p₂ h₂ xs

theorem lift_not_additive :
    capture 5 (capture 3 (7 + 1)) ≠ capture 5 (capture 3 7 + capture 3 1) := by decide

theorem lift_not_multiplicative :
    capture 5 (capture 3 (3 * 3)) ≠ capture 5 (capture 3 3 * capture 3 3) := by decide

end SourceCreationPrecision

#print axioms SourceCreationPrecision.capture_lt
#print axioms SourceCreationPrecision.lift_unchanged
#print axioms SourceCreationPrecision.reduce_capture
#print axioms SourceCreationPrecision.lift_roundtrip
#print axioms SourceCreationPrecision.coordinates_lift_unchanged
#print axioms SourceCreationPrecision.coordinates_lift_chain
#print axioms SourceCreationPrecision.coordinates_two_levels
#print axioms SourceCreationPrecision.lift_not_additive
#print axioms SourceCreationPrecision.lift_not_multiplicative
