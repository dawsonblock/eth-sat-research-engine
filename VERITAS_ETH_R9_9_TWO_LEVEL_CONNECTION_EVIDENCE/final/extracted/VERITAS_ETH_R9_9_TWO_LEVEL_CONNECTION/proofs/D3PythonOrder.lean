import D3SymbolPorts

/-! A separate Lean model of the Python builder's vertex order.

The historical `d3GraphVertices` remains unchanged.  This model sorts the
distinct row IDs ascending, followed by the distinct column IDs ascending,
and retains the existing first-minimum label selector.  These theorems relate
the formal sorted-order program to the formal any-order port theorem; they do
not yet prove that CPython executes this model.
-/

def d3UniqueNatIds : List Nat → List Nat
  | [] => []
  | x :: xs =>
      let rest := d3UniqueNatIds xs
      if x ∈ rest then rest else x :: rest

theorem d3_unique_nat_ids_mem (xs : List Nat) (x : Nat) :
    x ∈ d3UniqueNatIds xs ↔ x ∈ xs := by
  induction xs generalizing x with
  | nil => simp [d3UniqueNatIds]
  | cons head tail ih =>
      simp only [d3UniqueNatIds]
      split <;> simp_all

theorem d3_unique_nat_ids_nodup (xs : List Nat) :
    (d3UniqueNatIds xs).Nodup := by
  induction xs with
  | nil => simp [d3UniqueNatIds]
  | cons head tail ih =>
      simp only [d3UniqueNatIds]
      split
      · exact ih
      · exact List.nodup_cons.mpr ⟨by assumption, ih⟩

theorem d3_pairwise_filter {α : Type} {R : α → α → Prop}
    (xs : List α) (hxs : xs.Pairwise R) (p : α → Bool) :
    (xs.filter p).Pairwise R := by
  induction xs with
  | nil => simp
  | cons x xs ih =>
      have h := List.pairwise_cons.mp hxs
      simp only [List.filter_cons]
      split
      · apply List.pairwise_cons.mpr
        exact ⟨fun y hy => h.1 y (List.mem_filter.mp hy).1, ih h.2⟩
      · exact ih h.2

theorem d3_unique_nat_ids_pairwise (xs : List Nat)
    (hxs : xs.Pairwise (· ≤ ·)) :
    (d3UniqueNatIds xs).Pairwise (· ≤ ·) := by
  induction xs with
  | nil => simp [d3UniqueNatIds]
  | cons x xs ih =>
      have h := List.pairwise_cons.mp hxs
      simp only [d3UniqueNatIds]
      split
      · exact ih h.2
      · apply List.pairwise_cons.mpr
        exact ⟨fun y hy => h.1 y ((d3_unique_nat_ids_mem _ _).mp hy), ih h.2⟩

def d3NatAscending (a b : Nat) : Bool := decide (a ≤ b)

def d3PythonSortedIds (ids : List Nat) : List Nat :=
  d3UniqueNatIds (ids.mergeSort d3NatAscending)

theorem d3_python_sorted_ids_mem (ids : List Nat) (x : Nat) :
    x ∈ d3PythonSortedIds ids ↔ x ∈ ids := by
  simp [d3PythonSortedIds, d3_unique_nat_ids_mem]

theorem d3_python_sorted_ids_nodup (ids : List Nat) :
    (d3PythonSortedIds ids).Nodup := by
  exact d3_unique_nat_ids_nodup _

theorem d3_python_sorted_ids_sorted (ids : List Nat) :
    (d3PythonSortedIds ids).Pairwise (· ≤ ·) := by
  apply d3_unique_nat_ids_pairwise
  have h := List.pairwise_mergeSort
    (le := d3NatAscending)
    (by intro a b c hab hbc; simp [d3NatAscending] at *; omega)
    (by intro a b; simp [d3NatAscending]; omega) ids
  simpa [d3NatAscending] using h

theorem d3_mergeSort_perm_extensionality {xs ys : List Nat}
    (hperm : List.Perm xs ys) :
    xs.mergeSort d3NatAscending = ys.mergeSort d3NatAscending := by
  apply List.Perm.eq_of_pairwise (fun a b _ _ hab hba => Nat.le_antisymm hab hba)
  · have h := List.pairwise_mergeSort
      (le := d3NatAscending)
      (by intro a b c hab hbc; simp [d3NatAscending] at *; omega)
      (by intro a b; simp [d3NatAscending]; omega) xs
    simpa [d3NatAscending] using h
  · have h := List.pairwise_mergeSort
      (le := d3NatAscending)
      (by intro a b c hab hbc; simp [d3NatAscending] at *; omega)
      (by intro a b; simp [d3NatAscending]; omega) ys
    simpa [d3NatAscending] using h
  · exact (List.mergeSort_perm xs d3NatAscending).trans
      (hperm.trans (List.mergeSort_perm ys d3NatAscending).symm)

