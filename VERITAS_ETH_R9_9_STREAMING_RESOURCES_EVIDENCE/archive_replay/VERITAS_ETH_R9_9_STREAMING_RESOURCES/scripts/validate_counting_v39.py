"""Reproducible finite experiment for the shared-linear-summary construction.

Implements the checkable part of `sec:counting` and `sec:construction` of the
pinned preprint: for a battery of bounded-occurrence CNFs, count satisfying
assignments by the replacement-form pipeline and compare against exhaustive
enumeration. Also reports the theorem-scale parameter schedule of
`lem:incidence-parameters` and one full `def:layout` certificate.

This establishes finite correctness only. It does not establish the paper's
subexponential running-time bound: the sizes a finite reference can execute
fail the balance hypotheses, which the report states explicitly.
"""
from __future__ import annotations

import argparse
from itertools import product
import json

from veritas.research.eth_counting_v39 import (
    build_auxiliary_layout, build_embedded_forms, build_schedules, cnf_instance,
    count_instance, scaled_parameters, theorem_parameters_from_lambda,
    verify_layout,
)

SCHEMA = 'VERITAS_SHARED_LINEAR_SUMMARIES_V39'

CASES = (
    (2, [[1, 2]]),
    (3, [[1, 2]]),
    (2, [[1, 2], [-1, -2]]),
    (3, [[1, 2, 3]]),
    (3, [[1, 2], [2, 3]]),
    (4, [[1, 2], [3, 4]]),
    (4, [[1, 2, 3], [2, 3, 4]]),
    (4, [[1, 2], [-1, 3], [2, -3]]),
    (5, [[1, 2], [2, 3], [3, 4], [4, 5]]),
    (4, [[1], [-1]]),
    (6, [[1, 2], [3, 4], [5, 6]]),
)


def brute_force(instance):
    total = 0
    for bits in product((0, 1), repeat=instance.n):
        value = 1
        for scope, factor in zip(instance.scopes, instance.factors):
            value *= factor.evaluate([bits[v] for v in scope])
        total += value
    return int(total)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-work', type=int, default=50_000_000)
    parser.add_argument('--max-pairs', type=int, default=5_000_000)
    args = parser.parse_args()

    results = []
    for n, clauses in CASES:
        instance = cnf_instance(clauses, n)
        parameters = scaled_parameters(instance.n, instance.b, instance.w,
                                        instance.M, instance.d, r=2, Q=2, R=2)
        outcome = count_instance(instance, parameters, max_work=args.max_work,
                                 max_pairs=args.max_pairs)
        expected = brute_force(instance)
        results.append({
            'n': n, 'clauses': clauses,
            'M': instance.M, 'b': instance.b, 'w': instance.w, 'd': instance.d,
            'r': parameters.r, 'Q': parameters.Q, 'R': parameters.R,
            'D': parameters.D, 'd_H': parameters.degree_bound,
            'q': parameters.q, 'J': parameters.J,
            'count': outcome.value, 'enumerated': expected,
            'matches': outcome.value == expected,
            'design_identity_valid': outcome.layout['valid_identity'],
            'cost_hypotheses_hold': outcome.layout['cost_hypotheses_hold'],
            'restriction_pairs_per_point': outcome.pairs_per_point,
            'measurement_tuples': outcome.measurement_tuples,
            'assignments_examined': outcome.assignments_examined,
        })

    # A full design certificate for one representative instance.
    instance = cnf_instance([[1, 2], [-1, 3], [2, -3]], 4)
    parameters = scaled_parameters(instance.n, instance.b, instance.w,
                                    instance.M, instance.d, r=2, Q=2, R=2)
    schedules = build_schedules(instance, parameters)
    forms = build_embedded_forms(instance, parameters, schedules,
                                 build_auxiliary_layout(parameters))
    report = verify_layout(forms)

    # Theorem-scale schedule: the formulas of eq:parameter-QR with every
    # numerical hypothesis of lem:incidence-parameters checked.
    theorem = theorem_parameters_from_lambda(2 ** 34, b=3, w=3, M=3, d=3, beta=1)

    print(json.dumps({
        'schema': SCHEMA,
        'cases': results,
        'all_cases_match': all(entry['matches'] for entry in results),
        'design_certificate': report.summary(),
        'theorem_scale_parameters': {
            key: value for key, value in theorem.items() if key != 'parameters'},
        'finite_reference_only': True,
        'runtime_bound_proven': False,
        'subexponential_runtime_proven': False,
    }, sort_keys=True))


if __name__ == '__main__':
    main()
