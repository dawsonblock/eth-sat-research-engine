import D3GlobalPacketAddress
import D3NumericSlot
import D3OccurrenceRank

/-! Composition of occurrence ranks, canonical class patterns, and numerical
packet slots. This is a Lean model. Source-language refinement and algorithmic
cost for the Python constructor remain separate obligations. -/

namespace D3FullPacketModel
open D3GlobalPacketAddress

abbrev SymbolClass := List (Nat × Nat)

structure Address where
  pattern : List (Nat × Nat)
  packet : Nat
  slot : Nat
  deriving DecidableEq, Repr

def encodeClass (cls : SymbolClass) (offset : Nat) : Option Address :=
  let pattern := patternOfClass cls
  (D3NumericSlot.encode (equalMask pattern) (orientationsOfClass cls) offset).map
    (fun addr => ⟨pattern, addr.1, addr.2⟩)

def decodeClass (address : Address) : SymbolClass × Nat :=
  let pair := D3NumericSlot.decode (equalMask address.pattern) address.packet address.slot
  (classOfPatternOrientations address.pattern pair.2, pair.1)

theorem class_pattern_length (cls : SymbolClass) :
    (equalMask (patternOfClass cls)).length = cls.length := by
  induction cls with
  | nil => simp [equalMask, patternOfClass]
  | cons pair tail ih =>
    cases pair
    simp [equalMask, patternOfClass] at ih ⊢
    exact ih

theorem class_orientation_length (cls : SymbolClass) :
    (orientationsOfClass cls).length +
      d3EqualCount (equalMask (patternOfClass cls)) =
      (equalMask (patternOfClass cls)).length := by
  induction cls with
  | nil => simp [orientationsOfClass, patternOfClass, equalMask, d3EqualCount]
  | cons pair tail ih =>
    cases pair with
    | mk row col =>
      by_cases heq : row = col
      · subst col
        simp [orientationsOfClass, patternOfClass, equalMask, d3EqualCount] at *
        omega
      · have hne : min row col ≠ max row col := by omega
        simp [orientationsOfClass, patternOfClass, equalMask, d3EqualCount,
          heq, hne] at *
        omega

theorem encodeClass_exists (cls : SymbolClass) (offset : Nat) :
    ∃ address, encodeClass cls offset = some address := by
  have h := class_orientation_length cls
  obtain ⟨packet, slot, he⟩ := D3NumericSlot.encode_exists
    (equalMask (patternOfClass cls)) (orientationsOfClass cls) offset h
  exact ⟨⟨patternOfClass cls, packet, slot⟩, by simp [encodeClass, he]⟩

theorem decodeClass_encodeClass (cls : SymbolClass) (offset : Nat) (address : Address)
    (h : encodeClass cls offset = some address) :
    decodeClass address = (cls, offset) := by
  unfold encodeClass at h
  cases hm : D3NumericSlot.encode (equalMask (patternOfClass cls))
      (orientationsOfClass cls) offset with
  | none => simp [hm] at h
  | some p =>
    cases p with
    | mk packet slot =>
      simp [hm] at h
      subst address
      have hdecoded := D3NumericSlot.decode_encode (equalMask (patternOfClass cls))
        (orientationsOfClass cls) offset packet slot hm
      simp [decodeClass, hdecoded, class_pattern_orientation_roundtrip]

theorem encodeClass_bounds (cls : SymbolClass) (offset height : Nat) (address : Address)
    (hpad : 2 ^ cls.length ∣ height) (hoff : offset < height)
    (h : encodeClass cls offset = some address) :
    address.packet < height / (2 ^ d3EqualCount (equalMask address.pattern)) ∧
      address.slot < 2 ^ cls.length := by
  unfold encodeClass at h
  cases hm : D3NumericSlot.encode (equalMask (patternOfClass cls))
      (orientationsOfClass cls) offset with
  | none => simp [hm] at h
  | some p =>
    cases p with
    | mk packet slot =>
      simp [hm] at h
      subst address
      have hlen := class_pattern_length cls
      have hp : 2 ^ (equalMask (patternOfClass cls)).length ∣ height := by
        simpa [hlen] using hpad
      have hb := D3NumericSlot.encode_bounds (equalMask (patternOfClass cls))
        (orientationsOfClass cls) offset packet slot height hp hoff hm
      simpa [hlen] using hb

def CanonicalPattern (pattern : List (Nat × Nat)) : Prop :=
  ∀ pair, pair ∈ pattern → pair.1 ≤ pair.2

theorem pattern_canonical (cls : SymbolClass) : CanonicalPattern (patternOfClass cls) := by
  induction cls with
  | nil => simp [CanonicalPattern, patternOfClass]
  | cons pair tail ih =>
    cases pair with
    | mk row col =>
      intro p hp
      simp only [patternOfClass, List.mem_cons] at hp
      cases hp with
      | inl he =>
        subst p
        change min row col ≤ max row col
        omega
      | inr ht => exact ih p ht

