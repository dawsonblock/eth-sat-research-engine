"""Audit one seeded 8--16-wire dense reference experiment in a fresh process.

Example: PYTHONPATH=src python scripts/validate_v39_dense_audit.py --wires 8
This does not run the v39 recursive engine or prove an asymptotic bound.
"""
import argparse
import hashlib
import json
from random import Random
import resource
import sys
from time import monotonic

from veritas.research.dense_cauchy_testbed import DenseWorkLimit, experiment, reconstruct_zero
from veritas.research.independent_dense_oracle import diagonal_node_four_oracle


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--wires', type=int, choices=(8, 10, 12, 14, 16), required=True)
    parser.add_argument('--max-table-entries', type=int, default=1 << 16)
    parser.add_argument('--max-scalar-ops', type=int, default=120_000_000)
    parser.add_argument('--max-reconstruction-ops', type=int, default=40_000_000)
    parser.add_argument('--max-live-jet-entries', type=int, default=2_000_000)
    args = parser.parse_args()
    if min(args.max_table_entries, args.max_scalar_ops, args.max_reconstruction_ops,
           args.max_live_jet_entries) < 1:
        parser.error('all resource caps must be positive')
    size = 1 << args.wires
    if size > args.max_table_entries:
        print(json.dumps({'status': 'INCONCLUSIVE_RESOURCE_LIMIT',
                          'reason': 'input table-entry cap exceeded'}))
        return
    start = monotonic()
    rng = Random(381 + args.wires)
    a = [rng.randrange(2) for _ in range(size)]
    b = [rng.randrange(2) for _ in range(size)]
    try:
        transformed = experiment(a, b, args.wires, precision=2, max_ops=args.max_scalar_ops)
        independent = diagonal_node_four_oracle(a, b, args.wires,
                                                max_table_entries=args.max_table_entries,
                                                max_scalar_ops=args.max_scalar_ops)
    except DenseWorkLimit as exc:
        print(json.dumps({'status': 'INCONCLUSIVE_RESOURCE_LIMIT', 'reason': str(exc)}))
        return
    if (transformed['original_count_modulus'] != independent['original_exact'] % 4 or
            transformed['deformed_value_modulus'] != independent['deformed_mod_4']):
        raise ArithmeticError('independent dense oracle disagrees with the experiment')
    try:
        reconstruction = reconstruct_zero(a, b, args.wires, precision=args.wires + 1,
                                          max_scalar_ops=args.max_reconstruction_ops,
                                          max_live_jet_entries=args.max_live_jet_entries)
        if reconstruction['reconstructed_at_zero'] != independent['original_exact']:
            raise ArithmeticError('zero reconstruction differs from independent count')
        reconstruction['original_count_uniquely_recovered'] = True
    except DenseWorkLimit as exc:
        reconstruction = {'status': 'BLOCKED_RESOURCE_LIMIT', 'reason': str(exc),
                          'partial_result_returned': False}
    peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform != 'darwin':
        peak_rss *= 1024
    result = {
        'schema': 'VERITAS_FINITE_DENSE_AUDIT_V1',
        'status': 'FINITE_DEFORMED_IDENTITY_CHECKED',
        'wires': args.wires, 'seed': 381 + args.wires,
        'table_a_sha256': hashlib.sha256(bytes(a)).hexdigest(),
        'table_b_sha256': hashlib.sha256(bytes(b)).hexdigest(),
        'independent_original_exact': independent['original_exact'],
        'independent_deformed_mod_4': independent['deformed_mod_4'],
        'deformed_value_mod_4': transformed['deformed_value_modulus'],
        'retained_modes': transformed['retained_structural_modes'],
        'discarded_modes': transformed['discarded_structural_modes'],
        'largest_child_wires': transformed['largest_child_wires'],
        'direct_halfedge_status': transformed['direct_halfedge_status'],
        'mode_work': transformed['counted_work_by_phase']['all_modes'],
        'baseline_work': transformed['counted_work_by_phase']['original'],
        'independent_oracle_scalar_ops': independent['scalar_ops_upper_count'],
        'independent_oracle_table_entries': independent['allocated_table_entries'],
        'reconstruction': reconstruction,
        'resource_limits': {'max_table_entries': args.max_table_entries,
                            'max_scalar_ops': args.max_scalar_ops,
                            'max_reconstruction_ops': args.max_reconstruction_ops,
                            'max_live_jet_entries': args.max_live_jet_entries},
        'process_peak_rss_bytes': peak_rss,
        'elapsed_seconds': round(monotonic() - start, 6),
        'accounting_complete': False,
        'resource_scope': ('selected scalar operations and process peak RSS; '
                           'not total bit operations or a hard memory limit'),
        'recursive_engine_used': False, 'subexponential_bound_proven': False,
    }
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
