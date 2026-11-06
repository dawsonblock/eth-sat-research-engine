import D3PythonOrder

/-! An executable-faithful Lean transcription of the CPython candidate scorer.

`src/veritas/research/eth_packing_v26/streaming.py` implements
`_candidate_score` with an index-based double loop over `edges` and, inside
it, a nested scan over `range(a)` and the two vertex sides.  This file
transcribes that routine literally (index-based pair enumeration, the
`value` substitution of the candidate label, the early-exit mismatch scan,
and integer division by `r ^ unknown`) and proves it equal to the abstract
score `concreteD3ScoreCandidate` that the rest of the Lean development uses.

Scope: this is a refinement theorem between two *Lean* definitions.  It does
not, by itself, prove that CPython executes this transcription.  The
source-to-model boundary is audited in `docs/R91_REFINEMENT_AUDIT.md` and is
tested differentially by `scripts/validate_r91_python_model.py`, which
evaluates this Lean model and CPython on the same corpus.
-/

namespace D3PythonScore

open PackingSide

instance : Inhabited PairCoordinate := ⟨(.resolved, .resolved)⟩

/-! ## List plumbing for the index-based pair enumeration -/

theorem sumBy_singleton {α : Type} (x : α) (f : α → Nat) : sumBy [x] f = f x := rfl

theorem sumBy_cons {α : Type} (x : α) (xs : List α) (f : α → Nat) :
    sumBy (x :: xs) f = f x + sumBy xs f := rfl

theorem unorderedEdgePairs_cons (e : PackingEdge) (es : List PackingEdge) :
    unorderedEdgePairs (e :: es) = es.map (fun other => (e, other)) ++ unorderedEdgePairs es :=
  rfl

theorem sumBy_map_range_getElem {α : Type} [Inhabited α] (xs : List α) (f : α → Nat) :
    sumBy (List.range xs.length) (fun k => f xs[k]!) = sumBy xs f := by
  induction xs with
  | nil => rfl
  | cons x xs ih =>
      rw [List.length_cons, List.range_succ_eq_map]
      show f (x :: xs)[0]! + sumBy (List.map Nat.succ (List.range xs.length))
        (fun k => f (x :: xs)[k]!) = f x + sumBy xs f
      rw [List.getElem!_cons_zero, sumBy_map]
      have hshift : (fun k => f (x :: xs)[Nat.succ k]!) = (fun k => f xs[k]!) := by
        funext k
        rw [List.getElem!_cons_succ]
      rw [hshift, ih]

theorem sumBy_range_getElem_pair (es : List PackingEdge) (e : PackingEdge)
    (g : PackingEdge × PackingEdge → Nat) :
    sumBy (List.range es.length) (fun k => g (e, es[k]!)) =
      sumBy es (fun other => g (e, other)) := by
  simpa using sumBy_map_range_getElem es (fun other => g (e, other))

theorem map_range_getElem {α β : Type} [Inhabited α] (xs : List α) (f : α → β) :
    (List.range xs.length).map (fun k => f xs[k]!) = xs.map f := by
  induction xs with
  | nil => rfl
  | cons x xs ih =>
      rw [List.length_cons, List.range_succ_eq_map]
      simp only [List.map_cons, List.map_map, Function.comp_def]
      rw [List.getElem!_cons_zero]
      rw [show (fun k => f (x :: xs)[Nat.succ k]!) = (fun k => f xs[k]!) from by
        funext k
        rw [List.getElem!_cons_succ]]
      rw [ih]

/-- Python enumerates the pairs `(edges[j], edges[i])` for `j < i`. -/
def pythonEdgePairs (edges : List PackingEdge) : List (PackingEdge × PackingEdge) :=
  (List.range edges.length).flatMap (fun i =>
    (edges.take i).map (fun earlier => (earlier, edges[i]!)))

/-- The Python pair list is a permutation of the Lean unordered pair list, so
any additive functional has the same value on both.  This is proved at the
level of sums, which is all the score identity needs. -/
theorem sumBy_pythonEdgePairs_cons (e : PackingEdge) (es : List PackingEdge)
    (g : PackingEdge × PackingEdge → Nat) :
    sumBy (pythonEdgePairs (e :: es)) g =
      sumBy es (fun other => g (e, other)) + sumBy (pythonEdgePairs es) g := by
  unfold pythonEdgePairs
  rw [List.length_cons, List.range_succ_eq_map]
  simp only [List.flatMap_cons, List.take_zero, List.nil_append, List.map_nil]
  rw [sumBy_flatMap, sumBy_map]
  simp only [List.take_succ_cons, List.getElem!_cons_succ, sumBy_map, sumBy_cons]
  rw [sumBy_add, sumBy_range_getElem_pair]
  rw [sumBy_flatMap]
  simp only [sumBy_map]

