"""Installed package point and full-grid certificate checks."""

from dataclasses import replace
import json
import platform
from pathlib import Path

from veritas.research.parent_child_r98.cycle_transfer import evaluate_cycle_transfer
from veritas.research.parent_child_r98.cycle_transfer_recovery import contract_cycle_transfer
from veritas.research.parent_child_r98.model import Budget
from veritas.research.parent_child_r98.shrinking_cli import load_input
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r98.transfer_io import load_transfer_layout
from veritas.research.parent_child_r98.transfer_recovery_verify import verify_transfer_recovery_certificate
from veritas.research.parent_child_r98.transfer_verify import verify_transfer_certificate
from veritas.research.tapered_v4.provenance import source_binding


def matmul(a, b, q):
    return tuple(tuple(sum(a[i][k]*b[k][j] for k in range(2)) % q
                       for j in range(2)) for i in range(2))


def independent_connected_oracle():
    # trace((K^T R K C)^22), W(1+4) = -84.
    q = 1 << 2944
    k, kt = ((1, 85), (0, -84)), ((1, 0), (85, -84))
    r, c = ((1, 2), (3, 4)), ((1, 2), (3, 5))
    a = matmul(matmul(matmul(kt, r, q), k, q), c, q)
    power = ((1, 0), (0, 1))
    for _ in range(22):
        power = matmul(power, a, q)
    return (power[0][0]+power[1][1]) % q


base = Path(__file__).parent
binding = source_binding()['digest']
policy = replace(DEFAULT_SHRINKING_POLICY, max_certificate_bytes=100_000_000,
                 max_calls=9899)
p = load_input(base / 'r98_transfer_cycle44.json')
l = load_transfer_layout(p, None, groups=64, budget=Budget(policy))
point = evaluate_cycle_transfer(p, l, 1, (1, 0), policy=policy)
assert point['status'] == 'PASS_FINITE_SCALED_CYCLE_TRANSFER_POINT', point
assert point['result'] == ((independent_connected_oracle(), 0),)
assert point['retained_modes'] == 22 and point['cycle_groups'] == 22
assert point['ledger']['actual_calls'] == 131
assert not point['source_qualified'] and not point['parent_contraction_recovered']
checked = verify_transfer_certificate(p, l, point['certificate'], policy=policy,
                                      expected_point=(1, (1, 0), 2944))
assert checked['status'] == 'PASS_FINITE_SCALED_CYCLE_TRANSFER_POINT', checked
assert checked['result'] == point['result']

p = load_input(base / 'r98_transfer_mode_cycle22.json', max_extension_degree=12)
l = load_transfer_layout(p, base / 'r98_transfer_mode_cycle22_layout.json',
                         groups=64, budget=Budget(policy))
full = contract_cycle_transfer(p, l, policy=policy)
assert full['status'] == 'PASS_FINITE_SCALED_CYCLE_TRANSFER_RECOVERY', full
assert full['result'] == ((17**22, 0, 0, 0, 0, 0, 0),)
assert full['retained_modes_per_nonzero_point'] == 3
assert full['point_evaluations'] == 134 and full['ledger']['actual_calls'] == 9899
assert full['full_hermite_grid'] == 'COMPLETE' and full['parent_contraction_recovered']
assert not full['source_qualified'] and not full['theorem_mode_enabled']
checked = verify_transfer_recovery_certificate(p, l, full['certificate'], policy=policy)
assert checked['status'] == 'PASS_FINITE_SCALED_CYCLE_TRANSFER_RECOVERY', checked
assert checked['result'] == full['result'] and checked['replayed_points'] == 134
assert binding == source_binding()['digest']
print(json.dumps({'status': 'PASS_INSTALLED_CYCLE_TRANSFER_AND_RECOVERY',
                  'python': platform.python_version(), 'source_binding': binding,
                  'connected_cycle_point': 'PASS_INDEPENDENT_2X2_MATRIX_ORACLE',
                  'point_modes': 22, 'point_calls': 131,
                  'full_recovery_result': str(17**22), 'full_recovery_calls': 9899,
                  'full_recovery_points': 134, 'full_recovery_modes': 3,
                  'full_recovery_certificate_bytes': len(full['certificate']),
                  'source_qualified': False, 'theorem_mode_enabled': False}))
