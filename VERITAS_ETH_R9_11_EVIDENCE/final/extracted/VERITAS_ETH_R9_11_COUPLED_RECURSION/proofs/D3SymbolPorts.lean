import D3VarianceAlgebra

/-! Symbol-frequency and port bounds for the *Lean-generated* labeling.

The theorem counts real edge incidences directly, with multiplicity for
parallel edges. The two source packing inequalities and degree hypotheses
imply the port bounds, and for radix 64 imply a half-wire count below M/8.
No packet-slot construction, child-network identity, or Python refinement
is asserted here. -/

def wordSymbolCount (r a i symbol : Nat) : Nat :=
  sumBy (labelWords r a) (fun word => if word[i]? == some symbol then 1 else 0)

theorem word_symbol_count (r a i symbol : Nat)
    (hi : i < a) (hs : symbol < r) :
    wordSymbolCount r a i symbol = r ^ (a - 1) := by
  induction a generalizing i with
  | zero => omega
  | succ a ih =>
    cases i with
    | zero =>
      unfold wordSymbolCount
      simp only [labelWords, sumBy_flatMap]
      calc
        _ = sumBy (List.range r) (fun x => if x == symbol then r^a else 0) := by
          apply sumBy_congr
          intro x hx
          rw [sumBy_map]
          by_cases heq : x = symbol
          · subst x
            simp [sumBy_constant, labelWords_length]
          · simp [heq, sumBy_zero]
        _ = r^a := by simpa [hs] using sumBy_range_eq r symbol (r^a)
        _ = r ^ (a + 1 - 1) := by simp
    | succ i =>
      unfold wordSymbolCount
      simp only [labelWords, sumBy_flatMap]
      calc
        _ = sumBy (List.range r) (fun _ => wordSymbolCount r a i symbol) := by
          apply sumBy_congr
          intro x hx
          rw [sumBy_map]
          rfl
        _ = r * wordSymbolCount r a i symbol := sumBy_range_const r _
        _ = r * r^(a-1) := by rw [ih i (by omega)]
        _ = r^(a+1-1) := by
          rw [Nat.mul_comm, ← Nat.pow_succ]
          congr 1 <;> omega

#print axioms word_symbol_count

def colorSymbolCount (r a i symbol : Nat) (row : Bool) : Nat :=
  sumBy (allWordPairs r a) (fun c =>
    if (if row then c.1 else c.2)[i]? == some symbol then 1 else 0)

theorem color_symbol_count (r a i symbol : Nat) (row : Bool)
    (hi : i < a) (hs : symbol < r) :
    colorSymbolCount r a i symbol row = r ^ (a-1) * r ^ a := by
  unfold colorSymbolCount allWordPairs
  rw [sumBy_flatMap]
  cases row with
  | false =>
      have hinner : ∀ left, left ∈ labelWords r a →
          sumBy ((labelWords r a).map (fun right => (left, right)))
            (fun c => if (if false then c.1 else c.2)[i]? == some symbol then 1 else 0)
              = wordSymbolCount r a i symbol := by
        intro left _
        rw [sumBy_map]
        rfl
      calc
        _ = sumBy (labelWords r a) (fun _ => wordSymbolCount r a i symbol) := by
          apply sumBy_congr
          exact hinner
        _ = (labelWords r a).length * wordSymbolCount r a i symbol := sumBy_constant _ _
        _ = r ^ (a-1) * r ^ a := by rw [labelWords_length, word_symbol_count r a i symbol hi hs, Nat.mul_comm]
  | true =>
      calc
        _ = sumBy (labelWords r a) (fun left =>
            if left[i]? == some symbol then r^a else 0) := by
          apply sumBy_congr
          intro left _
          rw [sumBy_map]
          by_cases h : left[i]? == some symbol
          · simp [h, sumBy_constant, labelWords_length]
          · simp [h, sumBy_zero]
        _ = wordSymbolCount r a i symbol * r^a := sumBy_if_constant _ _ _
        _ = r ^ (a-1) * r ^ a := by rw [word_symbol_count r a i symbol hi hs]