theorem sumBy_pythonEdgePairs (edges : List PackingEdge)
    (g : PackingEdge × PackingEdge → Nat) :
    sumBy (pythonEdgePairs edges) g = sumBy (unorderedEdgePairs edges) g := by
  induction edges with
  | nil => rfl
  | cons e es ih =>
      rw [sumBy_pythonEdgePairs_cons, ih, unorderedEdgePairs_cons,
        sumBy_append, sumBy_map]

/-! ## The transcription -/

/-- `value(side, ident, coordinate)` from `_candidate_score`.  The candidate
label shadows any recorded assignment for the current vertex. -/
def pyValue (s : PackingPartial) (current : PackingVertex) (word : List Nat)
    (side : PackingSide) (ident d : Nat) : Option Nat :=
  if (side, ident) = current then word[d]? else s (side, ident) d

/-- The `unknown += 1` branch: distinct endpoints with at least one unknown. -/
def pyCompUnknown (s : PackingPartial) (current : PackingVertex) (word : List Nat)
    (side : PackingSide) (left right d : Nat) : Bool :=
  (left != right) &&
    ((pyValue s current word side left d).isNone ||
      (pyValue s current word side right d).isNone)

/-- The `possible = False` branch: distinct known endpoints with unequal symbols. -/
def pyCompMismatch (s : PackingPartial) (current : PackingVertex) (word : List Nat)
    (side : PackingSide) (left right d : Nat) : Bool :=
  (left != right) &&
    (match pyValue s current word side left d, pyValue s current word side right d with
      | some x, some y => x != y
      | _, _ => false)

def pyPairUnknown (s : PackingPartial) (current : PackingVertex) (word : List Nat)
    (a : Nat) (first second : PackingEdge) : Nat :=
  sumBy (List.range a) (fun d =>
    (if pyCompUnknown s current word .row first.1 second.1 d then 1 else 0) +
      (if pyCompUnknown s current word .col first.2 second.2 d then 1 else 0))

def pyPairMismatch (s : PackingPartial) (current : PackingVertex) (word : List Nat)
    (a : Nat) (first second : PackingEdge) : Bool :=
  (List.range a).any (fun d =>
    pyCompMismatch s current word .row first.1 second.1 d ||
      pyCompMismatch s current word .col first.2 second.2 d)

/-- `2 * (D // r ** unknown)` when the pair can still agree, else `0`. -/
def pyPairTerm (s : PackingPartial) (current : PackingVertex) (word : List Nat)
    (r a : Nat) (first second : PackingEdge) : Nat :=
  if pyPairMismatch s current word a first second then 0
  else 2 * (r ^ (2 * a) / r ^ pyPairUnknown s current word a first second)

def pyCandidateScore (s : PackingPartial) (current : PackingVertex) (word : List Nat)
    (r a : Nat) (edges : List PackingEdge) : Nat :=
  edges.length * r ^ (2 * a) +
    sumBy (pythonEdgePairs edges) (fun pair => pyPairTerm s current word r a pair.1 pair.2)

/-! ## Per-comparison correspondence with `classifyEquality` -/

theorem pyValue_of_ne (s : PackingPartial) (current : PackingVertex) (word : List Nat)
    (side : PackingSide) (ident d : Nat) (h : (side, ident) ≠ current) :
    pyValue s current word side ident d = s (side, ident) d := by
  simp [pyValue, h]

theorem pyValue_of_eq (s : PackingPartial) (current : PackingVertex) (word : List Nat)
    (side : PackingSide) (ident d : Nat) (h : (side, ident) = current) :
    pyValue s current word side ident d = word[d]? := by
  simp [pyValue, h]

theorem assignmentsForCandidate_eq_none (s : PackingPartial) (current : PackingVertex)
    (v : PackingVertex) (d : Nat) :
    assignmentsForCandidate s current v d = none ↔ v = current ∨ s v d = none := by
  unfold assignmentsForCandidate
  by_cases h : v = current <;> simp [h]

theorem assignmentsForCandidate_eq_some (s : PackingPartial) (current : PackingVertex)
    (v : PackingVertex) (d x : Nat) :
    assignmentsForCandidate s current v d = some x ↔ v ≠ current ∧ s v d = some x := by
  unfold assignmentsForCandidate
  by_cases h : v = current <;> simp [h]

