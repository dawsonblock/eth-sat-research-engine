"""Run or independently replay bounded, degree-certified tapered recursion."""
import argparse
from dataclasses import replace
from pathlib import Path

from veritas.research.parent_child_r98.model import Budget, canonical
from veritas.research.parent_child_r98.shrinking_cli import load_input, _check_output
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r98.shrinking_layout import construct_vertex_shrinking_layout
from veritas.research.parent_child_r98.packing import audit_layout
from veritas.research.parent_child_r99.cli import load_layout, load_execution_report
from veritas.research.parent_child_r99.resources import prepare_scalar_field
from veritas.research.parent_child_r99.row_degree import certify_row_degree, verify_row_degree
from .engine import contract
from .checker import verify
from .preflight import preflight


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--layout-file', type=Path)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--replay-dir', type=Path)
    parser.add_argument('--preflight-only', action='store_true')
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--levels', type=int, default=2)
    parser.add_argument('--max-points', type=int, default=4096)
    parser.add_argument('--max-work', type=int, default=300_000_000)
    parser.add_argument('--max-seconds', type=int, default=600)
    parser.add_argument('--cache-bytes', type=int, default=1_000_000)
    parser.add_argument('--max-certificate-bytes', type=int, default=100_000_000)
    args = parser.parse_args(argv)
    _check_output(args.output_dir)
    if not 1 <= args.levels <= 16:
        parser.error('levels must be 1..16')
    policy = replace(DEFAULT_SHRINKING_POLICY, max_work=args.max_work,
        max_seconds=args.max_seconds, max_certificate_bytes=args.max_certificate_bytes)
    setup = Budget(policy)
    root = load_input(args.input, max_extension_degree=12)
    # Authenticate the original parent before transporting scalar entries.
    layout = load_layout(root, args.layout_file, setup) if args.layout_file else None
    certificate = certify_row_degree(root,1,budget=setup)
    verify_row_degree(root,1,certificate,budget=setup)
    parent = prepare_scalar_field(root,certificate['degree_bound']+1) if root.edge_count>4 else root
    if layout is not None:
        layout = replace(layout,parent_digest=parent.content_digest)
        audit_layout(parent,layout)
    elif parent.edge_count>4:
        layout = construct_vertex_shrinking_layout(parent,budget=setup)
    args.output_dir.mkdir(parents=True,exist_ok=False)
    (args.output_dir/'parent.json').write_bytes(canonical(parent.record()))
    if args.replay_dir:
        report = load_execution_report(args.replay_dir/'report.json',max_bytes=policy.max_certificate_bytes)
        with (args.replay_dir/'events.jsonl').open('rb') as stream:
            checked = verify(parent,(line.rstrip(b'\n') for line in stream),report,policy=policy)
        (args.output_dir/'verification.json').write_bytes(canonical(checked))
        print(checked['status'])
        return 0 if checked['status']=='PASS_INDEPENDENT_NUMERICAL_REPLAY' else 2
    planned = preflight(parent,layout,levels=args.levels,max_points=args.max_points,policy=policy) if layout else None
    (args.output_dir/'preflight.json').write_bytes(canonical(planned))
    if args.preflight_only or (planned and not planned['admitted']):
        print(planned['status'] if planned else 'PASS_LEAF_TOPOLOGY')
        return 0 if planned is None or planned['admitted'] else 2
    def factory(call,a,u,budget):
        return layout if call.depth==parent.depth else construct_vertex_shrinking_layout(call,budget=budget)
    with (args.output_dir/'events.jsonl').open('xb') as out:
        report = contract(parent,schedule=((1,1),)*args.levels,policy=policy,
            max_points=args.max_points,cache_bytes=args.cache_bytes,layout_factory=factory,
            preflight_work=setup.work+(planned['preflight_work_units'] if planned else 0),
            evidence_sink=lambda raw:out.write(raw+b'\n'))
    (args.output_dir/'report.json').write_bytes(canonical(report))
    success = report['status']=='PASS_FINITE_TWO_LEVEL_CAPABLE_RECURSION'
    if args.verify and success:
        with (args.output_dir/'events.jsonl').open('rb') as stream:
            checked = verify(parent,(line.rstrip(b'\n') for line in stream),report,policy=policy)
        (args.output_dir/'verification.json').write_bytes(canonical(checked))
        success = checked['status']=='PASS_INDEPENDENT_NUMERICAL_REPLAY'
    print(report['status'])
    return 0 if success else 2


if __name__ == '__main__':
    raise SystemExit(main())