theorem color_symbol_scaled_count (r a i symbol : Nat) (row : Bool)
    (hi : i < a) (hs : symbol < r) :
    r * colorSymbolCount r a i symbol row = r ^ (2*a) := by
  rw [color_symbol_count r a i symbol row hi hs]
  have ha : 1 ≤ a := by omega
  calc
    r * (r^(a-1) * r^a) = (r^(a-1)*r) * r^a := by ac_rfl
    _ = r^a * r^a := by rw [← Nat.pow_succ]; congr 2 <;> omega
    _ = r^(2*a) := by rw [← Nat.pow_add]; congr 1 <;> omega

#print axioms color_symbol_count
#print axioms color_symbol_scaled_count

def d3ColorHasSymbol (i symbol : Nat) (row : Bool) (c : D3EdgeColor) : Bool :=
  (if row then c.1 else c.2)[i]? == some symbol

def d3SymbolPortCount (edges : List PackingEdge) (color : PackingEdge → D3EdgeColor)
    (i symbol : Nat) (row : Bool) : Nat :=
  sumBy edges (fun e => if d3ColorHasSymbol i symbol row (color e) then 1 else 0)

theorem d3_symbol_loads_equal_ports (edges : List PackingEdge)
    (color : PackingEdge → D3EdgeColor) (classes : List D3EdgeColor)
    (i symbol : Nat) (row : Bool)
    (hcount : ∀ e, e ∈ edges →
      sumBy classes (fun c => if color e == c then 1 else 0) = 1) :
    sumBy classes (fun c => if d3ColorHasSymbol i symbol row c then
      d3ClassLoad edges color c else 0) = d3SymbolPortCount edges color i symbol row := by
  calc
    _ = sumBy classes (fun c => sumBy edges (fun e =>
        if d3ColorHasSymbol i symbol row c && (color e == c) then 1 else 0)) := by
      apply sumBy_congr
      intro c hc
      by_cases hp : d3ColorHasSymbol i symbol row c
      · simp [hp, d3ClassLoad]
      · simp [hp, sumBy_zero]
    _ = sumBy edges (fun e => sumBy classes (fun c =>
        if d3ColorHasSymbol i symbol row c && (color e == c) then 1 else 0)) := by
      rw [sumBy_swap]
    _ = sumBy edges (fun e => if d3ColorHasSymbol i symbol row (color e) then 1 else 0) := by
      apply sumBy_congr
      intro e he
      have hinner : sumBy classes (fun c =>
          if d3ColorHasSymbol i symbol row c && (color e == c) then 1 else 0) =
          sumBy classes (fun c => if color e == c then
            (if d3ColorHasSymbol i symbol row (color e) then 1 else 0) else 0) := by
        apply sumBy_congr
        intro c hc
        by_cases h : color e = c
        · subst c
          simp
        · simp [h]
      rw [hinner, sumBy_if_constant, hcount e he]
      simp
    _ = d3SymbolPortCount edges color i symbol row := rfl

theorem d3_symbol_port_bound_from_padded_classes
    (r a : Nat) (edges : List PackingEdge) (color : PackingEdge → D3EdgeColor)
    (i symbol H : Nat) (row : Bool) (hi : i < a) (hs : symbol < r)
    (hcount : ∀ e, e ∈ edges →
      sumBy (allWordPairs r a) (fun c => if color e == c then 1 else 0) = 1)
    (hload : ∀ c, c ∈ allWordPairs r a → d3ClassLoad edges color c ≤ H)
    (hpad : r^(2*a)*H ≤ 3*edges.length) :
    r*d3SymbolPortCount edges color i symbol row ≤ 3*edges.length := by
  have hpoint : ∀ c, c ∈ allWordPairs r a →
      (if d3ColorHasSymbol i symbol row c then d3ClassLoad edges color c else 0) ≤
      (if d3ColorHasSymbol i symbol row c then H else 0) := by
    intro c hc
    by_cases hp : d3ColorHasSymbol i symbol row c
    · simpa [hp] using hload c hc
    · simp [hp]
  have hsum := sumBy_le_of_pointwise (allWordPairs r a) _ _ hpoint
  rw [d3_symbol_loads_equal_ports edges color (allWordPairs r a) i symbol row hcount] at hsum
  rw [sumBy_if_constant] at hsum
  change d3SymbolPortCount edges color i symbol row ≤ colorSymbolCount r a i symbol row * H at hsum
  have hm := Nat.mul_le_mul_left r hsum
  calc
    r*d3SymbolPortCount edges color i symbol row ≤ r*(colorSymbolCount r a i symbol row*H) := hm
    _ = (r*colorSymbolCount r a i symbol row)*H := by ac_rfl
    _ = r^(2*a)*H := by rw [color_symbol_scaled_count r a i symbol row hi hs]
    _ ≤ 3*edges.length := hpad

