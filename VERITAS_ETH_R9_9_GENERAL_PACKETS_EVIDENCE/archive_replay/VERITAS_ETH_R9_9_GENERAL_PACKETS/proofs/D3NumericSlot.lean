import D3SlotSplit
import D3BinaryBits

namespace D3NumericSlot
open D3BinaryBits

theorem equal_count_le_length (mask : List Bool) : d3EqualCount mask ≤ mask.length := by
  induction mask with
  | nil => simp [d3EqualCount]
  | cons b tail ih => cases b <;> simp [d3EqualCount] at * <;> omega

theorem merge_length (mask copies orientations bits : List Bool)
    (h : d3MergeSlot mask copies orientations = some bits) :
    bits.length = mask.length := by
  induction mask generalizing copies orientations bits with
  | nil =>
    cases copies <;> cases orientations <;> simp [d3MergeSlot] at h
    subst bits
    rfl
  | cons equal tail ih =>
    cases equal with
    | false =>
      cases orientations with
      | nil => simp [d3MergeSlot] at h
      | cons bit orientations =>
        cases hm : d3MergeSlot tail copies orientations with
        | none => simp [d3MergeSlot, hm] at h
        | some remaining =>
          simp [d3MergeSlot, hm] at h
          subst bits
          simp [ih copies orientations remaining hm]
    | true =>
      cases copies with
      | nil => simp [d3MergeSlot] at h
      | cons bit copies =>
        cases hm : d3MergeSlot tail copies orientations with
        | none => simp [d3MergeSlot, hm] at h
        | some remaining =>
          simp [d3MergeSlot, hm] at h
          subst bits
          simp [ih copies orientations remaining hm]

theorem merge_exists (mask copies orientations : List Bool)
    (hc : copies.length = d3EqualCount mask)
    (ho : orientations.length + d3EqualCount mask = mask.length) :
    ∃ word, d3MergeSlot mask copies orientations = some word := by
  induction mask generalizing copies orientations with
  | nil =>
    cases copies <;> cases orientations <;> simp_all [d3EqualCount, d3MergeSlot]
  | cons equal tail ih =>
    cases equal with
    | false =>
      cases orientations with
      | nil =>
        have hb := equal_count_le_length tail
        simp [d3EqualCount] at ho
        omega
      | cons bit rest =>
        have hc' : copies.length = d3EqualCount tail := by simpa [d3EqualCount] using hc
        have ho' : rest.length + d3EqualCount tail = tail.length := by
          simp [d3EqualCount] at ho
          omega
        obtain ⟨word, hw⟩ := ih copies rest hc' ho'
        exact ⟨bit :: word, by simp [d3MergeSlot, hw]⟩
    | true =>
      cases copies with
      | nil => simp [d3EqualCount] at hc; omega
      | cons bit rest =>
        have hc' : rest.length = d3EqualCount tail := by
          simp [d3EqualCount] at hc
          omega
        have ho' : orientations.length + d3EqualCount tail = tail.length := by
          simp [d3EqualCount] at ho
          omega
        obtain ⟨word, hw⟩ := ih rest orientations hc' ho'
        exact ⟨bit :: word, by simp [d3MergeSlot, hw]⟩
/-- Encode an offset, using orientation bits for unequal coordinates and
little-endian copy bits for equal coordinates. -/
def encode (mask orientations : List Bool) (offset : Nat) : Option (Nat × Nat) :=
  let count := d3EqualCount mask
  let copies := 2 ^ count
  (d3MergeSlot mask (bits count (offset % copies)) orientations).map
    (fun slotBits => (offset / copies, value slotBits))

def decode (mask : List Bool) (packet slot : Nat) : Nat × List Bool :=
  let split := d3SplitSlot mask (bits mask.length slot)
  ((2 ^ d3EqualCount mask) * packet + value split.1, split.2)

theorem encode_exists (mask orientations : List Bool) (offset : Nat)
    (ho : orientations.length + d3EqualCount mask = mask.length) :
    ∃ packet slot, encode mask orientations offset = some (packet, slot) := by
  let copies := bits (d3EqualCount mask) (offset % (2 ^ d3EqualCount mask))
  have hc : copies.length = d3EqualCount mask := bits_length _ _
  obtain ⟨word, hw⟩ := merge_exists mask copies orientations hc ho
  exact ⟨offset / (2 ^ d3EqualCount mask), value word,
    by simp [encode, ← show copies = bits (d3EqualCount mask)
      (offset % (2 ^ d3EqualCount mask)) by rfl, hw]⟩

/-- Every emitted slot decodes to the original offset and orientations.
The existence lemma above establishes emission for a well-sized orientation
word, so the successful-encoding hypothesis is not an assumption of validity. -/
theorem decode_encode (mask orientations : List Bool) (offset packet slot : Nat)
    (h : encode mask orientations offset = some (packet, slot)) :
    decode mask packet slot = (offset, orientations) := by
  unfold encode at h
  let c := 2 ^ d3EqualCount mask
  let cs := bits (d3EqualCount mask) (offset % c)
  cases hm : d3MergeSlot mask cs orientations with
  | none => simp [c, cs, hm] at h
  | some word =>
    simp only [show d3MergeSlot mask (bits (d3EqualCount mask) (offset % (2 ^ d3EqualCount mask))) orientations = some word by simpa [c, cs] using hm,
      Option.map_some, Option.some.injEq, Prod.mk.injEq] at h
    rcases h with ⟨rfl, rfl⟩
    have hlen := merge_length mask cs orientations word hm
    have hsplit := d3_split_merge_slot mask cs orientations word hm
    have hbits : bits mask.length (value word) = word := by
      rw [← hlen]
      exact bits_value word
    have hc : 0 < c := Nat.pow_pos (by decide)
    have hval : value cs = offset % c := by
      apply value_bits
      exact Nat.mod_lt offset hc
    simp only [decode, hbits, hsplit]
    rw [hval]
    exact congrArg (fun n => (n, orientations)) (Nat.div_add_mod offset c)

