import D3InitialScore
import D3SelectionBridge

/-! The Lean selector takes the first minimum in the finite word list, and
its first score satisfies the initial bound. Recursive monotonicity is
conditional on explicit parent-score, child-score, and readiness hypotheses.
This module does not establish those hypotheses for the source potential or
show that Python implements the Lean program. -/

def d3PartialValid (r : Nat) (s : PackingPartial) : Prop :=
  ∀ v d x, s v d = some x → x < r

def d3AssignWord (s : PackingPartial) (v : PackingVertex)
    (word : List Nat) : PackingPartial :=
  fun u d => if u = v then word[d]? else s u d

theorem d3_assign_word_valid (r a : Nat) (s : PackingPartial)
    (hs : d3PartialValid r s) (v : PackingVertex) (word : List Nat)
    (hw : word ∈ labelWords r a) : d3PartialValid r (d3AssignWord s v word) := by
  intro u d x hx
  by_cases h : u = v
  · simp [d3AssignWord, h] at hx
    exact labelWords_member_symbols_lt r a word hw x (List.mem_of_getElem? hx)
  · simp [d3AssignWord, h] at hx
    exact hs u d x hx

theorem d3_label_words_nonempty (r a : Nat) (hr : 0 < r) :
    labelWords r a ≠ [] := by
  intro h
  have hl := labelWords_length r a
  rw [h] at hl
  simp only [List.length_nil] at hl
  have hp : 0 < r ^ a := Nat.pow_pos hr
  omega

def d3CanonicalWord (r a : Nat) (hr : 0 < r)
    (edges : List PackingEdge) (s : PackingPartial) (v : PackingVertex) : List Nat :=
  (labelWords r a).minOn (concreteD3ScoreCandidate s v r a edges)
    (d3_label_words_nonempty r a hr)

theorem d3_canonical_word_mem (r a : Nat) (hr : 0 < r)
    (edges : List PackingEdge) (s : PackingPartial) (v : PackingVertex) :
    d3CanonicalWord r a hr edges s v ∈ labelWords r a := by
  exact List.minOn_mem

theorem d3_canonical_word_nonincreasing (r a : Nat) (hr : 0 < r)
    (edges : List PackingEdge) (s : PackingPartial) (hs : d3PartialValid r s)
    (v : PackingVertex) :
    concreteD3ScoreCandidate s v r a edges (d3CanonicalWord r a hr edges s v) ≤
      concreteD3ScoreParent s v r a edges := by
  obtain ⟨word, hw, hle⟩ :=
    concrete_d3_exists_nonincreasing_candidate r a s hs v edges hr
  have hmin := List.apply_minOn_le_of_mem
    (f := concreteD3ScoreCandidate s v r a edges) hw
  exact Nat.le_trans hmin hle

def d3CanonicalRun (r a : Nat) (hr : 0 < r) (edges : List PackingEdge) :
    List PackingVertex → PackingPartial → PackingPartial
  | [], s => s
  | v :: vs, s => d3CanonicalRun r a hr edges vs
      (d3AssignWord s v (d3CanonicalWord r a hr edges s v))

inductive D3ChoiceTrace (r a : Nat)
    (advance : PackingPartial → PackingVertex → List Nat → PackingPartial)
    (potential : PackingPartial → Nat) :
    List PackingVertex → PackingPartial → PackingPartial → Prop where
  | done (s) : D3ChoiceTrace r a advance potential [] s s
  | step (v vs s word final)
      (word_valid : word ∈ labelWords r a)
      (nonincrease : potential (advance s v word) ≤ potential s)
      (rest : D3ChoiceTrace r a advance potential vs (advance s v word) final) :
      D3ChoiceTrace r a advance potential (v :: vs) s final

theorem d3_conditional_trace_exists (r a : Nat) (hr : 0 < r)
    (edges : List PackingEdge)
    (potential : PackingPartial → Nat)
    (ready : List PackingVertex → PackingPartial → Prop)
    (hparent : ∀ v vs s, ready (v :: vs) s → d3PartialValid r s →
      potential s = concreteD3ScoreParent s v r a edges)
    (hchild : ∀ v vs s word, ready (v :: vs) s → d3PartialValid r s →
      word ∈ labelWords r a →
      potential (d3AssignWord s v word) = concreteD3ScoreCandidate s v r a edges word)
    (hadvance : ∀ v vs s word, ready (v :: vs) s → d3PartialValid r s →
      word ∈ labelWords r a →
      ready vs (d3AssignWord s v word)) :
    ∀ vertices s, ready vertices s → d3PartialValid r s →
      ∃ final, D3ChoiceTrace r a d3AssignWord potential vertices s final ∧
        potential final ≤ potential s := by
  intro vertices
  induction vertices with
  | nil =>
      intro s hready hvalid
      exact ⟨s, .done s, Nat.le_refl _⟩
  | cons v vs ih =>
      intro s hready hvalid
      obtain ⟨word, hw, hscore⟩ :=
        concrete_d3_exists_nonincreasing_candidate r a s hvalid v edges hr
      have hstep : potential (d3AssignWord s v word) ≤ potential s := by
        rw [hchild v vs s word hready hvalid hw, hparent v vs s hready hvalid]
        exact hscore
      have hready' := hadvance v vs s word hready hvalid hw
      have hvalid' := d3_assign_word_valid r a s hvalid v word hw
      obtain ⟨final, htrace, hle⟩ := ih (d3AssignWord s v word) hready' hvalid'
      exact ⟨final, .step v vs s word final hw hstep htrace, Nat.le_trans hle hstep⟩

