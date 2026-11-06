import Lean

/- A conditional arithmetic lemma only. It assumes the two side-load bounds;
   it does not construct a packing or verify tensor identities. -/
theorem conditional_group_wire_bound (r M R C : Nat)
    (hR : r * R ≤ 3 * M) (hC : r * C ≤ 3 * M) :
    r * (R + C) ≤ 6 * M := by
  rw [Nat.mul_add]
  omega

theorem conditional_sixty_four_group_load (M R C : Nat)
    (hR : 64 * R ≤ 3 * M) (hC : 64 * C ≤ 3 * M) :
    32 * (R + C) ≤ 3 * M := by
  have h := conditional_group_wire_bound 64 M R C hR hC
  omega

theorem conditional_sixty_four_group_shrink (M R C : Nat)
    (hM : 0 < M) (hR : 64 * R ≤ 3 * M) (hC : 64 * C ≤ 3 * M) :
    8 * (R + C) < M := by
  have h := conditional_sixty_four_group_load M R C hR hC
  omega

#print axioms conditional_group_wire_bound
#print axioms conditional_sixty_four_group_load
#print axioms conditional_sixty_four_group_shrink
