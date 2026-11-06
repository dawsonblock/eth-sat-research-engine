import D3PotentialIdentity

/-! The complete-label collision potential and the pair-marginal initial
bound both have the diagonal plus twice-unordered-pairs form. This does not
yet prove that the partial-state classifier or Python scorer computes these
terms, nor does it construct a full sequence of vertex assignments. -/

set_option linter.unusedSimpArgs false in
theorem ordered_pair_sum_decomposition
    (edges : List PackingEdge) (f : PackingEdge → PackingEdge → Nat)
    (hsym : ∀ x y, f x y = f y x) :
    sumBy (allOrderedEdgePairs edges) (fun p => f p.1 p.2) =
      sumBy edges (fun e => f e e) +
        2 * sumBy (unorderedEdgePairs edges) (fun p => f p.1 p.2) := by
  induction edges with
  | nil => simp [allOrderedEdgePairs, unorderedEdgePairs, sumBy]
  | cons e es ih =>
      have hc : sumBy es (fun x => f x e) = sumBy es (fun x => f e x) := by
        apply sumBy_congr
        intro x hx
        exact hsym x e
      have ho : sumBy (allOrderedEdgePairs (e :: es)) (fun p => f p.1 p.2) =
          f e e + sumBy es (fun x => f e x) +
          sumBy es (fun x => f x e) +
          sumBy (allOrderedEdgePairs es) (fun p => f p.1 p.2) := by
        unfold allOrderedEdgePairs
        rw [sumBy_flatMap, sumBy_flatMap]
        simp only [sumBy, List.map_cons]
        rw [sumBy_map]
        simp only [Prod.fst, Prod.snd]
        rw [sumBy_add]
        omega
      rw [ho, ih, hc]
      simp only [sumBy, unorderedEdgePairs, sumBy_append, sumBy_map]
      omega

theorem d3_scaled_class_square_eq_diagonal_plus_unordered
    (r a : Nat) (edges : List PackingEdge) (color : PackingEdge → D3EdgeColor) :
    r ^ (2 * a) * d3EdgeClassSquareSum edges color =
      edges.length * r ^ (2 * a) +
        2 * sumBy (unorderedEdgePairs edges) (fun p =>
          if color p.1 == color p.2 then r ^ (2 * a) else 0) := by
  rw [← d3_scaled_ordered_collision_count_eq]
  unfold d3ScaledOrderedCollisionCount
  have hs : ∀ x y : PackingEdge,
      (if color x == color y then r ^ (2 * a) else 0) =
      (if color y == color x then r ^ (2 * a) else 0) := by
    intro x y
    by_cases h : color x = color y
    · simp [h]
    · have h' : color y ≠ color x := Ne.symm h
      simp [h, h']
  have h := ordered_pair_sum_decomposition edges
    (fun x y => if color x == color y then r ^ (2 * a) else 0) hs
  simpa [sumBy_constant] using h

theorem edgePairScaledAgreement_symm (r a : Nat) (x y : PackingEdge) :
    edgePairScaledAgreement r a x y = edgePairScaledAgreement r a y x := by
  by_cases hr : x.1 = y.1 <;> by_cases hc : x.2 = y.2
  · simp only [edgePairScaledAgreement, edgePairUnknown, beq_iff_eq, hr, hc]
  · simp only [edgePairScaledAgreement, edgePairUnknown, beq_iff_eq, hr, hc, Ne.symm hc]
  · simp only [edgePairScaledAgreement, edgePairUnknown, beq_iff_eq, hr, hc, Ne.symm hr]
  · simp only [edgePairScaledAgreement, edgePairUnknown, beq_iff_eq, hr, hc, Ne.symm hr, Ne.symm hc]

theorem scaled_pair_second_moment_eq_diagonal_plus_unordered
    (r a : Nat) (edges : List PackingEdge) :
    scaledPairSecondMoment r a edges = edges.length * r ^ (2 * a) +
      2 * sumBy (unorderedEdgePairs edges)
        (fun p => edgePairScaledAgreement r a p.1 p.2) := by
  have h := ordered_pair_sum_decomposition edges (edgePairScaledAgreement r a)
    (edgePairScaledAgreement_symm r a)
  simpa [scaledPairSecondMoment, edgePairScaledAgreement, edgePairUnknown,
    sumBy_constant] using h

theorem initial_unordered_pair_score_le
    (r a : Nat) (hr : 0 < r) (edges : List PackingEdge) (delta : Nat)
    (hrow : ∀ vertex, rowDegreeOnList edges vertex ≤ delta)
    (hcol : ∀ vertex, columnDegreeOnList edges vertex ≤ delta) :
    edges.length * r ^ (2 * a) +
      2 * sumBy (unorderedEdgePairs edges)
        (fun p => edgePairScaledAgreement r a p.1 p.2) ≤
      edges.length * edges.length + 2 * edges.length * delta * r ^ (2 * a) := by
  rw [← scaled_pair_second_moment_eq_diagonal_plus_unordered]
  have h := scaled_pair_second_moment_sub_square_le r a hr edges delta hrow hcol
  omega

#print axioms ordered_pair_sum_decomposition
#print axioms d3_scaled_class_square_eq_diagonal_plus_unordered
#print axioms scaled_pair_second_moment_eq_diagonal_plus_unordered
#print axioms initial_unordered_pair_score_le
