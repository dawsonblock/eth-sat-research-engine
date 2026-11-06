import ConcreteD3ConditionalExpectation

/-!
Finite pair-marginal counting for the variance estimate in
`lem:tensor-packets` of `paper/quantitative-contraction.tex`.

For each ordered pair of edges, `edgePairLabelSamples` explicitly lists the
independent labels on its distinct row and column endpoints. The exact count
identity below computes the scaled pair-agreement probability without
division. The final theorem sums those pair contributions and uses the
independently proved degree/overlap bound from
`ConcreteD3ConditionalExpectation`.

This module proves the finite pair-marginal variance bound. It does not yet
prove that the Python state/update implementation refines this model, nor the
global product-space/marginal correspondence, packet padding, port loads, or
the full packing lemma.
-/

theorem labelWords_member_length (r a : Nat) (word : List Nat)
    (hword : word ∈ labelWords r a) : word.length = a := by
  induction a generalizing word with
  | zero => cases word <;> simp [labelWords] at hword ⊢
  | succ a ih =>
      change word ∈ (List.range r).flatMap
        (fun x => (labelWords r a).map (fun w => x :: w)) at hword
      rcases List.mem_flatMap.mp hword with ⟨x, hx, hmap⟩
      rcases List.mem_map.mp hmap with ⟨tail, htail, hcons⟩
      subst word
      have htailLen := ih tail htail
      simp [htailLen]

theorem labelWords_member_symbols_lt (r a : Nat) (word : List Nat)
    (hword : word ∈ labelWords r a) : ∀ x, x ∈ word → x < r := by
  induction a generalizing word with
  | zero =>
      simp [labelWords] at hword
      subst word
      simp
  | succ a ih =>
      change word ∈ (List.range r).flatMap
        (fun x => (labelWords r a).map (fun w => x :: w)) at hword
      rcases List.mem_flatMap.mp hword with ⟨head, hhead, hmap⟩
      rcases List.mem_map.mp hmap with ⟨tail, htail, hcons⟩
      subst word
      intro x hx
      simp only [List.mem_cons] at hx
      rcases hx with rfl | hx
      · exact List.mem_range.mp hhead
      · exact ih tail htail x hx

def fixedWordConstraints (word : List Nat) : List (Option Nat) := word.map some

theorem wordMatches_fixed_iff (left right : List Nat) :
    wordMatches (fixedWordConstraints left) right = true ↔ left = right := by
  induction left generalizing right with
  | nil => cases right <;> simp [fixedWordConstraints, wordMatches]
  | cons x xs ih =>
      cases right with
      | nil => simp [fixedWordConstraints, wordMatches]
      | cons y ys =>
          simp only [fixedWordConstraints, List.map_cons, wordMatches,
            Bool.and_eq_true, beq_iff_eq]
          constructor
          · rintro ⟨hxy, htail⟩
            subst y
            have hEq := (ih ys).mp htail
            subst ys
            rfl
          · intro h
            cases h
            exact ⟨rfl, (ih xs).mpr rfl⟩

theorem fixedWordConstraints_valid (r : Nat) (word : List Nat)
    (hword : ∀ x, x ∈ word → x < r) :
    ∀ c, some c ∈ fixedWordConstraints word → c < r := by
  intro c hc
  simp only [fixedWordConstraints, List.mem_map] at hc
  rcases hc with ⟨x, hx, hSome⟩
  cases hSome
  exact hword c hx

theorem fixedWordConstraints_length (word : List Nat) :
    (fixedWordConstraints word).length = word.length := by
  simp [fixedWordConstraints]

theorem wildcardCount_fixedWordConstraints (word : List Nat) :
    wildcardCount (fixedWordConstraints word) = 0 := by
  induction word with
  | nil => rfl
  | cons x xs ih =>
      change wildcardCount (some x :: fixedWordConstraints xs) = 0
      simp [wildcardCount, ih]