theorem d3_python_sorted_ids_perm {xs ys : List Nat}
    (hperm : List.Perm xs ys) : d3PythonSortedIds xs = d3PythonSortedIds ys := by
  unfold d3PythonSortedIds
  rw [d3_mergeSort_perm_extensionality hperm]

def d3PythonRows (edges : List PackingEdge) : List PackingVertex :=
  (d3PythonSortedIds (edges.map Prod.fst)).map (fun id => (.row, id))

def d3PythonColumns (edges : List PackingEdge) : List PackingVertex :=
  (d3PythonSortedIds (edges.map Prod.snd)).map (fun id => (.col, id))

def d3PythonOrderedVertices (edges : List PackingEdge) : List PackingVertex :=
  d3PythonRows edges ++ d3PythonColumns edges

theorem d3_python_ordered_vertices_shape (edges : List PackingEdge) :
    d3PythonOrderedVertices edges = d3PythonRows edges ++ d3PythonColumns edges := rfl

theorem d3_python_ordered_vertices_nodup (edges : List PackingEdge) :
    (d3PythonOrderedVertices edges).Nodup := by
  rw [d3PythonOrderedVertices, List.nodup_append]
  refine ⟨?_, ?_, ?_⟩
  · change List.Pairwise (fun x y : PackingVertex => x ≠ y)
      ((d3PythonSortedIds (edges.map Prod.fst)).map fun id => (.row, id))
    exact List.Pairwise.map (fun id : Nat => (PackingSide.row, id))
      (fun x y hneq heq => hneq (by injection heq))
      (d3_python_sorted_ids_nodup _)
  · change List.Pairwise (fun x y : PackingVertex => x ≠ y)
      ((d3PythonSortedIds (edges.map Prod.snd)).map fun id => (.col, id))
    exact List.Pairwise.map (fun id : Nat => (PackingSide.col, id))
      (fun x y hneq heq => hneq (by injection heq))
      (d3_python_sorted_ids_nodup _)
  · intro v hv w hw heq
    have hvrow : v.1 = .row := by
      obtain ⟨id, _, rfl⟩ := List.mem_map.mp hv
      rfl
    have hwcol : w.1 = .col := by
      obtain ⟨id, _, rfl⟩ := List.mem_map.mp hw
      rfl
    have hside := congrArg Prod.fst heq
    simp [hvrow, hwcol] at hside

theorem d3_python_ordered_vertices_membership (edges : List PackingEdge)
    (v : PackingVertex) :
    v ∈ d3PythonOrderedVertices edges ↔
      (∃ id, id ∈ d3PythonSortedIds (edges.map Prod.fst) ∧ (.row, id) = v) ∨
      (∃ id, id ∈ d3PythonSortedIds (edges.map Prod.snd) ∧ (.col, id) = v) := by
  simp [d3PythonOrderedVertices, d3PythonRows, d3PythonColumns]

theorem d3_python_ordered_vertices_cover (edges : List PackingEdge) :
    d3VerticesCover edges (d3PythonOrderedVertices edges) := by
  intro e he
  have hr : e.1 ∈ edges.map Prod.fst := List.mem_map.mpr ⟨e, he, rfl⟩
  have hc : e.2 ∈ edges.map Prod.snd := List.mem_map.mpr ⟨e, he, rfl⟩
  constructor
  · rw [d3_python_ordered_vertices_membership]
    exact Or.inl ⟨e.1, (d3_python_sorted_ids_mem _ _).mpr hr, rfl⟩
  · rw [d3_python_ordered_vertices_membership]
    exact Or.inr ⟨e.2, (d3_python_sorted_ids_mem _ _).mpr hc, rfl⟩

theorem d3_python_ordered_vertices_edge_permutation
    {edges edges' : List PackingEdge} (hperm : List.Perm edges edges') :
    d3PythonOrderedVertices edges = d3PythonOrderedVertices edges' := by
  unfold d3PythonOrderedVertices d3PythonRows d3PythonColumns
  have hr := d3_python_sorted_ids_perm (List.Perm.map Prod.fst hperm)
  have hc := d3_python_sorted_ids_perm (List.Perm.map Prod.snd hperm)
  rw [hr, hc]

def d3PythonCanonicalTrace (r a : Nat) (hr : 0 < r)
    (edges : List PackingEdge) : List PackingVertex → PackingPartial →
      List (PackingVertex × List Nat × Nat)
  | [], _ => []
  | v :: vs, s =>
      let word := d3CanonicalWord r a hr edges s v
      (v, word, concreteD3ScoreCandidate s v r a edges word) ::
        d3PythonCanonicalTrace r a hr edges vs (d3AssignWord s v word)

