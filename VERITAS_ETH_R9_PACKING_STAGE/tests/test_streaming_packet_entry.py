from random import Random

import pytest

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.eth_recursive_contraction_v39.lazy_children import (
    ChildEvaluationBudgetExceeded, PacketTensorEntry, _Budget,
)


def test_streaming_row_selection_matches_bounded_coefficient_dp():
    rng = Random(20261101)
    ring = JetRing(ExtensionRing(3, first_irreducible(2)), 2)

    def coefficient():
        return tuple(tuple(rng.randrange(8) for _ in range(2)) for _ in range(2))

    for _ in range(80):
        nrows, ncols, nmodes = (rng.randrange(5), rng.randrange(4), rng.randrange(4))
        variables = tuple([('Y', i) for i in range(nrows)] +
                          [('X', i) for i in range(ncols)])
        rows = tuple((i, tuple((j, coefficient()) for j in range(ncols)
                               if rng.randrange(2))) for i in range(nrows))
        target = tuple((mid, rng.randrange(3),
                        tuple((i, coefficient()) for i in range(nrows)
                              if rng.randrange(2))) for mid in range(nmodes))
        source = tuple((mid, rng.randrange(3),
                        tuple((j, rng.randrange(4)) for j in range(ncols)
                              if rng.randrange(2))) for mid in range(nmodes))
        recipe = PacketTensorEntry(0, tuple(range(len(variables))), variables,
                                   rows, target, source)
        for _ in range(8):
            bits = tuple(rng.randrange(2) for _ in variables)
            actual = recipe.evaluate(bits, ring, _Budget(100_000, 5))
            reference = recipe.evaluate_dp_reference(bits, ring, _Budget(100_000, 5))
            assert actual == reference


def test_streaming_empty_rows_and_zero_powers():
    ring = JetRing(ExtensionRing(3, first_irreducible(1)), 1)
    assert PacketTensorEntry(0, (), (), (), (), ((1, 0, ()),)).evaluate(
        (), ring, _Budget(100, 5)) == ring.one
    assert PacketTensorEntry(0, (), (), (), ((1, 1, ()),), ()).evaluate(
        (), ring, _Budget(100, 5)) == ring.zero
    assert PacketTensorEntry(0, (), (), (), (), ((1, 1, ()),)).evaluate(
        (), ring, _Budget(100, 5)) == ring.zero

    extension_jets = JetRing(ExtensionRing(3, first_irreducible(2)), 2)
    source = PacketTensorEntry(0, (0, 1), (('X', 3), ('X', 4)), (), (),
                               ((0, 2, ((3, 2), (4, 3))),))
    assert source.evaluate((1, 0), extension_jets, _Budget(100, 5)) == extension_jets.elem([[4]])
    assert source.evaluate((0, 1), extension_jets, _Budget(100, 5)) == extension_jets.elem([[1]])


def test_streaming_checks_budget_while_enumerating_and_has_no_row_recursion():
    ring = JetRing(ExtensionRing(3, first_irreducible(1)), 1)
    rows = tuple((i, ()) for i in range(4))
    modes = ((0, 2, tuple((i, ((1,),)) for i in range(4))),)
    recipe = PacketTensorEntry(0, tuple(range(4)), tuple(('Y', i) for i in range(4)),
                               rows, modes, ())
    with pytest.raises(ChildEvaluationBudgetExceeded):
        recipe.evaluate((0, 0, 0, 0), ring, _Budget(10, 5))

    count = 1200
    deep = PacketTensorEntry(0, tuple(range(count)), tuple(('Y', i) for i in range(count)),
                             tuple((i, ()) for i in range(count)), (), ())
    assert deep.evaluate((0,) * count, ring, _Budget(5000, 5)) == ring.one


def test_streaming_checks_cooperative_deadline(monkeypatch):
    from veritas.research.eth_recursive_contraction_v39 import lazy_children
    ring = JetRing(ExtensionRing(3, first_irreducible(1)), 1)
    budget = _Budget(100, 5)
    monkeypatch.setattr(lazy_children, 'monotonic', lambda: budget.started + 6)
    with pytest.raises(ChildEvaluationBudgetExceeded):
        PacketTensorEntry(0, (), (), (), (), ()).evaluate((), ring, budget)


def test_streaming_prunes_selections_exceeding_target_degree():
    ring = JetRing(ExtensionRing(8, first_irreducible(1)), 1)
    count = 24
    rows = tuple((i, ()) for i in range(count))
    modes = ((0, 1, tuple((i, ((1,),)) for i in range(count))),)
    recipe = PacketTensorEntry(0, tuple(range(count)), tuple(('Y', i) for i in range(count)),
                               rows, modes, ())
    budget = _Budget(1_000, 5)
    assert recipe.evaluate((0,) * count, ring, budget) == ring.elem([[-count]])
    assert budget.used < 1_000
