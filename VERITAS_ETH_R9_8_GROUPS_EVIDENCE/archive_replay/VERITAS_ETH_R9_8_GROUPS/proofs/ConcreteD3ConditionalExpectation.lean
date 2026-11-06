import ConditionalExpectationAverage

/-!
Concrete edge-pair refinement for the candidate-label step in
`lem:tensor-packets` of `paper/quantitative-contraction.tex`.

This file turns each actual bipartite edge pair into the coordinate comparison
states consumed by `coordinate_pair_term_average`. It proves the per-pair and
whole-edge-list averaging identities, and it proves the degree-based count of
ordered edge pairs that share an endpoint. It does not prove the initial
probability-space variance bound, packetization, port loads, or the universal
packing lemma.
-/

inductive PackingSide where
  | row
  | col
  deriving Repr, DecidableEq

abbrev PackingVertex := PackingSide × Nat
abbrev PackingEdge := Nat × Nat
abbrev PackingPartial := PackingVertex → Nat → Option Nat

def classifyEquality (assignments : PackingPartial) (current : PackingVertex)
    (coordinate : Nat) (side : PackingSide) (left right : Nat) : PairComparison :=
  if left == right then
    .resolved
  else
    match assignments (side, left) coordinate, assignments (side, right) coordinate with
    | some x, some y => if x == y then .resolved else .mismatch
    | some x, none => if current == (side, right) then .candidate x else .unresolved
    | none, some y => if current == (side, left) then .candidate y else .unresolved
    | none, none => .unresolved


def assignmentsForCandidate (assignments : PackingPartial)
    (current : PackingVertex) : PackingPartial :=
  fun vertex coordinate => if vertex = current then none else assignments vertex coordinate

theorem assignmentsForCandidate_valid (r : Nat) (assignments : PackingPartial)
    (hassignments : ∀ v d x, assignments v d = some x → x < r)
    (current : PackingVertex) :
    ∀ v d x, assignmentsForCandidate assignments current v d = some x → x < r := by
  intro v d x hv
  by_cases h : v = current
  · simp [assignmentsForCandidate, h] at hv
  · simp [assignmentsForCandidate, h] at hv
    exact hassignments v d x hv

def concretePairCoordinate (assignments : PackingPartial) (current : PackingVertex)
    (coordinate : Nat) (first second : PackingEdge) : PairCoordinate :=
  (classifyEquality assignments current coordinate .row first.1 second.1,
   classifyEquality assignments current coordinate .col first.2 second.2)

theorem classify_candidate_current (assignments : PackingPartial) (current : PackingVertex)
    (coordinate : Nat) (side : PackingSide) (left right target : Nat)
    (h : classifyEquality assignments current coordinate side left right = .candidate target) :
    current.1 = side := by
  unfold classifyEquality at h
  split at h
  · cases h
  · cases hl : assignments (side, left) coordinate with
    | none =>
      cases hr : assignments (side, right) coordinate with
      | none => simp [hl, hr] at h
      | some y =>
        by_cases hc : current = (side, left)
        · simp [hl, hr, hc] at h
          cases h
          exact congrArg Prod.fst hc
        · simp [hl, hr, hc] at h
    | some x =>
      cases hr : assignments (side, right) coordinate with
      | none =>
        by_cases hc : current = (side, right)
        · simp [hl, hr, hc] at h
          cases h
          exact congrArg Prod.fst hc
        · simp [hl, hr, hc] at h
      | some y =>
        by_cases heq : x = y
        · simp [hl, hr, heq] at h
        · simp [hl, hr, heq] at h

theorem classify_candidate_target_valid (r : Nat) (assignments : PackingPartial)
    (hassignments : ∀ v d x, assignments v d = some x → x < r)
    (current : PackingVertex) (coordinate : Nat) (side : PackingSide)
    (left right target : Nat)
    (h : classifyEquality assignments current coordinate side left right = .candidate target) :
    target < r := by
  unfold classifyEquality at h
  split at h
  · cases h
  · cases hl : assignments (side, left) coordinate with
    | none =>
      cases hr : assignments (side, right) coordinate with
      | none => simp [hl, hr] at h
      | some y =>
        by_cases hc : current = (side, left)
        · simp [hl, hr, hc] at h
          subst target
          exact hassignments (side, right) coordinate y hr
        · simp [hl, hr, hc] at h
    | some x =>
      cases hr : assignments (side, right) coordinate with
      | none =>
        by_cases hc : current = (side, right)
        · simp [hl, hr, hc] at h
          subst target
          exact hassignments (side, left) coordinate x hl
        · simp [hl, hr, hc] at h
      | some y =>
        by_cases heq : x = y
        · simp [hl, hr, heq] at h
        · simp [hl, hr, heq] at h

