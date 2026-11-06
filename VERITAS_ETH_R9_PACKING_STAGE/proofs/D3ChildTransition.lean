import D3ParentScoreIndependence

/-! Exact transition from the concrete candidate score to the unmasked Lean
state score after assigning a word, including both preexisting mismatches and
newly rejected constraints. The canonical Lean run therefore satisfies its
raw-score bound without a child-transition hypothesis. Equating the final raw
score with realized class loads, connecting global probability semantics, and
refining the Python implementation remain separate obligations. -/

set_option linter.unusedSimpArgs false

def comparisonCandidateFixed : PairComparison → Nat
  | .candidate _ => 1
  | _ => 0

def comparisonRejects (p : PairComparison) (x : Nat) : Bool :=
  match p with
  | .mismatch => true
  | .candidate y => x != y
  | _ => false

theorem classify_assign_transition (s : PackingPartial) (current : PackingVertex)
    (d : Nat) (side : PackingSide) (left right : Nat) (word : List Nat) (x : Nat)
    (hf : s current d = none) (hx : word[d]? = some x) :
    let before := classifyEquality s current d side left right
    let after := classifyEquality (d3AssignWord s current word) current d side left right
    comparisonUnknown before = comparisonUnknown after + comparisonCandidateFixed before ∧
      (after == .mismatch) = comparisonRejects before x := by
  dsimp only
  by_cases hsame : left = right
  · subst right
    simp [classifyEquality, comparisonUnknown, comparisonCandidateFixed, comparisonRejects]
  · by_cases hl : (side, left) = current
    · have hr : (side, right) ≠ current := by
        intro heq
        have h := hl.trans heq.symm
        have : left = right := congrArg Prod.snd h
        exact hsame this
      have hlval : s (side, left) d = none := by rw [hl]; exact hf
      cases hv : s (side, right) d with
      | none =>
          simp [classifyEquality, d3AssignWord, hsame, hl, hr, Ne.symm hr, hf, hlval, hv, hx,
            comparisonUnknown, comparisonCandidateFixed, comparisonRejects]
      | some y =>
          by_cases hxy : x = y
          · simp [classifyEquality, d3AssignWord, hsame, hl, hr, Ne.symm hr, hf, hlval, hv, hx,
              comparisonUnknown, comparisonCandidateFixed, comparisonRejects, hxy]
          · simp [classifyEquality, d3AssignWord, hsame, hl, hr, Ne.symm hr, hf, hlval, hv, hx,
              comparisonUnknown, comparisonCandidateFixed, comparisonRejects, hxy, Ne.symm hxy]
    · by_cases hr : (side, right) = current
      · have hrval : s (side, right) d = none := by rw [hr]; exact hf
        cases hv : s (side, left) d with
        | none =>
            simp [classifyEquality, d3AssignWord, hsame, hl, Ne.symm hl, hr, hf, hrval, hv, hx,
              comparisonUnknown, comparisonCandidateFixed, comparisonRejects]
        | some y =>
            by_cases hxy : x = y
            · simp [classifyEquality, d3AssignWord, hsame, hl, Ne.symm hl, hr, hf, hrval, hv, hx,
                comparisonUnknown, comparisonCandidateFixed, comparisonRejects, hxy]
            · simp [classifyEquality, d3AssignWord, hsame, hl, Ne.symm hl, hr, hf, hrval, hv, hx,
                comparisonUnknown, comparisonCandidateFixed, comparisonRejects, hxy, Ne.symm hxy]
      · cases hv1 : s (side, left) d <;> cases hv2 : s (side, right) d <;>
          simp [classifyEquality, d3AssignWord, hsame, hl, Ne.symm hl, hr, Ne.symm hr,
            hv1, hv2, comparisonUnknown, comparisonCandidateFixed, comparisonRejects]
        all_goals split <;> simp [comparisonUnknown, comparisonCandidateFixed, comparisonRejects]
        all_goals split at * <;> simp_all [comparisonUnknown, comparisonCandidateFixed, comparisonRejects]

