import D3ChildTransition

/-! The completed Lean labeling's raw score equals the realized sum of
squared directed-class loads. A deterministic deduplicated edge-vertex list
provides distinctness and endpoint coverage, giving a class-square bound under
positive radix and degree hypotheses. Port bounds, packet construction,
cost, and refinement to the Python label order and execution remain open. -/

set_option linter.unusedSimpArgs false

def d3EdgeComplete (s : PackingPartial) (a : Nat) (e : PackingEdge) : Prop :=
  ∀ d, d < a → (∃ x, s (.row, e.1) d = some x) ∧
                 (∃ x, s (.col, e.2) d = some x)

def d3PartialColor (s : PackingPartial) (a : Nat) (e : PackingEdge) : D3EdgeColor :=
  d3EdgeColor (fun v d => (s v d).getD 0) a e

theorem complete_classification (s : PackingPartial) (current : PackingVertex)
    (d : Nat) (side : PackingSide) (left right x y : Nat)
    (hx : s (side, left) d = some x) (hy : s (side, right) d = some y) :
    comparisonUnknown (classifyEquality s current d side left right) = 0 ∧
    ((classifyEquality s current d side left right == .mismatch) = false ↔ x = y) := by
  by_cases he : left = right
  · subst right
    have hxy : x = y := by rw [hx] at hy; exact Option.some.inj hy
    simp [classifyEquality, comparisonUnknown, hxy]
  · by_cases hxy : x = y
    · simp [classifyEquality, comparisonUnknown, he, hx, hy, hxy]
    · simp [classifyEquality, comparisonUnknown, he, hx, hy, hxy]

theorem complete_coordinate (s : PackingPartial) (current : PackingVertex) (a d : Nat)
    (first second : PackingEdge) (hfirst : d3EdgeComplete s a first)
    (hsecond : d3EdgeComplete s a second) (hd : d < a) :
    coordinateUnknown (concretePairCoordinate s current d first second) = 0 ∧
    (coordinateHasMismatchB (concretePairCoordinate s current d first second) = false ↔
      (s (.row, first.1) d).getD 0 = (s (.row, second.1) d).getD 0 ∧
      (s (.col, first.2) d).getD 0 = (s (.col, second.2) d).getD 0) := by
  obtain ⟨⟨x, hx⟩, ⟨y, hy⟩⟩ := hfirst d hd
  obtain ⟨⟨x', hx'⟩, ⟨y', hy'⟩⟩ := hsecond d hd
  have hr := complete_classification s current d .row first.1 second.1 x x' hx hx'
  have hc := complete_classification s current d .col first.2 second.2 y y' hy hy'
  simp only [concretePairCoordinate, coordinateUnknown, coordinateHasMismatchB, Prod.fst, Prod.snd]
  simp [hr.1, hc.1, hr.2, hc.2, hx, hy, hx', hy']

theorem mismatch_map_false_iff {α : Type} (xs : List α) (f : α → PairCoordinate) :
    pairHasMismatchB (xs.map f) = false ↔ ∀ x, x ∈ xs → coordinateHasMismatchB (f x) = false := by
  induction xs with
  | nil => simp [pairHasMismatchB]
  | cons x xs ih => simp [pairHasMismatchB, ih]

theorem complete_pair_unknown_zero (s : PackingPartial) (current : PackingVertex)
    (a : Nat) (first second : PackingEdge) (hfirst : d3EdgeComplete s a first)
    (hsecond : d3EdgeComplete s a second) :
    pairUnknownComparisons (d3RawPairCoordinates s current a first second) = 0 := by
  unfold pairUnknownComparisons d3RawPairCoordinates
  rw [sumBy_map]
  calc
    _ = sumBy (List.range a) (fun _ => 0) := by
      apply sumBy_congr
      intro d hd
      exact (complete_coordinate s current a d first second hfirst hsecond (List.mem_range.mp hd)).1
    _ = 0 := sumBy_zero _

theorem complete_pair_mismatch_iff_color (s : PackingPartial) (current : PackingVertex)
    (a : Nat) (first second : PackingEdge) (hfirst : d3EdgeComplete s a first)
    (hsecond : d3EdgeComplete s a second) :
    pairHasMismatchB (d3RawPairCoordinates s current a first second) = false ↔
      d3PartialColor s a first = d3PartialColor s a second := by
  unfold d3RawPairCoordinates
  rw [mismatch_map_false_iff]
  simp only [d3PartialColor, d3EdgeColor, Prod.mk.injEq, List.map_inj_left, List.mem_range]
  constructor
  · intro h
    constructor
    · intro d hd
      exact ((complete_coordinate s current a d first second hfirst hsecond hd).2.mp (h d hd)).1
    · intro d hd
      exact ((complete_coordinate s current a d first second hfirst hsecond hd).2.mp (h d hd)).2
  · rintro ⟨hr, hc⟩ d hd
    exact (complete_coordinate s current a d first second hfirst hsecond hd).2.mpr ⟨hr d hd, hc d hd⟩