def d3PythonOrderAuditEdges : List PackingEdge := [(0,0), (1,1), (0,1)]

def d3PythonOrderAuditVertices : List PackingVertex :=
  d3PythonOrderedVertices d3PythonOrderAuditEdges

def d3PythonOrderAuditRun : PackingPartial :=
  d3CanonicalRun 2 1 (by decide) d3PythonOrderAuditEdges
    d3PythonOrderAuditVertices emptyPackingAssignments

theorem d3_python_order_audit_fixture :
    d3PythonOrderAuditVertices = [(.row, 0), (.row, 1), (.col, 0), (.col, 1)] ∧
    [d3PythonOrderAuditRun (.row, 0) 0, d3PythonOrderAuditRun (.row, 1) 0,
     d3PythonOrderAuditRun (.col, 0) 0, d3PythonOrderAuditRun (.col, 1) 0] =
      [some 0, some 1, some 0, some 1] ∧
    (d3PythonCanonicalTrace 2 1 (by decide) d3PythonOrderAuditEdges
      d3PythonOrderAuditVertices emptyPackingAssignments).map
        (fun item => (item.1, item.2.1)) =
      [((.row, 0), [0]), ((.row, 1), [1]), ((.col, 0), [0]), ((.col, 1), [1])] ∧
    (d3PythonCanonicalTrace 2 1 (by decide) d3PythonOrderAuditEdges
      d3PythonOrderAuditVertices emptyPackingAssignments).map (fun item => item.2.2) =
      [22, 16, 16, 12] ∧
    concreteD3ScoreParent emptyPackingAssignments (.row, 0) 2 1
      d3PythonOrderAuditEdges = 22 ∧
    2^(2*1) * d3EdgeClassSquareSum d3PythonOrderAuditEdges
      (d3PartialColor d3PythonOrderAuditRun 1) = 12 := by
  have horder : d3PythonOrderAuditVertices =
      [(.row, 0), (.row, 1), (.col, 0), (.col, 1)] := by
    simp [d3PythonOrderAuditVertices, d3PythonOrderedVertices,
      d3PythonRows, d3PythonColumns, d3PythonSortedIds, d3UniqueNatIds,
      d3NatAscending, d3PythonOrderAuditEdges, List.mergeSort]
  refine ⟨horder, ?_, ?_, ?_, ?_, ?_⟩
  · unfold d3PythonOrderAuditRun d3CanonicalRun
    rw [horder]
    decide
  · unfold d3PythonCanonicalTrace
    rw [horder]
    decide
  · unfold d3PythonCanonicalTrace
    rw [horder]
    decide
  · decide
  · unfold d3PythonOrderAuditRun d3CanonicalRun
    rw [horder]
    decide

theorem d3_python_sorted_order_port_bound
    (r a : Nat) (hr : 0 < r) (edges : List PackingEdge) (delta : Nat)
    (hrow : ∀ vertex, rowDegreeOnList edges vertex ≤ delta)
    (hcol : ∀ vertex, columnDegreeOnList edges vertex ≤ delta)
    (hregime : 2*(r^(2*a))*(r^(2*a))*delta ≤ edges.length)
    (hwidth : (2^a)*(r^(2*a)) ≤ edges.length)
    (i symbol : Nat) (row : Bool) (hi : i < a) (hs : symbol < r) :
    let final := d3CanonicalRun r a hr edges
      (d3PythonOrderedVertices edges) emptyPackingAssignments
    r*d3SymbolPortCount edges (d3PartialColor final a) i symbol row ≤ 3*edges.length := by
  cases edges with
  | nil => simp [d3PythonOrderedVertices, d3PythonRows, d3PythonColumns,
      d3PythonSortedIds, d3UniqueNatIds, d3SymbolPortCount, sumBy]
  | cons e es =>
      have hcover := d3_python_ordered_vertices_cover (e :: es)
      have hn := d3_python_ordered_vertices_nodup (e :: es)
      cases hv : d3PythonOrderedVertices (e :: es) with
      | nil =>
          have hc := hcover e (by simp)
          rw [hv] at hc
          simp at hc
      | cons v vs =>
          rw [hv] at hn hcover
          have h := d3_any_order_symbol_port_bound r a hr (e :: es) v vs
            hn hcover delta hrow hcol hregime hwidth i symbol row hi hs
          simpa [hv] using h

