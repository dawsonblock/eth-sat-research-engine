from copy import deepcopy
import json

from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_packing_v26.implicit import construct_implicit_packing, implicit_mode_source
from veritas.research.eth_recursive_contraction_v39 import (
    check_point_child_expansion_certificate, contract_point_child_expansion,
    describe_integer_network, make_point_modes, run_tapered_finite,
)


def fixture():
    net = from_cnf(CNF.from_lists(2, [[1, 2]]))
    described = describe_integer_network(net, creation_precision=3,
                                         defining_polynomial=first_irreducible(3))
    packing = construct_implicit_packing(described.bipartite_edges(), r=2, a=1)
    modes = make_point_modes(implicit_mode_source(packing), node=1, precision=5,
                             extension_degree=3, zeta=(1, 0, 0))
    return described, modes


def test_child_certificate_replays_sizes_valuations_and_parent_identity():
    described, modes = fixture()
    proof = contract_point_child_expansion(described, modes)
    checked = check_point_child_expansion_certificate(described, modes, proof)
    assert checked['valid']
    assert check_point_child_expansion_certificate(
        described, modes, proof, max_parent_wires=8)['valid']
    assert check_point_child_expansion_certificate(
        described, modes, json.loads(json.dumps(proof)))['valid']
    assert proof['result'] == proof['direct_oracle_result']
    assert all(item['minimum_observed_valuation'] >= item['weight']
               for item in proof['mode_valuations'])
    assert all(sum(child['edge_count'] for child in row['children']) == 2 * described.edges
               for row in proof['tuples'])
    assert not proof['all_children_meet_strict_one_eighth']
    assert not proof['subexponential_runtime_proven']


def test_child_certificate_rejects_altered_edge_count_or_identity():
    described, modes = fixture()
    proof = contract_point_child_expansion(described, modes)
    for part in ('edge_count', 'boolean_edge_count', 'result', 'valuation'):
        bad = deepcopy(proof)
        if part == 'edge_count':
            bad['tuples'][0]['children'][0]['edge_count'] += 1
        elif part == 'boolean_edge_count':
            original = bad['tuples'][0]['children'][0]['edge_count']
            if original not in (0, 1):
                continue
            bad['tuples'][0]['children'][0]['edge_count'] = bool(original)
        elif part == 'result':
            bad['result'] = ((0, 0, 0),) if bad['result'] != ((0, 0, 0),) else ((1, 0, 0),)
        elif bad['mode_valuations']:
            bad['mode_valuations'][0]['minimum_observed_valuation'] += 1
        else:
            continue
        assert not check_point_child_expansion_certificate(described, modes, bad)['valid']


def test_mode_checker_rejects_boolean_substituted_for_integer_weight():
    from veritas.research.eth_recursive_contraction_v39 import check_point_modes

    _, modes = fixture()
    assert modes['modes'][0]['weight'] == 1
    forged = deepcopy(modes)
    forged['modes'][0]['weight'] = True
    assert not check_point_modes(forged)['valid']


def test_requested_one_eighth_invariant_fails_closed_for_scaled_example():
    described, _ = fixture()
    result = run_tapered_finite(described, target_precision=3,
                                require_one_eighth_shrink=True, max_work=2_000_000)
    assert result['status'] == 'INCONCLUSIVE_CHILD_SIZE_INVARIANT'
    assert 'result' not in result
