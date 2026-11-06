import D3FullPacketModel

namespace D3PaddedConstruction
open D3FullPacketModel D3OccurrenceRank

def maxOver {α : Type} (f : α → Nat) : List α → Nat
  | [] => 0
  | x :: xs => max (f x) (maxOver f xs)

theorem member_le_max {α : Type} (f : α → Nat) (xs : List α) (x : α)
    (hx : x ∈ xs) : f x ≤ maxOver f xs := by
  induction xs with
  | nil => simp at hx
  | cons y ys ih =>
    rcases List.mem_cons.mp hx with heq | hmem
    · subst x
      exact Nat.le_max_left _ _
    · exact Nat.le_trans (ih hmem) (Nat.le_max_right _ _)

theorem absent_count_zero {α : Type} [DecidableEq α] (xs : List α) (x : α)
    (hx : x ∉ xs) : countClass x xs = 0 := by
  induction xs with
  | nil => rfl
  | cons y ys ih =>
    have hne : y ≠ x := by intro h; apply hx; simp [h]
    have hnot : x ∉ ys := by intro h; apply hx; simp [h]
    simp [countClass, hne, ih hnot]

def maxLoad (classes : List SymbolClass) : Nat := maxOver (fun c => countClass c classes) classes

theorem load_le_max (classes : List SymbolClass) (cls : SymbolClass) :
    countClass cls classes ≤ maxLoad classes := by
  by_cases hm : cls ∈ classes
  · exact member_le_max (fun c => countClass c classes) classes cls hm
  · rw [absent_count_zero classes cls hm]
    exact Nat.zero_le _

def paddedHeight (classes : List SymbolClass) (width : Nat) : Nat :=
  ((maxLoad classes + 2 ^ width - 1) / (2 ^ width)) * (2 ^ width)

theorem height_divisible (classes : List SymbolClass) (width : Nat) :
    2 ^ width ∣ paddedHeight classes width := by
  exact ⟨(maxLoad classes + 2 ^ width - 1) / (2 ^ width), Nat.mul_comm _ _⟩

theorem max_le_height (classes : List SymbolClass) (width : Nat) :
    maxLoad classes ≤ paddedHeight classes width := by
  have hp : 0 < 2 ^ width := Nat.two_pow_pos width
  have hr := Nat.mod_lt (maxLoad classes + 2 ^ width - 1) hp
  have he := Nat.mod_add_div (maxLoad classes + 2 ^ width - 1) (2 ^ width)
  simp only [Nat.mul_comm (2 ^ width)] at he
  unfold paddedHeight
  omega

theorem height_lt_max_add_width (classes : List SymbolClass) (width : Nat) :
    paddedHeight classes width < maxLoad classes + 2 ^ width := by
  have hp : 0 < 2 ^ width := Nat.two_pow_pos width
  have he := Nat.mod_add_div (maxLoad classes + 2 ^ width - 1) (2 ^ width)
  simp only [Nat.mul_comm (2 ^ width)] at he
  unfold paddedHeight
  omega

theorem empty_height (width : Nat) : paddedHeight [] width = 0 := by
  have hp : 0 < 2 ^ width := Nat.two_pow_pos width
  have hlt : 2 ^ width - 1 < 2 ^ width := by omega
  simp [paddedHeight, maxLoad, maxOver, Nat.div_eq_of_lt hlt]

/-- The padding premises are derived from the computed maximum, rather than
assumed. Common label width is the only structural premise of this model. -/
theorem constructed_real_edge_contract (classes : List SymbolClass) (width edgeId : Nat)
    (hwidth : ∀ cls, cls ∈ classes → cls.length = width)
    (hedge : edgeId < classes.length) :
    ∃ address, encodeEdge classes edgeId = some address ∧
      ValidPaddedAddress width (paddedHeight classes width) address ∧
      decodeEdge classes address = some edgeId ∧
      (∀ other, encodeEdge classes other = some address → other = edgeId) := by
  obtain ⟨address, he⟩ := encodeEdge_exists classes edgeId hedge
  have hload : ∀ cls, countClass cls classes ≤ paddedHeight classes width := by
    intro cls
    exact Nat.le_trans (load_le_max classes cls) (max_le_height classes width)
  exact ⟨address, he, encodeEdge_valid classes width (paddedHeight classes width)
    edgeId address hwidth (height_divisible classes width) hload he,
    decodeEdge_encodeEdge classes edgeId address he,
    fun other ho => encodeEdge_injective classes other edgeId address ho he⟩

#print axioms member_le_max
#print axioms absent_count_zero
#print axioms load_le_max
#print axioms height_divisible
#print axioms max_le_height
#print axioms height_lt_max_add_width
#print axioms empty_height
#print axioms constructed_real_edge_contract
end D3PaddedConstruction
