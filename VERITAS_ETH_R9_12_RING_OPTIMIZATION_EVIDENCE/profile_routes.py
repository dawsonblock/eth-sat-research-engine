"""Bounded cProfile runs over the direct and scaled-recursive routes.

Read-only profiling: imports the COMPONENT_OPTIMIZATION checkout source, never
mutates it. Each case is capped at max_seconds=30 via the route's own Budget
clock, so resource refusals return cleanly and the partial profile is preserved.
Writes pstats_<case>.txt + profile_summary.json next to this script.
"""
import cProfile, io, json, pstats, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path('/Users/dawsonblock/MATH SPEED/VERITAS_ETH_R9_12_RING_OPTIMIZATION/src')
sys.path.insert(0, str(SRC))

from veritas.research.manuscript.cnf import Formula, count
from veritas.research.manuscript.optimizations import count_optimized, common_zeros_factored
from veritas.research.manuscript.sparse_query import common_zeros
from veritas.research.manuscript.experimental import count_scaled_cnf, ScaledExperiment
from veritas.research.manuscript.resources import Limits

CAP = Limits(max_work=2_000_000_000, max_seconds=30.0)
CERTIFIED = ScaledExperiment(certified_support=True)          # smallest passing fixture
FULL = ScaledExperiment(a=1, u=1, radix=2, active_depth=1, column_shift=0)

CASES = {}


def case(name):
    def wrap(fn):
        CASES[name] = fn
        return fn
    return wrap


# --- Direct route: grouped sparse tensor contraction (n >= 20 -> tensor path).
# Weak system keeps arities under Schedule(60).delta = 40 while enumeration and
# contraction still execute (expected: completes).
@case('direct_grouped_sparse_small')
def _():
    return common_zeros(20, [[[0, 1], [2]], [[0, 2], [4]]], limits=CAP)


# Same entry point, denser system: exercises the same grouped machinery harder
# (expected: may hit the 30 s budget cap -> INCONCLUSIVE, profile kept).
@case('direct_grouped_sparse_capped')
def _():
    eqs = [
        [[0, 1], [2, 3], [8]],
        [[4, 5], [6, 7], [9]],
        [[0, 2], [4, 6], [10]],
        [[1, 3], [5, 7], [11]],
    ]
    return common_zeros(20, eqs, limits=CAP)


# --- Direct route: factored entry on a two-component disconnected system
# (measures the new component path end-to-end).
@case('direct_factored_two_components')
def _():
    eqs = [
        [[0, 1], [2, 3]], [[0, 2], [4]],
        [[10, 11], [12, 13]], [[10, 12], [14]],
    ]
    return common_zeros_factored(20, eqs, limits=CAP)


# --- CNF end-to-end direct: reference vs optimized on an identical formula.
CNF = Formula(12, tuple(tuple(c) for c in (
    (1, 2, 3), (-1, 4, 5), (2, -4, 6),
    (7, 8, 9), (-7, 10, 11), (8, -10, 12),
)))


@case('cnf_reference_count')
def _():
    return count(CNF, limits=CAP)


@case('cnf_optimized_count')
def _():
    return count_optimized(CNF, limits=CAP)


# --- Scaled-recursive route: smallest passing fixtures from
# tests/test_manuscript_scaled_cnf.py (certified support, tiny formulas).
@case('scaled_certified_n5_1cl')
def _():
    return count_scaled_cnf(Formula(5, ((1, 2),)), experiment=CERTIFIED, limits=CAP)


@case('scaled_certified_n2_2cl')
def _():
    return count_scaled_cnf(Formula(2, ((1, 2), (1, -2))), experiment=CERTIFIED, limits=CAP)


# Full-domain scaled variant (the mode the test refuses at max_work=1000):
# expected to cap at 30 s -> partial profile retained for hotspot evidence.
@case('scaled_full_domain_capped')
def _():
    return count_scaled_cnf(Formula(5, ((1, 2),)), experiment=FULL, limits=CAP)


def summarize(pr, top=25):
    st = pstats.Stats(pr)
    st.sort_stats('cumulative')
    st.stream = io.StringIO()
    st.print_stats(top)
    text = st.stream.getvalue()
    st.stream = None
    rows = []
    for func, (cc, nc, tt, ct, callers) in st.stats.items():
        rows.append(dict(func='%s:%d:%s' % func, ncalls=nc, tottime=round(tt, 6),
                         cumtime=round(ct, 6)))
    rows.sort(key=lambda r: -r['cumtime'])
    return text, rows[:top]


def main():
    out = {}
    for name, fn in CASES.items():
        pr = cProfile.Profile()
        t0 = time.perf_counter()
        pr.enable()
        try:
            result = fn()
            outcome = 'COMPLETED' if result.get('status') == 'PASS_EXACT_COUNT' else \
                'CAPPED_OR_REFUSED'
        except Exception as exc:  # noqa: BLE001 - record and continue
            result = {'status': 'PROFILER_CASE_ERROR', 'error': repr(exc)}
            outcome = 'ERROR'
        pr.disable()
        dt = time.perf_counter() - t0
        text, rows = summarize(pr)
        (HERE / f'pstats_{name}.txt').write_text(text)
        out[name] = dict(outcome=outcome, wall_seconds=round(dt, 3),
                         receipt={k: v for k, v in result.items()
                                  if k in ('status', 'count', 'route', 'inner_route',
                                           'reason', 'encoded_wires', 'extension_degree',
                                           'component_variables', 'reused_components')},
                         hotspots=rows)
        print(f'{name}: {outcome} {dt:.2f}s status={result.get("status")} '
              f'count={result.get("count")}', flush=True)
    (HERE / 'profile_summary.json').write_text(json.dumps(out, indent=1))
    print('wrote profile_summary.json + pstats_*.txt')


if __name__ == '__main__':
    main()