theorem coordinate_fixed_is_sum (r : Nat) (p : PairCoordinate)
    (h : coordinateIsValid r p) :
    coordinateFixed p = comparisonCandidateFixed p.1 + comparisonCandidateFixed p.2 := by
  cases p with
  | mk l rcomp =>
      cases l <;> cases rcomp <;>
        simp_all [coordinateIsValid, coordinateFixed, coordinateConstraint, comparisonCandidateFixed]

theorem coordinate_rejects_is_constraint (r : Nat) (p : PairCoordinate)
    (h : coordinateIsValid r p) (x : Nat) :
    (comparisonRejects p.1 x || comparisonRejects p.2 x) =
      (match coordinateConstraint p with | none => false | some target => x != target) := by
  cases p with
  | mk l rcomp =>
      cases l <;> cases rcomp <;>
        simp_all [coordinateIsValid, coordinateConstraint, comparisonRejects]

theorem concrete_coordinate_assign_transition (r : Nat) (s : PackingPartial)
    (hs : ∀ v d x, s v d = some x → x < r) (current : PackingVertex)
    (d : Nat) (first second : PackingEdge) (word : List Nat) (x : Nat)
    (hf : s current d = none) (hx : word[d]? = some x)
    (hgood : ¬ coordinateHasMismatch (concretePairCoordinate s current d first second)) :
    let before := concretePairCoordinate s current d first second
    let after := concretePairCoordinate (d3AssignWord s current word) current d first second
    coordinateUnknown before = coordinateUnknown after + coordinateFixed before ∧
      coordinateHasMismatchB after =
        (match coordinateConstraint before with | none => false | some target => x != target) := by
  have hv := concretePairCoordinate_valid r s hs current d first second hgood
  have hr := classify_assign_transition s current d .row first.1 second.1 word x hf hx
  have hc := classify_assign_transition s current d .col first.2 second.2 word x hf hx
  constructor
  · have hfixed := coordinate_fixed_is_sum r (concretePairCoordinate s current d first second) hv
    simp only [concretePairCoordinate, coordinateUnknown, Prod.fst, Prod.snd] at hfixed ⊢
    omega
  · have hreject := coordinate_rejects_is_constraint r
      (concretePairCoordinate s current d first second) hv x
    simp only [concretePairCoordinate, coordinateHasMismatchB, Prod.fst, Prod.snd]
    rw [hr.2, hc.2]
    exact hreject

