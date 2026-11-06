import D3CandidateOrder

/-! Extensional, finite-support dictionary semantics. This does not model the
CPython allocator, interpreter or hash table and does not certify bytecode. -/
namespace D3KeyedRun
abbrev Key := PackingSide × Nat × Nat
abbrev Dictionary := Key → Option Nat

def view (s : Dictionary) : PackingPartial := fun v d => s (v.1, v.2, d)
def Related (s : Dictionary) (p : PackingPartial) : Prop := ∀ v d, s (v.1,v.2,d) = p v d

def Bounded (s : Dictionary) (a : Nat) : Prop := ∀ side ident d, a ≤ d → s (side,ident,d) = none

def writeWord (s : Dictionary) (v : PackingVertex) (w : List Nat) : Dictionary :=
  fun key => if (key.1, key.2.1) = v ∧ key.2.2 < w.length then w[key.2.2]? else s key

theorem view_related (s : Dictionary) : Related s (view s) := by intro v d; rfl

theorem write_view (s : Dictionary) (v : PackingVertex) (w : List Nat)
    (a : Nat) (hs : Bounded s a) (hw : w.length = a) :
    view (writeWord s v w) = d3AssignWord (view s) v w := by
  funext u d
  by_cases huv : u = v
  · by_cases hd : d < a
    · simp [view, writeWord, d3AssignWord, huv, hw, hd]
    · have hn : w[d]? = none := List.getElem?_eq_none (by omega)
      have he := hs u.1 u.2 d (by omega)
      simp [view, writeWord, d3AssignWord, huv, hw, hd] at *
      exact he
  · simp [view, writeWord, d3AssignWord, huv]

theorem write_bounded (s : Dictionary) (v : PackingVertex) (w : List Nat)
    (a : Nat) (hs : Bounded s a) (hw : w.length = a) : Bounded (writeWord s v w) a := by
  intro side ident d hd
  simp [writeWord, hw, Nat.not_lt.mpr hd, hs side ident d hd]

def run (r a : Nat) (hr : 0 < r) (edges : List PackingEdge) :
    List PackingVertex → Dictionary → Dictionary
  | [], s => s
  | v :: vs, s =>
    let w := D3CandidateOrder.choose r a hr edges (view s) v
    run r a hr edges vs (writeWord s v w)

def trace (r a : Nat) (hr : 0 < r) (edges : List PackingEdge) :
    List PackingVertex → Dictionary → List (PackingVertex × List Nat × Nat)
  | [], _ => []
  | v :: vs, s =>
    let w := D3CandidateOrder.choose r a hr edges (view s) v
    (v, w, D3PythonScore.pyCandidateScore (view s) v w r a edges) ::
      trace r a hr edges vs (writeWord s v w)

theorem run_correspondence (r a : Nat) (hr : 0 < r) (edges : List PackingEdge)
    (vertices : List PackingVertex) (s : Dictionary) (hs : Bounded s a) :
    view (run r a hr edges vertices s) = d3CanonicalRun r a hr edges vertices (view s) := by
  induction vertices generalizing s with
  | nil => rfl
  | cons v vs ih =>
    simp only [run, d3CanonicalRun, D3CandidateOrder.choose_eq]
    have hw := labelWords_member_length r a _ (d3_canonical_word_mem r a hr edges (view s) v)
    rw [ih _ (write_bounded s v _ a hs hw), write_view s v _ a hs hw]

theorem trace_correspondence (r a : Nat) (hr : 0 < r) (edges : List PackingEdge)
    (vertices : List PackingVertex) (s : Dictionary) (hs : Bounded s a) :
    trace r a hr edges vertices s = d3PythonCanonicalTrace r a hr edges vertices (view s) := by
  induction vertices generalizing s with
  | nil => rfl
  | cons v vs ih =>
    simp only [trace, d3PythonCanonicalTrace, D3CandidateOrder.choose_eq]
    have hm := d3_canonical_word_mem r a hr edges (view s) v
    have hw := labelWords_member_length r a _ hm
    rw [D3PythonScore.pyCandidateScore_eq _ _ _ _ _ _ hm,
      ih _ (write_bounded s v _ a hs hw), write_view s v _ a hs hw]

def empty : Dictionary := fun _ => none

theorem empty_bounded (a : Nat) : Bounded empty a := by intro side ident d hd; rfl

theorem sorted_run_contract (r a : Nat) (hr : 0 < r) (edges : List PackingEdge) :
    let vertices := d3PythonOrderedVertices edges
    Related (run r a hr edges vertices empty)
      (d3CanonicalRun r a hr edges vertices emptyPackingAssignments) ∧
    trace r a hr edges vertices empty =
      d3PythonCanonicalTrace r a hr edges vertices emptyPackingAssignments ∧
    r^(2*a) * d3EdgeClassSquareSum edges
      (d3PartialColor (view (run r a hr edges vertices empty)) a) =
      r^(2*a) * d3EdgeClassSquareSum edges
        (d3PartialColor (d3CanonicalRun r a hr edges vertices emptyPackingAssignments) a) := by
  dsimp only
  have h := run_correspondence r a hr edges (d3PythonOrderedVertices edges) empty (empty_bounded a)
  have ht := trace_correspondence r a hr edges (d3PythonOrderedVertices edges) empty (empty_bounded a)
  change view (run r a hr edges (d3PythonOrderedVertices edges) empty) =
    d3CanonicalRun r a hr edges (d3PythonOrderedVertices edges) emptyPackingAssignments at h
  refine ⟨?_, ht, ?_⟩
  · intro v d
    exact congrFun (congrFun h v) d
  · rw [h]

#print axioms write_view
#print axioms write_bounded
#print axioms run_correspondence
#print axioms trace_correspondence
#print axioms sorted_run_contract
end D3KeyedRun
