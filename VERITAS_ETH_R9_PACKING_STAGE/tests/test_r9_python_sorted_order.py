"""Regression for the Python sorted-order packing semantics."""
from veritas.research.eth_packing_v26.streaming import (
    _ordered_vertices,
    construct_streaming_d3_packing,
)


def test_required_three_edge_trace_and_scaled_scores():
    edges = [(0, 0), (1, 1), (0, 1)]
    built = construct_streaming_d3_packing(edges, r=2, a=1)
    trace = built.certificate["steps"]
    assert [(step["side"], step["vertex"]) for step in trace] == [
        ("R", 0), ("R", 1), ("C", 0), ("C", 1)
    ]
    assert [step["label"] for step in trace] == [[0], [1], [0], [1]]
    assert [step["expected_square_scaled"] for step in trace] == [22, 16, 16, 12]
    assert built.certificate["initial_expected_square_scaled"] == 22
    assert built.certificate["final_square_scaled"] == 12


def test_sorted_vertex_order_is_edge_permutation_invariant_and_side_tagged():
    edges = [(7, 2), (1, 2), (7, 0), (7, 2)]
    expected = (("R", 1), ("R", 7), ("C", 0), ("C", 2))
    assert _ordered_vertices(edges) == expected
    assert _ordered_vertices(list(reversed(edges))) == expected
    assert _ordered_vertices([]) == ()


def test_parallel_edges_remain_distinct_occurrences_but_vertices_are_unique():
    edges = [(0, 0), (0, 0), (0, 0)]
    built = construct_streaming_d3_packing(edges, r=2, a=1)
    assert _ordered_vertices(edges) == (("R", 0), ("C", 0))
    assert built.packing.edges == tuple(edges)
    assert sum(len(ids) for ids in built.packing.classes.values()) == 3


def test_equal_numeric_row_and_column_ids_are_distinct_vertices():
    assert _ordered_vertices([(0, 0)]) == (("R", 0), ("C", 0))

