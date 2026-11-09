"""Finite recursive tensor execution with jets, tapered nodes and compact evidence."""
import argparse
from dataclasses import replace
from pathlib import Path

from veritas.research.parent_child_r98.model import ParentCall, Semantics, canonical, decode, read_vertex
from veritas.research.parent_child_r98.shrinking_cli import load_input, _check_output
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r99.cli import load_execution_report
from veritas.research.parent_child_r99.execution import ExecutionSpec
from veritas.research.parent_child_r910.engine import contract
from veritas.research.parent_child_r910.checker import verify
from veritas.research.independent_r82.point_mode_oracle import OracleLimits
from .layout import derandomized_layout, finite_layout


def load_parent(path):
    """Load the canonical parent schema, including full creation-time jet recipes."""
    if path.stat().st_size > 20_000_000:
        raise ValueError('parent input byte cap')
    record = decode(path.read_bytes())
    if 'edges' in record:
        return load_input(path, max_extension_degree=12)
    if (record.get('semantics') != Semantics.FINITE_SCALED_EXPERIMENT.value or
            record.get('source_context') is not None):
        raise ValueError('finite parent schema required')
    fields = dict(record)
    fields['semantics'] = Semantics(fields['semantics'])
    fields['vertices'] = tuple(read_vertex(v) for v in fields['vertices'])
    parent = ParentCall(**fields)
    if canonical(parent.record()) != canonical(record):
        raise ValueError('noncanonical parent fields')
    return parent


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--replay-dir', type=Path)
    parser.add_argument('--schedule', default='1:1,1:1', help='finite a:u pairs in depth order')
    parser.add_argument('--max-work', type=int, default=300_000_000)
    parser.add_argument('--max-seconds', type=int, default=600)
    parser.add_argument('--oracle-max-work', type=int, default=100_000_000)
    parser.add_argument('--cache-bytes', type=int, default=8_000_000)
    parser.add_argument('--max-certificate-bytes', type=int, default=100_000_000)
    parser.add_argument('--max-points', type=int, default=4096)
    parser.add_argument('--conformance', choices=('report', 'strict'),
                        help='check the hypotheses of the Lean theorem active_node_bounds')
    parser.add_argument('--layout', choices=('finite', 'derandomized'), default='finite')
    args = parser.parse_args(argv)
    _check_output(args.output_dir)
    schedule = tuple(tuple(int(n) for n in pair.split(':')) for pair in args.schedule.split(','))
    ExecutionSpec(schedule=schedule, max_points=args.max_points)
    policy = replace(DEFAULT_SHRINKING_POLICY, max_work=args.max_work,
        max_seconds=args.max_seconds, max_certificate_bytes=args.max_certificate_bytes)
    oracle = OracleLimits(args.oracle_max_work, args.max_seconds)
    parent = load_parent(args.input)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    (args.output_dir/'parent.json').write_bytes(canonical(parent.record()))
    if args.replay_dir:
        source = args.replay_dir
        report = load_execution_report(source/'report.json', max_bytes=policy.max_certificate_bytes)
    else:
        source = args.output_dir
        with (source/'events.jsonl').open('xb') as out:
            report = contract(parent, schedule=schedule, policy=policy, oracle_limits=oracle,
                max_points=args.max_points, cache_bytes=args.cache_bytes, layout_factory=finite_layout if args.layout == 'finite' else derandomized_layout,
                conformance=args.conformance, coefficient_encoding=True, compressed_records=True, evidence_sink=lambda raw: out.write(raw+b'\n'))
        (source/'report.json').write_bytes(canonical(report))
    if report.get('status') != 'PASS_FINITE_TWO_LEVEL_CAPABLE_RECURSION':
        print(report['status'])
        return 2
    with (source/'events.jsonl').open('rb') as stream:
        checked = verify(parent, (line.rstrip(b'\n') for line in stream), report,
                         policy=policy, oracle_limits=oracle)
    (args.output_dir/'verification.json').write_bytes(canonical(checked))
    print(checked['status'])
    return 0 if checked['status'] == 'PASS_INDEPENDENT_NUMERICAL_REPLAY' else 2


if __name__ == '__main__':
    raise SystemExit(main())