theorem complete_pair_term_is_collision (s : PackingPartial) (current : PackingVertex)
    (r a : Nat) (first second : PackingEdge) (hfirst : d3EdgeComplete s a first)
    (hsecond : d3EdgeComplete s a second) :
    pairTermParent r a (d3RawPairTerm s current a first second) =
      if d3PartialColor s a first == d3PartialColor s a second then 2 * r ^ (2 * a) else 0 := by
  have hu := complete_pair_unknown_zero s current a first second hfirst hsecond
  have hm := complete_pair_mismatch_iff_color s current a first second hfirst hsecond
  by_cases he : d3PartialColor s a first = d3PartialColor s a second
  · have hb := hm.mpr he
    simp [d3RawPairTerm, hb, pairTermParent, pairTermOfCoordinates, hu, he]
  · have hb : pairHasMismatchB (d3RawPairCoordinates s current a first second) = true := by
      cases hx : pairHasMismatchB (d3RawPairCoordinates s current a first second) with
      | false => exact False.elim (he (hm.mp hx))
      | true => rfl
    simp [d3RawPairTerm, hb, pairTermParent, he]

theorem unordered_pair_endpoints_mem (edges : List PackingEdge) (p : PackingEdge × PackingEdge)
    (hp : p ∈ unorderedEdgePairs edges) : p.1 ∈ edges ∧ p.2 ∈ edges := by
  induction edges with
  | nil => simp [unorderedEdgePairs] at hp
  | cons e es ih =>
      simp only [unorderedEdgePairs, List.mem_append, List.mem_map] at hp
      rcases hp with ⟨other, ho, heq⟩ | ht
      · subst p
        simp [ho]
      · have h := ih ht
        exact ⟨by simp [h.1], by simp [h.2]⟩

theorem complete_raw_potential_eq_class_square (s : PackingPartial) (r a : Nat)
    (edges : List PackingEdge) (hcomplete : ∀ e, e ∈ edges → d3EdgeComplete s a e) :
    d3RawPotential s r a edges = r ^ (2 * a) * d3EdgeClassSquareSum edges (d3PartialColor s a) := by
  rw [d3_scaled_class_square_eq_diagonal_plus_unordered]
  unfold d3RawPotential
  congr 1
  rw [← sumBy_mul_left]
  apply sumBy_congr
  intro p hp
  have hmem := unordered_pair_endpoints_mem edges p hp
  rw [complete_pair_term_is_collision s (.row, 0) r a p.1 p.2
    (hcomplete p.1 hmem.1) (hcomplete p.2 hmem.2)]
  split <;> simp

def d3VerticesCover (edges : List PackingEdge) (vertices : List PackingVertex) : Prop :=
  ∀ e, e ∈ edges → (.row, e.1) ∈ vertices ∧ (.col, e.2) ∈ vertices

theorem canonical_run_edges_complete (r a : Nat) (hr : 0 < r)
    (edges : List PackingEdge) (vertices : List PackingVertex) (hn : vertices.Nodup)
    (hcover : d3VerticesCover edges vertices) (s : PackingPartial) :
    ∀ e, e ∈ edges → d3EdgeComplete (d3CanonicalRun r a hr edges vertices s) a e := by
  intro e he d hd
  have hc := hcover e he
  obtain ⟨x, hx, _⟩ := d3_run_labels_all r a hr edges vertices hn s (.row, e.1) hc.1 d hd
  obtain ⟨y, hy, _⟩ := d3_run_labels_all r a hr edges vertices hn s (.col, e.2) hc.2 d hd
  exact ⟨⟨x, hx⟩, ⟨y, hy⟩⟩

theorem d3_realized_run_class_square_bound (r a : Nat) (hr : 0 < r)
    (edges : List PackingEdge) (v : PackingVertex) (vs : List PackingVertex)
    (hn : (v :: vs).Nodup) (hcover : d3VerticesCover edges (v :: vs))
    (delta : Nat) (hrow : ∀ vertex, rowDegreeOnList edges vertex ≤ delta)
    (hcol : ∀ vertex, columnDegreeOnList edges vertex ≤ delta) :
    let final := d3CanonicalRun r a hr edges (v :: vs) emptyPackingAssignments
    r ^ (2 * a) * d3EdgeClassSquareSum edges (d3PartialColor final a) ≤
      edges.length * edges.length + 2 * edges.length * delta * r ^ (2 * a) := by
  have hbound := d3_raw_canonical_run_bound r a hr edges v vs hn delta hrow hcol
  have hcomplete := canonical_run_edges_complete r a hr edges (v :: vs) hn hcover emptyPackingAssignments
  rw [complete_raw_potential_eq_class_square _ r a edges hcomplete] at hbound
  exact hbound

