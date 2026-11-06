import D3VarianceBound

/-!
Pointwise collision identity underlying the source's D.3 load potential.

For a fixed complete edge-color/signature assignment, the sum of squared
class loads is represented without enumerating empty classes by summing, for
each edge occurrence, the load of its signature. This counts a class of size
`x` exactly `x` times and therefore contributes `x^2`. The result equals the
number of ordered edge pairs with equal signatures.

This module proves the finite combinatorial identity. It does not yet define
the global random-label sample space or its probability/expectation.
-/

abbrev D3EdgeColor := List Nat × List Nat

def d3EdgeColor (labels : PackingVertex → Nat → Nat) (a : Nat)
    (edge : PackingEdge) : D3EdgeColor :=
  ((List.range a).map (labels (.row, edge.1)),
   (List.range a).map (labels (.col, edge.2)))

def d3EdgeClassLoad (edges : List PackingEdge)
    (color : PackingEdge → D3EdgeColor) (edge : PackingEdge) : Nat :=
  sumBy edges (fun other => if color edge == color other then 1 else 0)

def d3EdgeClassSquareSum (edges : List PackingEdge)
    (color : PackingEdge → D3EdgeColor) : Nat :=
  sumBy edges (d3EdgeClassLoad edges color)

def d3OrderedCollisionCount (edges : List PackingEdge)
    (color : PackingEdge → D3EdgeColor) : Nat :=
  sumBy (allOrderedEdgePairs edges) (fun pair =>
    if color pair.1 == color pair.2 then 1 else 0)

theorem d3_edge_class_square_sum_eq_ordered_collision_count
    (edges : List PackingEdge) (color : PackingEdge → D3EdgeColor) :
    d3EdgeClassSquareSum edges color = d3OrderedCollisionCount edges color := by
  unfold d3EdgeClassSquareSum d3EdgeClassLoad d3OrderedCollisionCount
    allOrderedEdgePairs
  rw [sumBy_flatMap]
  apply sumBy_congr
  intro edge hedge
  rw [sumBy_map]

def d3ScaledOrderedCollisionCount (r a : Nat) (edges : List PackingEdge)
    (color : PackingEdge → D3EdgeColor) : Nat :=
  sumBy (allOrderedEdgePairs edges) (fun pair =>
    if color pair.1 == color pair.2 then r ^ (2 * a) else 0)

theorem d3_scaled_ordered_collision_count_eq
    (r a : Nat) (edges : List PackingEdge)
    (color : PackingEdge → D3EdgeColor) :
    d3ScaledOrderedCollisionCount r a edges color =
      r ^ (2 * a) * d3EdgeClassSquareSum edges color := by
  unfold d3ScaledOrderedCollisionCount
  calc
    sumBy (allOrderedEdgePairs edges) (fun pair =>
        if color pair.1 == color pair.2 then r ^ (2 * a) else 0) =
      sumBy (allOrderedEdgePairs edges) (fun pair =>
        (if color pair.1 == color pair.2 then 1 else 0) * r ^ (2 * a)) := by
          apply sumBy_congr
          intro pair hpair
          cases (color pair.1 == color pair.2) <;> simp
    _ = d3OrderedCollisionCount edges color * r ^ (2 * a) := by
          rw [sumBy_mul_right]
          rfl
    _ = r ^ (2 * a) * d3EdgeClassSquareSum edges color := by
          rw [d3_edge_class_square_sum_eq_ordered_collision_count]
          exact Nat.mul_comm _ _

#print axioms d3_edge_class_square_sum_eq_ordered_collision_count
#print axioms d3_scaled_ordered_collision_count_eq