def BoundedClass (radix : Nat) (cls : SymbolClass) : Prop :=
  ∀ pair, pair ∈ cls → pair.1 < radix ∧ pair.2 < radix

theorem pattern_bounded (radix : Nat) (cls : SymbolClass) (h : BoundedClass radix cls) :
    ∀ pair, pair ∈ patternOfClass cls → pair.2 < radix := by
  induction cls with
  | nil => simp [patternOfClass]
  | cons head tail ih =>
    cases head with
    | mk row col =>
      have hrowcol := h (row, col) (by simp)
      have htail : BoundedClass radix tail := by
        intro p hp
        exact h p (by simp [hp])
      intro p hp
      simp only [patternOfClass, List.mem_cons] at hp
      cases hp with
      | inl he =>
        subst p
        change max row col < radix
        omega
      | inr ht => exact ih htail p ht

theorem encodeClass_pattern (cls : SymbolClass) (offset : Nat) (address : Address)
    (h : encodeClass cls offset = some address) : address.pattern = patternOfClass cls := by
  unfold encodeClass at h
  cases hm : D3NumericSlot.encode (equalMask (patternOfClass cls))
      (orientationsOfClass cls) offset with
  | none => simp [hm] at h
  | some p =>
    cases p with
    | mk packet slot => simp [hm] at h; subst address; rfl

theorem pattern_orientations_inverse (pattern : List (Nat × Nat))
    (orientations : List Bool) (hc : CanonicalPattern pattern)
    (hlen : orientations.length + d3EqualCount (equalMask pattern) = pattern.length) :
    patternOfClass (classOfPatternOrientations pattern orientations) = pattern ∧
      orientationsOfClass (classOfPatternOrientations pattern orientations) = orientations := by
  induction pattern generalizing orientations with
  | nil =>
    cases orientations <;>
      simp_all [classOfPatternOrientations, patternOfClass, orientationsOfClass,
        equalMask, d3EqualCount]
  | cons pair tail ih =>
    cases pair with
    | mk low high =>
      have hle : low ≤ high := hc (low, high) (by simp)
      have hctail : CanonicalPattern tail := by
        intro p hp
        exact hc p (by simp [hp])
      by_cases heq : low = high
      · subst high
        have ht : orientations.length + d3EqualCount (equalMask tail) = tail.length := by
          simp [equalMask, d3EqualCount] at hlen ⊢
          omega
        obtain ⟨hp, ho⟩ := ih orientations hctail ht
        simp [classOfPatternOrientations, patternOfClass, orientationsOfClass, hp, ho]
      · have hlt : low < high := by omega
        have hreverse : high ≠ low := Ne.symm heq
        cases orientations with
        | nil =>
          have hb := D3NumericSlot.equal_count_le_length (equalMask tail)
          simp [equalMask] at hb
          simp [equalMask, d3EqualCount, heq] at hlen
          omega
        | cons bit rest =>
          have ht : rest.length + d3EqualCount (equalMask tail) = tail.length := by
            simp [equalMask, d3EqualCount, heq] at hlen ⊢
            omega
          obtain ⟨hp, ho⟩ := ih rest hctail ht
          cases bit <;>
            simp [classOfPatternOrientations, patternOfClass, orientationsOfClass,
              d3DecodeSymbolPair, classOrientation, heq, hreverse, hlt, Nat.le_of_lt hlt,
              Nat.min_eq_left, Nat.max_eq_right, Nat.min_eq_right, Nat.max_eq_left,
              hp, ho]

theorem encodeClass_decodeClass (address : Address)
    (hc : CanonicalPattern address.pattern)
    (hslot : address.slot < 2 ^ address.pattern.length) :
    encodeClass (decodeClass address).1 (decodeClass address).2 = some address := by
  let mask := equalMask address.pattern
  let numbers := D3NumericSlot.decode mask address.packet address.slot
  have hm : mask.length = address.pattern.length := by simp [mask, equalMask]
  have hslen := d3_split_slot_lengths mask (D3BinaryBits.bits mask.length address.slot)
    (by simp [D3BinaryBits.bits_length])
  have ho : numbers.2.length + d3EqualCount mask = address.pattern.length := by
    simpa [numbers, D3NumericSlot.decode, hm] using hslen.2
  have hinv := pattern_orientations_inverse address.pattern numbers.2 hc (by
    simpa [mask] using ho)
  have hnum := D3NumericSlot.encode_decode mask address.packet address.slot (by
    simpa [hm] using hslot)
  cases address with
  | mk pattern packet slot =>
    simp only [decodeClass]
    change encodeClass (classOfPatternOrientations pattern numbers.2) numbers.1 =
      some ⟨pattern, packet, slot⟩
    simp only [encodeClass, hinv.1, hinv.2]
    simpa [mask, numbers] using congrArg
      (fun x => x.map (fun v => Address.mk pattern v.1 v.2)) hnum

