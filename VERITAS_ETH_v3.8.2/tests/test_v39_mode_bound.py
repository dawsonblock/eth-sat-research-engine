from copy import deepcopy

from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_recursion_v30.implicit_children import make_bipartite_edges
from veritas.research.eth_packing_v26.implicit import construct_implicit_packing, implicit_mode_source
from veritas.research.eth_recursive_contraction_v39 import make_point_modes, audit_point_mode_multiplicity


def test_checked_point_modes_satisfy_the_abstract_weighted_tuple_bound():
    network = from_cnf(CNF.from_lists(2, [[1, 2], [-1, -2]]))
    packing = construct_implicit_packing(make_bipartite_edges(network), r=2, a=2)
    cert = make_point_modes(implicit_mode_source(packing), node=1, precision=5,
                            extension_degree=3, zeta=(1, 0, 0))
    audit = audit_point_mode_multiplicity(cert)
    assert audit['valid']
    assert cert['mode_tuple_count'] <= 1 << audit['tuple_count_upper_power_of_two']
    assert not audit['uniform_packing_proven']
    assert not audit['total_runtime_proven']

    corrupt = deepcopy(cert)
    corrupt['modes'][0]['weight'] += 1
    assert not audit_point_mode_multiplicity(corrupt)['valid']