def d3UniqueVertices : List PackingVertex → List PackingVertex
  | [] => []
  | v :: vs =>
      let rest := d3UniqueVertices vs
      if v ∈ rest then rest else v :: rest

theorem d3_unique_vertices_mem (vertices : List PackingVertex) (v : PackingVertex) :
    v ∈ d3UniqueVertices vertices ↔ v ∈ vertices := by
  induction vertices generalizing v with
  | nil => simp [d3UniqueVertices]
  | cons head tail ih =>
      simp only [d3UniqueVertices]
      by_cases h : head ∈ d3UniqueVertices tail
      · simp only [h, ↓reduceIte, List.mem_cons, ih]
        constructor
        · intro hv; exact Or.inr hv
        · rintro (heq | hv)
          · subst v; exact (ih head).mp h
          · exact hv
      · simp [h, ih]

theorem d3_unique_vertices_nodup (vertices : List PackingVertex) :
    (d3UniqueVertices vertices).Nodup := by
  induction vertices with
  | nil => simp [d3UniqueVertices]
  | cons head tail ih =>
      simp only [d3UniqueVertices]
      split
      · exact ih
      · exact List.nodup_cons.mpr ⟨by assumption, ih⟩

def d3GraphVertices (edges : List PackingEdge) : List PackingVertex :=
  d3UniqueVertices (edges.map (fun e => (.row, e.1)) ++ edges.map (fun e => (.col, e.2)))

theorem d3_graph_vertices_nodup (edges : List PackingEdge) :
    (d3GraphVertices edges).Nodup := d3_unique_vertices_nodup _

theorem d3_graph_vertices_cover (edges : List PackingEdge) :
    d3VerticesCover edges (d3GraphVertices edges) := by
  intro e he
  constructor
  · unfold d3GraphVertices
    apply (d3_unique_vertices_mem _ _).2
    exact List.mem_append.mpr (Or.inl (List.mem_map.mpr ⟨e, he, rfl⟩))
  · unfold d3GraphVertices
    apply (d3_unique_vertices_mem _ _).2
    exact List.mem_append.mpr (Or.inr (List.mem_map.mpr ⟨e, he, rfl⟩))

theorem d3_generated_run_class_square_bound (r a : Nat) (hr : 0 < r)
    (edges : List PackingEdge) (delta : Nat)
    (hrow : ∀ vertex, rowDegreeOnList edges vertex ≤ delta)
    (hcol : ∀ vertex, columnDegreeOnList edges vertex ≤ delta) :
    let final := d3CanonicalRun r a hr edges (d3GraphVertices edges) emptyPackingAssignments
    r ^ (2 * a) * d3EdgeClassSquareSum edges (d3PartialColor final a) ≤
      edges.length * edges.length + 2 * edges.length * delta * r ^ (2 * a) := by
  cases edges with
  | nil => simp [d3EdgeClassSquareSum, sumBy]
  | cons e es =>
      have hcover := d3_graph_vertices_cover (e :: es)
      have hn := d3_graph_vertices_nodup (e :: es)
      cases hv : d3GraphVertices (e :: es) with
      | nil =>
          have hc := hcover e (by simp)
          rw [hv] at hc
          simp at hc
      | cons v vs =>
          rw [hv] at hn hcover
          have h := d3_realized_run_class_square_bound r a hr (e :: es) v vs hn hcover delta hrow hcol
          simpa [hv] using h

#print axioms complete_classification
#print axioms complete_coordinate
#print axioms mismatch_map_false_iff
#print axioms complete_pair_unknown_zero
#print axioms complete_pair_mismatch_iff_color
#print axioms complete_pair_term_is_collision
#print axioms unordered_pair_endpoints_mem
#print axioms complete_raw_potential_eq_class_square
#print axioms canonical_run_edges_complete
#print axioms d3_realized_run_class_square_bound
#print axioms d3_unique_vertices_mem
#print axioms d3_unique_vertices_nodup
#print axioms d3_graph_vertices_nodup
#print axioms d3_graph_vertices_cover
#print axioms d3_generated_run_class_square_bound
