import FiniteBoundaryReduction

namespace BoundaryGather

def bit (b : Bool) : Nat := if b then 1 else 0

def little : List Bool → Nat
  | [] => 0
  | b::bs => bit b + 2 * little bs

/-- Slots in the original tensor's port order. A free position consumes
    exactly one low bit of the child's local table index. -/
def fixedOffset : List (Option Bool) → Nat
  | [] => 0
  | none::ps => 2 * fixedOffset ps
  | (some b)::ps => bit b + 2 * fixedOffset ps

def scatter : List (Option Bool) → Nat → Nat
  | [], _ => 0
  | none::ps, x => x%2 + 2 * scatter ps (x/2)
  | (some _)::ps, x => 2 * scatter ps x

def freePorts (fixed : Nat → Option Bool) : List Nat → List Nat
  | [] => []
  | w::ws => match fixed w with
    | none => w :: freePorts fixed ws
    | some _ => freePorts fixed ws

def restored (fixed : Nat → Option Bool) (atFree : Nat → Bool) (w : Nat) : Bool :=
  (fixed w).getD (atFree w)

theorem gather_index (ports : List Nat) (fixed : Nat → Option Bool) (v : Nat → Bool) :
    fixedOffset (ports.map fixed) +
      scatter (ports.map fixed) (little ((freePorts fixed ports).map v)) =
    little (ports.map (restored fixed v)) := by
  induction ports with
  | nil => rfl
  | cons w ws ih =>
    cases h : fixed w with
    | none =>
      have half (n : Nat) : (1 + 2*n)/2 = n := by omega
      cases hbit : v w <;>
        simp [freePorts, h, hbit, fixedOffset, scatter, little, restored, bit, half] at * <;> omega
    | some b =>
      simp [freePorts, h, fixedOffset, scatter, little, restored] at *; omega

theorem little_bound (bs : List Bool) : little bs < 2^bs.length := by
  induction bs with
  | nil => decide
  | cons b bs ih => cases b <;> simp [little, bit, Nat.pow_succ] <;> omega

theorem valid_gather_address (ps : List Nat) (fixed : Nat → Option Bool) (v : Nat → Bool) :
    fixedOffset (ps.map fixed) + scatter (ps.map fixed) (little ((freePorts fixed ps).map v))
      < 2^ps.length := by
  rw [gather_index]
  simpa using little_bound (ps.map (restored fixed v))

structure Factor where
  ports : List Nat
  table : List Int
  deriving Repr

def value (t : Factor) (assignment : Nat → Bool) : Int :=
  t.table.getD (little (t.ports.map assignment)) 0

def gather (t : Factor) (fixed : Nat → Option Bool) (i : Nat) : Int :=
  t.table.getD (fixedOffset (t.ports.map fixed) + scatter (t.ports.map fixed) i) 0

def restricted (t : Factor) (fixed : Nat → Option Bool) (renumber : Nat → Nat)
    (child : Nat → Bool) : Int :=
  gather t fixed (little (((freePorts fixed t.ports).map renumber).map child))

theorem restricted_eq (t : Factor) (b : Nat → Option Bool) (number : Nat → Nat)
    (x : Nat → Bool) :
    restricted t b number x = value t (restored b (x ∘ number)) := by
  simp only [restricted, List.map_map, gather, value, gather_index]

def atWire (bits : List Bool) (w : Nat) : Bool := bits.getD w false

def parentSide (ts : List Factor) (b : Nat → Option Bool) (num : Nat → Nat)
    (x : List Bool) : Int :=
  (ts.map (fun t => value t (restored b (atWire x ∘ num)))).prod

def childSide (ts : List Factor) (b : Nat → Option Bool) (num : Nat → Nat)
    (x : List Bool) : Int :=
  (ts.map (fun t => restricted t b num (atWire x))).prod

/-- Separated assignment domains. Both sides use the same boundary valuation.
    The closed statement includes table restriction, port renumbering and
    modular contraction. Certification of the incoming graph partition is separate. -/
theorem split_recovery (L R : List Factor) (cut left right p : Nat)
    (fixed : List Bool → Nat → Option Bool) (numL numR : Nat → Nat) :
    FiniteBoundaryReduction.assignments cut (fun b =>
      FiniteBoundaryReduction.assignments left (fun x =>
        FiniteBoundaryReduction.assignments right (fun y =>
          parentSide L (fixed b) numL x * parentSide R (fixed b) numR y))) % (2:Int)^p =
    FiniteBoundaryReduction.assignments cut (fun b =>
      FiniteBoundaryReduction.assignments left (childSide L (fixed b) numL) *
      FiniteBoundaryReduction.assignments right (childSide R (fixed b) numR)) % (2:Int)^p := by
  have eq (ts : List Factor) (b : Nat → Option Bool) (num : Nat → Nat) :
      childSide ts b num = parentSide ts b num := by
    funext x
    simp only [childSide, parentSide, restricted_eq]
  simp only [eq]
  exact FiniteBoundaryReduction.boundary_mod cut left right p _ _

#print axioms valid_gather_address
#print axioms gather_index
#print axioms restricted_eq
#print axioms split_recovery
end BoundaryGather