theorem py_side_unknown (s : PackingPartial) (current : PackingVertex)
    (word : List Nat) (side : PackingSide) (left right d : Nat)
    (hne : left ≠ right) (hlen : d < word.length) :
    pyCompUnknown s current word side left right d =
      (classifyEquality (assignmentsForCandidate s current) current d side left right
        == .unresolved) := by
  have hbeq : (left == right) = false := by rw [beq_eq_false_iff_ne]; exact hne
  have hbne : (left != right) = true := by rw [bne_iff_ne]; exact hne
  obtain ⟨w, hw⟩ : ∃ w, word[d]? = some w := ⟨word[d], List.getElem?_eq_getElem hlen⟩
  simp only [pyCompUnknown, classifyEquality, hbne, hbeq, Bool.true_and,
    Bool.false_eq_true, ite_false, Option.isNone_some]
  by_cases hcl : (side, left) = current
  · have hcondL : (current == (side, left)) = true := by
      rw [beq_iff_eq]; exact hcl.symm
    have hneR : (side, right) ≠ current :=
      fun h => hne (congrArg Prod.snd (hcl.trans h.symm))
    have hcondR : (current == (side, right)) = false := by
      rw [beq_eq_false_iff_ne]; exact fun h => hneR h.symm
    have hAl : assignmentsForCandidate s current (side, left) d = none := by
      simp [assignmentsForCandidate, hcl]
    rw [pyValue_of_eq s current word side left d hcl,
      pyValue_of_ne s current word side right d hneR, hAl]
    cases hr : assignmentsForCandidate s current (side, right) d with
    | none =>
        have hn : s (side, right) d = none :=
          ((assignmentsForCandidate_eq_none s current (side, right) d).1 hr).resolve_left hneR
        rw [hn]
        simp [hcondL, hcondR, hw]
    | some y =>
        have hv : s (side, right) d = some y :=
          ((assignmentsForCandidate_eq_some s current (side, right) d y).1 hr).2
        rw [hv]
        simp only [hcondL, hcondR, hw, Bool.false_or, reduceIte]
        rfl
  · have hcondL : (current == (side, left)) = false := by
      rw [beq_eq_false_iff_ne]; exact fun h => hcl h.symm
    by_cases hcr : (side, right) = current
    · have hcondR : (current == (side, right)) = true := by
        rw [beq_iff_eq]; exact hcr.symm
      have hneL : (side, left) ≠ current :=
        fun h => hne (congrArg Prod.snd (h.trans hcr.symm))
      have hAr : assignmentsForCandidate s current (side, right) d = none := by
        simp [assignmentsForCandidate, hcr]
      rw [pyValue_of_ne s current word side left d hneL,
        pyValue_of_eq s current word side right d hcr, hAr]
      cases hl : assignmentsForCandidate s current (side, left) d with
      | none =>
          have hn : s (side, left) d = none :=
            ((assignmentsForCandidate_eq_none s current (side, left) d).1 hl).resolve_left hneL
          rw [hn]
          simp [hcondL, hcondR, hw]
      | some x =>
          have hv : s (side, left) d = some x :=
            ((assignmentsForCandidate_eq_some s current (side, left) d x).1 hl).2
          rw [hv]
          simp only [hcondL, hcondR, hw, Bool.false_or, reduceIte]
          rfl
    · have hcondR : (current == (side, right)) = false := by
        rw [beq_eq_false_iff_ne]; exact fun h => hcr h.symm
      rw [pyValue_of_ne s current word side left d hcl,
        pyValue_of_ne s current word side right d hcr]
      cases hl : assignmentsForCandidate s current (side, left) d with
      | none =>
          have hnL : s (side, left) d = none :=
            ((assignmentsForCandidate_eq_none s current (side, left) d).1 hl).resolve_left hcl
          cases hr : assignmentsForCandidate s current (side, right) d with
          | none =>
              have hnR : s (side, right) d = none :=
                ((assignmentsForCandidate_eq_none s current (side, right) d).1 hr).resolve_left hcr
              rw [hnL, hnR]
              simp [hcondL, hcondR, hw]
          | some y =>
              have hvR : s (side, right) d = some y :=
                ((assignmentsForCandidate_eq_some s current (side, right) d y).1 hr).2
              rw [hnL, hvR]
              simp [hcondL, hcondR, hw]
      | some x =>
          have hvL : s (side, left) d = some x :=
            ((assignmentsForCandidate_eq_some s current (side, left) d x).1 hl).2
          cases hr : assignmentsForCandidate s current (side, right) d with
          | none =>
              have hnR : s (side, right) d = none :=
                ((assignmentsForCandidate_eq_none s current (side, right) d).1 hr).resolve_left hcr
              rw [hvL, hnR]
              simp [hcondL, hcondR, hw]
          | some y =>
              have hvR : s (side, right) d = some y :=
                ((assignmentsForCandidate_eq_some s current (side, right) d y).1 hr).2
              rw [hvL, hvR]
              by_cases heq : x = y
              · subst heq
                simp [hcondL, hcondR, hw]
              · have hxy : (x == y) = false := by rw [beq_eq_false_iff_ne]; exact heq
                simp only [hxy, Option.isNone_some, Bool.or_self, Bool.false_eq_true,
                  beq_self_eq_true, reduceIte]
                rfl

/-- The symbol written into the candidate's coordinate, when it has one. -/
def pyCandidateMismatch (cmp : PairComparison) (wordSym : Option Nat) : Bool :=
  match cmp with
  | .candidate y => wordSym != some y
  | _ => false

