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
from veritas.research.contraction_planner import ContractLimit, choose_plan
from veritas.research.graph_decomposition import components, primal_graph, small_separator
from veritas.research.optimal_order import MAX_OPTIMAL_VERTICES


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
    deadline: float | None = None,
) -> list[BackendEstimate]:
    model, plan, _ = choose_plan(
        cnf,
        max_table_entries=max_table_entries,
        max_work_assignments=max_work_assignments,
        include_copy3=True,
        allow_infeasible=True,
        deadline=deadline,
    )
    graph = primal_graph(model.variables, model.factors)
    groups = components(graph)
    # max_separator=0 means "no separator search", as in adaptive_count.
    separator = (small_separator(graph, max_size=max_separator)
                 if enable_separators and max_separator else None)
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
    # One time budget covers routing and execution. An invalid timeout_s is left for
    # adaptive_count to reject.
    timeout_s = kwargs.get('timeout_s', 15)
    start = monotonic()
    deadline = (start + timeout_s
                if type(timeout_s) in (int, float) and 0 < timeout_s <= 60 else None)
    estimates = estimate_backends(
        cnf,
        max_table_entries=max_table_entries,
        max_work_assignments=max_work_assignments,
        max_separator=max_separator,
        enable_separators=enable_separators,
        deadline=deadline,
    )
    chosen = choose_backend(estimates)
    routing_seconds = monotonic() - start
    prefer_dp = chosen.name == 'EXACT_BOUNDARY_DP' and chosen.feasible
    if prefer_dp:
        kwargs = dict(kwargs)
        kwargs['enable_separators'] = True
    elif chosen.name == 'EXACT_VARIABLE_ELIMINATION':
        kwargs = dict(kwargs)
        kwargs['enable_separators'] = False
        # The certified order search refuses more than MAX_OPTIMAL_VERTICES wires;
        # larger inputs keep adaptive_count's heuristic planner.
        if cnf.n <= MAX_OPTIMAL_VERTICES:
            kwargs.setdefault('portfolio_mode', 'optimal_small')
    if deadline is not None:
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise ContractLimit('routing estimates exhausted the time budget')
        kwargs = dict(kwargs)
        kwargs['timeout_s'] = remaining
    result = adaptive_count(cnf, **kwargs)
    result['routing'] = {
        'chosen_backend': chosen.name,
        'estimates': [asdict(e) for e in estimates],
        'routing_seconds': round(routing_seconds, 6),
        'warning': 'Heuristic treewidth-dependent routing only; not Anthropic/OpenAI subexponential algorithms.',
    }
    return result