def coordinateHasMismatch (p : PairCoordinate) : Prop :=
  p.1 = .mismatch ∨ p.2 = .mismatch

theorem concretePairCoordinate_valid (r : Nat) (assignments : PackingPartial)
    (hassignments : ∀ v d x, assignments v d = some x → x < r)
    (current : PackingVertex) (coordinate : Nat) (first second : PackingEdge)
    (hNoMismatch : ¬ coordinateHasMismatch
      (concretePairCoordinate assignments current coordinate first second)) :
    coordinateIsValid r (concretePairCoordinate assignments current coordinate first second) := by
  unfold coordinateIsValid concretePairCoordinate coordinateHasMismatch at *
  cases p : classifyEquality assignments current coordinate .row first.1 second.1 with
  | resolved =>
    cases q : classifyEquality assignments current coordinate .col first.2 second.2 with
    | resolved => simp
    | unresolved => simp
    | candidate y => exact classify_candidate_target_valid r assignments hassignments current coordinate .col first.2 second.2 y q
    | mismatch => exact False.elim (hNoMismatch (Or.inr q))
  | unresolved =>
    cases q : classifyEquality assignments current coordinate .col first.2 second.2 with
    | resolved => simp
    | unresolved => simp
    | candidate y => exact classify_candidate_target_valid r assignments hassignments current coordinate .col first.2 second.2 y q
    | mismatch => exact False.elim (hNoMismatch (Or.inr q))
  | candidate x =>
    cases q : classifyEquality assignments current coordinate .col first.2 second.2 with
    | resolved => exact classify_candidate_target_valid r assignments hassignments current coordinate .row first.1 second.1 x p
    | unresolved => exact classify_candidate_target_valid r assignments hassignments current coordinate .row first.1 second.1 x p
    | candidate y =>
        have hcurR := classify_candidate_current assignments current coordinate .row first.1 second.1 x p
        have hcurC := classify_candidate_current assignments current coordinate .col first.2 second.2 y q
        have hside : PackingSide.row = PackingSide.col := (hcurR.symm).trans hcurC
        have : False := by cases hside
        exact False.elim this
    | mismatch => exact False.elim (hNoMismatch (Or.inr q))
  | mismatch => exact False.elim (hNoMismatch (Or.inl p))

def concretePairCoordinates (assignments : PackingPartial) (current : PackingVertex)
    (a : Nat) (first second : PackingEdge) : List PairCoordinate :=
  (List.range a).map (fun d => concretePairCoordinate
    (assignmentsForCandidate assignments current) current d first second)

def pairHasMismatch (coordinates : List PairCoordinate) : Prop :=
  ∃ p, p ∈ coordinates ∧ coordinateHasMismatch p

def coordinateHasMismatchB (p : PairCoordinate) : Bool :=
  (p.1 == .mismatch) || (p.2 == .mismatch)

def pairHasMismatchB : List PairCoordinate → Bool
  | [] => false
  | p :: ps => coordinateHasMismatchB p || pairHasMismatchB ps

theorem pairHasMismatchB_eq_true_iff (coordinates : List PairCoordinate) :
    pairHasMismatchB coordinates = true ↔ pairHasMismatch coordinates := by
  induction coordinates with
  | nil => simp [pairHasMismatchB, pairHasMismatch]
  | cons p ps ih =>
      simp [pairHasMismatchB, pairHasMismatch, coordinateHasMismatchB,
        coordinateHasMismatch, ih]

def concreteD3PairTerm (assignments : PackingPartial) (current : PackingVertex)
    (_r a : Nat) (first second : PackingEdge) : ConditionalPairTerm :=
  if pairHasMismatchB (concretePairCoordinates assignments current a first second) then
    { constraints := none, parentUnknown := 0, coefficient := 2 }
  else
    pairTermOfCoordinates (concretePairCoordinates assignments current a first second)

theorem concretePairCoordinates_length (assignments : PackingPartial)
    (current : PackingVertex) (a : Nat) (first second : PackingEdge) :
    (concretePairCoordinates assignments current a first second).length = a := by
  simp [concretePairCoordinates]

theorem concretePairCoordinates_valid (r : Nat) (assignments : PackingPartial)
    (hassignments : ∀ v d x, assignments v d = some x → x < r)
    (current : PackingVertex) (a : Nat) (first second : PackingEdge)
    (hNoMismatch : ¬ pairHasMismatch
      (concretePairCoordinates assignments current a first second)) :
    ∀ p, p ∈ concretePairCoordinates assignments current a first second →
      coordinateIsValid r p := by
  intro p hp
  simp only [concretePairCoordinates, List.mem_map] at hp
  rcases hp with ⟨d, hd, hEq⟩
  subst p
  apply concretePairCoordinate_valid r (assignmentsForCandidate assignments current)
    (assignmentsForCandidate_valid r assignments hassignments current) current d first second
  intro hbad
  exact hNoMismatch ⟨concretePairCoordinate
      (assignmentsForCandidate assignments current) current d first second,
    by exact List.mem_map.mpr ⟨d, hd, rfl⟩, hbad⟩

