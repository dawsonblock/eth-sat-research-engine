import Lean

/-!
Finite selection step used by the streaming implementation of
`lem:tensor-packets`.  This proves only the arithmetic fact that a finite,
nonempty candidate list whose average is at most `bound` contains a candidate
at most `bound`.  The Python construction checks the candidate-average
identity for each concrete vertex.  This file does not prove that identity
from the tensor-label probability space, nor does it prove the packet lemma or
the manuscript's recursion and complexity claims.
-/

theorem sum_lower_bound_of_all_gt (xs : List Nat) (bound : Nat)
    (hgt : ∀ x, x ∈ xs → bound < x) :
    xs.length * (bound + 1) ≤ xs.sum := by
  induction xs with
  | nil => simp
  | cons head tail ih =>
      have hhead : bound < head := hgt head (by simp)
      have htail : ∀ x, x ∈ tail → bound < x := by
        intro x hx
        exact hgt x (by simp [hx])
      have hsum := ih htail
      simp only [List.length_cons, List.sum_cons]
      have hhead' : bound + 1 ≤ head := Nat.succ_le_of_lt hhead
      have hparts : tail.length * (bound + 1) + (bound + 1) ≤ tail.sum + head :=
        Nat.add_le_add hsum hhead'
      simpa [Nat.add_mul, Nat.one_mul, Nat.add_comm] using hparts

theorem exists_candidate_le_of_sum_le (scores : List Nat) (bound : Nat)
    (hne : scores ≠ [])
    (hmean : scores.sum ≤ scores.length * bound) :
    ∃ score, score ∈ scores ∧ score ≤ bound := by
  classical
  by_cases hex : ∃ score, score ∈ scores ∧ score ≤ bound
  · exact hex
  · have hgt : ∀ x, x ∈ scores → bound < x := by
      intro x hx
      by_cases hle : x ≤ bound
      · exact False.elim (hex ⟨x, hx, hle⟩)
      · exact Nat.lt_of_not_ge hle
    cases scores with
    | nil => exact False.elim (hne rfl)
    | cons head tail =>
        have hLower := sum_lower_bound_of_all_gt (head :: tail) bound hgt
        simp only [List.length_cons, List.sum_cons] at hmean hLower
        simp only [Nat.add_mul, Nat.one_mul, Nat.mul_add] at hmean hLower
        omega

theorem exists_minimizing_candidate_no_worse_than_parent
    (scores : List Nat) (parentScore : Nat)
    (hne : scores ≠ [])
    (haverage : scores.sum = scores.length * parentScore) :
    ∃ score, score ∈ scores ∧ score ≤ parentScore := by
  apply exists_candidate_le_of_sum_le scores parentScore hne
  omega

#print axioms sum_lower_bound_of_all_gt
#print axioms exists_candidate_le_of_sum_le
#print axioms exists_minimizing_candidate_no_worse_than_parent
