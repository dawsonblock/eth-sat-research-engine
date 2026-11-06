"""External finite cycle-point calculation and standalone certificate replay."""

import argparse
from dataclasses import asdict, replace
from hashlib import sha256
import json
from pathlib import Path

from .cycle_transfer import evaluate_cycle_transfer
from .model import Budget, Refusal, canonical
from .shrinking_cli import _check_output, load_input
from .shrinking_engine import DEFAULT_SHRINKING_POLICY
from .transfer_io import load_transfer_layout
from .transfer_verify import verify_transfer_certificate


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--groups', type=int, default=64)
    parser.add_argument('--layout-file', type=Path, help='optional independently audited finite layout')
    parser.add_argument('--node', type=int, choices=(-1, 1), default=1)
    parser.add_argument('--zeta', help='JSON integer coordinate array; defaults to scalar one')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--certificate', type=Path, required=True)
    parser.add_argument('--verify', action='store_true', help='replay an existing certificate')
    for name in ('work', 'seconds', 'calls', 'edges', 'precision', 'certificate_bytes'):
        parser.add_argument('--max-' + name.replace('_', '-'), type=int,
                            default=getattr(DEFAULT_SHRINKING_POLICY, 'max_' + name))
    args = parser.parse_args(argv)
    output_allowed = False
    try:
        _check_output(args.output)
        _check_output(args.certificate)
        protected = {args.input.resolve()}
        if args.layout_file is not None:
            protected.add(args.layout_file.resolve())
        if (args.output.resolve() == args.certificate.resolve()
                or args.output.resolve() in protected or args.certificate.resolve() in protected):
            raise ValueError('input, layout, report and certificate paths must be distinct')
        if not args.verify and args.certificate.exists():
            raise ValueError('refusing to overwrite an existing transfer certificate')
        output_allowed = True
        parent = load_input(args.input, max_extension_degree=12)
        degree = parent.defining_polynomial.bit_length() - 1
        zeta = tuple(json.loads(args.zeta)) if args.zeta else (1,) + (0,) * (degree - 1)
        policy = replace(DEFAULT_SHRINKING_POLICY, **{
            'max_' + name: getattr(args, 'max_' + name)
            for name in ('work', 'seconds', 'calls', 'edges', 'precision', 'certificate_bytes')
        })
        budget = Budget(policy)
        layout = load_transfer_layout(parent, args.layout_file, groups=args.groups, budget=budget)
        if args.verify:
            if args.certificate.stat().st_size > policy.max_certificate_bytes:
                raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'transfer certificate byte cap')
            payload = args.certificate.read_bytes()
            report = verify_transfer_certificate(parent, layout, payload, budget=budget,
                expected_point=(args.node, zeta, parent.precision + 64 * parent.edge_count))
        else:
            report = evaluate_cycle_transfer(parent, layout, args.node, zeta, budget=budget)
            payload = report.pop('certificate', None)
            if payload is not None:
                args.certificate.parent.mkdir(parents=True, exist_ok=True)
                with args.certificate.open('xb') as handle:
                    handle.write(payload)
        if payload is not None:
            report['certificate_file'] = str(args.certificate)
            report['certificate_sha256'] = sha256(payload).hexdigest()
            report['certificate_bytes'] = len(payload)
        report['policy'] = asdict(policy)
    except (ValueError, TypeError, KeyError, ArithmeticError, RuntimeError, OSError) as exc:
        report = {'status': getattr(exc, 'status', 'INVALID_CYCLE_TRANSFER_CALL'),
                  'reason': str(exc), 'source_qualified': False, 'theorem_mode_enabled': False}
    if output_allowed:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(canonical(report))
    print(json.dumps({'status': report['status'], 'reason': report.get('reason'),
                      'output': str(args.output) if output_allowed else None,
                      'certificate': report.get('certificate_file')}))
    return 0 if report['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