theorem concrete_d3_pair_term_average (r a : Nat) (assignments : PackingPartial)
    (hassignments : ∀ v d x, assignments v d = some x → x < r)
    (current : PackingVertex) (first second : PackingEdge) (hr : 0 < r) :
    sumBy (labelWords r a) (pairTermCandidate r a
      (concreteD3PairTerm assignments current r a first second)) =
      r ^ a * pairTermParent r a
        (concreteD3PairTerm assignments current r a first second) := by
  classical
  by_cases hbad : pairHasMismatch
      (concretePairCoordinates assignments current a first second)
  · have hbool : pairHasMismatchB
        (concretePairCoordinates assignments current a first second) = true :=
      (pairHasMismatchB_eq_true_iff _).2 hbad
    have hzero : pairTermCandidate r a
        ({ constraints := none, parentUnknown := 0, coefficient := 2 } : ConditionalPairTerm) =
        (fun _ => 0) := by
      funext word
      simp [pairTermCandidate]
    rw [show concreteD3PairTerm assignments current r a first second =
      ({ constraints := none, parentUnknown := 0, coefficient := 2 } : ConditionalPairTerm) by
        simp [concreteD3PairTerm, hbool]]
    rw [hzero, sumBy_zero]
    simp [pairTermParent]
  · have hbool : pairHasMismatchB
        (concretePairCoordinates assignments current a first second) = false := by
      cases hb : pairHasMismatchB
          (concretePairCoordinates assignments current a first second) with
      | false => rfl
      | true => exact False.elim (hbad ((pairHasMismatchB_eq_true_iff _).1 hb))
    have hlen : (concretePairCoordinates assignments current a first second).length = a :=
      concretePairCoordinates_length assignments current a first second
    have hvalid := concretePairCoordinates_valid r assignments hassignments
      current a first second hbad
    simpa [concreteD3PairTerm, hbool] using
      coordinate_pair_term_average r a
        (concretePairCoordinates assignments current a first second)
        hr hlen hvalid


def unorderedEdgePairs : List PackingEdge → List (PackingEdge × PackingEdge)
  | [] => []
  | edge :: rest => rest.map (fun other => (edge, other)) ++ unorderedEdgePairs rest

def concreteD3PairTerms (assignments : PackingPartial) (current : PackingVertex)
    (r a : Nat) (edges : List PackingEdge) : List ConditionalPairTerm :=
  (unorderedEdgePairs edges).map (fun pair =>
    concreteD3PairTerm assignments current r a pair.1 pair.2)

def concreteD3ScoreCandidate (assignments : PackingPartial) (current : PackingVertex)
    (r a : Nat) (edges : List PackingEdge) (word : List Nat) : Nat :=
  edges.length * r ^ (2 * a) +
    sumBy (concreteD3PairTerms assignments current r a edges)
      (fun term => pairTermCandidate r a term word)

def concreteD3ScoreParent (assignments : PackingPartial) (current : PackingVertex)
    (r a : Nat) (edges : List PackingEdge) : Nat :=
  edges.length * r ^ (2 * a) +
    sumBy (concreteD3PairTerms assignments current r a edges)
      (fun term => pairTermParent r a term)

theorem concrete_d3_pair_terms_average (r a : Nat) (assignments : PackingPartial)
    (hassignments : ∀ v d x, assignments v d = some x → x < r)
    (current : PackingVertex) (edges : List PackingEdge) (hr : 0 < r) :
    sumBy (labelWords r a) (fun word =>
      sumBy (concreteD3PairTerms assignments current r a edges)
        (fun term => pairTermCandidate r a term word)) =
      r ^ a * sumBy (concreteD3PairTerms assignments current r a edges)
        (fun term => pairTermParent r a term) := by
  let pairTerm := fun pair : PackingEdge × PackingEdge =>
    concreteD3PairTerm assignments current r a pair.1 pair.2
  change sumBy (labelWords r a) (fun word =>
      sumBy ((unorderedEdgePairs edges).map pairTerm)
        (fun term => pairTermCandidate r a term word)) =
    r ^ a * sumBy ((unorderedEdgePairs edges).map pairTerm)
        (fun term => pairTermParent r a term)
  calc
    _ = sumBy (labelWords r a) (fun word =>
          sumBy (unorderedEdgePairs edges) (fun pair =>
            pairTermCandidate r a (pairTerm pair) word)) := by
      congr 1
      funext word
      exact sumBy_map (unorderedEdgePairs edges) pairTerm
        (fun term => pairTermCandidate r a term word)
    _ = sumBy (unorderedEdgePairs edges) (fun pair =>
          sumBy (labelWords r a) (fun word =>
            pairTermCandidate r a (pairTerm pair) word)) :=
      sumBy_swap (labelWords r a) (unorderedEdgePairs edges)
        (fun word pair => pairTermCandidate r a (pairTerm pair) word)
    _ = sumBy (unorderedEdgePairs edges) (fun pair =>
          r ^ a * pairTermParent r a (pairTerm pair)) := by
      apply sumBy_congr
      intro pair hp
      exact concrete_d3_pair_term_average r a assignments hassignments current
        pair.1 pair.2 hr
    _ = r ^ a * sumBy (unorderedEdgePairs edges) (fun pair =>
          pairTermParent r a (pairTerm pair)) :=
      sumBy_mul_left (unorderedEdgePairs edges)
        (fun pair => pairTermParent r a (pairTerm pair)) (r ^ a)
    _ = r ^ a * sumBy ((unorderedEdgePairs edges).map pairTerm)
          (fun term => pairTermParent r a term) := by
      rw [sumBy_map]

