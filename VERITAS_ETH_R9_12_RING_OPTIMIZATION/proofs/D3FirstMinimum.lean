import D3PythonOrder

/-! First-minimum property of the existing Lean whole-word selector.
This is a theorem about the Lean candidate list and score, not a proof that
CPython or the separate coordinate-wise builder execute the same program. -/

theorem d3_canonical_word_first_minimum (r a : Nat) (hr : 0 < r)
    (edges : List PackingEdge) (s : PackingPartial) (v : PackingVertex) :
    let words := labelWords r a
    let score := concreteD3ScoreCandidate s v r a edges
    ∃ i, ∃ hi : i < words.length,
      d3CanonicalWord r a hr edges s v = words[i] ∧
      (∀ j, ∀ hj : j < words.length, score words[i] ≤ score words[j]) ∧
      (∀ j, ∀ hj : j < i, score words[i] < score (words[j]'(by omega))) := by
  let words := labelWords r a
  let score := concreteD3ScoreCandidate s v r a edges
  have hn : words ≠ [] := d3_label_words_nonempty r a hr
  let i := words.minIdxOn score hn
  have hs := (List.minIdxOn_eq_iff (f := score) hn).1 (show words.minIdxOn score hn = i by rfl)
  obtain ⟨hi, hmin, hfirst⟩ := hs
  refine ⟨i, hi, ?_, hmin, hfirst⟩
  simpa [d3CanonicalWord, words, score, i] using (List.getElem_minIdxOn (f := score) hn).symm

#print axioms d3_canonical_word_first_minimum
