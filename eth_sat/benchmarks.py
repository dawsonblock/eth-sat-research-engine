"""Small reproducible benchmark driver (no benchmark result is qualification)."""

from __future__ import annotations

import argparse
import json
import random
import time

from .algebraic import algebraic_count
from .measurements import cnf_shared_measurement_count
from .model import CNF
from .references import dpll_count


def random_formula(seed: int, variables: int, clauses: int) -> CNF:
    rng = random.Random(seed)
    generated = []
    for _ in range(clauses):
        width = rng.randint(1, min(3, variables)) if variables else 0
        generated.append(
            tuple(
                (1 if rng.randrange(2) else -1) * rng.randint(1, variables)
                for _ in range(width)
            )
        )
    return CNF.from_signed_clauses(variables, generated)


def timed(callable_):
    started = time.perf_counter()
    value = callable_()
    return value, time.perf_counter() - started


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variables", type=int, default=12)
    parser.add_argument("--clauses", type=int, default=24)
    parser.add_argument("--seed", type=int, default=20261029)
    args = parser.parse_args()
    if args.variables < 1 or args.clauses < 0:
        parser.error("variables must be positive and clauses nonnegative")
    formula = random_formula(args.seed, args.variables, args.clauses)
    results = {}
    for name, engine in (
        ("algebraic_interpolation", lambda: algebraic_count(formula).count),
        ("shared_measurements", lambda: cnf_shared_measurement_count(formula)),
        ("dpll", lambda: dpll_count(formula)),
    ):
        value, seconds = timed(engine)
        results[name] = {"count": value, "seconds": round(seconds, 6)}
    results["input"] = {
        "seed": args.seed,
        "variables": args.variables,
        "clauses": args.clauses,
        "dimacs_sha256": __import__("hashlib").sha256(
            formula.to_dimacs().encode("utf-8")
        ).hexdigest(),
    }
    results["counts_agree"] = len(
        {
            results[name]["count"]
            for name in ("algebraic_interpolation", "shared_measurements", "dpll")
        }
    ) == 1
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0 if results["counts_agree"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