theorem decodeClass_bounds (address : Address) (height : Nat)
    (hpad : 2 ^ address.pattern.length ∣ height)
    (hpacket : address.packet < height /
      (2 ^ d3EqualCount (equalMask address.pattern))) :
    (decodeClass address).2 < height := by
  have hp : 2 ^ (equalMask address.pattern).length ∣ height := by
    simpa [equalMask] using hpad
  exact D3NumericSlot.decode_bounds (equalMask address.pattern) address.packet
    address.slot height hp hpacket

def ValidPaddedAddress (width height : Nat) (address : Address) : Prop :=
  address.pattern.length = width ∧ CanonicalPattern address.pattern ∧
    address.packet < height / (2 ^ d3EqualCount (equalMask address.pattern)) ∧
      address.slot < 2 ^ width

/-- Every padded directed-class offset maps to a valid packet position. -/
theorem paddedClass_forward (cls : SymbolClass) (offset height : Nat)
    (hpad : 2 ^ cls.length ∣ height) (hoff : offset < height) :
    ∃ address, encodeClass cls offset = some address ∧
      ValidPaddedAddress cls.length height address ∧ decodeClass address = (cls, offset) := by
  obtain ⟨address, he⟩ := encodeClass_exists cls offset
  have hp := encodeClass_pattern cls offset address he
  have hb := encodeClass_bounds cls offset height address hpad hoff he
  refine ⟨address, he, ?_, decodeClass_encodeClass cls offset address he⟩
  refine ⟨?_, ?_, hb.1, hb.2⟩
  · rw [hp]
    simpa [equalMask] using class_pattern_length cls
  · rw [hp]
    exact pattern_canonical cls

/-- Every valid padded packet position decodes to an in-range directed-class
offset and re-encodes to the identical address. -/
theorem paddedClass_reverse (width height : Nat) (address : Address)
    (hpad : 2 ^ width ∣ height) (h : ValidPaddedAddress width height address) :
    (decodeClass address).2 < height ∧
      encodeClass (decodeClass address).1 (decodeClass address).2 = some address := by
  obtain ⟨hlen, hc, hpacket, hslot⟩ := h
  constructor
  · exact decodeClass_bounds address height (by simpa [hlen] using hpad) hpacket
  · exact encodeClass_decodeClass address hc (by simpa [hlen] using hslot)

def encodeEdge (classes : List SymbolClass) (edgeId : Nat) : Option Address :=
  (D3OccurrenceRank.encode classes edgeId).bind fun position =>
    encodeClass position.1 position.2

def decodeEdge (classes : List SymbolClass) (address : Address) : Option Nat :=
  let position := decodeClass address
  D3OccurrenceRank.decode position.1 classes position.2

theorem encodeEdge_exists (classes : List SymbolClass) (edgeId : Nat)
    (h : edgeId < classes.length) : ∃ address, encodeEdge classes edgeId = some address := by
  obtain ⟨position, hp⟩ := D3OccurrenceRank.encode_exists classes edgeId h
  obtain ⟨address, ha⟩ := encodeClass_exists position.1 position.2
  exact ⟨address, by simp [encodeEdge, hp, ha]⟩

theorem decodeEdge_encodeEdge (classes : List SymbolClass) (edgeId : Nat)
    (address : Address) (h : encodeEdge classes edgeId = some address) :
    decodeEdge classes address = some edgeId := by
  unfold encodeEdge at h
  cases hp : D3OccurrenceRank.encode classes edgeId with
  | none => simp [hp] at h
  | some position =>
    simp only [hp, Option.bind_some] at h
    have hd := decodeClass_encodeClass position.1 position.2 address h
    have hi := D3OccurrenceRank.decode_encode classes edgeId position.1 position.2 (by
      cases position; exact hp)
    simpa [decodeEdge, hd] using hi

theorem encodeEdge_injective (classes : List SymbolClass) (left right : Nat)
    (address : Address) (hl : encodeEdge classes left = some address)
    (hr : encodeEdge classes right = some address) : left = right := by
  have hleft := decodeEdge_encodeEdge classes left address hl
  have hright := decodeEdge_encodeEdge classes right address hr
  rw [hleft] at hright
  exact Option.some.inj hright

/-- Any occupied canonical packet slot encodes back to that same address. -/
theorem encodeEdge_decodeEdge (classes : List SymbolClass) (address : Address)
    (edgeId : Nat) (hc : CanonicalPattern address.pattern)
    (hslot : address.slot < 2 ^ address.pattern.length)
    (h : decodeEdge classes address = some edgeId) :
    encodeEdge classes edgeId = some address := by
  have hclass := encodeClass_decodeClass address hc hslot
  have hocc := D3OccurrenceRank.encode_decode classes (decodeClass address).1
    (decodeClass address).2 edgeId (by simpa [decodeEdge] using h)
  simpa [encodeEdge, hocc] using hclass

