"""New transfer graph, arithmetic and checker scans obey the work budget."""

from dataclasses import replace

import pytest

from test_cycle_transfer_fixture import three_crossing_matching
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.parent_child_r98.cycle_transfer import _cycle_order, _multiply_cycle
from veritas.research.parent_child_r98.model import Budget, Refusal
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r98.transfer_children import TransferChildren
from veritas.research.parent_child_r98.transfer_verify import _check_child, _group_contexts, _group_value


def _budget(work):
    return Budget(replace(DEFAULT_SHRINKING_POLICY, max_work=work))


def test_cycle_order_is_metered_before_graph_processing():
    modes = [{"source_group": 0, "target_group": 1},
             {"source_group": 1, "target_group": 2},
             {"source_group": 2, "target_group": 0}]
    with pytest.raises(Refusal, match="work/time"):
        _cycle_order(3, modes, budget=_budget(1))
    budget = _budget(100)
    _, nodes, edges = _cycle_order(3, modes, budget=budget)
    assert len(nodes) == len(edges) == 3 and budget.work >= 9


def test_cycle_matrix_ring_work_is_charged_before_multiplication():
    modes = [{"source_group": 0, "target_group": 1},
             {"source_group": 1, "target_group": 2},
             {"source_group": 2, "target_group": 0}]
    adjacency, nodes, edges = _cycle_order(3, modes)
    ring = JetRing(ExtensionRing(8, 7), 1)
    values = [[ring.one] * 4 for _ in range(3)]
    with pytest.raises(Refusal, match="work/time"):
        _multiply_cycle(ring, adjacency, nodes, edges, values, budget=_budget(4))
    budget = _budget(1000)
    assert _multiply_cycle(ring, adjacency, nodes, edges, values, budget=budget) == ((8, 0),)
    assert budget.work > 100


def test_child_preparation_and_checker_scans_are_charged():
    parent, layout, modes = three_crossing_matching()
    with pytest.raises(Refusal, match="work/time"):
        TransferChildren(parent, layout, modes, budget=_budget(1))
    with pytest.raises(Refusal, match="work/time"):
        _group_contexts(parent, layout.source, 64, _budget(1))
    with pytest.raises(Refusal, match="work/time"):
        _group_value(parent, layout.source, {}, [], 0, (), (), _budget(1), 1416)


def test_child_bytes_are_charged_before_deserialization():
    parent, layout, modes = three_crossing_matching()
    with pytest.raises(Refusal, match="work/time"):
        _check_child(parent, layout, layout.source, modes.certificate,
                     modes.content_digest, 0, (), (), " " * 100, ((), ()),
                     1416, _budget(1))
