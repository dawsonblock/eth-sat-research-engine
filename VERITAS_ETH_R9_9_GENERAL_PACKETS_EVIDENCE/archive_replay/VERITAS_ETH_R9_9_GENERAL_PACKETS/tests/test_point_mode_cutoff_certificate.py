from copy import deepcopy

from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_recursion_v30.implicit_children import make_bipartite_edges
from veritas.research.eth_packing_v26.implicit import construct_implicit_packing, implicit_mode_source
from veritas.research.eth_recursive_contraction_v39.point_modes import (
    certify_point_mode_tuple, make_point_modes,
)


def test_point_tuple_cutoff_uses_verified_coefficient_valuations():
    network = from_cnf(CNF.from_lists(2, [[1, 2]]))
    packing = construct_implicit_packing(make_bipartite_edges(network), r=2, a=1)
    certificate = make_point_modes(implicit_mode_source(packing), node=1,
                                   precision=5, extension_degree=3,
                                   zeta=(1, 0, 0))
    assert certificate['modes']

    zero = certify_point_mode_tuple(certificate, (0,) * len(certificate['modes']))
    assert zero['valid'] and not zero['discarded_by_declared_cutoff']
    assert not zero['zero_modulo_precision_certified']

    beta = (5,) + (0,) * (len(certificate['modes']) - 1)
    omitted = certify_point_mode_tuple(certificate, beta)
    assert omitted['valid'] and omitted['discarded_by_declared_cutoff']
    assert omitted['zero_modulo_precision_certified']
    assert omitted['certified_valuation_lower_bound'] >= omitted['declared_total_weight'] >= 5

    assert not certify_point_mode_tuple(certificate, (-1,) * len(beta))['valid']
    assert not certify_point_mode_tuple(certificate, (True,) * len(beta))['valid']
    assert not certify_point_mode_tuple(certificate, ())['valid']
    forged = deepcopy(certificate)
    forged['modes'][0]['weight'] += 1
    assert not certify_point_mode_tuple(forged, beta)['valid']
