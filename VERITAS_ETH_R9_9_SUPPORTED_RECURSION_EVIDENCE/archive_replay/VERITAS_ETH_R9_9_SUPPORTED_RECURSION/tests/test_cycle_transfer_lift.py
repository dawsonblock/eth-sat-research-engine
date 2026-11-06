"""Creation-time reduction survives actual cycle transfer child evaluation."""

from dataclasses import replace

from test_cycle_transfer_fixture import _matmul, cycle_parent
from veritas.research.independent_r95.recipe_oracle import ReferenceArithmetic, _entry
from veritas.research.parent_child_r98.cycle_transfer import evaluate_cycle_transfer
from veritas.research.parent_child_r98.model import Budget
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r98.shrinking_layout import construct_vertex_shrinking_layout
from veritas.research.parent_child_r98.transfer_verify import verify_transfer_certificate
from veritas.research.tapered_v4.source_recipes import EntryLimits, evaluate_source_entry, make_reference


def _cycle_point_with_row(row, point_precision=2944):
    """Independent scalar trace formula using the selected creation lift."""
    modulus = 1 << point_precision
    w = -84  # W_xx(1 + 4*1)
    k = ((1, 1-w), (0, w))
    kt = ((k[0][0], k[1][0]), (k[0][1], k[1][1]))
    column = ((1, 2), (3, 5))
    factor = _matmul(_matmul(_matmul(kt, row, modulus), k, modulus), column, modulus)
    value = ((1, 0), (0, 1))
    for _ in range(22):
        value = _matmul(value, factor, modulus)
    return (value[0][0] + value[1][1]) % modulus


def test_cycle_transfer_preserves_creation_residue_before_high_precision_lift():
    # At creation precision 8, this packet entry is 1-3 = 254 mod 256.
    packet = make_reference(kind="packet", arity=2, creation_precision=8,
                            defining_polynomial=7, jet_length=1,
                            data=[[0], [1], [[[[3, 0]]]], [], []])
    limits = EntryLimits(max_precision_bits=65536)
    assert evaluate_source_entry(packet, (0, 1), precision=128, limits=limits)["result"] == ((254, 0),)
    assert _entry(packet, (0, 1), ReferenceArithmetic(128, 7, 1, 100_000)) == ((254, 0),)

    original = cycle_parent()
    vertices = tuple(replace(vertex, tensor=packet) if vertex.side == "row" else vertex
                     for vertex in original.vertices)
    parent = replace(original, vertices=vertices)
    assert parent.precision == 128
    assert all(vertex.tensor.creation_precision == 8 for vertex in parent.vertices if vertex.side == "row")
    layout = construct_vertex_shrinking_layout(parent, groups=64,
                                                budget=Budget(DEFAULT_SHRINKING_POLICY))
    report = evaluate_cycle_transfer(parent, layout, 1, (1, 0))
    assert report["status"] == "PASS_FINITE_SCALED_CYCLE_TRANSFER_POINT", report
    expected = _cycle_point_with_row(((1, 254), (0, 3)))
    forbidden_reevaluation = _cycle_point_with_row(((1, -2), (0, 3)))
    assert expected != forbidden_reevaluation
    assert report["result"] == ((expected, 0),)
    assert report["result"] != ((forbidden_reevaluation, 0),)
    checked = verify_transfer_certificate(parent, layout, report["certificate"],
                                           expected_point=(1, (1, 0), 2944))
    assert checked["status"] == "PASS_FINITE_SCALED_CYCLE_TRANSFER_POINT", checked
    assert checked["result"] == report["result"]