theorem py_side_mismatch (s : PackingPartial) (current : PackingVertex)
    (word : List Nat) (side : PackingSide) (left right d : Nat)
    (hne : left ≠ right) (hlen : d < word.length) :
    pyCompMismatch s current word side left right d =
      ((classifyEquality (assignmentsForCandidate s current) current d side left right
        == .mismatch) ||
        pyCandidateMismatch
          (classifyEquality (assignmentsForCandidate s current) current d side left right)
          word[d]?) := by
  have hbeq : (left == right) = false := by rw [beq_eq_false_iff_ne]; exact hne
  have hbne : (left != right) = true := by rw [bne_iff_ne]; exact hne
  obtain ⟨w, hw⟩ : ∃ w, word[d]? = some w := ⟨word[d], List.getElem?_eq_getElem hlen⟩
  simp only [pyCompMismatch, classifyEquality, hbne, hbeq, Bool.true_and,
    Bool.false_eq_true, ite_false, hw, pyCandidateMismatch]
  by_cases hcl : (side, left) = current
  · have hcondL : (current == (side, left)) = true := by
      rw [beq_iff_eq]; exact hcl.symm
    have hneR : (side, right) ≠ current :=
      fun h => hne (congrArg Prod.snd (hcl.trans h.symm))
    have hcondR : (current == (side, right)) = false := by
      rw [beq_eq_false_iff_ne]; exact fun h => hneR h.symm
    have hAl : assignmentsForCandidate s current (side, left) d = none := by
      simp [assignmentsForCandidate, hcl]
    rw [pyValue_of_eq s current word side left d hcl,
      pyValue_of_ne s current word side right d hneR, hAl]
    cases hr : assignmentsForCandidate s current (side, right) d with
    | none =>
        have hn : s (side, right) d = none :=
          ((assignmentsForCandidate_eq_none s current (side, right) d).1 hr).resolve_left hneR
        rw [hn]
        simp [hcondL, hcondR, hw]
    | some y =>
        have hv : s (side, right) d = some y :=
          ((assignmentsForCandidate_eq_some s current (side, right) d y).1 hr).2
        rw [hv]
        simp only [hcondL, hcondR, hw, Bool.false_or, reduceIte]
        rfl
  · have hcondL : (current == (side, left)) = false := by
      rw [beq_eq_false_iff_ne]; exact fun h => hcl h.symm
    by_cases hcr : (side, right) = current
    · have hcondR : (current == (side, right)) = true := by
        rw [beq_iff_eq]; exact hcr.symm
      have hneL : (side, left) ≠ current :=
        fun h => hne (congrArg Prod.snd (h.trans hcr.symm))
      have hAr : assignmentsForCandidate s current (side, right) d = none := by
        simp [assignmentsForCandidate, hcr]
      rw [pyValue_of_ne s current word side left d hneL,
        pyValue_of_eq s current word side right d hcr, hAr]
      cases hl : assignmentsForCandidate s current (side, left) d with
      | none =>
          have hn : s (side, left) d = none :=
            ((assignmentsForCandidate_eq_none s current (side, left) d).1 hl).resolve_left hneL
          rw [hn]
          simp [hcondL, hcondR, hw]
      | some x =>
          have hv : s (side, left) d = some x :=
            ((assignmentsForCandidate_eq_some s current (side, left) d x).1 hl).2
          rw [hv]
          simp only [hcondL, hcondR, hw, Bool.false_or, reduceIte]
          rw [bne_comm]
          rfl
    · have hcondR : (current == (side, right)) = false := by
        rw [beq_eq_false_iff_ne]; exact fun h => hcr h.symm
      rw [pyValue_of_ne s current word side left d hcl,
        pyValue_of_ne s current word side right d hcr]
      cases hl : assignmentsForCandidate s current (side, left) d with
      | none =>
          have hnL : s (side, left) d = none :=
            ((assignmentsForCandidate_eq_none s current (side, left) d).1 hl).resolve_left hcl
          cases hr : assignmentsForCandidate s current (side, right) d with
          | none =>
              have hnR : s (side, right) d = none :=
                ((assignmentsForCandidate_eq_none s current (side, right) d).1 hr).resolve_left hcr
              rw [hnL, hnR]
              simp [hcondL, hcondR, hw]
          | some y =>
              have hvR : s (side, right) d = some y :=
                ((assignmentsForCandidate_eq_some s current (side, right) d y).1 hr).2
              rw [hnL, hvR]
              simp [hcondL, hcondR, hw]
      | some x =>
          have hvL : s (side, left) d = some x :=
            ((assignmentsForCandidate_eq_some s current (side, left) d x).1 hl).2
          cases hr : assignmentsForCandidate s current (side, right) d with
          | none =>
              have hnR : s (side, right) d = none :=
                ((assignmentsForCandidate_eq_none s current (side, right) d).1 hr).resolve_left hcr
              rw [hvL, hnR]
              simp [hcondL, hcondR, hw]
          | some y =>
              have hvR : s (side, right) d = some y :=
                ((assignmentsForCandidate_eq_some s current (side, right) d y).1 hr).2
              rw [hvL, hvR]
              by_cases heq : x = y
              · subst heq
                simp [hcondL, hcondR, hw]
              · have hxy : (x != y) = true := by rw [bne_iff_ne]; exact heq
                have hxy' : (x == y) = false := by rw [beq_eq_false_iff_ne]; exact heq
                simp only [hxy, hxy', Bool.true_or, Bool.false_or, Bool.false_eq_true,
                  reduceIte]
                rfl