theorem decodedEdge_in_bounds (classes : List SymbolClass) (address : Address)
    (edgeId : Nat) (h : decodeEdge classes address = some edgeId) :
    edgeId < classes.length := by
  exact D3OccurrenceRank.decode_in_bounds classes (decodeClass address).1
    (decodeClass address).2 edgeId (by simpa [decodeEdge] using h)

/-- Under common-width and class-load hypotheses, every emitted real edge
lies inside the paper's padded packet and slot bounds. -/
theorem encodeEdge_bounds (classes : List SymbolClass) (width height edgeId : Nat)
    (address : Address)
    (hwidth : ∀ cls, cls ∈ classes → cls.length = width)
    (hpad : 2 ^ width ∣ height)
    (hload : ∀ cls, D3OccurrenceRank.countClass cls classes ≤ height)
    (h : encodeEdge classes edgeId = some address) :
    address.packet < height / (2 ^ d3EqualCount (equalMask address.pattern)) ∧
      address.slot < 2 ^ width := by
  unfold encodeEdge at h
  cases hp : D3OccurrenceRank.encode classes edgeId with
  | none => simp [hp] at h
  | some position =>
    cases position with
    | mk cls rank =>
      simp only [hp, Option.bind_some] at h
      have hs := D3OccurrenceRank.encode_spec classes edgeId cls rank hp
      have hw := hwidth cls (List.mem_of_getElem? hs.1)
      have hrank := D3OccurrenceRank.prefix_rank_lt_load classes edgeId cls hs.1
      have hoff : rank < height := by rw [hs.2]; exact Nat.lt_of_lt_of_le hrank (hload cls)
      have hb := encodeClass_bounds cls rank height address (by simpa [hw] using hpad) hoff h
      simpa [hw] using hb

theorem encodeEdge_valid (classes : List SymbolClass) (width height edgeId : Nat)
    (address : Address)
    (hwidth : ∀ cls, cls ∈ classes → cls.length = width)
    (hpad : 2 ^ width ∣ height)
    (hload : ∀ cls, D3OccurrenceRank.countClass cls classes ≤ height)
    (h : encodeEdge classes edgeId = some address) :
    ValidPaddedAddress width height address := by
  have hb := encodeEdge_bounds classes width height edgeId address hwidth hpad hload h
  unfold encodeEdge at h
  cases hp : D3OccurrenceRank.encode classes edgeId with
  | none => simp [hp] at h
  | some position =>
    cases position with
    | mk cls rank =>
      simp only [hp, Option.bind_some] at h
      have hs := D3OccurrenceRank.encode_spec classes edgeId cls rank hp
      have hw := hwidth cls (List.mem_of_getElem? hs.1)
      have hpattern := encodeClass_pattern cls rank address h
      refine ⟨?_, ?_, hb.1, hb.2⟩
      · rw [hpattern]
        simpa [equalMask, hw] using class_pattern_length cls
      · rw [hpattern]
        exact pattern_canonical cls

theorem padding_has_no_edge (classes : List SymbolClass) (address : Address)
    (hc : CanonicalPattern address.pattern)
    (hslot : address.slot < 2 ^ address.pattern.length) :
    decodeEdge classes address = none ↔
      ¬ ∃ edgeId, encodeEdge classes edgeId = some address := by
  constructor
  · intro hnone hexists
    obtain ⟨edgeId, he⟩ := hexists
    have hd := decodeEdge_encodeEdge classes edgeId address he
    rw [hnone] at hd
    contradiction
  · intro hnone
    cases hd : decodeEdge classes address with
    | none => rfl
    | some edgeId =>
      have he := encodeEdge_decodeEdge classes address edgeId hc hslot hd
      exact False.elim (hnone ⟨edgeId, he⟩)

#print axioms class_orientation_length
#print axioms class_pattern_length
#print axioms encodeClass_exists
#print axioms decodeClass_encodeClass
#print axioms encodeClass_bounds
#print axioms pattern_orientations_inverse
#print axioms pattern_canonical
#print axioms pattern_bounded
#print axioms encodeClass_pattern
#print axioms encodeClass_decodeClass
#print axioms decodeClass_bounds
#print axioms paddedClass_forward
#print axioms paddedClass_reverse
#print axioms encodeEdge_exists
#print axioms decodeEdge_encodeEdge
#print axioms encodeEdge_injective
#print axioms encodeEdge_decodeEdge
#print axioms decodedEdge_in_bounds
#print axioms encodeEdge_bounds
#print axioms encodeEdge_valid
#print axioms padding_has_no_edge

end D3FullPacketModel