theorem fixed_word_match_count_one (r a : Nat) (word : List Nat)
    (hwordLen : word.length = a)
    (hwordValues : ∀ x, x ∈ word → x < r) :
    sumBy (labelWords r a) (fun candidate =>
      if wordMatches (fixedWordConstraints word) candidate then 1 else 0) = 1 := by
  have hvalid := fixedWordConstraints_valid r word hwordValues
  have hcount := countSatisfyingWords r (fixedWordConstraints word) hvalid
  rw [fixedWordConstraints_length, hwordLen, wildcardCount_fixedWordConstraints] at hcount
  simpa using hcount

def equalWordPairCount (r a : Nat) : Nat :=
  sumBy (labelWords r a) (fun left =>
    sumBy (labelWords r a) (fun right => if right == left then 1 else 0))

theorem equalWordPairCount_eq (r a : Nat) :
    equalWordPairCount r a = r ^ a := by
  unfold equalWordPairCount
  calc
    sumBy (labelWords r a) (fun left =>
        sumBy (labelWords r a) (fun right => if right == left then 1 else 0)) =
      sumBy (labelWords r a) (fun _ => 1) := by
        apply sumBy_congr
        intro left hleft
        have hlen := labelWords_member_length r a left hleft
        have hvalues := labelWords_member_symbols_lt r a left hleft
        have hcount := fixed_word_match_count_one r a left hlen hvalues
        have hcongr :
            sumBy (labelWords r a) (fun right => if right == left then 1 else 0) =
              sumBy (labelWords r a) (fun right =>
                if wordMatches (fixedWordConstraints left) right then 1 else 0) := by
          apply sumBy_congr
          intro right hright
          by_cases h : right = left
          · subst right
            simp [wordMatches_fixed_iff]
          · have hnot : wordMatches (fixedWordConstraints left) right = false := by
              cases hm : wordMatches (fixedWordConstraints left) right with
              | false => rfl
              | true => exact False.elim (h ((wordMatches_fixed_iff left right).mp hm).symm)
            simp [h, hnot]
        rw [hcongr]
        exact hcount
    _ = (labelWords r a).length := by simp [sumBy_constant]
    _ = r ^ a := labelWords_length r a

def allWordPairs (r a : Nat) : List (List Nat × List Nat) :=
  (labelWords r a).flatMap (fun left =>
    (labelWords r a).map (fun right => (left, right)))

theorem allWordPairs_length (r a : Nat) :
    (allWordPairs r a).length = r ^ (2 * a) := by
  unfold allWordPairs
  rw [List.length_flatMap, sum_map_eq_sumBy]
  have hconstant :
      sumBy (labelWords r a) (fun left =>
        ((labelWords r a).map (fun right => (left, right))).length) =
      sumBy (labelWords r a) (fun _ => (labelWords r a).length) := by
    apply sumBy_congr
    intro left hleft
    simp
  rw [hconstant, sumBy_constant, labelWords_length]
  rw [← Nat.pow_add]
  congr 1
  omega

theorem allWordPairs_equal_count (r a : Nat) :
    sumBy (allWordPairs r a) (fun pair => if pair.1 == pair.2 then 1 else 0) = r ^ a := by
  unfold allWordPairs
  rw [sumBy_flatMap]
  have hinner :
      ∀ left, left ∈ labelWords r a →
        sumBy ((labelWords r a).map (fun right => (left, right)))
          (fun pair => if pair.1 == pair.2 then 1 else 0) = 1 := by
    intro left hleft
    have hlen := labelWords_member_length r a left hleft
    have hvalues := labelWords_member_symbols_lt r a left hleft
    have hcount := fixed_word_match_count_one r a left hlen hvalues
    rw [sumBy_map]
    have hcongr :
        sumBy (labelWords r a) (fun right => if left == right then 1 else 0) =
          sumBy (labelWords r a) (fun right =>
            if wordMatches (fixedWordConstraints left) right then 1 else 0) := by
      apply sumBy_congr
      intro right hright
      by_cases heq : right = left
      · subst right
        simp [wordMatches_fixed_iff]
      · have hnot : wordMatches (fixedWordConstraints left) right = false := by
          cases hm : wordMatches (fixedWordConstraints left) right with
          | false => rfl
          | true => exact False.elim (heq ((wordMatches_fixed_iff left right).mp hm).symm)
        have hne : left ≠ right := fun hEq => heq hEq.symm
        simp [hne, hnot]
    rw [hcongr]
    exact hcount
  calc
    sumBy (labelWords r a) (fun left =>
        sumBy ((labelWords r a).map (fun right => (left, right)))
          (fun pair => if pair.1 == pair.2 then 1 else 0)) =
      sumBy (labelWords r a) (fun _ => 1) := by
        apply sumBy_congr
        exact hinner
    _ = (labelWords r a).length := by simp [sumBy_constant]
    _ = r ^ a := labelWords_length r a