/-! ## Pair-level and score-level assembly -/

theorem py_side_unknown' (s : PackingPartial) (current : PackingVertex)
    (word : List Nat) (side : PackingSide) (left right d : Nat)
    (hlen : d < word.length) :
    pyCompUnknown s current word side left right d =
      (classifyEquality (assignmentsForCandidate s current) current d side left right
        == .unresolved) := by
  by_cases hne : left = right
  · subst hne
    have hbne : (left != left) = false := by rw [bne_self_eq_false]
    simp only [pyCompUnknown, hbne, Bool.false_and, classifyEquality, beq_self_eq_true,
      Bool.false_eq_true, ite_true]
    rfl
  · exact py_side_unknown s current word side left right d hne hlen

theorem py_side_mismatch' (s : PackingPartial) (current : PackingVertex)
    (word : List Nat) (side : PackingSide) (left right d : Nat)
    (hlen : d < word.length) :
    pyCompMismatch s current word side left right d =
      ((classifyEquality (assignmentsForCandidate s current) current d side left right
        == .mismatch) ||
        pyCandidateMismatch
          (classifyEquality (assignmentsForCandidate s current) current d side left right)
          word[d]?) := by
  by_cases hne : left = right
  · subst hne
    have hbne : (left != left) = false := by rw [bne_self_eq_false]
    simp only [pyCompMismatch, hbne, Bool.false_and, classifyEquality, beq_self_eq_true,
      Bool.false_eq_true, ite_true, pyCandidateMismatch]
    rfl
  · exact py_side_mismatch s current word side left right d hne hlen

theorem any_congr {α : Type} (xs : List α) (f g : α → Bool)
    (h : ∀ x, x ∈ xs → f x = g x) : xs.any f = xs.any g := by
  induction xs with
  | nil => rfl
  | cons x xs ih =>
      have hx := h x (by simp)
      have htail : ∀ y, y ∈ xs → f y = g y := fun y hy => h y (by simp [hy])
      simp only [List.any_cons, hx, ih htail]

theorem any_or {α : Type} (xs : List α) (f g : α → Bool) :
    xs.any (fun x => f x || g x) = (xs.any f || xs.any g) := by
  induction xs with
  | nil => rfl
  | cons x xs ih =>
      simp only [List.any_cons, ih]
      ac_rfl

def pyCoordMismatch (p : PairCoordinate) (wordSym : Option Nat) : Bool :=
  ((p.1 == .mismatch) || pyCandidateMismatch p.1 wordSym) ||
    ((p.2 == .mismatch) || pyCandidateMismatch p.2 wordSym)

def pyCoordUnknown (p : PairCoordinate) : Nat :=
  (if p.1 == .unresolved then 1 else 0) + (if p.2 == .unresolved then 1 else 0)

theorem pyPairUnknown_eq (s : PackingPartial) (current : PackingVertex)
    (word : List Nat) (a : Nat) (first second : PackingEdge)
    (hlen : word.length = a) :
    pyPairUnknown s current word a first second =
      sumBy (concretePairCoordinates s current a first second) pyCoordUnknown := by
  unfold pyPairUnknown concretePairCoordinates
  rw [sumBy_map]
  apply sumBy_congr
  intro d hd
  have hda : d < a := List.mem_range.1 hd
  have hdw : d < word.length := by omega
  unfold pyCoordUnknown
  simp only [concretePairCoordinate]
  have h1 := py_side_unknown' s current word .row first.1 second.1 d hdw
  have h2 := py_side_unknown' s current word .col first.2 second.2 d hdw
  simp only [← h1, ← h2]

theorem pyPairMismatch_eq (s : PackingPartial) (current : PackingVertex)
    (word : List Nat) (a : Nat) (first second : PackingEdge)
    (hlen : word.length = a) :
    pyPairMismatch s current word a first second =
      (List.range a).any (fun d => pyCoordMismatch
        (concretePairCoordinate (assignmentsForCandidate s current) current d first second)
        word[d]?) := by
  unfold pyPairMismatch
  apply any_congr
  intro d hd
  have hda : d < a := List.mem_range.1 hd
  have hdw : d < word.length := by omega
  unfold pyCoordMismatch
  simp only [concretePairCoordinate]
  have h1 := py_side_mismatch' s current word .row first.1 second.1 d hdw
  have h2 := py_side_mismatch' s current word .col first.2 second.2 d hdw
  simp only [← h1, ← h2]

