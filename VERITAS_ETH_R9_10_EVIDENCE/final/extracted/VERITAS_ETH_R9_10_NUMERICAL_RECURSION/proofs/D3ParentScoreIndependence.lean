import D3StateInvariants

/-! A fully unassigned current vertex can be changed without changing the
modeled parent score. The resulting raw state potential satisfies the parent
equality in the conditional run theorem. The child transition equality, its
global probability-space interpretation, and Python refinement remain open. -/

set_option linter.unusedSimpArgs false

theorem classify_unknown_independent (s : PackingPartial) (c1 c2 : PackingVertex)
    (d : Nat) (side : PackingSide) (left right : Nat) :
    comparisonUnknown (classifyEquality s c1 d side left right) =
      comparisonUnknown (classifyEquality s c2 d side left right) := by
  unfold classifyEquality
  split
  · rfl
  · cases hl : s (side, left) d <;> cases hr : s (side, right) d <;>
      simp only [hl, hr]
    all_goals try rfl
    all_goals split <;> split <;> rfl

theorem classify_mismatch_independent (s : PackingPartial) (c1 c2 : PackingVertex)
    (d : Nat) (side : PackingSide) (left right : Nat) :
    (classifyEquality s c1 d side left right == .mismatch) =
      (classifyEquality s c2 d side left right == .mismatch) := by
  unfold classifyEquality
  split
  · rfl
  · cases hl : s (side, left) d <;> cases hr : s (side, right) d <;>
      simp only [hl, hr]
    all_goals try rfl
    all_goals split <;> split <;> rfl

theorem masked_fresh_eq (s : PackingPartial) (c : PackingVertex)
    (hc : ∀ d, s c d = none) : assignmentsForCandidate s c = s := by
  funext v d
  by_cases hv : v = c
  · subst v
    simp [assignmentsForCandidate, hc]
  · simp [assignmentsForCandidate, hv]

theorem coordinate_unknown_independent (s : PackingPartial) (c1 c2 : PackingVertex)
    (d : Nat) (first second : PackingEdge) :
    coordinateUnknown (concretePairCoordinate s c1 d first second) =
      coordinateUnknown (concretePairCoordinate s c2 d first second) := by
  simp only [concretePairCoordinate, coordinateUnknown, Prod.fst, Prod.snd]
  rw [classify_unknown_independent s c1 c2 d .row,
      classify_unknown_independent s c1 c2 d .col]

theorem coordinate_mismatch_independent (s : PackingPartial) (c1 c2 : PackingVertex)
    (d : Nat) (first second : PackingEdge) :
    coordinateHasMismatchB (concretePairCoordinate s c1 d first second) =
      coordinateHasMismatchB (concretePairCoordinate s c2 d first second) := by
  simp only [concretePairCoordinate, coordinateHasMismatchB, Prod.fst, Prod.snd]
  rw [classify_mismatch_independent s c1 c2 d .row,
      classify_mismatch_independent s c1 c2 d .col]

theorem mismatch_map_congr {α : Type} (xs : List α) (f g : α → PairCoordinate)
    (h : ∀ x, x ∈ xs → coordinateHasMismatchB (f x) = coordinateHasMismatchB (g x)) :
    pairHasMismatchB (xs.map f) = pairHasMismatchB (xs.map g) := by
  induction xs with
  | nil => rfl
  | cons x xs ih =>
      simp only [List.map_cons, pairHasMismatchB]
      rw [h x (by simp), ih (by intro y hy; exact h y (by simp [hy]))]

theorem fresh_pair_parent_independent (s : PackingPartial) (c1 c2 : PackingVertex)
    (hc1 : ∀ d, s c1 d = none) (hc2 : ∀ d, s c2 d = none)
    (r a : Nat) (first second : PackingEdge) :
    pairTermParent r a (concreteD3PairTerm s c1 r a first second) =
      pairTermParent r a (concreteD3PairTerm s c2 r a first second) := by
  have hm1 := masked_fresh_eq s c1 hc1
  have hm2 := masked_fresh_eq s c2 hc2
  have hmismatch : pairHasMismatchB (concretePairCoordinates s c1 a first second) =
      pairHasMismatchB (concretePairCoordinates s c2 a first second) := by
    unfold concretePairCoordinates
    rw [hm1, hm2]
    apply mismatch_map_congr
    intro d hd
    exact coordinate_mismatch_independent s c1 c2 d first second
  have hunknown : pairUnknownComparisons (concretePairCoordinates s c1 a first second) =
      pairUnknownComparisons (concretePairCoordinates s c2 a first second) := by
    unfold pairUnknownComparisons concretePairCoordinates
    rw [hm1, hm2, sumBy_map, sumBy_map]
    apply sumBy_congr
    intro d hd
    exact coordinate_unknown_independent s c1 c2 d first second
  unfold concreteD3PairTerm
  rw [hmismatch]
  split <;> simp [pairTermParent, pairTermOfCoordinates, hunknown]