def sideLabelPairSamples (r a : Nat) (sameEndpoint : Bool) :
    List (List Nat × List Nat) :=
  if sameEndpoint then
    (labelWords r a).map (fun word => (word, word))
  else
    allWordPairs r a

theorem sideLabelPairSamples_length (r a : Nat) (sameEndpoint : Bool) :
    (sideLabelPairSamples r a sameEndpoint).length =
      if sameEndpoint then r ^ a else r ^ (2 * a) := by
  cases sameEndpoint <;> simp [sideLabelPairSamples, allWordPairs_length, labelWords_length]

def sideLabelPairAgreementCount (r a : Nat) (sameEndpoint : Bool) : Nat :=
  sumBy (sideLabelPairSamples r a sameEndpoint)
    (fun pair => if pair.1 == pair.2 then 1 else 0)

theorem sideLabelPairAgreementCount_eq (r a : Nat) (sameEndpoint : Bool) :
    sideLabelPairAgreementCount r a sameEndpoint = r ^ a := by
  cases sameEndpoint with
  | false =>
      simpa [sideLabelPairAgreementCount, sideLabelPairSamples] using
        allWordPairs_equal_count r a
  | true =>
      change sumBy ((labelWords r a).map (fun word => (word, word)))
        (fun pair => if pair.1 == pair.2 then 1 else 0) = r ^ a
      rw [sumBy_map]
      simp [sumBy_constant, labelWords_length]

theorem sumBy_mul_right {α : Type} (xs : List α) (f : α → Nat) (c : Nat) :
    sumBy xs (fun x => f x * c) = sumBy xs f * c := by
  induction xs with
  | nil => simp [sumBy]
  | cons x xs ih =>
      simp only [sumBy]
      rw [Nat.add_mul, ih]

theorem flatMap_map_length {α β : Type} (xs : List α) (ys : List β) :
    (xs.flatMap (fun x => ys.map (fun y => (x, y)))).length = xs.length * ys.length := by
  rw [List.length_flatMap, sum_map_eq_sumBy]
  have hconstant :
      sumBy xs (fun x => (ys.map (fun y => (x, y))).length) =
        sumBy xs (fun _ => ys.length) := by
    apply sumBy_congr
    intro x hx
    simp
  rw [hconstant, sumBy_constant]

def edgePairLabelSamples (r a : Nat) (first second : PackingEdge) :
    List ((List Nat × List Nat) × (List Nat × List Nat)) :=
  (sideLabelPairSamples r a (first.1 == second.1)).flatMap (fun rowPair =>
    (sideLabelPairSamples r a (first.2 == second.2)).map
      (fun colPair => (rowPair, colPair)))

def edgePairAgreementCount (r a : Nat) (first second : PackingEdge) : Nat :=
  sumBy (edgePairLabelSamples r a first second) (fun sample =>
    if sample.1.1 == sample.1.2 && sample.2.1 == sample.2.2 then 1 else 0)

theorem edgePairLabelSamples_length (r a : Nat) (first second : PackingEdge) :
    (edgePairLabelSamples r a first second).length =
      r ^ (2 * a +
        (if first.1 == second.1 then 0 else a) +
        (if first.2 == second.2 then 0 else a)) := by
  unfold edgePairLabelSamples
  rw [flatMap_map_length, sideLabelPairSamples_length, sideLabelPairSamples_length]
  cases hrow : (first.1 == second.1) <;>
  cases hcol : (first.2 == second.2) <;>
    simp_all
  all_goals repeat rw [← Nat.pow_add]
  all_goals congr 1
  all_goals omega