theorem pairHasMismatchB_any (ps : List PairCoordinate) :
    pairHasMismatchB ps = ps.any coordinateHasMismatchB := by
  induction ps with
  | nil => rfl
  | cons p ps ih => simp only [pairHasMismatchB, List.any_cons, ih]


/-! ## Candidate-constraint bookkeeping -/

def atMostOneCandidate (p : PairCoordinate) : Prop :=
  ∀ x y, p.1 = .candidate x → p.2 = .candidate y → False

theorem pyCoordMismatch_eq (p : PairCoordinate) (w : Option Nat) :
    pyCoordMismatch p w =
      (coordinateHasMismatchB p ||
        (pyCandidateMismatch p.1 w || pyCandidateMismatch p.2 w)) := by
  unfold pyCoordMismatch coordinateHasMismatchB
  ac_rfl

theorem any_map_eq {α β : Type} (xs : List α) (g : α → β) (f : β → Bool) :
    (xs.map g).any f = xs.any (fun x => f (g x)) := by
  induction xs with
  | nil => rfl
  | cons x xs ih => simp only [List.map_cons, List.any_cons, ih]

/-! ## Unknown-count accounting -/

theorem pyCoordUnknown_add_fixed (p : PairCoordinate) (hone : atMostOneCandidate p) :
    pyCoordUnknown p + coordinateFixed p = coordinateUnknown p := by
  obtain ⟨a, b⟩ := p
  cases a <;> cases b <;>
    simp_all [pyCoordUnknown, coordinateFixed, coordinateConstraint, coordinateUnknown,
      comparisonUnknown, atMostOneCandidate]

theorem fixedCount_constraints (ps : List PairCoordinate) :
    fixedCount (constraintsFromCoordinates ps) = sumBy ps coordinateFixed := by
  induction ps with
  | nil => rfl
  | cons p ps ih =>
      simp only [constraintsFromCoordinates, sumBy, ih]
      cases hc : coordinateConstraint p with
      | none =>
          have hz : coordinateFixed p = 0 := by simp [coordinateFixed, hc]
          simp only [fixedCount, hz, ih, Nat.zero_add]
      | some c =>
          have ho : coordinateFixed p = 1 := by simp [coordinateFixed, hc]
          simp only [fixedCount, ho, ih, Nat.one_add]


/-! ## The constraint-alignment bridge -/

theorem beq_iff_not_bne_option (x y : Nat) :
    (x == y) = !((some x : Option Nat) != some y) := by
  show (x == y) = !(x != y)
  cases h : (x == y) <;> simp [h, bne]

/-- The single constraint generated for a pair coordinate agrees with the two
Python candidate comparisons.  `atMostOneCandidate` is what makes the single
`Option Nat` constraint lossless: a row candidate and a column candidate can
never occur at the same coordinate because `current` has one side. -/
theorem coordinate_constraint_wordMatches (p : PairCoordinate) (w : Nat)
    (hone : atMostOneCandidate p) :
    (match coordinateConstraint p with
      | none => true
      | some c => (w == c)) =
      !(pyCandidateMismatch p.1 (some w) || pyCandidateMismatch p.2 (some w)) := by
  obtain ⟨a, b⟩ := p
  cases a <;> cases b <;>
    simp_all [coordinateConstraint, pyCandidateMismatch, atMostOneCandidate,
      beq_iff_not_bne_option]

/-- `wordMatches` over `constraintsFromCoordinates` is the negation of the
coordinate-indexed candidate scan.  This is the alignment lemma that connects
the Lean constraint representation to the Python `label[coordinate]`
comparison. -/
theorem wordMatches_range_any : ∀ (a : Nat) (g : Nat → PairCoordinate) (word : List Nat),
    word.length = a → (∀ d, d < a → atMostOneCandidate (g d)) →
    wordMatches (constraintsFromCoordinates ((List.range a).map g)) word =
      !((List.range a).any (fun d =>
        pyCandidateMismatch (g d).1 word[d]? || pyCandidateMismatch (g d).2 word[d]?)) := by
  intro a
  induction a with
  | zero =>
      intro g word hlen hone
      have hnil : word = [] := List.eq_nil_of_length_eq_zero (by simpa using hlen)
      subst hnil
      rfl
  | succ a ih =>
      intro g word hlen hone
      cases word with
      | nil => simp at hlen
      | cons w ws =>
          have hlen' : ws.length = a := by simpa using hlen
          have hone' : ∀ d, d < a → atMostOneCandidate ((fun x => g x.succ) d) :=
            fun d hd => hone (Nat.succ d) (by omega)
          have hrec := ih (fun x => g x.succ) ws hlen' hone'
          rw [List.range_succ_eq_map]
          simp only [List.map_cons, List.any_cons, List.map_map, Function.comp_def,
            List.getElem?_cons_zero, constraintsFromCoordinates]
          rw [any_map_eq]
          simp only [List.getElem?_cons_succ]
          cases hc : coordinateConstraint (g 0) with
          | none =>
              have hhead : (true : Bool) =
                  !(pyCandidateMismatch (g 0).1 (some w) ||
                    pyCandidateMismatch (g 0).2 (some w)) := by
                simpa [hc] using coordinate_constraint_wordMatches (g 0) w (hone 0 (by omega))
              have hc0 : (pyCandidateMismatch (g 0).1 (some w) ||
                  pyCandidateMismatch (g 0).2 (some w)) = false := by
                cases h : (pyCandidateMismatch (g 0).1 (some w) ||
                    pyCandidateMismatch (g 0).2 (some w)) <;> simp_all
              simp only [hc, wordMatches, hrec, hc0, Bool.false_or]
          | some c =>
              have hhead : (w == c) =
                  !(pyCandidateMismatch (g 0).1 (some w) ||
                    pyCandidateMismatch (g 0).2 (some w)) := by
                simpa [hc] using coordinate_constraint_wordMatches (g 0) w (hone 0 (by omega))
              simp only [hc, wordMatches, hrec, hhead, ← Bool.not_or]

