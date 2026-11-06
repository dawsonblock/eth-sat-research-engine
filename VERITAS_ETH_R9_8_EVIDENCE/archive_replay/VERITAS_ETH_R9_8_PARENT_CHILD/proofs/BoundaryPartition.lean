import BoundaryGather

namespace BoundaryPartition
open BoundaryGather FiniteBoundaryReduction

theorem splitBits (k n : Nat) (f : List Bool → Int) :
    assignments (k+n) f = assignments k (fun b => assignments n (fun x => f (b++x))) := by
  induction k generalizing f with
  | zero => simp [assignments]
  | succ k ih =>
    simp only [Nat.succ_add, assignments, ih, List.cons_append]

theorem sumCongr (n : Nat) (f g : List Bool → Int)
    (h : ∀ x, x.length=n → f x = g x) : assignments n f = assignments n g := by
  induction n generalizing f g with
  | zero => exact h [] rfl
  | succ n ih =>
    simp only [assignments]
    congr 1 <;> apply ih <;> intro x hx <;> apply h <;> simp [hx]

def fixed (k : Nat) (b : List Bool) (w : Nat) : Option Bool :=
    if w < k then some (atWire b w) else none

theorem leftWire (b x y : List Bool) (w : Nat) (h : w < b.length+x.length) :
    atWire ((b++x)++y) w =
      restored (fixed b.length b) (atWire x ∘ (fun i => i-b.length)) w := by
  simp only [restored, fixed, atWire, Function.comp_apply, List.getD_eq_getElem?_getD]
  rw [List.getElem?_append_left (by simpa using h)]
  split
  next hc => simp [List.getElem?_append_left hc]
  next hc => simp [List.getElem?_append_right (Nat.le_of_not_gt hc)]

theorem rightWire (b x y : List Bool) (w : Nat) (h : w < b.length ∨ b.length+x.length ≤ w) :
    atWire ((b++x)++y) w =
      restored (fixed b.length b) (atWire y ∘ (fun i => i-(b.length+x.length))) w := by
  rcases h with hc | hc
  · have hfull : w < (b++x).length := by simp; omega
    simp only [restored, fixed, atWire, ite_eq_left hc, Option.getD_some, List.getD_eq_getElem?_getD,
          List.getElem?_append_left hfull, List.getElem?_append_left hc]
  · have hfull : (b++x).length ≤ w := by simpa using hc
    have hnot : ¬w<b.length := by omega
    simp only [restored, fixed, atWire, ite_eq_right hnot, Option.getD_none, Function.comp_apply,
         List.getD_eq_getElem?_getD, List.getElem?_append_right hfull, List.length_append]

def fullValue (ts : List Factor) (bits : List Bool) : Int :=
  (ts.map (fun t => value t (atWire bits))).prod

theorem side_eq (ts : List Factor) (bits : List Bool) (b : Nat → Option Bool)
    (num : Nat → Nat) (x : List Bool)
    (h : ∀ t ∈ ts, ∀ w ∈ t.ports, atWire bits w = restored b (atWire x ∘ num) w) :
    fullValue ts bits = childSide ts b num x := by
  unfold fullValue childSide
  congr 1
  apply List.map_congr_left
  intro t ht
  rw [restricted_eq]
  unfold value
  rw [List.map_congr_left (h t ht)]

theorem prod_perm {xs ys : List Int} (h : xs.Perm ys) : xs.prod=ys.prod := by
  induction h with
  | nil => rfl
  | cons a h ih => simp [List.prod_cons, ih]
  | swap a b xs => simp [List.prod_cons, Int.mul_left_comm]
  | trans _ _ ih₁ ih₂ => exact ih₁.trans ih₂

/-- Input numbering concatenates boundary, left-internal and right-internal
    wires. A factor partition preserves every occurrence via a permutation. -/
theorem network_recovery (ts L R : List Factor) (k l r p : Nat)
    (partition : ts.Perm (L++R))
    (leftPorts : ∀ t ∈ L, ∀ w ∈ t.ports, w < k+l)
    (rightPorts : ∀ t ∈ R, ∀ w ∈ t.ports, w < k ∨ (k+l ≤ w ∧ w < k+l+r)) :
    assignments (k+l+r) (fullValue ts) % (2:Int)^p =
    assignments k (fun b => assignments l (childSide L (fixed k b) (fun w => w-k)) *
      assignments r (childSide R (fixed k b) (fun w => w-(k+l)))) % (2:Int)^p := by
  rw [splitBits (k+l) r, splitBits k l]
  rw [←boundary_mod]
  apply congrArg (fun z : Int => z % (2:Int)^p)
  apply sumCongr; intro b hb
  apply sumCongr; intro x hx
  apply sumCongr; intro y hy
  have hl := side_eq L ((b++x)++y) (fixed k b) (fun w => w-k) x (by
    intro t ht w hw
    simpa [hb,hx] using leftWire b x y w (by simpa [hb,hx] using leftPorts t ht w hw))
  have hr := side_eq R ((b++x)++y) (fixed k b) (fun w => w-(k+l)) y (by
    intro t ht w hw
    have ok : w < k ∨ k+l ≤ w := (rightPorts t ht w hw).imp id And.left
    simpa only [hb,hx] using rightWire b x y w (by simpa only [hb,hx] using ok))
  change fullValue ts _ = _ * _
  rw [←hl, ←hr]
  unfold fullValue
  have perm := partition.map (fun t => value t (atWire ((b++x)++y)))
  rw [prod_perm perm, List.map_append, List.prod_append_int]

#print axioms network_recovery
end BoundaryPartition
