import D3PythonScoreModel
import D3FirstMinimum

namespace D3CandidateOrder

/-- Iterated prefix extension: the finite semantics of product(range r, repeat a).
This does not claim correctness of the CPython itertools binary. -/
def productWords (r : Nat) : Nat → List (List Nat)
  | 0 => [[]]
  | a + 1 => (productWords r a).flatMap (fun w => (List.range r).map (fun x => w ++ [x]))

theorem extend_labelWords (r a : Nat) :
    (labelWords r a).flatMap (fun w => (List.range r).map (fun x => w ++ [x])) =
      labelWords r (a+1) := by
  induction a with
  | zero => simp only [labelWords, List.flatMap_singleton, List.nil_append, List.map_singleton]; exact List.map_eq_flatMap
  | succ a ih =>
    change ((List.range r).flatMap (fun x => (labelWords r a).map (fun w => x :: w))).flatMap
      (fun w => (List.range r).map (fun x => w ++ [x])) =
      (List.range r).flatMap (fun x => (labelWords r (a+1)).map (fun w => x :: w))
    rw [List.flatMap_assoc]
    congr 1
    funext x
    rw [List.flatMap_map, ← ih, List.map_flatMap]
    simp [List.map_map, Function.comp_def]

theorem productWords_eq (r a : Nat) : productWords r a = labelWords r a := by
  induction a with
  | zero => rfl
  | succ a ih => rw [productWords, ih, extend_labelWords]

/-- A deterministic first-minimum selector on the independent product list. -/
def choose (r a : Nat) (hr : 0 < r) (edges : List PackingEdge)
    (s : PackingPartial) (v : PackingVertex) : List Nat :=
  (productWords r a).minOn (fun w => D3PythonScore.pyCandidateScore s v w r a edges)
    (by rw [productWords_eq]; exact d3_label_words_nonempty r a hr)

theorem minOn_congr_on {α : Type} (xs : List α) (hx : xs ≠ []) (f g : α → Nat)
    (h : ∀ x, x ∈ xs → f x = g x) : xs.minOn f hx = xs.minOn g hx := by
  induction xs with
  | nil => contradiction
  | cons x xs ih =>
    cases xs with
    | nil => simp
    | cons y ys =>
      rw [List.minOn_cons (x := x) (xs := y :: ys) (f := f),
          List.minOn_cons (x := x) (xs := y :: ys) (f := g)]
      simp only [List.cons_ne_nil, reduceDIte]
      have ht : ∀ z, z ∈ y :: ys → f z = g z := by
        intro z hz; exact h z (by simp [hz])
      have he := ih (by simp) ht
      rw [he]
      simp only [minOn, h x (by simp), h ((y :: ys).minOn g (by simp))
        (List.mem_cons_of_mem x List.minOn_mem)]

theorem choose_eq (r a : Nat) (hr : 0 < r) (edges : List PackingEdge)
    (s : PackingPartial) (v : PackingVertex) :
    choose r a hr edges s v = d3CanonicalWord r a hr edges s v := by
  simp only [choose, d3CanonicalWord, productWords_eq]
  apply minOn_congr_on
  intro w hw
  exact D3PythonScore.pyCandidateScore_eq s v w r a edges hw

#print axioms extend_labelWords
#print axioms productWords_eq
#print axioms minOn_congr_on
#print axioms choose_eq

theorem labelWords_lex_sorted (r a : Nat) :
    (labelWords r a).Pairwise (List.Lex (· < ·)) := by
  induction a with
  | zero => simp [labelWords]
  | succ a ih =>
    rw [labelWords, List.pairwise_flatMap]
    constructor
    · intro x hx
      exact List.Pairwise.map (fun w => x :: w) (fun _ _ h => .cons h) ih
    · apply List.Pairwise.imp _ List.pairwise_lt_range
      intro x y hxy w hw z hz
      obtain ⟨u, _, rfl⟩ := List.mem_map.mp hw
      obtain ⟨v, _, rfl⟩ := List.mem_map.mp hz
      exact .rel hxy

/-- Minimum of the exact (score, lexicographic word) key, including ties. -/
theorem choose_pair_minimum (r a : Nat) (hr : 0 < r)
    (edges : List PackingEdge) (s : PackingPartial) (v : PackingVertex) :
    let selected := choose r a hr edges s v
    selected ∈ productWords r a ∧
    ∀ w ∈ productWords r a,
      D3PythonScore.pyCandidateScore s v selected r a edges ≤
        D3PythonScore.pyCandidateScore s v w r a edges ∧
      (D3PythonScore.pyCandidateScore s v selected r a edges =
        D3PythonScore.pyCandidateScore s v w r a edges →
        selected = w ∨ List.Lex (· < ·) selected w) := by
  dsimp only
  rw [choose_eq, productWords_eq]
  have hsel := d3_canonical_word_mem r a hr edges s v
  refine ⟨hsel, ?_⟩
  intro w hw
  rw [D3PythonScore.pyCandidateScore_eq s v _ r a edges hsel,
    D3PythonScore.pyCandidateScore_eq s v w r a edges hw]
  obtain ⟨i, hi, heq, hmin, hfirst⟩ :=
    d3_canonical_word_first_minimum r a hr edges s v
  obtain ⟨j, hj, rfl⟩ := List.mem_iff_getElem.mp hw
  rw [heq]
  refine ⟨hmin j hj, ?_⟩
  intro hscore
  have hij : i ≤ j := by
    by_cases h : i ≤ j
    · exact h
    · have := hfirst j (by omega)
      omega
  rcases Nat.eq_or_lt_of_le hij with h | h
  · left; subst j; rfl
  · right
    exact (List.pairwise_iff_getElem.mp (labelWords_lex_sorted r a)) i j hi hj h

#print axioms labelWords_lex_sorted
#print axioms choose_pair_minimum
end D3CandidateOrder