theorem edgePairAgreementCount_eq (r a : Nat) (first second : PackingEdge) :
    edgePairAgreementCount r a first second = r ^ (2 * a) := by
  unfold edgePairAgreementCount edgePairLabelSamples
  rw [sumBy_flatMap]
  have hinner (rowPair : List Nat × List Nat) :
      sumBy ((sideLabelPairSamples r a (first.2 == second.2)).map
        (fun colPair => (rowPair, colPair)))
        (fun sample =>
          if sample.1.1 == sample.1.2 && sample.2.1 == sample.2.2 then 1 else 0) =
        (if rowPair.1 == rowPair.2 then 1 else 0) * r ^ a := by
    rw [sumBy_map]
    by_cases hrow : rowPair.1 == rowPair.2
    · have hcount := sideLabelPairAgreementCount_eq r a (first.2 == second.2)
      simpa [hrow, sideLabelPairAgreementCount] using hcount
    · simp [hrow, sumBy_zero]
  calc
    sumBy (sideLabelPairSamples r a (first.1 == second.1)) (fun rowPair =>
        sumBy ((sideLabelPairSamples r a (first.2 == second.2)).map
          (fun colPair => (rowPair, colPair)))
          (fun sample =>
            if sample.1.1 == sample.1.2 && sample.2.1 == sample.2.2 then 1 else 0)) =
      sumBy (sideLabelPairSamples r a (first.1 == second.1)) (fun rowPair =>
        (if rowPair.1 == rowPair.2 then 1 else 0) * r ^ a) := by
          apply sumBy_congr
          intro rowPair hrow
          exact hinner rowPair
    _ = sideLabelPairAgreementCount r a (first.1 == second.1) * r ^ a := by
          rw [sumBy_mul_right]
          rfl
    _ = r ^ a * r ^ a := by rw [sideLabelPairAgreementCount_eq]
    _ = r ^ (2 * a) := by rw [← Nat.pow_add]; congr 1 <;> omega

def edgePairUnknown (a : Nat) (first second : PackingEdge) : Nat :=
  (if first.1 == second.1 then 0 else a) +
    (if first.2 == second.2 then 0 else a)

theorem edgePairUnknown_le_two_a (a : Nat) (first second : PackingEdge) :
    edgePairUnknown a first second ≤ 2 * a := by
  unfold edgePairUnknown
  cases first.1 == second.1 <;> cases first.2 == second.2 <;> simp <;> omega

def edgePairScaledAgreement (r a : Nat) (first second : PackingEdge) : Nat :=
  r ^ (2 * a - edgePairUnknown a first second)

theorem edgePairScaledAgreement_count_identity (r a : Nat)
    (first second : PackingEdge) :
    edgePairAgreementCount r a first second * r ^ (2 * a) =
      (edgePairLabelSamples r a first second).length *
        edgePairScaledAgreement r a first second := by
  rw [edgePairAgreementCount_eq, edgePairLabelSamples_length]
  unfold edgePairScaledAgreement edgePairUnknown
  rw [← Nat.pow_add, ← Nat.pow_add]
  congr 1
  cases hrow : (first.1 == second.1) <;>
  cases hcol : (first.2 == second.2) <;>
    simp_all <;> omega

theorem edgePairScaledAgreement_le (r a : Nat) (hr : 0 < r)
    (first second : PackingEdge) :
    edgePairScaledAgreement r a first second ≤ r ^ (2 * a) := by
  unfold edgePairScaledAgreement
  apply Nat.pow_le_pow_right hr
  exact Nat.sub_le _ _

theorem edgePairScaledAgreement_ge_one (r a : Nat) (hr : 0 < r)
    (first second : PackingEdge) :
    1 ≤ edgePairScaledAgreement r a first second := by
  unfold edgePairScaledAgreement
  have hpow (n : Nat) : 1 ≤ r ^ n := by
    induction n with
    | zero => simp
    | succ n ih =>
        rw [Nat.pow_succ]
        have hpowpos : 0 < r ^ n := by omega
        have hpos : 0 < r ^ n * r := Nat.mul_pos hpowpos hr
        omega
  apply hpow

