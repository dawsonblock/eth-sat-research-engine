import D3FullPacketModel
import D3FirstMinimum
import D3PaddedConstruction

/-! Explicit contracts for the R9.3 Lean models. These statements do not
assert that CPython or C++ has been formally refined to those models. -/

open D3FullPacketModel

theorem r93_real_edge_packet_contract (classes : List SymbolClass)
    (width height edgeId : Nat)
    (hwidth : ∀ cls, cls ∈ classes → cls.length = width)
    (hpad : 2 ^ width ∣ height)
    (hload : ∀ cls, D3OccurrenceRank.countClass cls classes ≤ height)
    (hedge : edgeId < classes.length) :
    ∃ address, encodeEdge classes edgeId = some address ∧
      ValidPaddedAddress width height address ∧
      decodeEdge classes address = some edgeId ∧
      (∀ other, encodeEdge classes other = some address → other = edgeId) := by
  obtain ⟨address, he⟩ := encodeEdge_exists classes edgeId hedge
  refine ⟨address, he, encodeEdge_valid classes width height edgeId address
    hwidth hpad hload he, decodeEdge_encodeEdge classes edgeId address he, ?_⟩
  intro other ho
  exact encodeEdge_injective classes other edgeId address ho he

theorem r93_occupied_packet_contract (classes : List SymbolClass)
    (width height : Nat) (address : Address) (edgeId : Nat)
    (h : ValidPaddedAddress width height address) :
    decodeEdge classes address = some edgeId ↔ encodeEdge classes edgeId = some address := by
  obtain ⟨hlen, hc, _, hslot⟩ := h
  have hs : address.slot < 2 ^ address.pattern.length := by simpa [hlen] using hslot
  exact ⟨fun hd => encodeEdge_decodeEdge classes address edgeId hc hs hd,
    fun he => decodeEdge_encodeEdge classes edgeId address he⟩

theorem r93_padded_slot_contract (width height : Nat) (address : Address)
    (hpad : 2 ^ width ∣ height) (h : ValidPaddedAddress width height address) :
    (decodeClass address).2 < height ∧
      encodeClass (decodeClass address).1 (decodeClass address).2 = some address :=
  paddedClass_reverse width height address hpad h

theorem r93_first_minimum_contract (r a : Nat) (hr : 0 < r)
    (edges : List PackingEdge) (s : PackingPartial) (v : PackingVertex) :
    let words := labelWords r a
    let score := concreteD3ScoreCandidate s v r a edges
    ∃ i, ∃ hi : i < words.length,
      d3CanonicalWord r a hr edges s v = words[i] ∧
      (∀ j, ∀ hj : j < words.length, score words[i] ≤ score words[j]) ∧
      (∀ j, ∀ hj : j < i, score words[i] < score (words[j]'(by omega))) :=
  d3_canonical_word_first_minimum r a hr edges s v

#print axioms r93_real_edge_packet_contract
#print axioms r93_occupied_packet_contract
#print axioms r93_padded_slot_contract
#print axioms r93_first_minimum_contract

theorem r93_constructed_edge_contract (classes : List SymbolClass) (width edgeId : Nat)
    (hwidth : ∀ cls, cls ∈ classes → cls.length = width)
    (hedge : edgeId < classes.length) :
    ∃ address, encodeEdge classes edgeId = some address ∧
      ValidPaddedAddress width (D3PaddedConstruction.paddedHeight classes width) address ∧
      decodeEdge classes address = some edgeId ∧
      (∀ other, encodeEdge classes other = some address → other = edgeId) :=
  D3PaddedConstruction.constructed_real_edge_contract classes width edgeId hwidth hedge

#print axioms r93_constructed_edge_contract
