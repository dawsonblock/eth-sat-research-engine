"""Check the singleton support argument at the packet-entry level."""

from itertools import product

import pytest

from test_cycle_transfer_fixture import three_crossing_matching
from veritas.research.independent_r95.recipe_oracle import ReferenceArithmetic, _entry
from veritas.research.parent_child_r98.constructor import construct_children
from veritas.research.parent_child_r98.model import Budget, ExponentTuple
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.tapered_v4.source_recipes import EntryLimits, evaluate_source_entry


@pytest.mark.parametrize("values", ((2, 0, 0), (0, 3, 1), (1, 0, 5)))
def test_exponent_above_one_makes_target_packet_zero_for_every_boolean_entry(values):
    parent, layout, modes = three_crossing_matching()
    budget = Budget(DEFAULT_SHRINKING_POLICY)
    beta = ExponentTuple(modes.content_digest, values)
    children = construct_children(parent, layout, modes, beta, budget=budget,
                                  _admitted=True, require_shrink=True)
    index = next(i for i, exponent in enumerate(values) if exponent > 1)
    mode = modes.certificate["modes"][index]
    child = children[mode["target_group"]]
    packet_index = child.packet_ids.index(mode["packet"])
    packet = child.vertices[len(child.inherited) + packet_index].tensor
    assert packet.arity == 1 and packet.creation_precision == 1416
    limits = EntryLimits(max_precision_bits=65536)
    for bits in product((0, 1), repeat=packet.arity):
        actual = evaluate_source_entry(packet, bits, precision=1416, limits=limits)["result"]
        reference = _entry(packet, bits, ReferenceArithmetic(1416, 7, 1, 1_000_000,
                                                              max_precision_bits=65536))
        assert actual == reference == ((0, 0),)
