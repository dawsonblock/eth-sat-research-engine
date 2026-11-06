import ConcreteD3ConditionalExpectation
import ConditionalExpectationSelection

/-!
One-step deterministic-selection consequence for the concrete bipartite
edge-pair score. The score average is proved in
`ConcreteD3ConditionalExpectation`; the finite minimum lemma is proved in
`ConditionalExpectationSelection`. This theorem composes those two results to
show that, for any eligible current partial state and vertex, some label word
does not increase the modeled conditional score.

It does not yet define the whole vertex-assignment recursion, the Python
refinement, or the packet/port construction.
-/

def concreteD3CandidateScores (assignments : PackingPartial)
    (current : PackingVertex) (r a : Nat) (edges : List PackingEdge) : List Nat :=
  (labelWords r a).map
    (concreteD3ScoreCandidate assignments current r a edges)

theorem concreteD3CandidateScores_length (assignments : PackingPartial)
    (current : PackingVertex) (r a : Nat) (edges : List PackingEdge) :
    (concreteD3CandidateScores assignments current r a edges).length = r ^ a := by
  unfold concreteD3CandidateScores
  simp [labelWords_length]

theorem concreteD3CandidateScores_sum (r a : Nat)
    (assignments : PackingPartial)
    (hassignments : ∀ v d x, assignments v d = some x → x < r)
    (current : PackingVertex) (edges : List PackingEdge) (hr : 0 < r) :
    (concreteD3CandidateScores assignments current r a edges).sum =
      r ^ a * concreteD3ScoreParent assignments current r a edges := by
  unfold concreteD3CandidateScores
  rw [sum_map_eq_sumBy]
  exact concrete_d3_score_average r a assignments hassignments current edges hr

theorem concrete_d3_exists_nonincreasing_candidate (r a : Nat)
    (assignments : PackingPartial)
    (hassignments : ∀ v d x, assignments v d = some x → x < r)
    (current : PackingVertex) (edges : List PackingEdge) (hr : 0 < r) :
    ∃ word, word ∈ labelWords r a ∧
      concreteD3ScoreCandidate assignments current r a edges word ≤
        concreteD3ScoreParent assignments current r a edges := by
  let scores := concreteD3CandidateScores assignments current r a edges
  have hlen : scores.length = r ^ a := by
    dsimp [scores]
    exact concreteD3CandidateScores_length assignments current r a edges
  have hpow : 0 < r ^ a := Nat.pow_pos hr
  have hne : scores ≠ [] := by
    intro hnil
    rw [hnil] at hlen
    simp at hlen
    omega
  have hsum := concreteD3CandidateScores_sum r a assignments hassignments
    current edges hr
  have haverage : scores.sum = scores.length *
      concreteD3ScoreParent assignments current r a edges := by
    rw [hsum, hlen]
  obtain ⟨score, hscore, hle⟩ :=
    exists_minimizing_candidate_no_worse_than_parent scores
      (concreteD3ScoreParent assignments current r a edges) hne haverage
  rcases List.mem_map.mp (show score ∈ scores from hscore) with
    ⟨word, hword, hvalue⟩
  exact ⟨word, hword, by rw [hvalue]; exact hle⟩

#print axioms concreteD3CandidateScores_sum
#print axioms concrete_d3_exists_nonincreasing_candidate
