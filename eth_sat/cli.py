"""Command-line interface for the ETH-SAT research prototype."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .algebraic import algebraic_count, grouped_count
from .examples import simple
from .layout import build_spectral_cnf_layout
from .measurements import cnf_shared_measurement_count
from .model import CNF
from .references import dpll_count
from .subexponential import count_subexponential
from .taylor import spectral_taylor_count


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eth-sat",
        description="Exact counting prototype and research subexponential pipeline.",
    )
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--example", choices=("simple",), help="run a bundled example")
    inputs.add_argument("--input", type=Path, help="read a DIMACS CNF file")
    parser.add_argument(
        "--engine",
        choices=(
            "algebraic", "shared", "grouped", "spectral", "dpll",
            "subexponential", "compare",
        ),
        default="compare",
    )
    parser.add_argument("--group-size", type=int, default=4)
    parser.add_argument("--interpolation-nodes", type=int, default=2)
    parser.add_argument("--spectral-r", type=int, default=2)
    parser.add_argument("--spectral-points", type=int, default=3)
    parser.add_argument("--spectral-degree-window", type=int, default=2)
    parser.add_argument("--max-taylor-pairs", type=int, default=100_000)
    parser.add_argument("--max-auxiliary-dimension", type=int, default=64)
    parser.add_argument(
        "--max-subexponential-auxiliary-dimension",
        type=int,
        default=-1,
        help="guard the full research engine's exact dense dimension; use -1 to disable",
    )
    parser.add_argument(
        "--max-variables",
        type=int,
        default=24,
        help="refuse exponential engines above this declared variable count",
    )
    parser.add_argument(
        "--max-fallback-variables",
        type=int,
        default=24,
        help="guard exact fallbacks used by the research pipeline; use -1 to disable",
    )
    parser.add_argument(
        "--max-construction-candidates",
        type=int,
        default=100_000,
        help="guard exhaustive Tanner-code construction searches; use -1 to disable",
    )
    parser.add_argument(
        "--max-parity-candidates",
        type=int,
        default=100_000,
        help="guard exact parity-row candidate enumeration; use -1 to disable",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        formula = simple() if args.example == "simple" else CNF.from_dimacs(args.input)
        if args.max_variables < 0:
            raise ValueError("--max-variables must be nonnegative")
        if args.engine != "subexponential" and formula.num_variables > args.max_variables:
            raise ValueError(
                f"formula has {formula.num_variables} variables; refusing exponential "
                f"enumeration above --max-variables={args.max_variables}"
            )
        if args.group_size < 1:
            raise ValueError("--group-size must be positive")
        if args.interpolation_nodes < 1:
            raise ValueError("--interpolation-nodes must be positive")
        if args.max_fallback_variables < -1:
            raise ValueError("--max-fallback-variables must be nonnegative or -1")
        fallback_cap = (
            None if args.max_fallback_variables == -1
            else args.max_fallback_variables
        )
        construction_cap = (
            None if args.max_construction_candidates == -1
            else args.max_construction_candidates
        )
        parity_cap = (
            None if args.max_parity_candidates == -1
            else args.max_parity_candidates
        )
        if construction_cap is not None and construction_cap < 1:
            raise ValueError("--max-construction-candidates must be positive or -1")
        if parity_cap is not None and parity_cap < 1:
            raise ValueError("--max-parity-candidates must be positive or -1")
        if args.max_subexponential_auxiliary_dimension == 0 or args.max_subexponential_auxiliary_dimension < -1:
            raise ValueError(
                "--max-subexponential-auxiliary-dimension must be positive or -1"
            )
        subexponential_dimension_cap = (
            None if args.max_subexponential_auxiliary_dimension == -1
            else args.max_subexponential_auxiliary_dimension
        )

        selected = (
            ("algebraic", "shared", "spectral", "dpll")
            if args.engine == "compare"
            else (args.engine,)
        )
        values: list[tuple[str, int]] = []
        for engine in selected:
            if engine == "algebraic":
                value = algebraic_count(formula, args.interpolation_nodes).count
            elif engine == "shared":
                value = cnf_shared_measurement_count(formula, args.group_size)
            elif engine == "grouped":
                value = grouped_count(formula, args.group_size)
            elif engine == "spectral":
                layout = build_spectral_cnf_layout(
                    formula,
                    r=args.spectral_r,
                    q=args.spectral_points,
                    degree_window=args.spectral_degree_window,
                    max_auxiliary_dimension=args.max_auxiliary_dimension,
                )
                value = spectral_taylor_count(
                    layout,
                    max_substitution_pairs=args.max_taylor_pairs,
                ).count
            elif engine == "subexponential":
                value = count_subexponential(
                    formula,
                    max_fallback_variables=fallback_cap,
                    max_construction_candidates=construction_cap,
                    max_parity_candidates=parity_cap,
                    max_auxiliary_dimension=subexponential_dimension_cap,
                ).count
            else:
                value = dpll_count(formula)
            values.append((engine, value))

        print(f"Variables: {formula.num_variables}; clauses: {len(formula.clauses)}")
        print(f"{'Engine':<30} Exact solution count")
        names = {
            "algebraic": "Algebraic interpolation",
            "shared": "Shared measurements",
            "grouped": "Grouped factor computation",
            "spectral": "Spectral Taylor interpolation",
            "dpll": "Independent DPLL",
            "subexponential": "Sparsification + sparse parity engine",
        }
        for engine, value in values:
            print(f"{names[engine]:<30} {value}")
        if args.engine == "compare" and len({value for _, value in values}) != 1:
            print("ERROR: engines disagree", file=sys.stderr)
            return 2
        return 0
    except (OSError, ValueError, ArithmeticError) as exc:
        print(f"eth-sat: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