theorem d3_generated_symbol_port_bound (r a : Nat) (hr : 0 < r)
    (edges : List PackingEdge) (delta : Nat)
    (hrow : ∀ vertex, rowDegreeOnList edges vertex ≤ delta)
    (hcol : ∀ vertex, columnDegreeOnList edges vertex ≤ delta)
    (hregime : 2 * (r^(2*a)) * (r^(2*a)) * delta ≤ edges.length)
    (hwidth : (2^a) * (r^(2*a)) ≤ edges.length)
    (i symbol : Nat) (row : Bool) (hi : i < a) (hs : symbol < r) :
    let final := d3CanonicalRun r a hr edges (d3GraphVertices edges) emptyPackingAssignments
    r*d3SymbolPortCount edges (d3PartialColor final a) i symbol row ≤ 3*edges.length := by
  let final := d3CanonicalRun r a hr edges (d3GraphVertices edges) emptyPackingAssignments
  let color := d3PartialColor final a
  let maximum := d3MaxClassLoad (allWordPairs r a) (d3ClassLoad edges color)
  let H := d3PaddedClassLoad (2^a) maximum
  have hb := d3_generated_padded_load_bound r a hr edges delta hrow hcol hregime hwidth
  change (∀ c, c ∈ allWordPairs r a → d3ClassLoad edges color c ≤ H) ∧
    (2^a) ∣ H ∧ r^(2*a)*H ≤ 3*edges.length at hb
  have hcount : ∀ e, e ∈ edges →
      sumBy (allWordPairs r a) (fun c => if color e == c then 1 else 0) = 1 := by
    intro e he
    exact canonical_run_color_indicator_count r a hr edges (d3GraphVertices edges)
      (d3_graph_vertices_nodup edges) (d3_graph_vertices_cover edges) emptyPackingAssignments e he
  exact d3_symbol_port_bound_from_padded_classes r a edges color i symbol H row hi hs hcount hb.1 hb.2.2

#print axioms d3_symbol_loads_equal_ports
#print axioms d3_symbol_port_bound_from_padded_classes
#print axioms d3_generated_symbol_port_bound

theorem d3_generated_group_half_wire_shrink (a : Nat)
    (edges : List PackingEdge) (delta : Nat)
    (hrow : ∀ vertex, rowDegreeOnList edges vertex ≤ delta)
    (hcol : ∀ vertex, columnDegreeOnList edges vertex ≤ delta)
    (hregime : 2 * (64^(2*a)) * (64^(2*a)) * delta ≤ edges.length)
    (hwidth : (2^a) * (64^(2*a)) ≤ edges.length)
    (i symbol : Nat) (hi : i < a) (hs : symbol < 64)
    (hM : 0 < edges.length) :
    let final := d3CanonicalRun 64 a (by decide) edges (d3GraphVertices edges) emptyPackingAssignments
    let color := d3PartialColor final a
    32*(d3SymbolPortCount edges color i symbol true +
        d3SymbolPortCount edges color i symbol false) ≤ 3*edges.length ∧
    8*(d3SymbolPortCount edges color i symbol true +
       d3SymbolPortCount edges color i symbol false) < edges.length := by
  have hR := d3_generated_symbol_port_bound 64 a (by decide) edges delta hrow hcol
    hregime hwidth i symbol true hi hs
  have hC := d3_generated_symbol_port_bound 64 a (by decide) edges delta hrow hcol
    hregime hwidth i symbol false hi hs
  dsimp only at hR hC ⊢
  constructor <;> omega

#print axioms d3_generated_group_half_wire_shrink

-- Kernel-checked finite indexing fixtures, covering both sides, both
-- coordinates, and an out-of-alphabet symbol (which has no occurrences).
example : colorSymbolCount 3 2 0 2 true = 27 := by decide
example : colorSymbolCount 3 2 1 2 false = 27 := by decide
example : colorSymbolCount 3 2 0 3 true = 0 := by decide
example : colorSymbolCount 2 1 0 1 false = 2 := by decide
example : colorSymbolCount 2 0 0 0 true = 0 := by decide

