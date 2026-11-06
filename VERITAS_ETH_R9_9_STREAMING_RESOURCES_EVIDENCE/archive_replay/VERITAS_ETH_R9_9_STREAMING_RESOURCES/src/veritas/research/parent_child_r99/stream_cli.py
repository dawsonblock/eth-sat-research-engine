"""Explicit finite streaming run with automatic scalar-root field preparation."""
import argparse
from dataclasses import replace
import json
from pathlib import Path

from veritas.research.parent_child_r98.model import canonical
from veritas.research.parent_child_r98.shrinking_cli import load_input, _check_output
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from .resources import prepare_scalar_field
from .stream_engine import contract_streaming
from .stream_verify import verify_streaming


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output-dir', type=Path, required=True)
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
                     max_work=args.max_work, max_calls=args.max_calls)
    root = load_input(args.input, max_extension_degree=12)
    parent = prepare_scalar_field(root, 3*root.edge_count+1) if root.edge_count > 4 else root
    args.output_dir.mkdir(parents=True, exist_ok=False)
    (args.output_dir/'parent.json').write_bytes(canonical(parent.record()))
    with (args.output_dir/'events.jsonl').open('xb') as output:
        report = contract_streaming(parent, schedule=((1, 1),)*args.levels, policy=policy,
            max_points=args.max_points, cache_bytes=args.cache_bytes,
            evidence_sink=lambda raw: output.write(raw+b'\n'))
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
