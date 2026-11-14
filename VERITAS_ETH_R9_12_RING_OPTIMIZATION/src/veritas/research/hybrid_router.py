"""Cost-aware routing among conventional exact #SAT backends.

Chooses among structure-aware boundary DP and variable elimination using
planner estimates only. Does not invoke manuscript R9 recursion or Anthropic's
full algorithm; routing output is advisory engineering, not a theorem.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from time import monotonic

from veritas.core.cnf import CNF
from veritas.research.adaptive_contract import adaptive_count
from veritas.research.contraction_planner import choose_plan
from veritas.research.graph_decomposition import components, primal_graph, small_separator


@dataclass(frozen=True)
class BackendEstimate:
    name: str
    setup_work: int
    run_work: int
    feasible: bool
    reason: str


def estimate_backends(
    cnf: CNF,
    *,
    max_table_entries: int = 65536,
    max_work_assignments: int = 2_000_000,
    max_separator: int = 2,
    enable_separators: bool = True,
) -> list[BackendEstimate]:
    model, plan, _ = choose_plan(
        cnf,
        max_table_entries=max_table_entries,
        max_work_assignments=max_work_assignments,
        include_copy3=True,
        allow_infeasible=True,
    )
    graph = primal_graph(model.variables, model.factors)
    groups = components(graph)
    separator = small_separator(graph, max_size=max_separator) if enable_separators else None
    estimates: list[BackendEstimate] = []
    elim_feasible = (
        plan.peak_table_entries <= max_table_entries
        and plan.estimated_assignments <= max_work_assignments
    )
    estimates.append(
        BackendEstimate(
            name='EXACT_VARIABLE_ELIMINATION',
            setup_work=plan.estimated_assignments // 20,
            run_work=plan.estimated_assignments,
            feasible=elim_feasible,
            reason=f"induced_width={plan.induced_width}, peak_table={plan.peak_table_entries}",
        )
    )
    if enable_separators and (len(groups) > 1 or separator is not None):
        sep_vars = len(separator.variables) if separator else 0
        comp_penalty = sum(2 ** len(g) for g in groups[:4])  # coarse upper proxy
        run = (2**sep_vars) * max(plan.estimated_assignments // max(len(groups), 1), 1) + comp_penalty
        estimates.append(
            BackendEstimate(
                name='EXACT_BOUNDARY_DP',
                setup_work=sep_vars * 8 + len(groups) * 16,
                run_work=run,
                feasible=sep_vars <= max_separator or len(groups) > 1,
                reason=f"components={len(groups)}, separator_vars={sep_vars}",
            )
        )
    else:
        estimates.append(
            BackendEstimate(
                name='EXACT_BOUNDARY_DP',
                setup_work=0,
                run_work=10**12,
                feasible=False,
                reason='no small separator or disconnected structure detected',
            )
        )
    return estimates


def choose_backend(estimates: list[BackendEstimate]) -> BackendEstimate:
    viable = [e for e in estimates if e.feasible]
    pool = viable or estimates
    return min(pool, key=lambda e: e.setup_work + e.run_work)


def hybrid_count(cnf: CNF, **kwargs) -> dict:
    """Run adaptive_count after recording routing estimates in the result."""
    enable_separators = kwargs.get('enable_separators', True)
    max_separator = kwargs.get('max_separator', 2)
    max_table_entries = kwargs.get('max_table_entries', 65536)
    max_work_assignments = kwargs.get('max_work_assignments', 2_000_000)
    estimates = estimate_backends(
        cnf,
        max_table_entries=max_table_entries,
        max_work_assignments=max_work_assignments,
        max_separator=max_separator,
        enable_separators=enable_separators,
    )
    chosen = choose_backend(estimates)
    prefer_dp = chosen.name == 'EXACT_BOUNDARY_DP' and chosen.feasible
    if prefer_dp:
        kwargs = dict(kwargs)
        kwargs['enable_separators'] = True
    elif chosen.name == 'EXACT_VARIABLE_ELIMINATION':
        kwargs = dict(kwargs)
        kwargs['enable_separators'] = False
        kwargs.setdefault('portfolio_mode', 'optimal_small')
    start = monotonic()
    result = adaptive_count(cnf, **kwargs)
    result['routing'] = {
        'chosen_backend': chosen.name,
        'estimates': [asdict(e) for e in estimates],
        'routing_seconds': round(monotonic() - start, 6),
        'warning': 'Heuristic treewidth-dependent routing only; not Anthropic/OpenAI subexponential algorithms.',
    }
    return result
