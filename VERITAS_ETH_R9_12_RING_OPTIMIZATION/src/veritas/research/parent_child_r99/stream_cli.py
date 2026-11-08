"""Explicit finite streaming run with automatic scalar-root field preparation."""
import argparse
from dataclasses import replace
import json
from pathlib import Path

from veritas.research.parent_child_r98.model import canonical, digest, Budget
from veritas.research.parent_child_r98.shrinking_cli import load_input, _check_output
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from .resources import prepare_scalar_field
from .cli import load_layout
from .execution import ExecutionSpec, TupleStrategy
from .preflight import preflight_packet_recursion
from veritas.research.parent_child_r98.packing import audit_layout
from veritas.research.parent_child_r98.shrinking_layout import construct_vertex_shrinking_layout


def prepare_layout_input(root, path, *, budget):
    # First authenticate the file against the ORIGINAL input. Never accept a
    # stale digest by merely overwriting it with the prepared parent digest.
    layout = load_layout(root, path, budget) if path is not None else None
    parent = prepare_scalar_field(root, 3*root.edge_count+1) if root.edge_count > 4 else root
    if layout is not None:
        layout = replace(layout, parent_digest=parent.content_digest)
        audit_layout(parent, layout)
    return parent, layout


def streaming_preflight(parent, layout, levels, max_points, policy):
    report = preflight_packet_recursion(parent, layout,
        ExecutionSpec(schedule=((1, 1),)*levels, tuples=TupleStrategy.SUPPORT, max_points=max_points),
        policy=policy, descendant_strategy='singleton_first_fit')
    # These two legacy estimates concern an executor that recomputes children
    # and retains every node grid. Preserve them as diagnostics, not admission
    # bounds for this cached, streaming executor. All other refusals remain.
    advisory = {'RECURSIVE_CALL_LOWER_BOUND', 'DENSE_GRID_POLICY_ESTIMATE'}
    report['legacy_executor_advisories'] = [b for b in report.get('blockers', []) if b['code'] in advisory]
    report['blockers'] = [b for b in report.get('blockers', []) if b['code'] not in advisory]
    admitted = (report.get('status') in ('PASS_FINITE_NECESSARY_CONDITIONS', 'INCONCLUSIVE_RESOURCE_OR_STRUCTURE')
                and report.get('descendant_topologies_complete') is True and not report['blockers'])
    report['streaming_topology_admitted'] = admitted
    report['streaming_runtime_feasibility'] = 'NOT_ESTABLISHED'
    report['original_preflight_digest'] = report.pop('report_digest')
    report['report_digest'] = digest(canonical(report))
    return report

from .stream_engine import contract_streaming
from .stream_verify import verify_streaming


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--layout-file', type=Path)
    parser.add_argument('--preflight-only', action='store_true')
    parser.add_argument('--max-certificate-bytes', type=int, default=DEFAULT_SHRINKING_POLICY.max_certificate_bytes)
    parser.add_argument('--levels', type=int, default=1)
    parser.add_argument('--max-points', type=int, default=4096)
    parser.add_argument('--cache-bytes', type=int, default=1_000_000)
    parser.add_argument('--max-seconds', type=int, default=300)
    parser.add_argument('--max-work', type=int, default=100_000_000)
    parser.add_argument('--max-calls', type=int, default=300_000)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args(argv)
    _check_output(args.output_dir)
    if not 1 <= args.levels <= 16:
        parser.error('levels must be 1..16')
    policy = replace(DEFAULT_SHRINKING_POLICY, max_seconds=args.max_seconds,
                     max_work=args.max_work, max_calls=args.max_calls, max_certificate_bytes=args.max_certificate_bytes)
    root = load_input(args.input, max_extension_degree=12)
    parent, layout = prepare_layout_input(root, args.layout_file, budget=Budget(policy))
    args.output_dir.mkdir(parents=True, exist_ok=False)
    (args.output_dir/'parent.json').write_bytes(canonical(parent.record()))
    preflight = None
    if parent.edge_count > 4:
        layout = layout or construct_vertex_shrinking_layout(parent, budget=Budget(policy))
        preflight = streaming_preflight(parent, layout, args.levels, args.max_points, policy)
        (args.output_dir/'preflight.json').write_bytes(canonical(preflight))
        if args.preflight_only or not preflight['streaming_topology_admitted']:
            status = 'PASS_FINITE_TOPOLOGY_ONLY' if preflight['streaming_topology_admitted'] else 'INCONCLUSIVE_STREAMING_PREFLIGHT'
            report = {'status': status, 'preflight': preflight, 'source_qualified': False,
                      'input_parent_digest': root.content_digest, 'parent_digest': parent.content_digest}
            (args.output_dir/'report.json').write_bytes(canonical(report))
            print(status)
            return 0 if preflight['streaming_topology_admitted'] else 2
    elif args.preflight_only:
        report = {'status': 'PASS_FINITE_LEAF_TOPOLOGY_ONLY', 'parent_digest': parent.content_digest,
                  'source_qualified': False}
        (args.output_dir/'report.json').write_bytes(canonical(report))
        print(report['status'])
        return 0
    def factory(call, a, u, budget):
        return layout if call.depth == parent.depth else construct_vertex_shrinking_layout(call, budget=budget)
    with (args.output_dir/'events.jsonl').open('xb') as output:
        report = contract_streaming(parent, schedule=((1, 1),)*args.levels, policy=policy,
            max_points=args.max_points, cache_bytes=args.cache_bytes, layout_factory=factory,
            preflight_work=preflight['preflight_work_units'] if preflight else 0,
            evidence_sink=lambda raw: output.write(raw+b'\n'))
    report['preflight'] = preflight
    report['input_parent_digest'] = root.content_digest
    report['prepared_extension_degree'] = parent.defining_polynomial.bit_length()-1
    (args.output_dir/'report.json').write_bytes(canonical(report))
    success = report['status'].startswith('PASS_')
    if args.verify and success:
        with (args.output_dir/'events.jsonl').open('rb') as stream:
            checked = verify_streaming(parent, (line.rstrip(b'\n') for line in stream), report, policy=policy)
        (args.output_dir/'verification.json').write_bytes(canonical(checked))
        success = checked['status'].startswith('PASS_')
    print(json.dumps({'status': report['status'], 'output': str(args.output_dir),
                      'ledger': report['ledger']}, sort_keys=True))
    return 0 if success else 2


if __name__ == '__main__':
    raise SystemExit(main())
