import D3SymbolPorts
import D3PythonOrder
import D3SlotSplit

/-! Separately stated contracts for central packing sublemmas. This checks
that the imported theorems are usable at these exact types, not that their
definitions refine Python or the entire source packing lemma. -/

theorem r9_checked_any_order_port_contract (r a : Nat) (hr : 0 < r)
    (edges : List PackingEdge) (v : PackingVertex) (vs : List PackingVertex)
    (hn : (v :: vs).Nodup) (hcover : d3VerticesCover edges (v :: vs))
    (delta : Nat) (hrow : ∀ vertex, rowDegreeOnList edges vertex ≤ delta)
    (hcol : ∀ vertex, columnDegreeOnList edges vertex ≤ delta)
    (hregime : 2*(r^(2*a))*(r^(2*a))*delta ≤ edges.length)
    (hwidth : (2^a)*(r^(2*a)) ≤ edges.length)
    (i symbol : Nat) (row : Bool) (hi : i < a) (hs : symbol < r) :
    let final := d3CanonicalRun r a hr edges (v :: vs) emptyPackingAssignments
    r*d3SymbolPortCount edges (d3PartialColor final a) i symbol row ≤ 3*edges.length := by
  exact d3_any_order_symbol_port_bound r a hr edges v vs hn hcover delta hrow hcol
    hregime hwidth i symbol row hi hs

theorem r9_checked_generated_group_contract (a : Nat)
    (edges : List PackingEdge) (delta : Nat)
    (hrow : ∀ vertex, rowDegreeOnList edges vertex ≤ delta)
    (hcol : ∀ vertex, columnDegreeOnList edges vertex ≤ delta)
    (hregime : 2*(64^(2*a))*(64^(2*a))*delta ≤ edges.length)
    (hwidth : (2^a)*(64^(2*a)) ≤ edges.length)
    (i symbol : Nat) (hi : i < a) (hs : symbol < 64) (hM : 0 < edges.length) :
    let final := d3CanonicalRun 64 a (by decide) edges (d3GraphVertices edges) emptyPackingAssignments
    let color := d3PartialColor final a
    32*(d3SymbolPortCount edges color i symbol true +
        d3SymbolPortCount edges color i symbol false) ≤ 3*edges.length ∧
    8*(d3SymbolPortCount edges color i symbol true +
       d3SymbolPortCount edges color i symbol false) < edges.length := by
  exact d3_generated_group_half_wire_shrink a edges delta hrow hcol hregime hwidth i symbol hi hs hM

theorem r9_checked_slot_roundtrip_contract (mask bits : List Bool)
    (hlen : mask.length = bits.length) :
    d3MergeSlot mask (d3SplitSlot mask bits).1 (d3SplitSlot mask bits).2 = some bits := by
  exact d3_merge_split_slot mask bits hlen

theorem r9_checked_class_offset_contract (q packet copy : Nat)
    (hq : 0 < q) (hc : copy < q) :
    (q*packet+copy)/q = packet ∧ (q*packet+copy)%q = copy := by
  exact d3_offset_address_inverse q packet copy hq hc

theorem r9_checked_python_sorted_port_contract
    (r a : Nat) (hr : 0 < r) (edges : List PackingEdge) (delta : Nat)
    (hrow : ∀ vertex, rowDegreeOnList edges vertex ≤ delta)
    (hcol : ∀ vertex, columnDegreeOnList edges vertex ≤ delta)
    (hregime : 2*(r^(2*a))*(r^(2*a))*delta ≤ edges.length)
    (hwidth : (2^a)*(r^(2*a)) ≤ edges.length)
    (i symbol : Nat) (row : Bool) (hi : i < a) (hs : symbol < r) :
    let final := d3CanonicalRun r a hr edges
      (d3PythonOrderedVertices edges) emptyPackingAssignments
    r*d3SymbolPortCount edges (d3PartialColor final a) i symbol row ≤ 3*edges.length := by
  exact d3_python_sorted_order_port_bound r a hr edges delta hrow hcol
    hregime hwidth i symbol row hi hs

#print axioms r9_checked_any_order_port_contract
#print axioms r9_checked_generated_group_contract
#print axioms r9_checked_slot_roundtrip_contract
#print axioms r9_checked_class_offset_contract
#print axioms r9_checked_python_sorted_port_contract