/-- `lem:tensor-packets` padded-load bound instantiated at the sorted vertex
order CPython uses.  The order is distinct and covers every endpoint, so the
arbitrary-order theorem applies directly. -/
theorem d3_python_order_padded_bound (r a : Nat) (hr : 0 < r)
    (edges : List PackingEdge) (delta : Nat)
    (hrow : ∀ vertex, rowDegreeOnList edges vertex ≤ delta)
    (hcol : ∀ vertex, columnDegreeOnList edges vertex ≤ delta)
    (hregime : 2*(r^(2*a))*(r^(2*a))*delta ≤ edges.length)
    (hwidth : (2^a)*(r^(2*a)) ≤ edges.length) :
    let final := d3CanonicalRun r a hr edges (d3PythonOrderedVertices edges)
      emptyPackingAssignments
    let load := d3ClassLoad edges (d3PartialColor final a)
    let H := d3PaddedClassLoad (2^a) (d3MaxClassLoad (allWordPairs r a) load)
    (2^a) ∣ H ∧ r^(2*a)*H ≤ 3*edges.length := by
  cases edges with
  | nil =>
      have hz' : d3ClassLoad [] (d3PartialColor emptyPackingAssignments a) = fun _ => 0 := rfl
      have hz : d3MaxClassLoad (allWordPairs r a) (fun _ => 0) = 0 := d3MaxClassLoad_zero _
      have hpow : 0 < 2^a := Nat.pow_pos (by decide)
      have hd : (2^a - 1) / 2^a = 0 :=
        Nat.div_eq_of_lt (Nat.sub_lt hpow (by decide))
      simp [d3PythonOrderedVertices, d3PythonRows, d3PythonColumns, d3PythonSortedIds,
        d3UniqueNatIds, d3CanonicalRun, hz', hz, hd, d3PaddedClassLoad]
  | cons e es =>
      have hcover := d3_python_ordered_vertices_cover (e :: es)
      have hn := d3_python_ordered_vertices_nodup (e :: es)
      cases hv : d3PythonOrderedVertices (e :: es) with
      | nil =>
          have hc := hcover e (by simp)
          rw [hv] at hc
          simp at hc
      | cons v vs =>
          rw [hv] at hn hcover
          exact d3_any_order_padded_bound r a hr (e :: es) v vs hn hcover delta
            hrow hcol hregime hwidth

/-- `lem:tensor-packets`(1) at the sorted order: at most `3M/L` packets. -/
theorem d3_python_order_packet_count (r a : Nat) (hr : 0 < r)
    (edges : List PackingEdge) (delta : Nat)
    (hrow : ∀ vertex, rowDegreeOnList edges vertex ≤ delta)
    (hcol : ∀ vertex, columnDegreeOnList edges vertex ≤ delta)
    (hregime : 2*(r^(2*a))*(r^(2*a))*delta ≤ edges.length)
    (hwidth : (2^a)*(r^(2*a)) ≤ edges.length) :
    let final := d3CanonicalRun r a hr edges (d3PythonOrderedVertices edges)
      emptyPackingAssignments
    let load := d3ClassLoad edges (d3PartialColor final a)
    let H := d3PaddedClassLoad (2^a) (d3MaxClassLoad (allWordPairs r a) load)
    (2^a) * (r^(2*a) * (H / 2^a)) ≤ 3*edges.length := by
  let final := d3CanonicalRun r a hr edges (d3PythonOrderedVertices edges)
    emptyPackingAssignments
  let load := d3ClassLoad edges (d3PartialColor final a)
  let H := d3PaddedClassLoad (2^a) (d3MaxClassLoad (allWordPairs r a) load)
  change (2^a) * (r^(2*a) * (H / 2^a)) ≤ 3*edges.length
  have hb := d3_python_order_padded_bound r a hr edges delta hrow hcol hregime hwidth
  change (2^a) ∣ H ∧ r^(2*a)*H ≤ 3*edges.length at hb
  calc
    (2^a) * (r^(2*a) * (H / 2^a)) = r^(2*a) * ((2^a) * (H / 2^a)) := by ac_rfl
    _ = r^(2*a) * H := by rw [Nat.mul_div_cancel' hb.1]
    _ ≤ 3*edges.length := hb.2

#print axioms d3_python_order_packet_count
#print axioms d3_python_order_padded_bound

#print axioms d3_unique_nat_ids_mem
#print axioms d3_unique_nat_ids_nodup
#print axioms d3_python_sorted_ids_sorted
#print axioms d3_python_sorted_ids_perm
#print axioms d3_python_ordered_vertices_nodup
#print axioms d3_python_ordered_vertices_membership
#print axioms d3_python_ordered_vertices_cover
#print axioms d3_python_ordered_vertices_edge_permutation
#print axioms d3_python_order_audit_fixture
#print axioms d3_python_sorted_order_port_bound