theorem edgePairScaledAgreement_eq_one_of_disjoint (r a : Nat)
    (first second : PackingEdge)
    (hdisjoint : pairSharesEndpoint first second = false) :
    edgePairScaledAgreement r a first second = 1 := by
  unfold edgePairScaledAgreement edgePairUnknown pairSharesEndpoint at *
  cases hrow : (first.1 == second.1) <;>
  cases hcol : (first.2 == second.2) <;>
    simp_all <;> omega

def pairCenteredContribution (r a : Nat) (first second : PackingEdge) : Nat :=
  edgePairScaledAgreement r a first second - 1

theorem pairCenteredContribution_le_if_overlap (r a : Nat) (hr : 0 < r)
    (first second : PackingEdge) :
    pairCenteredContribution r a first second ≤
      if pairSharesEndpoint first second then r ^ (2 * a) else 0 := by
  by_cases hshare : pairSharesEndpoint first second = true
  · simp [pairCenteredContribution, hshare]
    have hbound := edgePairScaledAgreement_le r a hr first second
    omega
  · have hdisjoint : pairSharesEndpoint first second = false := by
      cases h : pairSharesEndpoint first second <;> simp_all
    have hone := edgePairScaledAgreement_eq_one_of_disjoint r a first second hdisjoint
    simp [pairCenteredContribution, hshare, hone]

def allOrderedEdgePairs (edges : List PackingEdge) : List (PackingEdge × PackingEdge) :=
  edges.flatMap (fun first => edges.map (fun second => (first, second)))

def scaledCenteredPairSum (r a : Nat) (edges : List PackingEdge) : Nat :=
  sumBy (allOrderedEdgePairs edges) (fun pair =>
    pairCenteredContribution r a pair.1 pair.2)

def scaledPairSecondMoment (r a : Nat) (edges : List PackingEdge) : Nat :=
  sumBy (allOrderedEdgePairs edges) (fun pair =>
    edgePairScaledAgreement r a pair.1 pair.2)

theorem allOrderedEdgePairs_length (edges : List PackingEdge) :
    (allOrderedEdgePairs edges).length = edges.length * edges.length := by
  unfold allOrderedEdgePairs
  exact flatMap_map_length edges edges

theorem scaledPairSecondMoment_eq_centered_add_mul (r a : Nat)
    (hr : 0 < r) (edges : List PackingEdge) :
    scaledPairSecondMoment r a edges =
      scaledCenteredPairSum r a edges + edges.length * edges.length := by
  unfold scaledPairSecondMoment scaledCenteredPairSum pairCenteredContribution
  calc
    sumBy (allOrderedEdgePairs edges)
        (fun pair => edgePairScaledAgreement r a pair.1 pair.2) =
      sumBy (allOrderedEdgePairs edges)
        (fun pair =>
          (edgePairScaledAgreement r a pair.1 pair.2 - 1) + 1) := by
            apply sumBy_congr
            intro pair hpair
            have hge := edgePairScaledAgreement_ge_one r a hr pair.1 pair.2
            omega
    _ = sumBy (allOrderedEdgePairs edges)
          (fun pair => edgePairScaledAgreement r a pair.1 pair.2 - 1) +
        sumBy (allOrderedEdgePairs edges) (fun _ => 1) := by
          rw [sumBy_add]
    _ = sumBy (allOrderedEdgePairs edges)
          (fun pair => edgePairScaledAgreement r a pair.1 pair.2 - 1) +
        edges.length * edges.length := by
          rw [sumBy_constant, allOrderedEdgePairs_length]
          simp
    _ = scaledCenteredPairSum r a edges + edges.length * edges.length := by
          rfl