/- The quantitative conclusion holds for any distinct covering order of
vertices, including a sorted order if the executable refines the Lean state
transition. This does not assert that refinement. -/
/-- The padded-load bound of `lem:tensor-packets` for *any* distinct covering
vertex order, including the sorted order CPython uses. -/
theorem d3_any_order_padded_bound (r a : Nat) (hr : 0 < r)
    (edges : List PackingEdge) (v : PackingVertex) (vs : List PackingVertex)
    (hn : (v :: vs).Nodup) (hcover : d3VerticesCover edges (v :: vs))
    (delta : Nat) (hrow : ∀ vertex, rowDegreeOnList edges vertex ≤ delta)
    (hcol : ∀ vertex, columnDegreeOnList edges vertex ≤ delta)
    (hregime : 2*(r^(2*a))*(r^(2*a))*delta ≤ edges.length)
    (hwidth : (2^a)*(r^(2*a)) ≤ edges.length) :
    let final := d3CanonicalRun r a hr edges (v :: vs) emptyPackingAssignments
    let color := d3PartialColor final a
    let maximum := d3MaxClassLoad (allWordPairs r a) (d3ClassLoad edges color)
    let H := d3PaddedClassLoad (2^a) maximum
    (2^a) ∣ H ∧ r^(2*a)*H ≤ 3*edges.length := by
  let final := d3CanonicalRun r a hr edges (v :: vs) emptyPackingAssignments
  let color := d3PartialColor final a
  let load := d3ClassLoad edges color
  let classes := allWordPairs r a
  let maximum := d3MaxClassLoad classes load
  let H := d3PaddedClassLoad (2^a) maximum
  change (2^a) ∣ H ∧ r^(2*a)*H ≤ 3*edges.length
  have hcount : ∀ e, e ∈ edges →
      sumBy classes (fun c => if color e == c then 1 else 0) = 1 := by
    intro e he
    exact canonical_run_color_indicator_count r a hr edges (v :: vs) hn hcover
      emptyPackingAssignments e he
  have hsum := class_loads_sum edges color classes hcount
  have hsquares := class_squares_sum edges color classes hcount
  have hbound := d3_realized_run_class_square_bound r a hr edges v vs hn hcover delta hrow hcol
  change r^(2*a)*d3EdgeClassSquareSum edges color ≤
    edges.length*edges.length+2*edges.length*delta*r^(2*a) at hbound
  have hclass : ∀ c, c ∈ classes → r^(2*a)*load c ≤ 2*edges.length := by
    intro c hc
    apply d3_centered_bound_implies_load_bound (r^(2*a)) edges.length delta (load c) hregime
    apply d3_centered_class_square_bound classes load (r^(2*a)) edges.length delta
      (d3EdgeClassSquareSum edges color) (allWordPairs_length r a) hsum hsquares hbound c hc
  have hmax := d3_max_class_load_scaled_bound classes load (r^(2*a)) edges.length hclass
  change r^(2*a)*maximum ≤ 2*edges.length at hmax
  have hpad := d3_padded_class_load_bounds (2^a) maximum (Nat.pow_pos (by decide))
  change maximum ≤ H ∧ H ≤ maximum + 2^a ∧ (2^a) ∣ H at hpad
  have hmul := Nat.mul_le_mul_left (r^(2*a)) hpad.2.1
  have hwidth' : r^(2*a)*(2^a) ≤ edges.length := by simpa [Nat.mul_comm] using hwidth
  refine ⟨hpad.2.2, ?_⟩
  rw [Nat.mul_add] at hmul
  omega

#print axioms d3_any_order_padded_bound

