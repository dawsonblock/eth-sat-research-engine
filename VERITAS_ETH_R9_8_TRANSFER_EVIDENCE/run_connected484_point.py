"""Run one nonconstant connected 484-edge transfer point; no Hermite claim."""
from dataclasses import asdict, replace
from hashlib import sha256
from pathlib import Path
import json
import platform
import sys
import time

from test_cycle_transfer_fixture import cycle_parent, scalar_cycle_oracle
from veritas.research.parent_child_r98.cycle_transfer import evaluate_cycle_transfer
from veritas.research.parent_child_r98.model import Budget, canonical
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r98.shrinking_layout import construct_vertex_shrinking_layout
from veritas.research.paper_verification.source_registry import source_registry
from veritas.research.tapered_v4.provenance import source_binding

ROOT = Path.cwd()
OUT = Path(__file__).resolve().parent
CERT = OUT / 'connected484-nonconstant-point.cert.json'
REPORT = OUT / 'connected484-nonconstant-point.json'
FIXTURE = ROOT / 'tests/test_cycle_transfer_fixture.py'
assert not CERT.exists() and not REPORT.exists(), 'refuse to overwrite prior evidence'
binding = source_binding()['digest']
fixture_hash = sha256(FIXTURE.read_bytes()).hexdigest()
runner_hash = sha256(Path(__file__).read_bytes()).hexdigest()
policy = replace(DEFAULT_SHRINKING_POLICY, max_certificate_bytes=100_000_000,
                 max_work=1_000_000_000, max_seconds=600)
record = {'schema': 'VERITAS_R98_CONNECTED484_TRANSFER_POINT_V1',
          'status': 'INCOMPLETE', 'source_qualified': False,
          'theorem_mode_enabled': False, 'scaled_experiment': True,
          'point_only': True, 'hermite_recovery': 'NOT_RUN',
          'parent_contraction_recovered': False, 'source_sha256': binding,
          'runner_sha256': runner_hash, 'fixture_sha256': fixture_hash,
          'paper': source_registry(), 'python': platform.python_version(),
          'policy': asdict(policy), 'node': 1, 'zeta': [1, 0], 'groups': 512}
start = time.monotonic()
try:
    parent = cycle_parent(484, 512)
    planning_budget = Budget(policy)
    layout = construct_vertex_shrinking_layout(parent, groups=512, budget=planning_budget)
    record.update(parent_digest=parent.content_digest, layout_digest=layout.content_digest,
                  parent_edges=484, planning_ledger=planning_budget.report())
    result = evaluate_cycle_transfer(parent, layout, 1, (1, 0), policy=policy)
    record.update(status=result['status'], execution_ledger=result.get('ledger'),
                  reason=result.get('reason'))
    if not result['status'].startswith('PASS_'):
        raise RuntimeError('production transfer refused: ' + str(result.get('reason')))
    expected = scalar_cycle_oracle(484, 31488, -84)
    if result['result'] != ((expected, 0),) or expected == 0:
        raise ValueError('computed point differs from independent nonzero integer matrix oracle')
    if (result['parent_edges'], result['group_count'], result['point_precision'],
        result['retained_modes'], result['cycle_groups']) != (484, 512, 31488, 242, 242):
        raise ValueError('actual point metadata differs')
    if not result['all_actual_children_are_leaves'] or result['ledger']['actual_calls'] != 1239:
        raise ValueError('actual local child inventory differs')
    cert = result['certificate']
    CERT.write_bytes(cert)
    record.update(status=result['status'], actual_calls=result['ledger']['actual_calls'],
        point_precision=31488, retained_modes=242, cycle_groups=242,
        all_actual_children_are_leaves=True,
        complete_weighted_tuple_count=result['complete_weighted_tuple_count'],
        binary_support_bound=result['potentially_nonzero_binary_tuple_count'],
        result=result['result'], independent_expected_sha256=sha256(canonical(((expected, 0),))).hexdigest(),
        result_sha256=sha256(canonical(result['result'])).hexdigest(),
        independent_scalar_oracle='PASS_MATRIX_TRACE_ON_PARENT_CYCLE',
        oracle_scope='ONE_INTERPOLATION_POINT_ONLY',
        internal_independent_certificate=result['independent_certificate'],
        internal_independent_half_edge=result['independent_point_oracle'],
        certificate_file=CERT.name, certificate_sha256=sha256(cert).hexdigest(),
        certificate_bytes=len(cert))
    if source_binding()['digest'] != binding or sha256(FIXTURE.read_bytes()).hexdigest() != fixture_hash:
        raise ValueError('source or fixture changed during execution')
except (ValueError, TypeError, KeyError, ArithmeticError, RuntimeError, MemoryError) as exc:
    record.update(status=record['status'] if record['status'].startswith('INCONCLUSIVE_') else 'FAILED_OR_INCONCLUSIVE',
                  reason=str(exc))
    record.pop('result', None)
record['elapsed_seconds'] = time.monotonic() - start
REPORT.write_bytes(canonical(record))
print(json.dumps({'status': record['status'], 'reason': record.get('reason'),
                  'actual_calls': record.get('actual_calls'),
                  'certificate_bytes': record.get('certificate_bytes'),
                  'elapsed_seconds': record['elapsed_seconds'], 'report': str(REPORT)}))
sys.exit(0 if record['status'].startswith('PASS_') else 1)