inductive D3CoordinateTransitions (r : Nat) :
    List PairCoordinate → List PairCoordinate → List Nat → Prop where
  | nil : D3CoordinateTransitions r [] [] []
  | cons (before after : PairCoordinate) (x : Nat) (bs as' : List PairCoordinate)
      (xs : List Nat) (valid : coordinateIsValid r before)
      (unknown : coordinateUnknown before = coordinateUnknown after + coordinateFixed before)
      (mismatch : coordinateHasMismatchB after =
        (match coordinateConstraint before with | none => false | some target => x != target))
      (rest : D3CoordinateTransitions r bs as' xs) :
      D3CoordinateTransitions r (before :: bs) (after :: as') (x :: xs)

theorem coordinate_transition_list (r : Nat) (before after : List PairCoordinate)
    (word : List Nat) (h : D3CoordinateTransitions r before after word) :
    pairUnknownComparisons before = pairUnknownComparisons after +
      fixedCount (constraintsFromCoordinates before) ∧
    pairHasMismatchB after = !(wordMatches (constraintsFromCoordinates before) word) := by
  induction h with
  | nil => simp [pairUnknownComparisons, sumBy, fixedCount, constraintsFromCoordinates,
      pairHasMismatchB, wordMatches]
  | cons before after x bs as' xs valid unknown mismatch rest ih =>
      have hfixed := fixedCount_constraints_eq_sum (before :: bs)
      constructor
      · simp only [pairUnknownComparisons, sumBy] at ih ⊢
        simp only [fixedCount_constraints_eq_sum, sumBy] at *
        omega
      · simp only [pairHasMismatchB, constraintsFromCoordinates, wordMatches, mismatch, ih.2]
        cases heq : coordinateConstraint before with
        | none => simp [wordMatches, heq]
        | some target =>
            simp only [wordMatches]
            cases hx : (x == target) with
            | false =>
                have hne : x ≠ target := by simpa using hx
                simp [hne]
            | true =>
                have heq' : x = target := by simpa using hx
                simp [heq']

theorem transitions_for_indexed_word (r : Nat) (s : PackingPartial)
    (hs : ∀ v d x, s v d = some x → x < r) (current : PackingVertex)
    (hf : ∀ d, s current d = none) (first second : PackingEdge)
    (word : List Nat) (zs : List (Nat × Nat))
    (hidx : ∀ z, z ∈ zs → word[z.2]? = some z.1)
    (hgood : ∀ z, z ∈ zs →
      ¬ coordinateHasMismatch (concretePairCoordinate s current z.2 first second)) :
    D3CoordinateTransitions r
      (zs.map (fun z => concretePairCoordinate s current z.2 first second))
      (zs.map (fun z => concretePairCoordinate (d3AssignWord s current word) current z.2 first second))
      (zs.map Prod.fst) := by
  induction zs with
  | nil => exact .nil
  | cons z zs ih =>
      simp only [List.map_cons]
      have hz : z ∈ z :: zs := by simp
      have hg := hgood z hz
      have ht := concrete_coordinate_assign_transition r s hs current z.2 first second word z.1
        (hf z.2) (hidx z hz) hg
      apply D3CoordinateTransitions.cons _ _ _ _ _ _
        (concretePairCoordinate_valid r s hs current z.2 first second hg) ht.1 ht.2
      apply ih
      · intro q hq; exact hidx q (by simp [hq])
      · intro q hq; exact hgood q (by simp [hq])

theorem concrete_pair_coordinate_transitions (r a : Nat) (s : PackingPartial)
    (hs : ∀ v d x, s v d = some x → x < r) (current : PackingVertex)
    (hf : ∀ d, s current d = none) (first second : PackingEdge)
    (word : List Nat) (hword : word.length = a)
    (hgood : ¬ pairHasMismatch (concretePairCoordinates s current a first second)) :
    D3CoordinateTransitions r
      (concretePairCoordinates s current a first second)
      (d3RawPairCoordinates (d3AssignWord s current word) current a first second) word := by
  have hmask := masked_fresh_eq s current hf
  have hz := transitions_for_indexed_word r s hs current hf first second word word.zipIdx
    (by
      intro z hz
      exact List.mk_mem_zipIdx_iff_getElem?.mp hz)
    (by
      intro z hz hbad
      have hx := List.mk_mem_zipIdx_iff_getElem?.mp hz
      have hlen := (List.getElem?_eq_some_iff.mp hx).choose
      have hd : z.2 < a := by simpa [hword] using hlen
      apply hgood
      refine ⟨concretePairCoordinate s current z.2 first second, ?_, hbad⟩
      unfold concretePairCoordinates
      rw [hmask]
      exact List.mem_map.mpr ⟨z.2, List.mem_range.mpr hd, rfl⟩)
  have hfirst : word.zipIdx.map (fun z => concretePairCoordinate s current z.2 first second) =
      concretePairCoordinates s current a first second := by
    unfold concretePairCoordinates
    rw [hmask]
    have heq := List.zipIdx_map_snd 0 word
    rw [List.range_eq_range', ← hword, ← heq, List.map_map]
    rfl
  have hsecond : word.zipIdx.map
      (fun z => concretePairCoordinate (d3AssignWord s current word) current z.2 first second) =
      d3RawPairCoordinates (d3AssignWord s current word) current a first second := by
    unfold d3RawPairCoordinates
    have heq := List.zipIdx_map_snd 0 word
    rw [List.range_eq_range', ← hword, ← heq, List.map_map]
    rfl
  rw [hfirst, hsecond, List.zipIdx_map_fst] at hz
  exact hz

theorem coordinate_mismatch_preserved (s : PackingPartial) (current : PackingVertex)
    (d : Nat) (first second : PackingEdge) (word : List Nat) (x : Nat)
    (hf : s current d = none) (hx : word[d]? = some x)
    (hbad : coordinateHasMismatch (concretePairCoordinate s current d first second)) :
    coordinateHasMismatch (concretePairCoordinate (d3AssignWord s current word) current d first second) := by
  unfold coordinateHasMismatch concretePairCoordinate at hbad ⊢
  simp only [Prod.fst, Prod.snd] at hbad ⊢
  rcases hbad with hrow | hcol
  · left
    have h := classify_assign_transition s current d .row first.1 second.1 word x hf hx
    rw [hrow] at h
    have hb : (classifyEquality (d3AssignWord s current word) current d .row first.1 second.1 == .mismatch) = true := by
      simpa [comparisonRejects] using h.2
    exact beq_iff_eq.mp hb
  · right
    have h := classify_assign_transition s current d .col first.2 second.2 word x hf hx
    rw [hcol] at h
    have hb : (classifyEquality (d3AssignWord s current word) current d .col first.2 second.2 == .mismatch) = true := by
      simpa [comparisonRejects] using h.2
    exact beq_iff_eq.mp hb

theorem raw_pair_parent_independent (s : PackingPartial) (c1 c2 : PackingVertex)
    (r a : Nat) (first second : PackingEdge) :
    pairTermParent r a (d3RawPairTerm s c1 a first second) =
      pairTermParent r a (d3RawPairTerm s c2 a first second) := by
  have hmismatch : pairHasMismatchB (d3RawPairCoordinates s c1 a first second) =
      pairHasMismatchB (d3RawPairCoordinates s c2 a first second) := by
    unfold d3RawPairCoordinates
    apply mismatch_map_congr
    intro d hd
    exact coordinate_mismatch_independent s c1 c2 d first second
  have hunknown : pairUnknownComparisons (d3RawPairCoordinates s c1 a first second) =
      pairUnknownComparisons (d3RawPairCoordinates s c2 a first second) := by
    unfold pairUnknownComparisons d3RawPairCoordinates
    rw [sumBy_map, sumBy_map]
    apply sumBy_congr
    intro d hd
    exact coordinate_unknown_independent s c1 c2 d first second
  unfold d3RawPairTerm
  dsimp only
  rw [hmismatch]
  split <;> simp [pairTermParent, pairTermOfCoordinates, hunknown]

theorem pair_mismatch_preserved (s : PackingPartial) (current : PackingVertex)
    (a : Nat) (first second : PackingEdge) (word : List Nat)
    (hf : ∀ d, s current d = none) (hword : word.length = a)
    (hbad : pairHasMismatch (concretePairCoordinates s current a first second)) :
    pairHasMismatch (d3RawPairCoordinates (d3AssignWord s current word) current a first second) := by
  obtain ⟨p, hp, hbad⟩ := hbad
  unfold concretePairCoordinates at hp
  rw [masked_fresh_eq s current hf] at hp
  rcases List.mem_map.mp hp with ⟨d, hd, heq⟩
  subst p
  have hdlen : d < word.length := by simpa [hword] using List.mem_range.mp hd
  have hx : word[d]? = some word[d] := List.getElem?_eq_getElem hdlen
  have hafter := coordinate_mismatch_preserved s current d first second word word[d]
    (hf d) hx hbad
  unfold d3RawPairCoordinates pairHasMismatch
  exact ⟨_, List.mem_map.mpr ⟨d, hd, rfl⟩, hafter⟩

theorem fresh_pair_candidate_eq_raw_child (r a : Nat) (s : PackingPartial)
    (hs : ∀ v d x, s v d = some x → x < r) (current : PackingVertex)
    (hf : ∀ d, s current d = none) (first second : PackingEdge)
    (word : List Nat) (hword : word.length = a) :
    pairTermCandidate r a (concreteD3PairTerm s current r a first second) word =
      pairTermParent r a (d3RawPairTerm (d3AssignWord s current word) current a first second) := by
  by_cases hbad : pairHasMismatch (concretePairCoordinates s current a first second)
  · have hb := (pairHasMismatchB_eq_true_iff _).2 hbad
    have ha := (pairHasMismatchB_eq_true_iff _).2
      (pair_mismatch_preserved s current a first second word hf hword hbad)
    simp [concreteD3PairTerm, d3RawPairTerm, hb, ha, pairTermCandidate, pairTermParent]
  · have hb : pairHasMismatchB (concretePairCoordinates s current a first second) = false := by
      cases h : pairHasMismatchB (concretePairCoordinates s current a first second) with
      | false => rfl
      | true => exact False.elim (hbad ((pairHasMismatchB_eq_true_iff _).1 h))
    have ht := concrete_pair_coordinate_transitions r a s hs current hf first second word hword hbad
    have hp := coordinate_transition_list r _ _ _ ht
    have hsub : pairUnknownComparisons (concretePairCoordinates s current a first second) -
        fixedCount (constraintsFromCoordinates (concretePairCoordinates s current a first second)) =
      pairUnknownComparisons (d3RawPairCoordinates (d3AssignWord s current word) current a first second) := by omega
    unfold concreteD3PairTerm d3RawPairTerm
    dsimp only
    rw [hb, hp.2]
    cases hm : wordMatches (constraintsFromCoordinates (concretePairCoordinates s current a first second)) word <;>
      simp [pairTermCandidate, pairTermParent, pairTermOfCoordinates, hm, hsub]

theorem fresh_candidate_eq_raw_child (r a : Nat) (s : PackingPartial)
    (hs : d3PartialValid r s) (current : PackingVertex)
    (hf : ∀ d, s current d = none) (edges : List PackingEdge)
    (word : List Nat) (hw : word ∈ labelWords r a) :
    concreteD3ScoreCandidate s current r a edges word =
      d3RawPotential (d3AssignWord s current word) r a edges := by
  unfold concreteD3ScoreCandidate concreteD3PairTerms d3RawPotential
  rw [sumBy_map]
  congr 1
  apply sumBy_congr
  intro p hp
  calc
    _ = pairTermParent r a (d3RawPairTerm (d3AssignWord s current word) current a p.1 p.2) :=
      fresh_pair_candidate_eq_raw_child r a s hs current hf p.1 p.2 word
        (labelWords_member_length r a word hw)
    _ = pairTermParent r a (d3RawPairTerm (d3AssignWord s current word) (.row, 0) a p.1 p.2) :=
      raw_pair_parent_independent (d3AssignWord s current word) current (.row, 0) r a p.1 p.2

theorem d3_raw_canonical_run_bound (r a : Nat) (hr : 0 < r)
    (edges : List PackingEdge) (v : PackingVertex) (vs : List PackingVertex)
    (hn : (v :: vs).Nodup) (delta : Nat)
    (hrow : ∀ vertex, rowDegreeOnList edges vertex ≤ delta)
    (hcol : ∀ vertex, columnDegreeOnList edges vertex ≤ delta) :
    d3RawPotential (d3CanonicalRun r a hr edges (v :: vs) emptyPackingAssignments) r a edges ≤
      edges.length * edges.length + 2 * edges.length * delta * r ^ (2 * a) := by
  apply d3_raw_run_initial_bound r a hr edges _ v vs hn delta hrow hcol
  intro current rest s word hf hs hw
  exact (fresh_candidate_eq_raw_child r a s hs current (hf.2 current (by simp)) edges word hw).symm

#print axioms classify_assign_transition
#print axioms coordinate_fixed_is_sum
#print axioms coordinate_rejects_is_constraint
#print axioms concrete_coordinate_assign_transition
#print axioms coordinate_transition_list
#print axioms concrete_pair_coordinate_transitions
#print axioms coordinate_mismatch_preserved
#print axioms raw_pair_parent_independent
#print axioms pair_mismatch_preserved
#print axioms fresh_pair_candidate_eq_raw_child
#print axioms fresh_candidate_eq_raw_child
#print axioms d3_raw_canonical_run_bound