theorem scaled_centered_pair_sum_le (r a : Nat) (hr : 0 < r)
    (edges : List PackingEdge) (delta : Nat)
    (hrow : ∀ vertex, rowDegreeOnList edges vertex ≤ delta)
    (hcol : ∀ vertex, columnDegreeOnList edges vertex ≤ delta) :
    scaledCenteredPairSum r a edges ≤
      2 * edges.length * delta * r ^ (2 * a) := by
  unfold scaledCenteredPairSum allOrderedEdgePairs
  rw [sumBy_flatMap]
  calc
    sumBy edges (fun first =>
        sumBy (edges.map (fun second => (first, second)))
          (fun pair => pairCenteredContribution r a pair.1 pair.2)) ≤
      sumBy edges (fun first =>
        sumBy (edges.map (fun second => (first, second)))
          (fun pair => if pairSharesEndpoint pair.1 pair.2 then r ^ (2 * a) else 0)) := by
            have hinner (first : PackingEdge) :
                sumBy (edges.map (fun second => (first, second)))
                  (fun pair => pairCenteredContribution r a pair.1 pair.2) ≤
                sumBy (edges.map (fun second => (first, second)))
                  (fun pair => if pairSharesEndpoint pair.1 pair.2 then r ^ (2 * a) else 0) := by
              rw [sumBy_map, sumBy_map]
              apply sumBy_le_of_pointwise
              intro second hsecond
              exact pairCenteredContribution_le_if_overlap r a hr first second
            apply sumBy_le_of_pointwise
            intro first hfirst
            exact hinner first
    _ = orderedOverlapCount edges * r ^ (2 * a) := by
          have hinner (first : PackingEdge) :
              sumBy (edges.map (fun second => (first, second)))
                (fun pair => if pairSharesEndpoint pair.1 pair.2 then r ^ (2 * a) else 0) =
              overlapCountWith edges first * r ^ (2 * a) := by
            rw [sumBy_map]
            calc
              sumBy edges (fun second =>
                  if pairSharesEndpoint first second then r ^ (2 * a) else 0) =
                sumBy edges (fun second =>
                  (if pairSharesEndpoint first second then 1 else 0) * r ^ (2 * a)) := by
                    apply sumBy_congr
                    intro second hsecond
                    by_cases hshare : pairSharesEndpoint first second <;> simp [hshare]
              _ = overlapCountWith edges first * r ^ (2 * a) := by
                    rw [sumBy_mul_right]
                    rfl
          calc
            sumBy edges (fun first =>
                sumBy (edges.map (fun second => (first, second)))
                  (fun pair => if pairSharesEndpoint pair.1 pair.2 then r ^ (2 * a) else 0)) =
              sumBy edges (fun first => overlapCountWith edges first * r ^ (2 * a)) := by
                apply sumBy_congr
                intro first hfirst
                exact hinner first
            _ = orderedOverlapCount edges * r ^ (2 * a) := by
                rw [sumBy_mul_right]
                rfl
    _ ≤ 2 * edges.length * delta * r ^ (2 * a) := by
          exact Nat.mul_le_mul_right (r ^ (2 * a))
            (ordered_overlap_count_le_two_m_delta edges delta hrow hcol)

theorem scaled_pair_second_moment_sub_square_le (r a : Nat)
    (hr : 0 < r) (edges : List PackingEdge) (delta : Nat)
    (hrow : ∀ vertex, rowDegreeOnList edges vertex ≤ delta)
    (hcol : ∀ vertex, columnDegreeOnList edges vertex ≤ delta) :
    scaledPairSecondMoment r a edges - edges.length * edges.length ≤
      2 * edges.length * delta * r ^ (2 * a) := by
  rw [scaledPairSecondMoment_eq_centered_add_mul r a hr edges]
  have hbound := scaled_centered_pair_sum_le r a hr edges delta hrow hcol
  omega

#print axioms edgePairScaledAgreement_ge_one
#print axioms edgePairScaledAgreement_count_identity
#print axioms edgePairLabelSamples_length
#print axioms edgePairAgreementCount_eq
#print axioms edgePairScaledAgreement_eq_one_of_disjoint
#print axioms allOrderedEdgePairs_length
#print axioms scaledPairSecondMoment_eq_centered_add_mul
#print axioms scaled_centered_pair_sum_le
#print axioms scaled_pair_second_moment_sub_square_le
