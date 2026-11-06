import D3CanonicalSequence

/-! Concrete freshness, validity, and completion invariants for the Lean
labeling run. The final potential bound still assumes the two score-to-
potential equalities; it does not establish the Python refinement. -/

def d3Fresh (vertices : List PackingVertex) (s : PackingPartial) : Prop :=
  vertices.Nodup ∧ ∀ v, v ∈ vertices → ∀ d, s v d = none

theorem d3_fresh_empty (vertices : List PackingVertex) (h : vertices.Nodup) :
    d3Fresh vertices emptyPackingAssignments := by
  exact ⟨h, by intros; rfl⟩

theorem d3_fresh_assign (v : PackingVertex) (vs : List PackingVertex)
    (s : PackingPartial) (word : List Nat) (h : d3Fresh (v :: vs) s) :
    d3Fresh vs (d3AssignWord s v word) := by
  obtain ⟨hne, hnodup⟩ := List.nodup_cons.mp h.1
  refine ⟨hnodup, ?_⟩
  intro u hu d
  have huv : u ≠ v := by intro heq; subst u; exact hne hu
  simp [d3AssignWord, huv, h.2 u (by simp [hu]) d]

theorem d3_run_preserves_unlisted (r a : Nat) (hr : 0 < r)
    (edges : List PackingEdge) (vertices : List PackingVertex) :
    ∀ s u d, u ∉ vertices → d3CanonicalRun r a hr edges vertices s u d = s u d := by
  induction vertices with
  | nil => intros; rfl
  | cons v vs ih =>
      intro s u d hu
      have hne : u ≠ v := by intro heq; subst u; exact hu (by simp)
      have htail : u ∉ vs := by intro hm; exact hu (by simp [hm])
      simp only [d3CanonicalRun]
      rw [ih _ u d htail]
      simp [d3AssignWord, hne]

theorem d3_run_preserves_valid (r a : Nat) (hr : 0 < r)
    (edges : List PackingEdge) (vertices : List PackingVertex) :
    ∀ s, d3PartialValid r s →
      d3PartialValid r (d3CanonicalRun r a hr edges vertices s) := by
  induction vertices with
  | nil => intro s hs; exact hs
  | cons v vs ih =>
      intro s hs
      simp only [d3CanonicalRun]
      apply ih
      exact d3_assign_word_valid r a s hs v _ (d3_canonical_word_mem r a hr edges s v)

theorem d3_run_labels_all (r a : Nat) (hr : 0 < r)
    (edges : List PackingEdge) (vertices : List PackingVertex) (hn : vertices.Nodup) :
    ∀ s u, u ∈ vertices → ∀ d, d < a →
      ∃ x, d3CanonicalRun r a hr edges vertices s u d = some x ∧ x < r := by
  induction vertices with
  | nil => intro s u hu; simp at hu
  | cons v vs ih =>
      obtain ⟨hv, ht⟩ := List.nodup_cons.mp hn
      intro s u hu d hd
      simp only [List.mem_cons] at hu
      rcases hu with heq | hu
      · subst u
        let word := d3CanonicalWord r a hr edges s v
        have hw := d3_canonical_word_mem r a hr edges s v
        have hlen := labelWords_member_length r a word hw
        have hlt : d < word.length := by omega
        let next := d3AssignWord s v word
        have hp := d3_run_preserves_unlisted r a hr edges vs next v d hv
        refine ⟨word[d], ?_, ?_⟩
        · change d3CanonicalRun r a hr edges vs next v d = some word[d]
          rw [hp]
          simp [next, d3AssignWord, List.getElem?_eq_getElem hlt]
        · exact labelWords_member_symbols_lt r a word hw word[d] (List.getElem_mem hlt)
      · simp only [d3CanonicalRun]
        exact ih ht _ u hu d hd

theorem d3_fresh_canonical_run_monotone (r a : Nat) (hr : 0 < r)
    (edges : List PackingEdge) (potential : PackingPartial → Nat)
    (hparent : ∀ v vs s, d3Fresh (v :: vs) s → d3PartialValid r s →
      potential s = concreteD3ScoreParent s v r a edges)
    (hchild : ∀ v vs s word, d3Fresh (v :: vs) s → d3PartialValid r s →
      word ∈ labelWords r a →
      potential (d3AssignWord s v word) = concreteD3ScoreCandidate s v r a edges word) :
    ∀ vertices s, d3Fresh vertices s → d3PartialValid r s →
      D3ChoiceTrace r a d3AssignWord potential vertices s
        (d3CanonicalRun r a hr edges vertices s) ∧
      potential (d3CanonicalRun r a hr edges vertices s) ≤ potential s := by
  apply d3_conditional_canonical_run r a hr edges potential d3Fresh hparent hchild
  intro v vs s word hready hvalid hw
  exact d3_fresh_assign v vs s word hready

theorem d3_fresh_run_initial_bound (r a : Nat) (hr : 0 < r)
    (edges : List PackingEdge) (potential : PackingPartial → Nat)
    (hparent : ∀ v vs s, d3Fresh (v :: vs) s → d3PartialValid r s →
      potential s = concreteD3ScoreParent s v r a edges)
    (hchild : ∀ v vs s word, d3Fresh (v :: vs) s → d3PartialValid r s →
      word ∈ labelWords r a →
      potential (d3AssignWord s v word) = concreteD3ScoreCandidate s v r a edges word)
    (v : PackingVertex) (vs : List PackingVertex) (hn : (v :: vs).Nodup)
    (delta : Nat) (hrow : ∀ vertex, rowDegreeOnList edges vertex ≤ delta)
    (hcol : ∀ vertex, columnDegreeOnList edges vertex ≤ delta) :
    potential (d3CanonicalRun r a hr edges (v :: vs) emptyPackingAssignments) ≤
      edges.length * edges.length + 2 * edges.length * delta * r ^ (2 * a) := by
  have hf := d3_fresh_empty (v :: vs) hn
  have hv : d3PartialValid r emptyPackingAssignments := by
    intro u d x hx
    simp [emptyPackingAssignments] at hx
  have hrun := (d3_fresh_canonical_run_monotone r a hr edges potential hparent hchild
    (v :: vs) emptyPackingAssignments hf hv).2
  rw [hparent v vs emptyPackingAssignments hf hv] at hrun
  exact Nat.le_trans hrun (empty_concrete_score_le r a hr v edges delta hrow hcol)

#print axioms d3_fresh_empty
#print axioms d3_fresh_assign
#print axioms d3_run_preserves_unlisted
#print axioms d3_run_preserves_valid
#print axioms d3_run_labels_all
#print axioms d3_fresh_canonical_run_monotone
#print axioms d3_fresh_run_initial_bound
