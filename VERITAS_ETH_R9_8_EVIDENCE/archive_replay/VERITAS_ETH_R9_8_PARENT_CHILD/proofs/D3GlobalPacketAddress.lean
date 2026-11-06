import D3PacketBijection

/-! A kernel-checked global slot-word bijection over canonical packet
descriptions. A description consists of an unordered symbol pattern, the
orientation bits for unequal coordinates, and the copy bits for equal
coordinates. The map interleaves those two bit lists into one physical slot
word. This composes the local slot split across every pattern and packet
index; the separate edge-occurrence-to-directed-class construction and its
Python/C++ source refinement remain distinct obligations. -/

namespace D3GlobalPacketAddress

structure ClassPosition where
  pattern : List (Nat × Nat)
  packet : Nat
  copies : List Bool
  orientations : List Bool
  deriving DecidableEq, Repr

structure PacketPosition where
  pattern : List (Nat × Nat)
  packet : Nat
  slotBits : List Bool
  deriving DecidableEq, Repr

def equalMask (pattern : List (Nat × Nat)) : List Bool :=
  pattern.map (fun pair => decide (pair.1 = pair.2))

def encode (position : ClassPosition) : Option PacketPosition :=
  (d3MergeSlot (equalMask position.pattern) position.copies position.orientations).map
    (fun bits => ⟨position.pattern, position.packet, bits⟩)

def decode (position : PacketPosition) : ClassPosition :=
  let parts := d3SplitSlot (equalMask position.pattern) position.slotBits
  ⟨position.pattern, position.packet, parts.1, parts.2⟩

/-- Every valid packet slot decomposes into a unique copy/orientation pair and
re-encoding those components returns the exact same physical slot address. -/
theorem encode_decode (position : PacketPosition)
    (hlen : (equalMask position.pattern).length = position.slotBits.length) :
    encode (decode position) = some position := by
  have hmerge := d3_merge_split_slot (equalMask position.pattern)
    position.slotBits hlen
  simp [encode, decode, hmerge]

/-- If a canonical class position has a valid interleaving, splitting the
physical word recovers its exact directed orientation and copy coordinates. -/
theorem decode_encode (position : ClassPosition) (bits : List Bool)
    (hmerge : d3MergeSlot (equalMask position.pattern) position.copies
      position.orientations = some bits) :
    decode ⟨position.pattern, position.packet, bits⟩ = position := by
  simp only [decode]
  have hsplit := d3_split_merge_slot (equalMask position.pattern)
    position.copies position.orientations bits hmerge
  cases position
  simp_all

/-- The source class's row/column orientation is a canonical representative:
equal symbols have the unique false orientation bit. -/
def classOrientation (row column : Nat) : Bool := decide (column < row)

theorem equal_symbol_orientation_is_false (symbol : Nat) :
    classOrientation symbol symbol = false := by
  simp [classOrientation]

theorem class_orientation_reconstructs (row column : Nat) :
    d3DecodeSymbolPair (min row column) (max row column)
      (classOrientation row column) = (row, column) := by
  exact d3_symbol_pair_roundtrip row column

def patternOfClass : List (Nat × Nat) → List (Nat × Nat)
  | [] => []
  | (row, column) :: rest =>
      (min row column, max row column) :: patternOfClass rest

/-- Only unequal symbol pairs carry an orientation bit. Equal pairs are
canonical and consume no bit. -/
def orientationsOfClass : List (Nat × Nat) → List Bool
  | [] => []
  | (row, column) :: rest =>
      if row = column then orientationsOfClass rest
      else classOrientation row column :: orientationsOfClass rest

def classOfPatternOrientations : List (Nat × Nat) → List Bool → List (Nat × Nat)
  | [], _ => []
  | (low, high) :: rest, orientations =>
      if low = high then
        (low, high) :: classOfPatternOrientations rest orientations
      else
        match orientations with
        | [] => []
        | orientation :: tail =>
            d3DecodeSymbolPair low high orientation ::
              classOfPatternOrientations rest tail

/-- Every row/column symbol word has exactly the stated canonical unordered
pattern and unequal-coordinate orientation representation. -/
theorem class_pattern_orientation_roundtrip (pairs : List (Nat × Nat)) :
    classOfPatternOrientations (patternOfClass pairs) (orientationsOfClass pairs) = pairs := by
  induction pairs with
  | nil => rfl
  | cons pair rest ih =>
      cases pair with
      | mk row column =>
          by_cases heq : row = column
          · subst column
            simp [patternOfClass, orientationsOfClass, classOfPatternOrientations,
              classOrientation, ih]
          · have hne : min row column ≠ max row column := by omega
            simp [patternOfClass, orientationsOfClass, classOfPatternOrientations,
              classOrientation, heq, hne, ih]
            rw [d3_symbol_pair_roundtrip row column]

#print axioms class_pattern_orientation_roundtrip

#print axioms encode_decode
#print axioms decode_encode
#print axioms equal_symbol_orientation_is_false
#print axioms class_orientation_reconstructs

end D3GlobalPacketAddress
