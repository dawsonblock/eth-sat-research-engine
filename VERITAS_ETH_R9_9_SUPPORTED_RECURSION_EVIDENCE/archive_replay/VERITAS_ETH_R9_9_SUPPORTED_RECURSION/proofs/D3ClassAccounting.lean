import D3RealizedLoads

/-! Exact finite accounting over every directed label class, including empty
classes. The generated Lean labeling has total load M and its class-square
sum agrees with the edge-indexed collision potential. -/

def d3ClassLoad (edges : List PackingEdge) (color : PackingEdge → D3EdgeColor)
    (classColor : D3EdgeColor) : Nat :=
  sumBy edges (fun e => if color e == classColor then 1 else 0)

theorem class_loads_sum (edges : List PackingEdge) (color : PackingEdge → D3EdgeColor)
    (classes : List D3EdgeColor)
    (hcount : ∀ e, e ∈ edges →
      sumBy classes (fun c => if color e == c then 1 else 0) = 1) :
    sumBy classes (d3ClassLoad edges color) = edges.length := by
  unfold d3ClassLoad
  rw [sumBy_swap]
  calc
    _ = sumBy edges (fun _ => 1) := by
      apply sumBy_congr
      intro e he
      exact hcount e he
    _ = edges.length := by simp [sumBy_constant]

theorem class_squares_sum (edges : List PackingEdge) (color : PackingEdge → D3EdgeColor)
    (classes : List D3EdgeColor)
    (hcount : ∀ e, e ∈ edges →
      sumBy classes (fun c => if color e == c then 1 else 0) = 1) :
    sumBy classes (fun c => d3ClassLoad edges color c * d3ClassLoad edges color c) =
      d3EdgeClassSquareSum edges color := by
  calc
    _ = sumBy classes (fun c => sumBy edges (fun e =>
        if color e == c then d3ClassLoad edges color c else 0)) := by
      apply sumBy_congr
      intro c hc
      rw [sumBy_if_constant]
      rfl
    _ = sumBy edges (fun e => sumBy classes (fun c =>
        if color e == c then d3ClassLoad edges color c else 0)) := by
      rw [sumBy_swap]
    _ = sumBy edges (fun e => d3ClassLoad edges color (color e)) := by
      apply sumBy_congr
      intro e he
      calc
        _ = sumBy classes (fun c =>
            if color e == c then d3ClassLoad edges color (color e) else 0) := by
          apply sumBy_congr
          intro c hc
          by_cases h : color e = c
          · subst c; simp
          · simp [h]
        _ = sumBy classes (fun c => if color e == c then 1 else 0) *
            d3ClassLoad edges color (color e) := sumBy_if_constant _ _ _
        _ = d3ClassLoad edges color (color e) := by rw [hcount e he]; simp
    _ = d3EdgeClassSquareSum edges color := by
      unfold d3EdgeClassSquareSum d3EdgeClassLoad d3ClassLoad
      apply sumBy_congr
      intro e he
      apply sumBy_congr
      intro other ho
      by_cases h : color other = color e
      · simp [h]
      · simp [h, Ne.symm h]

theorem valid_word_indicator_count (r a : Nat) (word : List Nat)
    (hlen : word.length = a) (hvals : ∀ x, x ∈ word → x < r) :
    sumBy (labelWords r a) (fun candidate => if word == candidate then 1 else 0) = 1 := by
  have hc := fixed_word_match_count_one r a word hlen hvals
  calc
    _ = sumBy (labelWords r a) (fun candidate =>
        if wordMatches (fixedWordConstraints word) candidate then 1 else 0) := by
      apply sumBy_congr
      intro candidate hcandidate
      by_cases heq : word = candidate
      · subst candidate
        simp [wordMatches_fixed_iff]
      · have hmatch : wordMatches (fixedWordConstraints word) candidate = false := by
          cases hm : wordMatches (fixedWordConstraints word) candidate with
          | false => rfl
          | true => exact False.elim (heq ((wordMatches_fixed_iff word candidate).mp hm))
        simp [heq, hmatch]
    _ = 1 := hc