/-! ## The score identity -/

/-- Python's early-exit mismatch scan is exactly "some directed class is
already contradictory, or the candidate label violates a recorded constraint". -/
theorem pyPairMismatch_iff (s : PackingPartial) (current : PackingVertex)
    (word : List Nat) (r a : Nat) (first second : PackingEdge)
    (hword : word ∈ labelWords r a) :
    pyPairMismatch s current word a first second =
      (pairHasMismatchB (concretePairCoordinates s current a first second) ||
        !(wordMatches
          (constraintsFromCoordinates (concretePairCoordinates s current a first second))
          word)) := by
  have hlen : word.length = a := labelWords_member_length r a word hword
  have hone : ∀ d, d < a → atMostOneCandidate
      (concretePairCoordinate (assignmentsForCandidate s current) current d first second) := by
    intro d _ x y hx hy
    have hx' := classify_candidate_current (assignmentsForCandidate s current) current d
      .row first.1 second.1 x hx
    have hy' := classify_candidate_current (assignmentsForCandidate s current) current d
      .col first.2 second.2 y hy
    have hside : PackingSide.row = PackingSide.col := hx'.symm.trans hy'
    cases hside
  have hcoord : concretePairCoordinates s current a first second =
      (List.range a).map (fun d =>
        concretePairCoordinate (assignmentsForCandidate s current) current d first second) := rfl
  have hstep : (List.range a).any (fun d => pyCoordMismatch
      (concretePairCoordinate (assignmentsForCandidate s current) current d first second)
      word[d]?) =
      ((List.range a).any (fun d => coordinateHasMismatchB
        (concretePairCoordinate (assignmentsForCandidate s current) current d first second)) ||
       (List.range a).any (fun d =>
        pyCandidateMismatch
          (concretePairCoordinate (assignmentsForCandidate s current) current d first second).1
          word[d]? ||
        pyCandidateMismatch
          (concretePairCoordinate (assignmentsForCandidate s current) current d first second).2
          word[d]?)) := by
    rw [← any_or]
    apply any_congr
    intro d _
    rw [pyCoordMismatch_eq]
  have hclass : (List.range a).any (fun d => coordinateHasMismatchB
      (concretePairCoordinate (assignmentsForCandidate s current) current d first second)) =
      pairHasMismatchB (concretePairCoordinates s current a first second) := by
    rw [pairHasMismatchB_any, hcoord, any_map_eq]
  have hcand : (List.range a).any (fun d =>
      (pyCandidateMismatch
          (concretePairCoordinate (assignmentsForCandidate s current) current d first second).1
          word[d]? ||
       pyCandidateMismatch
          (concretePairCoordinate (assignmentsForCandidate s current) current d first second).2
          word[d]?)) =
      !(wordMatches
        (constraintsFromCoordinates (concretePairCoordinates s current a first second)) word) := by
    rw [hcoord]
    rw [wordMatches_range_any a
      (fun d => concretePairCoordinate (assignmentsForCandidate s current) current d first second)
      word hlen hone]
    simp only [Bool.not_not]
  rw [pyPairMismatch_eq s current word a first second hlen, hstep, hclass, hcand]