theorem d3_any_order_symbol_port_bound (r a : Nat) (hr : 0 < r)
    (edges : List PackingEdge) (v : PackingVertex) (vs : List PackingVertex)
    (hn : (v :: vs).Nodup) (hcover : d3VerticesCover edges (v :: vs))
    (delta : Nat) (hrow : ∀ vertex, rowDegreeOnList edges vertex ≤ delta)
    (hcol : ∀ vertex, columnDegreeOnList edges vertex ≤ delta)
    (hregime : 2*(r^(2*a))*(r^(2*a))*delta ≤ edges.length)
    (hwidth : (2^a)*(r^(2*a)) ≤ edges.length)
    (i symbol : Nat) (row : Bool) (hi : i < a) (hs : symbol < r) :
    let final := d3CanonicalRun r a hr edges (v :: vs) emptyPackingAssignments
    r*d3SymbolPortCount edges (d3PartialColor final a) i symbol row ≤ 3*edges.length := by
  let final := d3CanonicalRun r a hr edges (v :: vs) emptyPackingAssignments
  let color := d3PartialColor final a
  let load := d3ClassLoad edges color
  let classes := allWordPairs r a
  let maximum := d3MaxClassLoad classes load
  let H := d3PaddedClassLoad (2^a) maximum
  have hcount : ∀ e, e ∈ edges →
      sumBy classes (fun c => if color e == c then 1 else 0) = 1 := by
    intro e he
    exact canonical_run_color_indicator_count r a hr edges (v :: vs) hn hcover
      emptyPackingAssignments e he
  have hsum := class_loads_sum edges color classes hcount
  have hsquares := class_squares_sum edges color classes hcount
  have hbound := d3_realized_run_class_square_bound r a hr edges v vs hn hcover delta hrow hcol
  change r^(2*a)*d3EdgeClassSquareSum edges color ≤
    edges.length*edges.length+2*edges.length*delta*r^(2*a) at hbound
  have hclass : ∀ c, c ∈ classes → r^(2*a)*load c ≤ 2*edges.length := by
    intro c hc
    apply d3_centered_bound_implies_load_bound (r^(2*a)) edges.length delta (load c) hregime
    apply d3_centered_class_square_bound classes load (r^(2*a)) edges.length delta
      (d3EdgeClassSquareSum edges color) (allWordPairs_length r a) hsum hsquares hbound c hc
  have hmax := d3_max_class_load_scaled_bound classes load (r^(2*a)) edges.length hclass
  change r^(2*a)*maximum ≤ 2*edges.length at hmax
  have hpad := d3_padded_class_load_bounds (2^a) maximum (Nat.pow_pos (by decide))
  change maximum ≤ H ∧ H ≤ maximum + 2^a ∧ (2^a) ∣ H at hpad
  have hmul := Nat.mul_le_mul_left (r^(2*a)) hpad.2.1
  have hwidth' : r^(2*a)*(2^a) ≤ edges.length := by simpa [Nat.mul_comm] using hwidth
  have Hbound : r^(2*a)*H ≤ 3*edges.length := by
    rw [Nat.mul_add] at hmul
    omega
  have hload : ∀ c, c ∈ classes → load c ≤ H := by
    intro c hc
    exact Nat.le_trans (d3_class_load_le_max classes load c hc) hpad.1
  exact d3_symbol_port_bound_from_padded_classes r a edges color i symbol H row hi hs hcount hload Hbound

#print axioms d3_any_order_symbol_port_bound

-- A parallel-edge fixture demonstrates that port counts count incidences,
-- not merely distinct endpoint vertices.
private def d3FixtureColor (e : PackingEdge) : D3EdgeColor :=
  ([e.1 % 2], [e.2 % 2])

example : d3SymbolPortCount [(0, 0), (0, 0), (1, 0)] d3FixtureColor 0 0 true = 2 := by decide
example : d3SymbolPortCount [(0, 0), (0, 0), (1, 0)] d3FixtureColor 0 0 false = 3 := by decide

/- This concrete counterexample records that d3GraphVertices keeps a
deduplicated order that need not be Python's sorted order. It intentionally
does not claim either construction refines the other. -/
def d3OrderAuditEdges : List PackingEdge := [(0,0), (1,1), (0,1)]
def d3OrderAuditRun : PackingPartial :=
  d3CanonicalRun 2 1 (by decide) d3OrderAuditEdges
    (d3GraphVertices d3OrderAuditEdges) emptyPackingAssignments

theorem d3_order_audit_fixture :
    d3GraphVertices d3OrderAuditEdges = [(.row, 1), (.row, 0), (.col, 0), (.col, 1)] ∧
    [d3OrderAuditRun (.row, 0) 0, d3OrderAuditRun (.row, 1) 0,
     d3OrderAuditRun (.col, 0) 0, d3OrderAuditRun (.col, 1) 0] =
      [some 1, some 0, some 0, some 1] := by decide

#print axioms d3_order_audit_fixture