theorem valid_color_indicator_count (r a : Nat) (left right : List Nat)
    (hl : left.length = a) (hr : right.length = a)
    (hvl : ∀ x, x ∈ left → x < r) (hvr : ∀ x, x ∈ right → x < r) :
    sumBy (allWordPairs r a) (fun c => if (left, right) == c then 1 else 0) = 1 := by
  unfold allWordPairs
  rw [sumBy_flatMap]
  calc
    _ = sumBy (labelWords r a) (fun u => if left == u then 1 else 0) := by
      apply sumBy_congr
      intro u hu
      rw [sumBy_map]
      by_cases heq : left = u
      · subst u
        simpa using valid_word_indicator_count r a right hr hvr
      · simp [heq, sumBy_zero]
    _ = 1 := valid_word_indicator_count r a left hl hvl

theorem canonical_run_color_indicator_count (r a : Nat) (hr : 0 < r)
    (edges : List PackingEdge) (vertices : List PackingVertex) (hn : vertices.Nodup)
    (hcover : d3VerticesCover edges vertices) (s : PackingPartial)
    (e : PackingEdge) (he : e ∈ edges) :
    sumBy (allWordPairs r a) (fun c =>
      if d3PartialColor (d3CanonicalRun r a hr edges vertices s) a e == c then 1 else 0) = 1 := by
  have hcover' := hcover e he
  have hrow : ∀ d, d < a →
      ((d3CanonicalRun r a hr edges vertices s) (.row, e.1) d).getD 0 < r := by
    intro d hd
    obtain ⟨x, hx, hv⟩ := d3_run_labels_all r a hr edges vertices hn s (.row, e.1) hcover'.1 d hd
    simpa [hx] using hv
  have hcol : ∀ d, d < a →
      ((d3CanonicalRun r a hr edges vertices s) (.col, e.2) d).getD 0 < r := by
    intro d hd
    obtain ⟨x, hx, hv⟩ := d3_run_labels_all r a hr edges vertices hn s (.col, e.2) hcover'.2 d hd
    simpa [hx] using hv
  unfold d3PartialColor d3EdgeColor
  apply valid_color_indicator_count r a
  · simp
  · simp
  · intro x hx
    rcases List.mem_map.mp hx with ⟨d, hd, heq⟩
    subst x
    exact hrow d (List.mem_range.mp hd)
  · intro x hx
    rcases List.mem_map.mp hx with ⟨d, hd, heq⟩
    subst x
    exact hcol d (List.mem_range.mp hd)

theorem generated_class_accounting (r a : Nat) (hr : 0 < r)
    (edges : List PackingEdge) (delta : Nat)
    (hrow : ∀ vertex, rowDegreeOnList edges vertex ≤ delta)
    (hcol : ∀ vertex, columnDegreeOnList edges vertex ≤ delta) :
    let final := d3CanonicalRun r a hr edges (d3GraphVertices edges) emptyPackingAssignments
    let color := d3PartialColor final a
    (allWordPairs r a).length = r ^ (2 * a) ∧
    sumBy (allWordPairs r a) (d3ClassLoad edges color) = edges.length ∧
    sumBy (allWordPairs r a) (fun c => d3ClassLoad edges color c * d3ClassLoad edges color c) =
      d3EdgeClassSquareSum edges color ∧
    r ^ (2 * a) * sumBy (allWordPairs r a) (fun c =>
      d3ClassLoad edges color c * d3ClassLoad edges color c) ≤
      edges.length * edges.length + 2 * edges.length * delta * r ^ (2 * a) := by
  let final := d3CanonicalRun r a hr edges (d3GraphVertices edges) emptyPackingAssignments
  let color := d3PartialColor final a
  have hcount : ∀ e, e ∈ edges →
      sumBy (allWordPairs r a) (fun c => if color e == c then 1 else 0) = 1 := by
    intro e he
    exact canonical_run_color_indicator_count r a hr edges (d3GraphVertices edges)
      (d3_graph_vertices_nodup edges) (d3_graph_vertices_cover edges) emptyPackingAssignments e he
  have hsquares := class_squares_sum edges color (allWordPairs r a) hcount
  refine ⟨allWordPairs_length r a, class_loads_sum edges color _ hcount, hsquares, ?_⟩
  rw [hsquares]
  exact d3_generated_run_class_square_bound r a hr edges delta hrow hcol

#print axioms class_loads_sum
#print axioms class_squares_sum
#print axioms valid_word_indicator_count
#print axioms valid_color_indicator_count
#print axioms canonical_run_color_indicator_count
#print axioms generated_class_accounting
