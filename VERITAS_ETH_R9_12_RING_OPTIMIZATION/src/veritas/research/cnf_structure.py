"""Count-preserving structural analysis and component factoring for #SAT."""
from __future__ import annotations

from dataclasses import dataclass

from veritas.core.cnf import CNF
from veritas.research.graph_decomposition import components


@dataclass(frozen=True)
class ComponentRecord:
    variables: tuple[int, ...]
    clause_count: int
    local_n: int
    unconstrained_locals: int


@dataclass(frozen=True)
class StructureReport:
    component_count: int
    global_unconstrained: int
    components: tuple[ComponentRecord, ...]
    count_preserving: bool
    contract: str


def variable_adjacency(cnf: CNF) -> dict[int, set[int]]:
    graph = {v: set() for v in range(1, cnf.n + 1)}
    for clause in cnf.clauses:
        vars_in_clause = sorted({abs(lit) for lit in clause})
        for i, a in enumerate(vars_in_clause):
            for b in vars_in_clause[i + 1 :]:
                graph[a].add(b)
                graph[b].add(a)
    return graph


def analyze_cnf_structure(cnf: CNF) -> StructureReport:
    if cnf.n == 0:
        return StructureReport(0, 0, (), True, 'COUNT_PRESERVING_EMPTY')
    appeared = {abs(lit) for clause in cnf.clauses for lit in clause}
    global_unconstrained = sum(1 for v in range(1, cnf.n + 1) if v not in appeared)
    graph = variable_adjacency(cnf)
    groups = components(graph)
    records: list[ComponentRecord] = []
    for group in groups:
        group_set = set(group)
        clause_count = sum(
            1 for clause in cnf.clauses if all(abs(lit) in group_set for lit in clause)
        )
        constrained_locals = sum(1 for v in group if v in appeared)
        records.append(
            ComponentRecord(
                variables=group,
                clause_count=clause_count,
                local_n=len(group),
                unconstrained_locals=len(group) - constrained_locals,
            )
        )
    return StructureReport(
        component_count=len(groups),
        global_unconstrained=global_unconstrained,
        components=tuple(records),
        count_preserving=True,
        contract='DISJOINT_COMPONENT_PRODUCT',
    )


def _project_component(cnf: CNF, variables: tuple[int, ...]) -> CNF:
    varset = set(variables)
    mapping = {v: i + 1 for i, v in enumerate(sorted(variables))}
    clauses = [
        tuple(mapping[abs(lit)] * (1 if lit > 0 else -1) for lit in clause)
        for clause in cnf.clauses
        if all(abs(lit) in varset for lit in clause)
    ]
    return CNF.from_lists(len(variables), [list(c) for c in clauses])


def structure_aware_count(cnf: CNF, *, inner_count=None, **kwargs) -> dict:
    """Exact #SAT via independent components when variables are disconnected."""
    from veritas.research.hybrid_router import hybrid_count

    counter = hybrid_count if inner_count is None else inner_count
    verify_direct = kwargs.pop('verify_direct', cnf.n <= 18)
    report = analyze_cnf_structure(cnf)
    needs_split = report.component_count > 1 or any(c.clause_count == 0 for c in report.components)
    if not needs_split:
        out = counter(cnf, **kwargs)
        out['structure'] = {
            'decomposed': False,
            'report': report.__dict__,
            'warning': 'No disjoint component split applied.',
        }
        return out

    product = 1
    parts: list[dict] = []
    for comp in report.components:
        if comp.clause_count == 0:
            factor = 2**comp.local_n
            parts.append(
                {
                    'variables': list(comp.variables),
                    'engine': 'UNCONSTRAINED_COMPONENT',
                    'count': str(factor),
                }
            )
        else:
            sub = _project_component(cnf, comp.variables)
            sub_result = counter(sub, **kwargs)
            factor = int(sub_result['count'])
            parts.append(
                {
                    'variables': list(comp.variables),
                    'engine': sub_result.get('engine'),
                    'count': str(factor),
                    'routing': sub_result.get('routing'),
                }
            )
        product *= factor
    merged = counter(cnf, **kwargs) if verify_direct else None
    return {
        'status': 'EXACT_COUNT',
        'count': str(product),
        'engine': 'STRUCTURE_AWARE_COMPONENT_PRODUCT',
        'formula_sha256': cnf.digest(),
        'structure': {
            'decomposed': True,
            'report': {
                'component_count': report.component_count,
                'global_unconstrained': report.global_unconstrained,
                'components': [c.__dict__ for c in report.components],
                'contract': report.contract,
            },
            'parts': parts,
            'cross_check': (
                {
                    'direct_count': merged.get('count'),
                    'matches_direct': str(product) == str(merged.get('count')),
                }
                if merged is not None
                else {'skipped': True, 'reason': 'verify_direct disabled'}
            ),
            'warning': 'Component product is exact for disjoint CNF components; not an ETH result.',
        },
        'independent_count_checked': merged is not None and str(merged.get('count')) == str(product),
        'elapsed_seconds': merged.get('elapsed_seconds') if merged is not None else None,
    }