theorem fresh_parent_score_independent (s : PackingPartial) (c1 c2 : PackingVertex)
    (hc1 : ∀ d, s c1 d = none) (hc2 : ∀ d, s c2 d = none)
    (r a : Nat) (edges : List PackingEdge) :
    concreteD3ScoreParent s c1 r a edges = concreteD3ScoreParent s c2 r a edges := by
  unfold concreteD3ScoreParent concreteD3PairTerms
  rw [sumBy_map, sumBy_map]
  congr 1
  apply sumBy_congr
  intro p hp
  exact fresh_pair_parent_independent s c1 c2 hc1 hc2 r a p.1 p.2

def d3RawPairCoordinates (s : PackingPartial) (c : PackingVertex)
    (a : Nat) (first second : PackingEdge) : List PairCoordinate :=
  (List.range a).map (fun d => concretePairCoordinate s c d first second)

def d3RawPairTerm (s : PackingPartial) (c : PackingVertex)
    (a : Nat) (first second : PackingEdge) : ConditionalPairTerm :=
  let coords := d3RawPairCoordinates s c a first second
  if pairHasMismatchB coords then
    { constraints := none, parentUnknown := 0, coefficient := 2 }
  else pairTermOfCoordinates coords

theorem fresh_pair_parent_eq_raw (s : PackingPartial) (c1 c2 : PackingVertex)
    (hc1 : ∀ d, s c1 d = none) (r a : Nat) (first second : PackingEdge) :
    pairTermParent r a (concreteD3PairTerm s c1 r a first second) =
      pairTermParent r a (d3RawPairTerm s c2 a first second) := by
  have hm1 := masked_fresh_eq s c1 hc1
  have hmismatch : pairHasMismatchB (concretePairCoordinates s c1 a first second) =
      pairHasMismatchB (d3RawPairCoordinates s c2 a first second) := by
    unfold concretePairCoordinates d3RawPairCoordinates
    rw [hm1]
    apply mismatch_map_congr
    intro d hd
    exact coordinate_mismatch_independent s c1 c2 d first second
  have hunknown : pairUnknownComparisons (concretePairCoordinates s c1 a first second) =
      pairUnknownComparisons (d3RawPairCoordinates s c2 a first second) := by
    unfold pairUnknownComparisons concretePairCoordinates d3RawPairCoordinates
    rw [hm1, sumBy_map, sumBy_map]
    apply sumBy_congr
    intro d hd
    exact coordinate_unknown_independent s c1 c2 d first second
  unfold concreteD3PairTerm d3RawPairTerm
  dsimp only
  rw [hmismatch]
  split <;> simp [pairTermParent, pairTermOfCoordinates, hunknown]

def d3RawPotential (s : PackingPartial) (r a : Nat) (edges : List PackingEdge) : Nat :=
  edges.length * r ^ (2 * a) +
    sumBy (unorderedEdgePairs edges) (fun p =>
      pairTermParent r a (d3RawPairTerm s (.row, 0) a p.1 p.2))

theorem fresh_parent_eq_raw_potential (s : PackingPartial) (c : PackingVertex)
    (hc : ∀ d, s c d = none) (r a : Nat) (edges : List PackingEdge) :
    concreteD3ScoreParent s c r a edges = d3RawPotential s r a edges := by
  unfold concreteD3ScoreParent concreteD3PairTerms d3RawPotential
  rw [sumBy_map]
  congr 1
  apply sumBy_congr
  intro p hp
  exact fresh_pair_parent_eq_raw s c (.row, 0) hc r a p.1 p.2

theorem fresh_raw_potential_eq_parent (s : PackingPartial) (v : PackingVertex)
    (vs : List PackingVertex) (hf : d3Fresh (v :: vs) s)
    (r a : Nat) (edges : List PackingEdge) :
    d3RawPotential s r a edges = concreteD3ScoreParent s v r a edges := by
  exact (fresh_parent_eq_raw_potential s v (hf.2 v (by simp)) r a edges).symm

theorem d3_raw_run_initial_bound (r a : Nat) (hr : 0 < r)
    (edges : List PackingEdge)
    (hchild : ∀ v vs s word, d3Fresh (v :: vs) s → d3PartialValid r s →
      word ∈ labelWords r a →
      d3RawPotential (d3AssignWord s v word) r a edges =
        concreteD3ScoreCandidate s v r a edges word)
    (v : PackingVertex) (vs : List PackingVertex) (hn : (v :: vs).Nodup)
    (delta : Nat) (hrow : ∀ vertex, rowDegreeOnList edges vertex ≤ delta)
    (hcol : ∀ vertex, columnDegreeOnList edges vertex ≤ delta) :
    d3RawPotential (d3CanonicalRun r a hr edges (v :: vs) emptyPackingAssignments) r a edges ≤
      edges.length * edges.length + 2 * edges.length * delta * r ^ (2 * a) := by
  apply d3_fresh_run_initial_bound r a hr edges
    (fun s => d3RawPotential s r a edges) _ hchild v vs hn delta hrow hcol
  intro current rest s hf hv
  exact fresh_raw_potential_eq_parent s current rest hf r a edges

#print axioms classify_unknown_independent
#print axioms classify_mismatch_independent
#print axioms fresh_pair_parent_independent
#print axioms fresh_parent_score_independent
#print axioms fresh_pair_parent_eq_raw
#print axioms fresh_parent_eq_raw_potential
#print axioms fresh_raw_potential_eq_parent
#print axioms d3_raw_run_initial_bound
