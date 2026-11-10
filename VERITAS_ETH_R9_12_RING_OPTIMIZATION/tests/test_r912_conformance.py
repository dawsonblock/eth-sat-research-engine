from dataclasses import replace
from math import log
from pathlib import Path

import pytest

from veritas.research.eth_packing_v26.implicit import construct_implicit_packing
from veritas.research.paper_verification.exact_parameters import hermite_parameters
from veritas.research.parent_child_r98.model import Refusal
from veritas.research.parent_child_r98.modes import weighted_count
from veritas.research.parent_child_r98.shrinking_cli import load_input
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r910.engine import contract
from veritas.research.parent_child_r912 import conformance as theorem
from veritas.research.parent_child_r912.layout import derandomized_layout

ROOT = Path(__file__).resolve().parents[1]
POLICY = replace(DEFAULT_SHRINKING_POLICY, max_work=1_000_000_000,
                 max_seconds=600, max_certificate_bytes=100_000_000)


def cycle(n):
    return [(i, i) for i in range(n)] + [(i, (i + 1) % n) for i in range(n)]


def test_conditional_expectation_labels_meet_packet_count_when_hypotheses_hold():
    edges = cycle(64)
    packing = construct_implicit_packing(edges, r=2, a=1, max_work=None)
    v = theorem.packing_check(edges, packing.rows, packing.cols, k=2, L=2, H_pad=packing.H)
    assert v['hypotheses_met'] and v['conclusions_met']
    assert v['padded_packets'] * 2 <= 3 * len(edges)


def test_bad_labeling_is_rejected_as_a_hypothesis():
    edges = cycle(64)
    same = {x: (0,) for x in range(64)}
    v = theorem.packing_check(edges, same, same, k=2, L=2, H_pad=128)
    assert not v['hypotheses']['spread_le_2M_delta']
    assert not v['hypotheses_met']


def test_packing_conditions_fail_for_runnable_sizes():
    edges = cycle(64)
    packing = construct_implicit_packing(edges, r=64, a=1, max_work=None)
    v = theorem.packing_check(edges, packing.rows, packing.cols, k=64, L=2, H_pad=packing.H)
    assert not v['hypotheses']['M_ge_2_D_squared_delta'] and not v['hypotheses']['M_ge_LD']


def _mode(packet, tile, b, weight=None):
    return {'packet': packet, 'tile_residue': tile, 'exponent': b, 'weight': b + 1 if weight is None else weight}


def test_mode_tags_meet_multiplicity_bound():
    modes = [_mode(p, y, b) for p in range(3) for y in range(2) for b in range(4)]
    v = theorem.mode_check(modes, P=3, i=0, L=4, M=8, Dt=4, packed=True)
    assert v['hypotheses_met'] and v['conclusions_met'] and v['largest_weight_class'] == 6


@pytest.mark.parametrize('modes, failed', [
    ([_mode(0, 0, 0), _mode(0, 0, 0)], 'tags_distinct'),
    ([_mode(3, 0, 0)], 'packet_lt_P'),
    ([_mode(0, 2, 0)], 'tile_lt_2_pow_i_plus_1'),
    ([_mode(0, 0, 1, weight=1)], 'weight_is_exponent_plus_1'),
])
def test_malformed_mode_tags_are_rejected(modes, failed):
    v = theorem.mode_check(modes, P=3, i=0, L=4, M=8, Dt=4, packed=True)
    assert not v['hypotheses'][failed]


