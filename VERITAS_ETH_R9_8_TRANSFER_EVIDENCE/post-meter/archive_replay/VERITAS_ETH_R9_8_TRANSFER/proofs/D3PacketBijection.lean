import D3SlotSplit
import D3SymbolPorts

/-! The directed-class padded-slot / packet-position bijection.

A directed class is one pair of label words, i.e. an element of
`allWordPairs r a`.  `lem:tensor-packets` pads every class to a common
multiple `H` of `L = 2^a`.  A padded slot is `(class, offset)` with
`offset < H`; a packet position is `(class, packet, copy)` with
`packet < H / L` and `copy < L`.

This module proves that `offset ↦ (offset / L, offset % L)` is a bijection
with inverse `(packet, copy) ↦ L * packet + copy`, that the slot and packet
counts agree exactly, that every packet holds exactly `L` slots, and that a
class with zero observed load still owns its full padded slot block.  It does
not construct the edge-to-class assignment or prove the manuscript's recursive
child construction; those remain open and are recorded in
`docs/R91_PACKET_BIJECTION.md`.
-/

namespace D3PacketBijection

/-- Split a padded offset into packet index and copy index. -/
def encodeOffset (L offset : Nat) : Nat × Nat := (offset / L, offset % L)

/-- Reassemble a padded offset from a packet index and a copy index. -/
def decodeOffset (L packet copy : Nat) : Nat := L * packet + copy

theorem encode_copy_bounded (L offset : Nat) (hL : 0 < L) :
    (encodeOffset L offset).2 < L := by
  simp only [encodeOffset]
  exact Nat.mod_lt offset hL

theorem decode_encode (L offset : Nat) :
    decodeOffset L (encodeOffset L offset).1 (encodeOffset L offset).2 = offset := by
  simp only [decodeOffset, encodeOffset]
  exact Nat.div_add_mod offset L

theorem encode_decode (L packet copy : Nat) (hL : 0 < L) (hc : copy < L) :
    encodeOffset L (decodeOffset L packet copy) = (packet, copy) := by
  obtain ⟨hdiv, hmod⟩ := d3_offset_address_inverse L packet copy hL hc
  simp only [encodeOffset, decodeOffset, hdiv, hmod]

theorem encode_injective (L left right : Nat)
    (h : encodeOffset L left = encodeOffset L right) : left = right := by
  have h1 := decode_encode L left
  rw [h] at h1
  exact h1.symm.trans (decode_encode L right)

/-- Every padded offset below a multiple of `L` is the image of exactly one
packet position. -/
theorem decode_surjective (L packets offset : Nat) (hL : 0 < L)
    (h : offset < packets * L) :
    ∃ packet copy, packet < packets ∧ copy < L ∧ decodeOffset L packet copy = offset := by
  refine ⟨offset / L, offset % L, ?_, Nat.mod_lt _ hL, ?_⟩
  · rw [Nat.div_lt_iff_lt_mul hL]; exact h
  · simp only [decodeOffset]
    exact Nat.div_add_mod offset L

/-- A packet holds exactly `L` padded slots. -/
theorem packet_capacity (L : Nat) :
    (List.range L).length = L ∧ ∀ copy, copy ∈ List.range L → copy < L := by
  refine ⟨List.length_range, ?_⟩
  intro copy hcopy
  exact List.mem_range.1 hcopy

/-- `r^(2*a)` directed classes padded to `H` each give exactly
`r^(2*a) * (H / L)` packets of `L` slots, with no slot left over. -/
theorem slot_packet_count (r a H L : Nat) (hdvd : L ∣ H) :
    r ^ (2 * a) * H = r ^ (2 * a) * (H / L) * L := by
  rw [Nat.mul_assoc, Nat.div_mul_cancel hdvd]

/-- The packet count is exact: dividing the padded block by `L` loses nothing. -/
theorem packet_count_exact (H L : Nat) (hdvd : L ∣ H) :
    (H / L) * L = H := Nat.div_mul_cancel hdvd

/-- A class with zero observed load still owns its full padded block, so the
slot map is total on every directed class, including empty ones. -/
theorem empty_class_still_padded (L H : Nat) (hL : 0 < L) (hpos : 0 < H) :
    0 < (H + L - 1) / L := by
  have hle : L ≤ H + L - 1 := by omega
  exact Nat.div_pos hle hL

