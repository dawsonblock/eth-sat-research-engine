import Init

namespace FiniteBoundaryReduction

/-- Binary elimination sum. Each recursive branch fixes a different next bit. -/
def assignments : Nat → (List Bool → Int) → Int
  | 0, f => f []
  | n+1, f => assignments n (fun x => f (false :: x)) +
                assignments n (fun x => f (true :: x))

theorem factor_left (n : Nat) (a : Int) (f : List Bool → Int) :
    assignments n (fun x => a * f x) = a * assignments n f := by
  induction n generalizing f with
  | zero => rfl
  | succ n ih => simp only [assignments, ih, Int.mul_add]

theorem factor_right (n : Nat) (f : List Bool → Int) (a : Int) :
    assignments n (fun x => f x * a) = assignments n f * a := by
  induction n generalizing f with
  | zero => rfl
  | succ n ih => simp only [assignments, ih, Int.add_mul]

/-- Arbitrary signed weights. Restricting the factors must give f and g
    on disjoint free wires with the same assignment b to every cut wire. -/
theorem boundary_mod (k l r p : Nat) (f g : List Bool → List Bool → Int) :
    (assignments k (fun b => assignments l (fun x =>
       assignments r (fun y => f b x * g b y)))) % (2:Int)^p =
    (assignments k (fun b => assignments l (f b) * assignments r (g b))) % (2:Int)^p := by
  simp only [factor_left, factor_right]

#print axioms factor_left
#print axioms factor_right
#print axioms boundary_mod
end FiniteBoundaryReduction