/-- Every packet number and in-range numerical slot is recovered after
decoding and re-encoding, including equal-symbol copy bits. -/
theorem encode_decode (mask : List Bool) (packet slot : Nat)
    (hslot : slot < 2 ^ mask.length) :
    encode mask (decode mask packet slot).2 (decode mask packet slot).1 =
      some (packet, slot) := by
  let word := bits mask.length slot
  let split := d3SplitSlot mask word
  let c := 2 ^ d3EqualCount mask
  have hwlen : mask.length = word.length := by simp [word, bits_length]
  have hlens := d3_split_slot_lengths mask word hwlen
  have hc : 0 < c := Nat.pow_pos (by decide)
  have hcopy : value split.1 < c := by
    have hb := value_bound split.1
    simpa [c, split, hlens.1] using hb
  have hdiv := d3_offset_address_inverse c packet (value split.1) hc hcopy
  have hcopies : bits (d3EqualCount mask) (value split.1) = split.1 := by
    have hlen : split.1.length = d3EqualCount mask := by simpa [split] using hlens.1
    rw [← hlen]
    exact bits_value split.1
  have hmerge : d3MergeSlot mask split.1 split.2 = some word := by
    simpa [split] using d3_merge_split_slot mask word hwlen
  have hword : value word = slot := value_bits mask.length slot hslot
  change encode mask split.2 (c * packet + value split.1) = some (packet, slot)
  simp only [encode]
  change (d3MergeSlot mask (bits (d3EqualCount mask)
    ((c * packet + value split.1) % c)) split.2).map
      (fun slotBits => ((c * packet + value split.1) / c, value slotBits)) =
        some (packet, slot)
  rw [hdiv.1, hdiv.2, hcopies, hmerge]
  simp [hword]

/-- An in-range offset under a width-aligned padding height maps to an
in-range packet index and numerical slot. -/
theorem encode_bounds (mask orientations : List Bool) (offset packet slot height : Nat)
    (hpad : 2 ^ mask.length ∣ height) (hoff : offset < height)
    (h : encode mask orientations offset = some (packet, slot)) :
    packet < height / (2 ^ d3EqualCount mask) ∧ slot < 2 ^ mask.length := by
  let c := 2 ^ d3EqualCount mask
  have hc : 0 < c := Nat.pow_pos (by decide)
  have hdiv : c ∣ height :=
    Nat.dvd_trans (Nat.pow_dvd_pow 2 (equal_count_le_length mask)) hpad
  unfold encode at h
  cases hm : d3MergeSlot mask
      (bits (d3EqualCount mask) (offset % c)) orientations with
  | none => simp [c, hm] at h
  | some word =>
    simp only [show d3MergeSlot mask (bits (d3EqualCount mask)
      (offset % (2 ^ d3EqualCount mask))) orientations = some word by simpa [c] using hm,
      Option.map_some, Option.some.injEq, Prod.mk.injEq] at h
    rcases h with ⟨rfl, rfl⟩
    constructor
    · change offset / c < height / c
      apply (Nat.div_lt_iff_lt_mul hc).2
      rw [Nat.div_mul_cancel hdiv]
      exact hoff
    · have hlen := merge_length mask _ orientations word hm
      simpa [hlen] using value_bound word

/-- Decoding a valid packet index produces an offset inside the padded
height. The slot is interpreted through its least-significant width bits. -/
theorem decode_bounds (mask : List Bool) (packet slot height : Nat)
    (hpad : 2 ^ mask.length ∣ height)
    (hpacket : packet < height / (2 ^ d3EqualCount mask)) :
    (decode mask packet slot).1 < height := by
  let c := 2 ^ d3EqualCount mask
  let word := bits mask.length slot
  let split := d3SplitSlot mask word
  have hdiv : c ∣ height :=
    Nat.dvd_trans (Nat.pow_dvd_pow 2 (equal_count_le_length mask)) hpad
  have hlens := d3_split_slot_lengths mask word (by simp [word, bits_length])
  have hcopy : value split.1 < c := by
    have hb := value_bound split.1
    simpa [split, c, hlens.1] using hb
  have hp : packet < height / c := by simpa [c] using hpacket
  have hnext : packet + 1 ≤ height / c := by omega
  have hmul := Nat.mul_le_mul_left c hnext
  have htotal : c * (height / c) = height := by
    simpa [Nat.mul_comm] using Nat.div_mul_cancel hdiv
  have hb : c * packet + value split.1 < c * (packet + 1) := by
    rw [Nat.mul_add]
    simp only [Nat.mul_one]
    omega
  change c * packet + value split.1 < height
  exact Nat.lt_of_lt_of_le hb (by simpa [htotal] using hmul)

#print axioms merge_length
#print axioms merge_exists
#print axioms encode_exists
#print axioms decode_encode
#print axioms encode_decode
#print axioms encode_bounds
#print axioms decode_bounds

end D3NumericSlot