theorem d3_first_candidate_with_initial_bound (r a : Nat) (hr : 0 < r)
    (v : PackingVertex) (edges : List PackingEdge) (delta : Nat)
    (hrow : ∀ vertex, rowDegreeOnList edges vertex ≤ delta)
    (hcol : ∀ vertex, columnDegreeOnList edges vertex ≤ delta) :
    ∃ word, word ∈ labelWords r a ∧
      concreteD3ScoreCandidate emptyPackingAssignments v r a edges word ≤
        edges.length * edges.length + 2 * edges.length * delta * r ^ (2 * a) := by
  have hv : d3PartialValid r emptyPackingAssignments := by
    intro v d x h
    simp [emptyPackingAssignments] at h
  obtain ⟨word, hw, hscore⟩ :=
    concrete_d3_exists_nonincreasing_candidate r a emptyPackingAssignments hv v edges hr
  exact ⟨word, hw, Nat.le_trans hscore (empty_concrete_score_le r a hr v edges delta hrow hcol)⟩

theorem d3_first_canonical_candidate_with_initial_bound (r a : Nat) (hr : 0 < r)
    (v : PackingVertex) (edges : List PackingEdge) (delta : Nat)
    (hrow : ∀ vertex, rowDegreeOnList edges vertex ≤ delta)
    (hcol : ∀ vertex, columnDegreeOnList edges vertex ≤ delta) :
    concreteD3ScoreCandidate emptyPackingAssignments v r a edges
      (d3CanonicalWord r a hr edges emptyPackingAssignments v) ≤
      edges.length * edges.length + 2 * edges.length * delta * r ^ (2 * a) := by
  have hv : d3PartialValid r emptyPackingAssignments := by
    intro v d x h
    simp [emptyPackingAssignments] at h
  exact Nat.le_trans
    (d3_canonical_word_nonincreasing r a hr edges emptyPackingAssignments hv v)
    (empty_concrete_score_le r a hr v edges delta hrow hcol)

theorem d3_conditional_canonical_run (r a : Nat) (hr : 0 < r)
    (edges : List PackingEdge) (potential : PackingPartial → Nat)
    (ready : List PackingVertex → PackingPartial → Prop)
    (hparent : ∀ v vs s, ready (v :: vs) s → d3PartialValid r s →
      potential s = concreteD3ScoreParent s v r a edges)
    (hchild : ∀ v vs s word, ready (v :: vs) s → d3PartialValid r s →
      word ∈ labelWords r a →
      potential (d3AssignWord s v word) = concreteD3ScoreCandidate s v r a edges word)
    (hadvance : ∀ v vs s word, ready (v :: vs) s → d3PartialValid r s →
      word ∈ labelWords r a → ready vs (d3AssignWord s v word)) :
    ∀ vertices s, ready vertices s → d3PartialValid r s →
      D3ChoiceTrace r a d3AssignWord potential vertices s
        (d3CanonicalRun r a hr edges vertices s) ∧
      potential (d3CanonicalRun r a hr edges vertices s) ≤ potential s := by
  intro vertices
  induction vertices with
  | nil =>
      intro s hready hvalid
      exact ⟨.done s, Nat.le_refl _⟩
  | cons v vs ih =>
      intro s hready hvalid
      let word := d3CanonicalWord r a hr edges s v
      have hw : word ∈ labelWords r a := d3_canonical_word_mem r a hr edges s v
      have hstep : potential (d3AssignWord s v word) ≤ potential s := by
        rw [hchild v vs s word hready hvalid hw, hparent v vs s hready hvalid]
        exact d3_canonical_word_nonincreasing r a hr edges s hvalid v
      have hready' := hadvance v vs s word hready hvalid hw
      have hvalid' := d3_assign_word_valid r a s hvalid v word hw
      obtain ⟨htrace, hle⟩ := ih (d3AssignWord s v word) hready' hvalid'
      exact ⟨.step v vs s word _ hw hstep htrace, Nat.le_trans hle hstep⟩

#print axioms d3_conditional_trace_exists
#print axioms d3_first_candidate_with_initial_bound
#print axioms d3_first_canonical_candidate_with_initial_bound
#print axioms d3_assign_word_valid
#print axioms d3_canonical_word_mem
#print axioms d3_canonical_word_nonincreasing
#print axioms d3_conditional_canonical_run
