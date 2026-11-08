"""Manuscript-executor #SAT counting: quantitative-reduction dispatch.

The route follows the sharper quantitative appendix exactly: normalize on
the original n variables; trivial cases and bounded sizes (n<20) answered
directly; unit-only formulas by propagation; otherwise lem:sparsify with
sigma=1/ceil(sqrt(lambda)), lambda=ceil(log2 n), then per-leaf
sparse-checks + greedy-hashes + lem:tensor-sparse-query (the
arbitrary-density branch). The fixed-density equality-tree route is
count_fixed_density. At paper scales the greedy candidate enumeration
exceeds the configured practical allowance and the result is
INCONCLUSIVE; the paper-scale expander/active recursion path is not
validated by bounded finite checks.
"""
import argparse
import json
from pathlib import Path

from .cnf import Formula, count, count_fixed_density, parse_dimacs
from .resources import Limits,ResourceLimit


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for command,help_text in (
            ('count','Count with the original ordered-list reference route'),
            ('count-optimized','Count with exact distinct-parity-row and unused-variable reductions'),
            ('count-fixed-density','Use the equality-tree fixed-density branch; no complexity qualification'),
            ('count-scaled','Explicit finite experimental CNF recursion; not the source schedule')):
        run = sub.add_parser(command, help=help_text)
        src = run.add_mutually_exclusive_group(required=True)
        src.add_argument('--dimacs', type=Path)
        src.add_argument('--clauses-json', type=str,
                         help='JSON literal lists, e.g. "[[1,2],[-1,3]]"')
        run.add_argument('--n', type=int,
                         help='declared variable count for --clauses-json')
        run.add_argument('--max-work', type=int, default=10_000_000)
        run.add_argument('--max-seconds', type=int, default=300)
        if command=='count-scaled':
            for name in ('a','u','radix','active-depth','column-shift'):
                run.add_argument('--'+name,type=int,required=True)
            run.add_argument('--mode-policy',choices=('full','certified'),required=True)
    args = parser.parse_args(argv)
    try:
        limits = Limits(max_work=args.max_work, max_seconds=args.max_seconds)
        if args.dimacs:
            formula = parse_dimacs(args.dimacs.read_text())
        else:
            parsed=json.loads(args.clauses_json)
            if type(parsed) is not list or any(type(c) is not list for c in parsed):
                raise ValueError('clauses JSON must be a list of literal lists')
            if any(type(literal) is not int for clause in parsed for literal in clause):
                raise ValueError('each literal must be an integer, not a Boolean, float or string')
            clauses=tuple(map(tuple,parsed))
            n=args.n if args.n is not None else max((abs(lit) for clause in clauses for lit in clause),default=0)
            formula=Formula(n,clauses)
        if args.command=='count-optimized':
            from .optimizations import count_optimized
            result=count_optimized(formula,limits=limits)
        elif args.command=='count-fixed-density':
            result=count_fixed_density(formula,limits=limits)
        elif args.command=='count-scaled':
            from .experimental import ScaledExperiment,count_scaled_cnf
            experiment=ScaledExperiment(a=args.a,u=args.u,radix=args.radix,
                active_depth=args.active_depth,column_shift=args.column_shift,
                certified_support=args.mode_policy=='certified')
            result=count_scaled_cnf(formula,experiment=experiment,limits=limits)
        else:result=count(formula,limits=limits)
    except (ValueError,TypeError,OSError,ResourceLimit) as exc:
        parser.error(str(exc))
    print(json.dumps(result, default=str))


if __name__ == '__main__':
    main()