/-- Distinct packet positions decode to distinct padded slots. -/
theorem packet_positions_distinct (L packet copy packet' copy' : Nat)
    (hL : 0 < L) (hc : copy < L) (hc' : copy' < L)
    (hne : (packet, copy) ≠ (packet', copy')) :
    decodeOffset L packet copy ≠ decodeOffset L packet' copy' := by
  intro heq
  apply hne
  have e := encode_decode L packet copy hL hc
  have e' := encode_decode L packet' copy' hL hc'
  rw [heq] at e
  rw [e] at e'
  exact e'

/-- A worked instance: `L = 2`, `H = 6` gives three packets of two slots. -/
example : (List.range 3).map (fun p => (List.range 2).map (fun c =>
    decodeOffset 2 p c)) = [[0, 1], [2, 3], [4, 5]] := by decide

example : (encodeOffset 2 5) = (2, 1) := by decide
example : decodeOffset 2 2 1 = 5 := by decide
example : (List.range 6).map (fun o => encodeOffset 2 o) =
    [(0, 0), (0, 1), (1, 0), (1, 1), (2, 0), (2, 1)] := by decide

/-- `lem:tensor-packets` accounting: the `M` edges occupy exactly `M` padded
slots out of the `D_arr * H_pad` available, and those slots regroup into
`D_arr * (H_pad / L)` packets of `L` slots.  The first conjunct is
`class_loads_sum`; the second is the padding bound; the third is
`slot_packet_count`. -/
theorem d3_edge_slot_accounting (r a : Nat) (hr : 0 < r)
    (edges : List PackingEdge) (delta : Nat)
    (hrow : ∀ vertex, rowDegreeOnList edges vertex ≤ delta)
    (hcol : ∀ vertex, columnDegreeOnList edges vertex ≤ delta)
    (hregime : 2 * (r ^ (2*a)) * (r ^ (2*a)) * delta ≤ edges.length)
    (hwidth : (2^a) * (r ^ (2*a)) ≤ edges.length) :
    let final := d3CanonicalRun r a hr edges (d3GraphVertices edges) emptyPackingAssignments
    let load := d3ClassLoad edges (d3PartialColor final a)
    let H := d3PaddedClassLoad (2^a) (d3MaxClassLoad (allWordPairs r a) load)
    sumBy (allWordPairs r a) load = edges.length ∧
      edges.length ≤ r ^ (2*a) * H ∧
      r ^ (2*a) * H = r ^ (2*a) * (H / 2^a) * (2^a) := by
  let final := d3CanonicalRun r a hr edges (d3GraphVertices edges) emptyPackingAssignments
  let load := d3ClassLoad edges (d3PartialColor final a)
  let H := d3PaddedClassLoad (2^a) (d3MaxClassLoad (allWordPairs r a) load)
  change sumBy (allWordPairs r a) load = edges.length ∧
    edges.length ≤ r ^ (2*a) * H ∧
    r ^ (2*a) * H = r ^ (2*a) * (H / 2^a) * (2^a)
  have hb := d3_generated_padded_load_bound r a hr edges delta hrow hcol hregime hwidth
  change (∀ c, c ∈ allWordPairs r a → load c ≤ H) ∧ (2^a) ∣ H ∧
    r ^ (2*a) * H ≤ 3 * edges.length at hb
  have hcount : ∀ e, e ∈ edges →
      sumBy (allWordPairs r a) (fun c =>
        if d3PartialColor final a e == c then 1 else 0) = 1 := by
    intro e he
    exact canonical_run_color_indicator_count r a hr edges (d3GraphVertices edges)
      (d3_graph_vertices_nodup edges) (d3_graph_vertices_cover edges)
      emptyPackingAssignments e he
  have hsum : sumBy (allWordPairs r a) load = edges.length :=
    class_loads_sum edges (d3PartialColor final a) (allWordPairs r a) hcount
  have hle : edges.length ≤ r ^ (2*a) * H := by
    rw [← hsum]
    calc
      sumBy (allWordPairs r a) load ≤ sumBy (allWordPairs r a) (fun _ => H) := by
        apply sumBy_le_of_pointwise
        intro c hc
        exact hb.1 c hc
      _ = (allWordPairs r a).length * H := sumBy_constant _ _
      _ = r ^ (2*a) * H := by rw [allWordPairs_length]
  exact ⟨hsum, hle, slot_packet_count r a H (2^a) hb.2.1⟩

#print axioms d3_edge_slot_accounting
#print axioms encode_copy_bounded
#print axioms decode_encode
#print axioms encode_decode
#print axioms encode_injective
#print axioms decode_surjective
#print axioms packet_capacity
#print axioms slot_packet_count
#print axioms packet_count_exact
#print axioms empty_class_still_padded
#print axioms packet_positions_distinct

end D3PacketBijection
