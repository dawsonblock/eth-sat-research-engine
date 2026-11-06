"""Independent v3.8 mathematical differential and tamper tests."""
from copy import deepcopy
from random import Random
import pytest
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_packing_v26.constructor import construct_d3_packing
from veritas.research.eth_recursion_v30.implicit_children import make_bipartite_edges
from veritas.research.eth_modes_v31 import make_jet_tile_modes
from veritas.research.eth_child_elimination_v38 import (
    construct_elimination_reference, verify_elimination_reference, ResourceLimit)


def instance(n=2, clauses=((1, 2),), precision=5, jet_length=2):
    net = from_cnf(CNF.from_lists(n, [list(c) for c in clauses]))
    d3 = construct_d3_packing(make_bipartite_edges(net), r=2, a=1)
    modes = make_jet_tile_modes(d3, node=1, precision=precision, jet_length=jet_length)
    return net, modes


def test_v38_reproduces_full_v37_and_direct_oracle():
    net, modes = instance()
    cert = construct_elimination_reference(net, modes, compare_v37=True)
    assert cert['result'] == [[0,0,0], [16,0,0]]
    assert cert['v37_cross_check_performed']
    assert cert['exact_direct_reference_matches']
    assert cert['packet_cache_hits'] > 0
    assert verify_elimination_reference(cert)['valid']
    assert all(c['extra_mode_bond_wires'] == 0 for c in cert['children'])


def test_v38_untrusted_claims_and_metrics_cannot_be_replayed():
    net, modes = instance()
    cert = construct_elimination_reference(net, modes)
    for field in ('result', 'children', 'mode_tuples_evaluated', 'work',
                  'max_intermediate_entries', 'packet_cache_hits', 'claim',
                  'scope', 'subexponential_runtime_proven'):
        forged = deepcopy(cert)
        if field == 'result': forged[field][0][0] += 1
        elif field == 'children': forged[field][0]['child_wires'] += 1
        elif field == 'scope': forged[field]['subexponential_runtime_proven'] = True
        elif field == 'claim': forged[field] = 'UNIVERSAL_ETH_PROOF'
        elif field == 'subexponential_runtime_proven': forged[field] = True
        else: forged[field] += 1
        assert not verify_elimination_reference(forged)['valid'], field


def test_v38_limits_fail_closed():
    net, modes = instance()
    with pytest.raises(ResourceLimit):
        construct_elimination_reference(net, modes, max_entries=2)
    with pytest.raises(ResourceLimit):
        construct_elimination_reference(net, modes, max_work=100, max_cache_entries=0)
    with pytest.raises(ValueError):
        construct_elimination_reference(net, modes, max_cache_entries=-1)


def test_v38_seeded_exact_differential():
    rng = Random(380031)
    for _ in range(12):
        n = rng.randint(1, 3)
        clauses = [[rng.choice((-1,1))*rng.randint(1,n)
                    for j in range(rng.randint(1,2))]
                   for k in range(rng.randint(1,2))]
        net = from_cnf(CNF.from_lists(n,clauses))
        if net.edges > 5: continue
        d3 = construct_d3_packing(make_bipartite_edges(net),r=2,a=1)
        modes = make_jet_tile_modes(d3,node=rng.choice((-1,1)),
                       precision=rng.randint(3,5),extension_degree=rng.randint(1,3),
                       jet_length=rng.randint(1,3))
        cert = construct_elimination_reference(net,modes,max_work=1200000,
                                               max_entries=256)
        assert verify_elimination_reference(cert,max_work=1200000)['valid']
        assert cert['mode_tuples_evaluated'] > 0
        assert not cert['manuscript_recursive_size_bound_proven']
