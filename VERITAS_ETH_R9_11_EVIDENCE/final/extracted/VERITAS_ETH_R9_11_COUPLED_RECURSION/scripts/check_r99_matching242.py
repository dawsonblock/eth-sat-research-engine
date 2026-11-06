"""Independent closed-form root point check for the named matching fixture.

This checker supplies no value to production. It uses integer pair arithmetic
for U^2+U+1, and the explicit shifted L=2 Cauchy polynomial, without importing
the production contraction, child constructor, entry evaluator or ring code.
"""
import argparse
import json
from pathlib import Path

from veritas.research.parent_child_r98.model import canonical, decode


def check(input_path, event_path, report_path):
    data = decode(input_path.read_bytes())
    expected = {'root_s': 512, 'precision': 512, 'extension_degree': 2, 'edges': 242,
        'vertices': [{'side': side, 'ports': [e], 'table': values if e == 0 else [1, 1]}
                     for e in range(242) for side, values in [('row', [1, 3]), ('column', [2, 5])]]}
    if data != expected:
        raise ValueError('this closed-form checker applies only to the declared matching fixture')
    # Runtime reports carry an elapsed-time float; no report float enters the
    # arithmetic below. The separate recursive consumer checks its schema.
    report = json.loads(report_path.read_bytes())
    points, count = set(), 0
    with event_path.open('rb') as stream:
        for line in stream:
            event = decode(line.rstrip(b'\n'))
            if event['kind'] != 'point' or event['depth'] != 0:
                continue
            certificate = event['certificate']
            mode = certificate['original_modes']
            source = mode['d3_certificate']
            if (mode['irreducible_polynomial'] != 7 or source['M'] != 242 or source['L'] != 2 or
                any(len(packet['occupied_slots']) != 1 for packet in source['packets'])):
                raise ValueError('closed-form packet or extension hypotheses differ')
            t, zeta, precision = mode['node'], tuple(mode['zeta']), mode['precision']
            if precision != 512+64*242 or t not in (-1, 1) or zeta not in ((0, 0), (1, 0), (0, 1), (1, 1)):
                raise ValueError('closed-form point grid differs')
            if (t, zeta) in points:
                raise ValueError('duplicated closed-form point')
            points.add((t, zeta))
            modulus = 1 << precision
            def mul(x, y):
                return ((x[0]*y[0]-x[1]*y[1]) % modulus,
                        (x[0]*y[1]+x[1]*y[0]-x[1]*y[1]) % modulus)
            square, cube = mul(zeta, zeta), mul(mul(zeta, zeta), zeta)
            coefficients = (4, 8, -32) if t == -1 else (-12, -40, -32)
            w = tuple(sum(c*v[j] for c, v in zip(coefficients, (zeta, square, cube))) % modulus
                      for j in range(2))
            value = [((7 if j == 0 else 0) + 10*w[j]) * 2**241 % modulus for j in range(2)]
            if certificate['result'] != [value]:
                raise ValueError('recursive root point differs from independent closed form')
            count += 1
    if len(points) != 8 or report.get('result') != [[17*2**241, 0]]:
        raise ValueError('incomplete closed-form grid or wrong parent result')
    return {'status': 'PASS_INDEPENDENT_MATCHING242_CAUCHY_FORMULA', 'point_count': count,
            'result': report['result'], 'formula': '2^241 * (7 + 10 W_xx(t+4z))',
            'source_qualified': False, 'scope': 'NAMED_MATCHING_FIXTURE_ONLY'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--events', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.output.resolve().is_relative_to(root) or args.output.exists():
        parser.error('select a new evidence file outside the source tree')
    result = check(args.input, args.events, args.report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical(result))
    print(result['status'])
