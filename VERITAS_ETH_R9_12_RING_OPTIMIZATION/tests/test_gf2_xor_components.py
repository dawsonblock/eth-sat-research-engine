from veritas.core.cnf import CNF
from veritas.research.gf2_xor_count import XorEquation, structure_with_optional_xor
from veritas.research.gf2_xor_components import try_component_product_mixed_xor


def test_component_product_when_xor_local():
    cnf = CNF.from_lists(4, [[1, 2], [3, 4]])
    eqs = (XorEquation((1, 2), 0),)
    comp = try_component_product_mixed_xor(cnf, eqs, max_enum_bits=18)
    assert comp is not None
    assert int(comp['count']) == 3
    out = structure_with_optional_xor(cnf, xor_equations=eqs, preprocess=False, verify_direct=True)
    assert out['count'] == '3'
    assert out.get('independent_count_checked') is True


def test_component_product_rejects_spanning_xor():
    cnf = CNF.from_lists(4, [[1, 2], [3, 4]])
    eqs = (XorEquation((2, 3), 1),)
    assert try_component_product_mixed_xor(cnf, eqs) is None