theorem concrete_d3_score_average (r a : Nat) (assignments : PackingPartial)
    (hassignments : ∀ v d x, assignments v d = some x → x < r)
    (current : PackingVertex) (edges : List PackingEdge) (hr : 0 < r) :
    sumBy (labelWords r a) (fun word =>
      concreteD3ScoreCandidate assignments current r a edges word) =
      r ^ a * concreteD3ScoreParent assignments current r a edges := by
  unfold concreteD3ScoreCandidate concreteD3ScoreParent
  rw [sumBy_add, sumBy_constant, labelWords_length,
    concrete_d3_pair_terms_average r a assignments hassignments current edges hr,
    Nat.mul_add]

#print axioms concretePairCoordinate_valid
#print axioms concrete_d3_pair_term_average
#print axioms concrete_d3_pair_terms_average
#print axioms concrete_d3_score_average

/-! The first counting sublemma used in the paper's variance estimate. -/

def pairSharesEndpoint (first second : PackingEdge) : Bool :=
  (first.1 == second.1) || (first.2 == second.2)

def rowDegreeOnList (edges : List PackingEdge) (vertex : Nat) : Nat :=
  sumBy edges (fun edge => if vertex == edge.1 then 1 else 0)

def columnDegreeOnList (edges : List PackingEdge) (vertex : Nat) : Nat :=
  sumBy edges (fun edge => if vertex == edge.2 then 1 else 0)

def overlapCountWith (edges : List PackingEdge) (edge : PackingEdge) : Nat :=
  sumBy edges (fun other => if pairSharesEndpoint edge other then 1 else 0)

def orderedOverlapCount (edges : List PackingEdge) : Nat :=
  sumBy edges (overlapCountWith edges)

theorem overlap_indicator_le_degrees (edge other : PackingEdge) :
    (if pairSharesEndpoint edge other then 1 else 0) ≤
      (if edge.1 == other.1 then 1 else 0) +
        (if edge.2 == other.2 then 1 else 0) := by
  unfold pairSharesEndpoint
  by_cases hrow : edge.1 = other.1 <;>
  by_cases hcol : edge.2 = other.2 <;>
    simp [hrow, hcol]

theorem overlap_count_with_le_degrees (edges : List PackingEdge) (edge : PackingEdge) :
    overlapCountWith edges edge ≤
      rowDegreeOnList edges edge.1 + columnDegreeOnList edges edge.2 := by
  unfold overlapCountWith
  calc
    _ ≤ sumBy edges (fun other =>
          (if edge.1 == other.1 then 1 else 0) +
            (if edge.2 == other.2 then 1 else 0)) := by
      apply sumBy_le_of_pointwise
      intro other hmem
      exact overlap_indicator_le_degrees edge other
    _ = rowDegreeOnList edges edge.1 + columnDegreeOnList edges edge.2 := by
      rw [sumBy_add]
      rfl

theorem ordered_overlap_count_le_two_m_delta (edges : List PackingEdge) (delta : Nat)
    (hrow : ∀ vertex, rowDegreeOnList edges vertex ≤ delta)
    (hcol : ∀ vertex, columnDegreeOnList edges vertex ≤ delta) :
    orderedOverlapCount edges ≤ 2 * edges.length * delta := by
  unfold orderedOverlapCount
  calc
    _ ≤ sumBy edges (fun _ => 2 * delta) := by
      apply sumBy_le_of_pointwise
      intro edge hmem
      have hlocal := overlap_count_with_le_degrees edges edge
      have hr := hrow edge.1
      have hc := hcol edge.2
      omega
    _ = edges.length * (2 * delta) := sumBy_constant edges (2 * delta)
    _ = 2 * edges.length * delta := by ac_rfl

#print axioms ordered_overlap_count_le_two_m_delta
