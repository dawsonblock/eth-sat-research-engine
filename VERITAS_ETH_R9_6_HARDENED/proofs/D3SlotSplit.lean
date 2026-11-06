import Lean

/-! A binary slot word separates uniquely into orientation bits for unequal
symbol pairs and copy bits for equal symbol pairs. This is a local list model,
not yet a packet construction or refinement proof. -/

def d3SplitSlot : List Bool → List Bool → List Bool × List Bool
  | [], _ => ([], [])
  | _, [] => ([], [])
  | equal :: mask, bit :: bits =>
      let (copies, orientations) := d3SplitSlot mask bits
      if equal then (bit :: copies, orientations) else (copies, bit :: orientations)

def d3MergeSlot : List Bool → List Bool → List Bool → Option (List Bool)
  | [], [], [] => some []
  | [], _, _ => none
  | true :: mask, bit :: copies, orientations =>
      (d3MergeSlot mask copies orientations).map (fun bits => bit :: bits)
  | false :: mask, copies, bit :: orientations =>
      (d3MergeSlot mask copies orientations).map (fun bits => bit :: bits)
  | _, _, _ => none

theorem d3_merge_split_slot (mask bits : List Bool) (hlen : mask.length = bits.length) :
    d3MergeSlot mask (d3SplitSlot mask bits).1 (d3SplitSlot mask bits).2 = some bits := by
  induction mask generalizing bits with
  | nil =>
    cases bits with
    | nil => rfl
    | cons b bs => simp at hlen
  | cons equal mask ih =>
    cases bits with
    | nil => simp at hlen
    | cons bit bits =>
      have hlen' : mask.length = bits.length := by simpa using hlen
      have h := ih bits hlen'
      cases hsplit : d3SplitSlot mask bits with
      | mk copies orientations =>
        cases equal <;> simp [d3SplitSlot, d3MergeSlot, hsplit] at h ⊢ <;> simp [h]

theorem d3_split_merge_slot (mask copies orientations bits : List Bool)
    (hmerge : d3MergeSlot mask copies orientations = some bits) :
    d3SplitSlot mask bits = (copies, orientations) := by
  induction mask generalizing copies orientations bits with
  | nil =>
    cases copies <;> cases orientations <;> simp [d3MergeSlot] at hmerge
    subst bits
    rfl
  | cons equal mask ih =>
    cases equal with
    | false =>
      cases orientations with
      | nil => simp [d3MergeSlot] at hmerge
      | cons bit orientations =>
        simp only [d3MergeSlot] at hmerge
        cases hm : d3MergeSlot mask copies orientations with
        | none => simp [hm] at hmerge
        | some tail =>
          simp [hm] at hmerge
          subst bits
          have ht := ih copies orientations tail hm
          simp [d3SplitSlot, ht]
    | true =>
      cases copies with
      | nil => simp [d3MergeSlot] at hmerge
      | cons bit copies =>
        simp only [d3MergeSlot] at hmerge
        cases hm : d3MergeSlot mask copies orientations with
        | none => simp [hm] at hmerge
        | some tail =>
          simp [hm] at hmerge
          subst bits
          have ht := ih copies orientations tail hm
          simp [d3SplitSlot, ht]

#print axioms d3_merge_split_slot
#print axioms d3_split_merge_slot

example : d3SplitSlot [true, false, true] [false, true, true] = ([false, true], [true]) := by decide
example : d3MergeSlot [true, false, true] [false, true] [true] = some [false, true, true] := by decide
example : d3MergeSlot [true, false, true] [false] [true] = none := by decide

def d3EqualCount : List Bool → Nat
  | [] => 0
  | equal :: mask => (if equal then 1 else 0) + d3EqualCount mask

