"""Generate or replay an eight-wire finite tapered-v4 experiment."""
from dataclasses import asdict
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from time import monotonic

try:
    import resource
except ImportError:  # Windows does not provide resource.getrusage.
    resource = None

from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_recursive_contraction_v39 import describe_integer_network
from veritas.research.tapered_v4 import TaperedState, RecursionPolicy, contract_recursive, replay_certificate

SCHEMA_V1 = 'VERITAS_TAPERED_V4_EIGHT_WIRE_EXPERIMENT_V1'
SCHEMA = 'VERITAS_TAPERED_V4_EIGHT_WIRE_EXPERIMENT_V3'


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii')


def _evidence_digest(record):
    payload = dict(record)
    payload.pop('evidence_sha256', None)
    return sha256(_canonical(payload)).hexdigest()


def process_peak_rss_bytes():
    if resource is None or sys.platform not in ('darwin', 'linux'):
        return None
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value if sys.platform == 'darwin' else value * 1024


def state_for(cnf_data):
    cnf = CNF.from_lists(cnf_data['n'], cnf_data['clauses'])
    p = cnf.n + 1
    f = first_irreducible(5)
    network = describe_integer_network(from_cnf(cnf), creation_precision=p, defining_polynomial=f)
    return TaperedState(network, 0, p, f, 1, network.edges)


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--write', type=Path)
    group.add_argument('--replay', type=Path)
    args = parser.parse_args()
    start = monotonic()
    if args.write:
        cnf = CNF.from_lists(8, [[i] for i in range(1, 9)]).as_dict()
        state = state_for(cnf)
        # Pin a finite cap with headroom for tuple, recipe and oracle checks.
        # Work-unit totals depend on the implementation and are reported by
        # each run; they do not include all bit operations or hard memory use.
        policy = RecursionPolicy(max_active_wires=8, leaf_edge_limit=7,
                                 finite_parameters=(1, 1, 4), max_depth=4,
                                 max_certificate_bytes=30_000_000,
                                 verify_small_nodes=True, oracle_edge_limit=8,
                                 max_seconds=120, max_work=3_000_000)
        result = contract_recursive(state, policy)
        if result['status'] != 'EXACT_MODULAR_CONTRACTION_FINITE':
            print(json.dumps({'status': result['status'], 'reason': result.get('reason'),
                              'max_work': policy.max_work}))
            return 1
        if result['result'] != ((1, 0, 0, 0, 0),):
            raise ArithmeticError('forced-assignment count differs from one')
        certificate = result['certificate']
        elapsed = round(monotonic() - start, 6)
        peak_rss = process_peak_rss_bytes()
        record = {'schema': SCHEMA, 'cnf': cnf, 'policy': asdict(policy),
                  'source_binding': certificate['source_binding'],
                  'manuscript_binding': certificate['manuscript_binding'],
                  'input_network_digest': certificate['input_network_digest'],
                  'point_coverage': certificate['point_coverage'],
                  'certificate': result['certificate'], 'ledger': result['ledger'],
                  'point_identity_coverage': result['point_identity_coverage'],
                  'elapsed_seconds': elapsed,
                  'process_peak_rss_bytes': peak_rss,
                  'peak_rss_unit': ('unavailable' if resource is None else 'bytes'),
                  'peak_rss_hard_limit_enforced': False}
        record['evidence_sha256'] = _evidence_digest(record)
        args.write.write_text(json.dumps(record, sort_keys=True, separators=(',', ':')) + '\n',
                              encoding='utf8')
        print(json.dumps({'status': result['status'], 'path': str(args.write),
                          'result': result['result'], 'ledger': result['ledger'],
                          'point_identity_coverage': result['point_identity_coverage'],
                          'elapsed_seconds': elapsed,
                          'process_peak_rss_bytes': peak_rss}))
        return 0
    record = json.loads(args.replay.read_text(encoding='utf8'))
    schema = record.get('schema')
    if schema not in (SCHEMA, SCHEMA_V1):
        print(json.dumps({'status': 'INVALID_CERTIFICATE', 'valid': False}))
        return 1
    if schema == SCHEMA:
        if record.get('evidence_sha256') != _evidence_digest(record):
            print(json.dumps({'status': 'EVIDENCE_HASH_MISMATCH', 'valid': False}))
            return 1
        certificate = record.get('certificate', {})
        if (not isinstance(certificate, dict) or
                record.get('source_binding') != certificate.get('source_binding') or
                record.get('manuscript_binding') != certificate.get('manuscript_binding') or
                record.get('input_network_digest') != certificate.get('input_network_digest') or
                record.get('point_coverage') != certificate.get('point_coverage')):
            print(json.dumps({'status': 'INVALID_CERTIFICATE', 'valid': False,
                              'reason': 'outer V3 evidence disagrees with its execution transcript'}))
            return 1
    settings = dict(record['policy'])
    settings['finite_parameters'] = tuple(settings['finite_parameters'])
    verdict = replay_certificate(state_for(record['cnf']), RecursionPolicy(**settings),
                                 record['certificate'])
    verdict['elapsed_seconds'] = round(monotonic() - start, 6)
    verdict['process_peak_rss_bytes'] = process_peak_rss_bytes()
    verdict['evidence_schema'] = schema
    verdict['legacy_evidence_wrapper'] = schema == SCHEMA_V1
    if not verdict.get('valid') and verdict.get('status') == 'INCONCLUSIVE_RESOURCE_LIMIT':
        # The recorded policy, not the current code, sets the budget here.
        verdict['recorded_max_work'] = settings.get('max_work')
    print(json.dumps(verdict))
    return 0 if verdict.get('valid') else 1


if __name__ == '__main__':
    raise SystemExit(main())
