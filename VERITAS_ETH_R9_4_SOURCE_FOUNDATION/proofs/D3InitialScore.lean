import D3CollisionBridge

/-! For the empty partial assignment, the concrete Lean pair classifier's
score equals the finite pair-marginal second moment and inherits its degree
bound. This says nothing yet about later partial assignments, the Python
implementation, or repeated deterministic selection. -/

def emptyPackingAssignments : PackingPartial := fun _ _ => none

theorem empty_coordinates (current : PackingVertex) (a : Nat)
    (first second : PackingEdge) :
    concretePairCoordinates emptyPackingAssignments current a first second =
      List.replicate a
        (if first.1 == second.1 then .resolved else .unresolved,
         if first.2 == second.2 then .resolved else .unresolved) := by
  simp [concretePairCoordinates, concretePairCoordinate, classifyEquality,
    assignmentsForCandidate, emptyPackingAssignments, List.map_const']

theorem mismatch_replicate_false (n : Nat) (p : PairCoordinate)
    (h : coordinateHasMismatchB p = false) :
    pairHasMismatchB (List.replicate n p) = false := by
  induction n with
  | zero => rfl
  | succ n ih => simp [List.replicate_succ, pairHasMismatchB, h, ih]

theorem sumBy_replicate_value {α : Type} (n : Nat) (x : α) (f : α → Nat) :
    sumBy (List.replicate n x) f = n * f x := by
  induction n with
  | zero => simp [sumBy]
  | succ n ih => simp [List.replicate_succ, sumBy, ih, Nat.succ_mul, Nat.add_comm]

theorem empty_pair_parent_eq (r a : Nat) (hr : 0 < r)
    (current : PackingVertex) (first second : PackingEdge) :
    pairTermParent r a (concreteD3PairTerm emptyPackingAssignments current r a first second) =
      2 * edgePairScaledAgreement r a first second := by
  let p : PairCoordinate :=
    (if first.1 == second.1 then .resolved else .unresolved,
     if first.2 == second.2 then .resolved else .unresolved)
  have hm : coordinateHasMismatchB p = false := by
    dsimp [p]
    cases (first.1 == second.1) <;> cases (first.2 == second.2) <;>
      rfl
  have hn : pairHasMismatchB (List.replicate a p) = false :=
    mismatch_replicate_false a p hm
  have hu : a * coordinateUnknown p = edgePairUnknown a first second := by
    dsimp [p, coordinateUnknown, comparisonUnknown, edgePairUnknown]
    cases (first.1 == second.1) <;> cases (first.2 == second.2) <;> simp <;> omega
  unfold concreteD3PairTerm
  rw [empty_coordinates]
  change pairTermParent r a (if pairHasMismatchB (List.replicate a p) then _ else _) = _
  rw [hn]
  simp only [Bool.false_eq_true, ↓reduceIte, pairTermParent, pairTermOfCoordinates,
    pairUnknownComparisons, sumBy_replicate_value]
  change 2 * (r ^ (2 * a) / r ^ (a * coordinateUnknown p)) = _
  rw [hu]
  rw [pow_div_eq_pow_sub r (2 * a) (edgePairUnknown a first second) hr
    (edgePairUnknown_le_two_a a first second)]
  rfl

theorem empty_concrete_score_eq_second_moment (r a : Nat) (hr : 0 < r)
    (current : PackingVertex) (edges : List PackingEdge) :
    concreteD3ScoreParent emptyPackingAssignments current r a edges =
      scaledPairSecondMoment r a edges := by
  unfold concreteD3ScoreParent concreteD3PairTerms
  rw [sumBy_map]
  calc
    _ = edges.length * r ^ (2 * a) +
        sumBy (unorderedEdgePairs edges) (fun p =>
          2 * edgePairScaledAgreement r a p.1 p.2) := by
            congr 1
            apply sumBy_congr
            intro p hp
            exact empty_pair_parent_eq r a hr current p.1 p.2
    _ = edges.length * r ^ (2 * a) +
        2 * sumBy (unorderedEdgePairs edges) (fun p =>
          edgePairScaledAgreement r a p.1 p.2) := by
            rw [sumBy_mul_left]
    _ = scaledPairSecondMoment r a edges :=
          (scaled_pair_second_moment_eq_diagonal_plus_unordered r a edges).symm

theorem empty_concrete_score_le (r a : Nat) (hr : 0 < r)
    (current : PackingVertex) (edges : List PackingEdge) (delta : Nat)
    (hrow : ∀ vertex, rowDegreeOnList edges vertex ≤ delta)
    (hcol : ∀ vertex, columnDegreeOnList edges vertex ≤ delta) :
    concreteD3ScoreParent emptyPackingAssignments current r a edges ≤
      edges.length * edges.length + 2 * edges.length * delta * r ^ (2 * a) := by
  rw [empty_concrete_score_eq_second_moment r a hr current edges]
  rw [scaled_pair_second_moment_eq_diagonal_plus_unordered]
  exact initial_unordered_pair_score_le r a hr edges delta hrow hcol

#print axioms empty_coordinates
#print axioms empty_pair_parent_eq
#print axioms empty_concrete_score_eq_second_moment
#print axioms empty_concrete_score_le
