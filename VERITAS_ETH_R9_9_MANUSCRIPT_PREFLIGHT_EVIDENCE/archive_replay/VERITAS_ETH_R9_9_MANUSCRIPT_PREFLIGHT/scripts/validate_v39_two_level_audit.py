"""Run bounded two-level SAT examples against an independent assignment sum."""
import argparse
from itertools import product
import json
from time import monotonic

from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_recursive_contraction_v39 import describe_integer_network, run_tapered_finite


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--include-four-wire', action='store_true')
    parser.add_argument('--timeout', type=float, default=25.0)
    args = parser.parse_args()
    cases = [[[1, 2]]]
    if args.include_four_wire:
        cases.append([[1, 2], [-1, -2]])
    outputs = []
    for clauses in cases:
        n = 2
        expected = sum(all(any(values[abs(lit)-1] if lit > 0 else not values[abs(lit)-1]
                               for lit in clause) for clause in clauses)
                       for values in product((False, True), repeat=n))
        network = from_cnf(CNF.from_lists(n, clauses))
        described = describe_integer_network(network, creation_precision=n+1,
                                             defining_polynomial=first_irreducible(5))
        start = monotonic()
        result = run_tapered_finite(described, target_precision=n+1,
                                    max_recursive_levels=2, max_work=2_000_000,
                                    timeout_s=args.timeout)
        if result['status'] == 'FINITE_TAPERED_CHILD_RECOVERY_VERIFIED':
            if (result['result'] != ((expected, 0, 0, 0, 0),) or
                    result['recursive_levels_exercised'] != 2):
                raise ArithmeticError('two-level result or independent count mismatch')
        elif 'result' in result:
            raise ArithmeticError('an inconclusive run returned a partial result')
        outputs.append({'clauses': clauses, 'wires': network.edges,
                        'independent_reference_count': expected,
                        'elapsed_seconds': round(monotonic()-start, 6), 'result': result})
    print(json.dumps({'schema': 'VERITAS_FINITE_TWO_LEVEL_AUDIT_V1',
                      'results': outputs, 'subexponential_runtime_proven': False},
                     sort_keys=True))


if __name__ == '__main__':
    main()
