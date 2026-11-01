"""Deterministic differential suite producing a machine-readable evidence report.

Run: python scripts/validate_10000.py --output validation/report.json
"""
import argparse
import json
import platform
import random
import sys
import time
from pathlib import Path
from veritas.core.cnf import CNF
from veritas.solvers.reference import solve, exhaustive_count
from veritas.research.tensor import eliminate, from_cnf


def validate(total=10_000):
    rng = random.Random(20261029)
    started = time.perf_counter()
    checked = 0
    tensor = 0
    for i in range(total):
        n = rng.randrange(0, 9)
        clauses = []
        for _ in range(rng.randrange(0, 16)):
            k = rng.randrange(0, 5) if n else 0
            clauses.append([rng.choice((-1, 1)) * rng.randint(1, n) for _ in range(k)])
        cnf = CNF.from_lists(n, clauses)
        expect = exhaustive_count(cnf, max_vars=8)
        result = solve(cnf, count=True, timeout_s=4)
        if result.status != 'COUNT' or result.count != expect:
            raise AssertionError(f'COUNT mismatch at instance {i}: {cnf.as_dict()}, got {result}')
        found = solve(cnf, timeout_s=4)
        if (expect > 0) != (found.status == 'SAT'):
            raise AssertionError(f'SAT mismatch at instance {i}')
        if found.status == 'SAT' and not cnf.evaluate(found.model):
            raise AssertionError(f'Witness mismatch at instance {i}')
        if i % 50 == 0 and sum(map(len, clauses)) <= 12:
            try:
                network = from_cnf(cnf, max_degree=15)
                contracted = eliminate(network, max_table_entries=1 << 12)
            except ValueError:
                continue
            if contracted != expect:
                raise AssertionError(f'Tensor mismatch at instance {i}')
            tensor += 1
        checked += 1
    return {
        'status': 'PASS', 'seed': 20261029, 'generated_instances': total,
        'reference_count_vs_exhaustive': checked, 'reference_sat_vs_exhaustive': checked,
        'tensor_vs_exhaustive': tensor,
        'seconds': round(time.perf_counter()-started, 3),
        'python_version': platform.python_version(), 'platform': platform.platform(),
        'scope': 'random CNF with n<=8, arbitrary clause lengths <=4; bounded reference algorithms only',
        'limitation': 'Finite differential tests do not constitute a formal proof or validate the ETH runtime theorem.'
    }


if __name__ == '__main__':
    arg = argparse.ArgumentParser()
    arg.add_argument('--output', type=Path)
    arg.add_argument('--cases', type=int, default=10000)
    args = arg.parse_args()
    report = validate(args.cases)
    txt = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(txt+'\n', encoding='utf-8')
    print(txt)
