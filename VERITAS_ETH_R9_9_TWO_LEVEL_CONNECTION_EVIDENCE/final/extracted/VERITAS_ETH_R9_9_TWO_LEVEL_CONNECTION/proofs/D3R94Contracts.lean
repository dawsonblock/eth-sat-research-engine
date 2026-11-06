import D3CandidateOrder
import D3KeyedRun
import D3FinitePacketDomain

/-! Independently spelled acceptance types. A same-named True replacement
cannot inhabit these contracts. All claims here are about Lean models. -/

theorem r94_candidate_contract (r a : Nat) :
    D3CandidateOrder.productWords r a = labelWords r a ∧
    (labelWords r a).Pairwise (List.Lex (· < ·)) :=
  ⟨D3CandidateOrder.productWords_eq r a, D3CandidateOrder.labelWords_lex_sorted r a⟩

theorem r94_tie_contract (r a : Nat) (hr : 0 < r) (edges : List PackingEdge)
    (s : PackingPartial) (v : PackingVertex) :
    let selected := D3CandidateOrder.choose r a hr edges s v
    selected ∈ D3CandidateOrder.productWords r a ∧
    ∀ w ∈ D3CandidateOrder.productWords r a,
      D3PythonScore.pyCandidateScore s v selected r a edges ≤
        D3PythonScore.pyCandidateScore s v w r a edges ∧
      (D3PythonScore.pyCandidateScore s v selected r a edges =
        D3PythonScore.pyCandidateScore s v w r a edges →
        selected = w ∨ List.Lex (· < ·) selected w) :=
  D3CandidateOrder.choose_pair_minimum r a hr edges s v

theorem r94_run_contract (r a : Nat) (hr : 0 < r) (edges : List PackingEdge)
    (vertices : List PackingVertex) (s : D3KeyedRun.Dictionary)
    (hs : ∀ side ident d, a ≤ d → s (side,ident,d) = none) :
    D3KeyedRun.view (D3KeyedRun.run r a hr edges vertices s) =
      d3CanonicalRun r a hr edges vertices (D3KeyedRun.view s) ∧
    D3KeyedRun.trace r a hr edges vertices s =
      d3PythonCanonicalTrace r a hr edges vertices (D3KeyedRun.view s) :=
  ⟨D3KeyedRun.run_correspondence r a hr edges vertices s hs,
   D3KeyedRun.trace_correspondence r a hr edges vertices s hs⟩

theorem r94_sorted_contract (r a : Nat) (hr : 0 < r) (edges : List PackingEdge) :
    let vs := d3PythonOrderedVertices edges
    D3KeyedRun.Related (D3KeyedRun.run r a hr edges vs D3KeyedRun.empty)
      (d3CanonicalRun r a hr edges vs emptyPackingAssignments) ∧
    D3KeyedRun.trace r a hr edges vs D3KeyedRun.empty =
      d3PythonCanonicalTrace r a hr edges vs emptyPackingAssignments ∧
    r^(2*a) * d3EdgeClassSquareSum edges
      (d3PartialColor (D3KeyedRun.view (D3KeyedRun.run r a hr edges vs D3KeyedRun.empty)) a) =
      r^(2*a) * d3EdgeClassSquareSum edges
        (d3PartialColor (d3CanonicalRun r a hr edges vs emptyPackingAssignments) a) :=
  D3KeyedRun.sorted_run_contract r a hr edges

theorem r94_packet_domain_contract (r a H : Nat) (hpad : 2^a ∣ H) :
    ((D3FinitePacketDomain.positions r a H).map D3FinitePacketDomain.totalEncode).Perm
      (D3FinitePacketDomain.addresses r a H) ∧
    (D3FinitePacketDomain.addresses r a H).Nodup ∧
    (D3FinitePacketDomain.addresses r a H).length = r^(2*a)*H :=
  ⟨D3FinitePacketDomain.domain_permutation r a H hpad,
   D3FinitePacketDomain.addresses_nodup r a H,
   D3FinitePacketDomain.domain_cardinality r a H hpad⟩

#print axioms r94_candidate_contract
#print axioms r94_tie_contract
#print axioms r94_sorted_contract
#print axioms r94_run_contract
#print axioms r94_packet_domain_contract