/-- The Python unknown count is exactly `parentUnknown - fixedCount`. -/
theorem pyPairUnknown_eq_parent (s : PackingPartial) (current : PackingVertex)
    (word : List Nat) (r a : Nat) (first second : PackingEdge)
    (hword : word ∈ labelWords r a) :
    pyPairUnknown s current word a first second =
      pairUnknownComparisons (concretePairCoordinates s current a first second) -
        fixedCount (constraintsFromCoordinates (concretePairCoordinates s current a first second)) := by
  have hlen : word.length = a := labelWords_member_length r a word hword
  have hone : ∀ p, p ∈ concretePairCoordinates s current a first second →
      atMostOneCandidate p := by
    intro p hp
    simp only [concretePairCoordinates, List.mem_map] at hp
    obtain ⟨d, _, rfl⟩ := hp
    intro x y hx hy
    have hx' := classify_candidate_current (assignmentsForCandidate s current) current d
      .row first.1 second.1 x hx
    have hy' := classify_candidate_current (assignmentsForCandidate s current) current d
      .col first.2 second.2 y hy
    have hside : PackingSide.row = PackingSide.col := hx'.symm.trans hy'
    cases hside
  have hsum : sumBy (concretePairCoordinates s current a first second) pyCoordUnknown +
      sumBy (concretePairCoordinates s current a first second) coordinateFixed =
      sumBy (concretePairCoordinates s current a first second) coordinateUnknown := by
    rw [← sumBy_add]
    apply sumBy_congr
    intro p hp
    exact pyCoordUnknown_add_fixed p (hone p hp)
  have hfix := fixedCount_constraints (concretePairCoordinates s current a first second)
  have hunk : pairUnknownComparisons (concretePairCoordinates s current a first second) =
      sumBy (concretePairCoordinates s current a first second) coordinateUnknown := rfl
  rw [pyPairUnknown_eq s current word a first second hlen]
  rw [hunk, hfix]
  exact Nat.eq_sub_of_add_eq hsum

/-- The Python pair term is the Lean conditional pair term. -/
theorem pyPairTerm_eq (s : PackingPartial) (current : PackingVertex)
    (word : List Nat) (r a : Nat) (first second : PackingEdge)
    (hword : word ∈ labelWords r a) :
    pyPairTerm s current word r a first second =
      pairTermCandidate r a (concreteD3PairTerm s current r a first second) word := by
  have hmiss := pyPairMismatch_iff s current word r a first second hword
  have hunk := pyPairUnknown_eq_parent s current word r a first second hword
  by_cases hbm : pairHasMismatchB (concretePairCoordinates s current a first second) = true
  · have hpy : pyPairMismatch s current word a first second = true := by
      rw [hmiss, hbm]; rfl
    have hterm : concreteD3PairTerm s current r a first second =
        { constraints := none, parentUnknown := 0, coefficient := 2 } := by
      simp only [concreteD3PairTerm, hbm, if_pos rfl, reduceIte]
    rw [pyPairTerm, if_pos hpy, hterm]
    simp only [pairTermCandidate]
  · have hbmf : pairHasMismatchB (concretePairCoordinates s current a first second) = false := by
      cases h : pairHasMismatchB (concretePairCoordinates s current a first second)
      · rfl
      · exact absurd h hbm
    have hterm : concreteD3PairTerm s current r a first second =
        pairTermOfCoordinates (concretePairCoordinates s current a first second) := by
      simp only [concreteD3PairTerm, hbmf, Bool.false_eq_true, if_false, reduceIte]
    by_cases hwm : wordMatches
        (constraintsFromCoordinates (concretePairCoordinates s current a first second)) word
    · have hpy : ¬ pyPairMismatch s current word a first second := by
        simp [hmiss, hbmf, hwm]
      rw [pyPairTerm, if_neg hpy, hunk, hterm]
      simp only [pairTermCandidate, pairTermOfCoordinates, hwm, if_pos rfl, reduceIte]
    · have hpy : pyPairMismatch s current word a first second = true := by
        simp [hmiss, hbmf, hwm]
      rw [pyPairTerm, if_pos hpy, hterm]
      simp only [pairTermCandidate, pairTermOfCoordinates, hwm, Bool.false_eq_true, reduceIte]

/-- **The score identity.**  The Lean transcription of `_candidate_score`
equals `concreteD3ScoreCandidate` on the corresponding state. -/
theorem pyCandidateScore_eq (s : PackingPartial) (current : PackingVertex)
    (word : List Nat) (r a : Nat) (edges : List PackingEdge)
    (hword : word ∈ labelWords r a) :
    pyCandidateScore s current word r a edges =
      concreteD3ScoreCandidate s current r a edges word := by
  unfold pyCandidateScore concreteD3ScoreCandidate concreteD3PairTerms
  rw [sumBy_pythonEdgePairs, sumBy_map]
  congr 1
  apply sumBy_congr
  intro pair _
  exact pyPairTerm_eq s current word r a pair.1 pair.2 hword

#print axioms py_side_unknown
#print axioms py_side_mismatch
#print axioms pyPairUnknown_eq
#print axioms pyPairMismatch_eq
#print axioms sumBy_pythonEdgePairs
#print axioms pyCoordUnknown_add_fixed
#print axioms fixedCount_constraints
#print axioms coordinate_constraint_wordMatches
#print axioms wordMatches_range_any
#print axioms pyPairMismatch_iff
#print axioms pyPairUnknown_eq_parent
#print axioms pyPairTerm_eq
#print axioms pyCandidateScore_eq

end D3PythonScore
