"""Seeded 8-16-wire finite Cauchy and bounded zero-reconstruction checks."""
import argparse
import hashlib
import json
from random import Random

from veritas.research.dense_cauchy_testbed import DenseWorkLimit, experiment, reconstruct_zero


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--wires', type=int, nargs='+', default=[8, 10, 12, 14, 16])
    parser.add_argument('--precision', type=int, default=2)
    parser.add_argument('--reconstruction-max-ops', type=int, default=40_000_000)
    args = parser.parse_args()
    results = []
    for wires in args.wires:
        if wires not in (8, 10, 12, 14, 16):
            raise ValueError('wires must be even and in 8..16')
        seed = 381 + wires
        rng = Random(seed)
        a = [rng.randrange(2) for _ in range(1 << wires)]
        b = [rng.randrange(2) for _ in range(1 << wires)]
        result = experiment(a, b, wires, precision=args.precision)
        try:
            result['zero_reconstruction'] = reconstruct_zero(
                a, b, wires, precision=args.precision,
                max_scalar_ops=args.reconstruction_max_ops)
        except DenseWorkLimit as exc:
            result['zero_reconstruction'] = {
                'status': 'BLOCKED_RESOURCE_LIMIT',
                'reason': str(exc),
                'partial_result_returned': False,
            }
        result['seed'] = seed
        result['table_a_sha256'] = hashlib.sha256(bytes(a)).hexdigest()
        result['table_b_sha256'] = hashlib.sha256(bytes(b)).hexdigest()
        results.append(result)
    print(json.dumps({'schema':'VERITAS_FINITE_DENSE_CAUCHY_382',
                      'results':results, 'asymptotic_claim':False}, indent=2))


if __name__ == '__main__':
    main()