theorem d3_split_slot_lengths (mask bits : List Bool) (hlen : mask.length = bits.length) :
    (d3SplitSlot mask bits).1.length = d3EqualCount mask ∧
    (d3SplitSlot mask bits).2.length + d3EqualCount mask = mask.length := by
  induction mask generalizing bits with
  | nil => cases bits <;> simp_all [d3SplitSlot, d3EqualCount]
  | cons equal mask ih =>
    cases bits with
    | nil => simp at hlen
    | cons bit bits =>
      have hlen' : mask.length = bits.length := by simpa using hlen
      have h := ih bits hlen'
      cases hsplit : d3SplitSlot mask bits with
      | mk copies orientations =>
        cases equal <;> simp [d3SplitSlot, d3EqualCount, hsplit] at h ⊢ <;> omega

#print axioms d3_split_slot_lengths

/- Within one directed class, split its padded offset into packet index and
copy index. These are arithmetic address lemmas, not the complete packet
bijection across distinct directed classes. -/
theorem d3_offset_address_bounded (q packets offset : Nat) (hq : 0 < q)
    (h : offset < packets*q) :
    offset/q < packets ∧ offset%q < q := by
  exact ⟨(Nat.div_lt_iff_lt_mul hq).2 h, Nat.mod_lt _ hq⟩

theorem d3_offset_address_injective (q left right : Nat)
    (hdiv : left/q = right/q) (hmod : left%q = right%q) : left = right := by
  have hl := Nat.mod_add_div left q
  have hr := Nat.mod_add_div right q
  rw [hdiv, hmod] at hl
  omega

theorem d3_offset_address_inverse (q packet copy : Nat) (hq : 0 < q) (hc : copy < q) :
    (q*packet+copy)/q = packet ∧ (q*packet+copy)%q = copy := by
  constructor
  · rw [Nat.mul_add_div hq, Nat.div_eq_of_lt hc]
    simp
  · rw [Nat.mul_add_mod, Nat.mod_eq_of_lt hc]

#print axioms d3_offset_address_bounded
#print axioms d3_offset_address_injective
#print axioms d3_offset_address_inverse

/- One coordinate's orientation. Equal-symbol coordinates do not carry an
orientation bit; their free slot bit is accounted for by d3SplitSlot. -/
def d3DecodeSymbolPair (low high : Nat) (orientation : Bool) : Nat × Nat :=
  if orientation then (high, low) else (low, high)

theorem d3_symbol_pair_roundtrip (row column : Nat) :
    d3DecodeSymbolPair (min row column) (max row column) (decide (column < row)) =
      (row, column) := by
  by_cases h : row ≤ column
  · have hn : ¬ column < row := by omega
    simp [d3DecodeSymbolPair, h, hn, Nat.min_eq_left, Nat.max_eq_right]
  · have hr : column ≤ row := by omega
    have ht : column < row := by omega
    simp [d3DecodeSymbolPair, hr, ht, Nat.min_eq_right, Nat.max_eq_left]

theorem d3_unequal_pair_orientation (low high : Nat) (orientation : Bool)
    (h : low < high) :
    let p := d3DecodeSymbolPair low high orientation
    (min p.1 p.2, max p.1 p.2) = (low, high) ∧
      decide (p.2 < p.1) = orientation := by
  cases orientation <;> simp [d3DecodeSymbolPair, Nat.min_eq_left, Nat.min_eq_right,
    Nat.max_eq_left, Nat.max_eq_right, Nat.le_of_lt h, h,
    Nat.not_lt_of_ge (Nat.le_of_lt h)]

#print axioms d3_symbol_pair_roundtrip
#print axioms d3_unequal_pair_orientation

theorem d3_merge_unique_components (mask copies₁ copies₂ orient₁ orient₂ bits : List Bool)
    (h₁ : d3MergeSlot mask copies₁ orient₁ = some bits)
    (h₂ : d3MergeSlot mask copies₂ orient₂ = some bits) :
    copies₁ = copies₂ ∧ orient₁ = orient₂ := by
  have hleft := d3_split_merge_slot mask copies₁ orient₁ bits h₁
  have hright := d3_split_merge_slot mask copies₂ orient₂ bits h₂
  rw [hleft] at hright
  cases hright
  exact ⟨rfl, rfl⟩

#print axioms d3_merge_unique_components
