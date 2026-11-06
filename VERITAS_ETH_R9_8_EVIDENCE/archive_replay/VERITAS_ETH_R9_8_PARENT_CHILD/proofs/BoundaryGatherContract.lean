import BoundaryPartition
open BoundaryGather FiniteBoundaryReduction

theorem r97_entry_contract (t : Factor) (b : Nat → Option Bool) (n : Nat → Nat)
    (x : Nat → Bool) :
    gather t b (little (((freePorts b t.ports).map n).map x)) =
      t.table.getD (little (t.ports.map (restored b (x ∘ n)))) 0 :=
  restricted_eq t b n x

theorem r97_recovery_contract (L R : List Factor) (k l r p : Nat)
    (b : List Bool → Nat → Option Bool) (nl nr : Nat → Nat) :
    assignments k (fun s => assignments l (fun x => assignments r (fun y =>
      parentSide L (b s) nl x * parentSide R (b s) nr y))) % (2:Int)^p =
    assignments k (fun s => assignments l (childSide L (b s) nl) *
      assignments r (childSide R (b s) nr)) % (2:Int)^p :=
  split_recovery L R k l r p b nl nr

#print axioms r97_entry_contract
#print axioms r97_recovery_contract

theorem r97_partition_contract (parent left right : List Factor) (b x y p : Nat)
    (covers : parent.Perm (left ++ right))
    (hl : ∀ t ∈ left, ∀ i ∈ t.ports, i < b+x)
    (hr : ∀ t ∈ right, ∀ i ∈ t.ports, i < b ∨ (b+x ≤ i ∧ i < b+x+y)) :
    assignments (b+x+y) (BoundaryPartition.fullValue parent) % (2:Int)^p =
      assignments b (fun bits =>
        assignments x (childSide left (BoundaryPartition.fixed b bits) (fun i => i-b)) *
        assignments y (childSide right (BoundaryPartition.fixed b bits) (fun i => i-(b+x)))) % (2:Int)^p :=
  BoundaryPartition.network_recovery parent left right b x y p covers hl hr
#print axioms r97_partition_contract