def test_precision_bound_holds_under_its_hypotheses():
    M, u, i, a = 1000, 1, 0, 8
    Dt, h, p = (1 << a) >> i, -(-3 * M // u), 5
    v = theorem.precision_check(M=M, a=a, u=u, i=i, p=p, h=h, Dt=Dt,
                                precision=theorem.node_precision(p, h, Dt, M, a))
    assert v['hypotheses_met'] and v['conclusions_met']


def test_precision_matches_engine_hermite_parameters():
    pars = hermite_parameters(20, 3, 1, 7, max_wires=32)
    for t, i, _, Dt, p_t in pars['nodes']:
        assert p_t == theorem.node_precision(7, pars['h'], Dt, 20, 3)


def test_low_precision_is_rejected():
    M, a, u, Dt, h, p = 1000, 8, 1, 256, 3000, 5
    v = theorem.precision_check(M=M, a=a, u=u, i=0, p=p, h=h, Dt=Dt,
                                precision=theorem.node_precision(p, h, Dt, M, a) - 1)
    assert not v['hypotheses']['precision_matches_lemma']


def test_u_equal_one_schedule_violates_shape():
    pars = hermite_parameters(22, 1, 1, 5, max_wires=32)
    _, i, _, Dt, p_t = pars['nodes'][0]
    v = theorem.precision_check(M=22, a=1, u=1, i=i, p=5, h=pars['h'], Dt=Dt, precision=p_t)
    assert not v['hypotheses']['a_ge_2u']


@pytest.mark.parametrize('weights, budget', [((1, 2), 4), ((1, 1, 3), 6), ((2, 3, 3, 5), 9), ((), 1), ((1,), 0)])
def test_enum_mirror_matches_weighted_count(weights, budget):
    tuples = theorem.enum_tuples(weights, budget)
    assert len(set(tuples)) == len(tuples)
    assert all(sum(w * b for w, b in zip(weights, t)) < budget for t in tuples)
    if budget:
        assert len(tuples) == weighted_count(weights, budget, 10**9)


def test_enum_mirror_matches_lean_example():
    assert theorem.enum_tuples((1, 2), 4) == [(0, 0), (0, 1), (1, 0), (1, 1), (2, 0), (3, 0)]


def test_tuple_bound_only_beats_brute_force_for_huge_u():
    threshold = theorem.saving_threshold()
    assert threshold > 2000
    assert theorem.tuple_bound_log(50, threshold) < 50 * log(2)
    assert theorem.tuple_bound_log(50, threshold - 1) >= 50 * log(2)
    v = theorem.tuple_check(weighted_count=10, support_tuples=[(0,)], support_weights=[1],
                            precision=5, M=50, u=1, upstream=True)
    assert v['conclusions_met'] and not v['bound_below_2_to_M']


def test_support_outside_budget_is_rejected():
    v = theorem.tuple_check(weighted_count=10, support_tuples=[(5,)], support_weights=[1],
                            precision=5, M=50, u=1, upstream=True)
    assert not v['hypotheses']['support_within_weight_budget']


def test_strict_audit_refuses_and_contradiction_is_an_error():
    class Call:
        content_digest = '0' * 64
    audit = theorem.NodeAudit(strict=True)
    with pytest.raises(Refusal, match='M_ge_LD'):
        audit.add(Call, 'packet_count', {'hypotheses': {'M_ge_LD': False}, 'conclusions': {},
                                         'hypotheses_met': False, 'conclusions_met': True})
    with pytest.raises(ValueError, match='proved conclusion'):
        theorem.NodeAudit().add(Call, 'x', {'hypotheses': {}, 'conclusions': {'c': False},
                                            'hypotheses_met': True, 'conclusions_met': False})


@pytest.fixture(scope='module')
def matching():
    return load_input(ROOT / 'examples/r98_general_matching22.json')


def test_report_mode_keeps_result_and_never_claims_conformance(matching):
    base = contract(matching, policy=POLICY)
    out = contract(matching, policy=POLICY, conformance='report')
    assert out['result'] == base['result'] and 'theorem_conformance' not in base
    report = out['theorem_conformance']
    assert report['conforms'] is False
    assert report['source_qualified'] is False and report['evidence_for_recursion_bound'] is False
    assert {c['check'] for c in report['checks']} >= {'packet_count', 'precision_bound'}


def test_strict_mode_refuses_without_partial_result(matching):
    out = contract(matching, policy=POLICY, conformance='strict')
    assert out['status'] == 'INCONCLUSIVE_THEOREM_HYPOTHESIS'
    assert 'result' not in out and out['source_qualified'] is False


def test_derandomized_layout_is_refused_at_runnable_sizes(matching):
    out = contract(matching, policy=POLICY, layout_factory=derandomized_layout)
    assert out['status'] == 'INCONCLUSIVE_SOURCE_PACKING' and 'result' not in out


def test_unknown_conformance_mode_is_rejected(matching):
    with pytest.raises(ValueError, match='conformance'):
        contract(matching, policy=POLICY, conformance='on')


def test_cli_conformance_modes(tmp_path, capsys):
    import sys
    sys.path.insert(0, str(ROOT / 'tests'))
    from test_r912_jets import jet_matching
    from veritas.research.parent_child_r98.model import canonical
    from veritas.research.parent_child_r99.cli import load_execution_report
    from veritas.research.parent_child_r912.cli import main
    source = tmp_path / 'parent.json'
    source.write_bytes(canonical(jet_matching().record()))
    assert main([str(source), '--output-dir', str(tmp_path / 'report'), '--conformance', 'report']) == 0
    report = load_execution_report(tmp_path / 'report' / 'report.json', max_bytes=100_000_000)
    assert report['theorem_conformance']['conforms'] is False
    assert main([str(source), '--output-dir', str(tmp_path / 'strict'), '--conformance', 'strict']) == 2
    assert 'INCONCLUSIVE_THEOREM_HYPOTHESIS' in capsys.readouterr().out
