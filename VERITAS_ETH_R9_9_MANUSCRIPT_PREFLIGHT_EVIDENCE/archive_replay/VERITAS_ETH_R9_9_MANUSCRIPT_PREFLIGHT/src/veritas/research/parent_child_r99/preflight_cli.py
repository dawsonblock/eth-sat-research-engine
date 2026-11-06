"""Read-only finite packet planning, optional exact point count, external evidence."""
import argparse
from dataclasses import asdict, replace
from pathlib import Path

from veritas.research.parent_child_r98.model import Budget, canonical, digest
from veritas.research.parent_child_r98.shrinking_cli import _check_output, load_input
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r98.shrinking_layout import construct_vertex_shrinking_layout
from veritas.research.tapered_v4.provenance import source_binding
from .cli import load_layout
from .conformance import conformance_ledger
from .execution import ExecutionSpec, TupleStrategy
from .preflight import compare_group_counts, preflight_packet_recursion


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--layout-file', type=Path)
    parser.add_argument('--schedule', default='1:1,1:1', help='explicit finite a:u pairs')
    parser.add_argument('--tuples', choices=[s.value for s in TupleStrategy], default='complete_weighted')
    parser.add_argument('--max-points', type=int, default=256)
    parser.add_argument('--descendants', choices=('unplanned', 'singleton_first_fit'), default='unplanned')
    parser.add_argument('--compare-groups', help='comma-separated finite singleton group counts')
    parser.add_argument('--count-point', type=int, nargs=2, metavar=('NODE', 'RESIDUE_INDEX'),
                        help='optional exact complete weighted count at one point; no contractions')
    for name in ('work', 'seconds', 'calls', 'edges', 'precision', 'certificate_bytes', 'tuples'):
        parser.add_argument('--max-' + name.replace('_', '-'), type=int,
                            default=getattr(DEFAULT_SHRINKING_POLICY, 'max_' + name))
    args = parser.parse_args(argv)
    allowed = False
    try:
        _check_output(args.output)
        if args.output.exists() or args.output.resolve() in {args.input.resolve(),
                args.layout_file.resolve() if args.layout_file else args.input.resolve()}:
            raise ValueError('a new external output path is required')
        allowed = True
        policy = replace(DEFAULT_SHRINKING_POLICY, **{'max_' + name: getattr(args, 'max_' + name)
            for name in ('work', 'seconds', 'calls', 'edges', 'precision', 'certificate_bytes', 'tuples')})
        parent = load_input(args.input, max_extension_degree=12)
        binding = source_binding()['digest']
        if args.compare_groups:
            if args.layout_file or args.count_point:
                raise ValueError('group comparison uses its explicit singleton layout; no custom layout or point count')
            report = compare_group_counts(parent, tuple(int(x) for x in args.compare_groups.split(',')), policy=policy)
            report['status'] = 'FINITE_GROUP_COMPARISON_COMPLETE'
        else:
            spec = ExecutionSpec(schedule=tuple(tuple(int(x) for x in p.split(':'))
                                               for p in args.schedule.split(',')),
                                 tuples=TupleStrategy(args.tuples), max_points=args.max_points)
            if not args.layout_file and spec.schedule[0] != (1, 1):
                raise ValueError('non-singleton root schedule requires an explicit layout file')
            layout = (load_layout(parent, args.layout_file, Budget(policy)) if args.layout_file else
                      construct_vertex_shrinking_layout(parent, budget=Budget(policy)))
            report = preflight_packet_recursion(parent, layout, spec, policy=policy,
                                               descendant_strategy=args.descendants)
            report['execution_spec'] = spec.record()
            if args.count_point:
                from .basis import build_packet_modes, verify_packet_modes
                t, index = args.count_point
                e = parent.defining_polynomial.bit_length() - 1
                if not 0 <= index < min(1 << e, parent.edge_count * ((2 << layout.a) - 1) + 1):
                    raise ValueError('point is outside the complete prescribed grid')
                point = tuple((index >> j) & 1 for j in range(e))
                budget = Budget(policy)
                modes = build_packet_modes(parent, layout, t, point, budget=budget)
                checked = verify_packet_modes(parent, layout, modes, budget=budget)
                report['exact_point_count'] = {'node': t, 'residue_index': index, 'mode_digest': modes.content_digest,
                    'mode_count': len(modes.certificate['modes']), **checked,
                    'scope': 'THIS_POINT_ONLY_NOT_THE_RECURSIVE_GRID', 'contractions_performed': 0}
        report['conformance'] = conformance_ledger()
        report['policy'] = asdict(policy)
        report['implementation_source_sha256'] = binding
        if source_binding()['digest'] != binding:
            raise ValueError('source changed during preflight')
        report.pop('report_digest', None)
        report['report_digest'] = digest(canonical(report))
    except (ValueError, TypeError, KeyError, RuntimeError, ArithmeticError, MemoryError, OSError) as exc:
        report = {'status': getattr(exc, 'status', 'INVALID_PREFLIGHT_REQUEST'), 'reason': str(exc),
                  'source_qualified': False}
    if allowed:
        raw = canonical(report)
        if len(raw) > args.max_certificate_bytes:
            report = {'status': 'INCONCLUSIVE_RESOURCE_LIMIT', 'reason': 'complete report byte cap',
                      'source_qualified': False}
            raw = canonical(report)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('xb') as stream:
            stream.write(raw)
    print(report['status'])
    return 0 if report['status'] in ('PASS_FINITE_NECESSARY_CONDITIONS', 'FINITE_GROUP_COMPARISON_COMPLETE') else 2


if __name__ == '__main__':
    raise SystemExit(main())
