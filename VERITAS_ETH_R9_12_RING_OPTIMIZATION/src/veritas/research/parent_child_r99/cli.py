"""External finite supported packet recovery, recursion and independent replay."""
import argparse
import json
import math
from dataclasses import asdict, replace
from pathlib import Path

from veritas.research.parent_child_r98.model import Budget, PacketLayout, Refusal, canonical, decode
from veritas.research.bounded_integer_encoding import decode_integer_object
from veritas.research.parent_child_r98.shrinking_cli import load_input, _check_output
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r98.shrinking_layout import construct_vertex_shrinking_layout
from veritas.research.parent_child_r98.packing import audit_layout
from .supported_engine import recover_supported_parent
from .supported_verify import verify_supported_recovery
from .degree_engine import contract_supported_recursion
from .degree_verify import verify_recursive_events


def load_execution_report(path, *, max_bytes):
    """Read a report whose only noninteger number is elapsed-time metadata.

    Mathematical certificate decoding remains integer-only. Do not use this
    reader for packet, support, entry or recovery certificates.
    """
    if path.stat().st_size > max_bytes:
        raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'recursive result report byte cap')
    raw = path.read_bytes()
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate execution report field')
            result[key] = value
        return decode_integer_object(result)
    def integer(value):
        if len(value) > 400:
            raise ValueError('execution report decimal integer cap')
        return int(value)
    def invalid(value):
        raise ValueError('nonfinite execution report number')
    report = json.loads(raw, object_pairs_hook=pairs, parse_int=integer, parse_constant=invalid)
    def check(value, path=()):
        if type(value) is float:
            if path != ('ledger', 'elapsed_seconds') or not math.isfinite(value) or value < 0:
                raise ValueError('floating point is allowed only for elapsed-time metadata')
        elif type(value) is dict:
            for key, item in value.items():
                check(item, path+(key,))
        elif type(value) is list:
            for i, item in enumerate(value):
                check(item, path+(i,))
    check(report)
    if type(report) is not dict or canonical(report) != raw:
        raise ValueError('noncanonical execution report')
    return report


def load_layout(parent, path, budget):
    if path.stat().st_size > budget.policy.max_certificate_bytes:
        raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'layout file byte cap')
    data = decode(path.read_bytes(), cap=budget.policy.max_certificate_bytes)
    if (set(data) != {'parent_digest', 'a', 'u', 'strategy', 'source'} or
            data['parent_digest'] != parent.content_digest):
        raise ValueError('layout input fields or parent binding')
    layout = PacketLayout(parent.content_digest, data['a'], data['u'], canonical(data['source']), data['strategy'])
    audit_layout(parent, layout)
    return layout


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--mode', choices=('recovery', 'recursion'), default='recovery')
    parser.add_argument('--layout-file', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--certificate', type=Path, required=True)
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--result-report', type=Path, help='required when replaying recursive events')
    parser.add_argument('--levels', type=int, default=2)
    parser.add_argument('--max-points', type=int, default=256)
    for name in ('work', 'seconds', 'calls', 'edges', 'precision', 'certificate_bytes', 'tuples'):
        parser.add_argument('--max-' + name.replace('_', '-'), type=int,
                            default=getattr(DEFAULT_SHRINKING_POLICY, 'max_' + name))
    args = parser.parse_args(argv)
    output_allowed = False
    try:
        _check_output(args.output)
        _check_output(args.certificate)
        protected = {p.resolve() for p in (args.input, args.layout_file, args.result_report) if p is not None}
        if (args.output.resolve() == args.certificate.resolve() or args.output.resolve() in protected or
                args.certificate.resolve() in protected or args.output.exists() or
                not args.verify and args.certificate.exists()):
            raise ValueError('distinct new output paths required; existing evidence is preserved')
        output_allowed = True
        policy = replace(DEFAULT_SHRINKING_POLICY, **{'max_' + name: getattr(args, 'max_' + name)
            for name in ('work', 'seconds', 'calls', 'edges', 'precision', 'certificate_bytes', 'tuples')})
        parent = load_input(args.input, max_extension_degree=12)
        layout = load_layout(parent, args.layout_file, Budget(policy)) if args.layout_file else None
        if args.mode == 'recovery':
            if layout is None:
                raise ValueError('general parent recovery requires an explicit layout file')
            if args.verify:
                if args.certificate.stat().st_size > policy.max_certificate_bytes:
                    raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'recovery certificate byte cap')
                certificate = decode(args.certificate.read_bytes(), cap=policy.max_certificate_bytes)
                report = verify_supported_recovery(parent, layout, certificate, policy=policy, max_points=args.max_points)
            else:
                report = recover_supported_parent(parent, layout, policy=policy, max_points=args.max_points)
                certificate = report.pop('certificate', None)
                if certificate is not None:
                    args.certificate.parent.mkdir(parents=True, exist_ok=True)
                    with args.certificate.open('xb') as stream:
                        stream.write(canonical(certificate))
        elif args.verify:
            if args.result_report is None:
                raise ValueError('recursive verification requires --result-report')
            claimed = load_execution_report(args.result_report, max_bytes=policy.max_certificate_bytes)
            with args.certificate.open('rb') as stream:
                def events():
                    while True:
                        raw = stream.readline(policy.max_certificate_bytes + 2)
                        if not raw:
                            break
                        if not raw.endswith(b'\n') or len(raw) > policy.max_certificate_bytes + 1:
                            raise ValueError('truncated or oversized recursive event line')
                        yield raw[:-1]
                report = verify_recursive_events(parent, events(), claimed, policy=policy, max_points=args.max_points)
        else:
            if not 1 <= args.levels <= policy.max_depth:
                raise ValueError('levels must fit the finite depth budget')
            def factory(call, a, u, budget):
                return layout if layout is not None and call.depth == parent.depth else construct_vertex_shrinking_layout(call, budget=budget)
            args.certificate.parent.mkdir(parents=True, exist_ok=True)
            with args.certificate.open('xb') as stream:
                report = contract_supported_recursion(parent, schedule=((1, 1),) * args.levels,
                    layout_factory=factory, policy=policy, max_points=args.max_points,
                    evidence_sink=lambda raw: stream.write(raw + b'\n'))
        report['policy'] = asdict(policy)
    except (ValueError, TypeError, KeyError, ArithmeticError, RuntimeError, OSError) as exc:
        report = {'status': getattr(exc, 'status', 'INVALID_SUPPORTED_CALL'), 'reason': str(exc),
                  'source_qualified': False}
    if output_allowed:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(canonical(report))
    print(report['status'], report.get('reason', ''))
    return 0 if report['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
