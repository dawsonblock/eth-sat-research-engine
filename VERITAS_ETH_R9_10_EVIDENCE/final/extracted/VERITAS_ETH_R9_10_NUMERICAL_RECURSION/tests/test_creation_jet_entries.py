import pytest

from veritas.research.eth_arithmetic.creation_lifts import CreationEntry, CreationJetEntry
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing


def test_jet_entry_lifts_each_creation_residue_without_recomputing_arithmetic():
    old = JetRing(ExtensionRing(2, 0b11), 2)
    new = JetRing(ExtensionRing(4, 0b11), 2)
    three = old.elem([[3], [1]])
    captured_sum = CreationJetEntry.capture(old, old.add(three, three))
    lifted_sum = captured_sum.evaluate(new)
    added_lifts = new.add(CreationJetEntry.capture(old, three).evaluate(new),
                          CreationJetEntry.capture(old, three).evaluate(new))
    assert lifted_sum == new.elem([[2], [2]])
    assert added_lifts == new.elem([[6], [2]])
    assert lifted_sum != added_lifts

    with pytest.raises(ValueError, match='incompatible'):
        captured_sum.evaluate(JetRing(ExtensionRing(1, 0b11), 2))
    with pytest.raises(ValueError, match='incompatible'):
        captured_sum.evaluate(JetRing(ExtensionRing(4, 0b11), 1))
    with pytest.raises(ValueError, match='immutable'):
        CreationJetEntry(2, 0b11, ([1],))
    with pytest.raises(ValueError, match='canonical'):
        CreationEntry(2, 0b11, [1])


def test_extended_precision_boundary_keeps_exact_unit_inverse():
    ring = ExtensionRing(1024, 0b1011)
    value = ring.elem([2, 1])
    assert ring.mul(value, ring.inverse(value)) == ring.one
    with pytest.raises(ValueError, match='1024'):
        ExtensionRing(1025, 0b1011)
