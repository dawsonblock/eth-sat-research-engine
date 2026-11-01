"""v1.5 exact structure-aware Boolean factor contraction.

Conventional treewidth-dependent algorithms. The estimated cost is a dense
entry-count proxy, not a runtime guarantee or ETH complexity result.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from time import monotonic
from veritas.core.cnf import CNF
from veritas.research.tensor import Factor
from veritas.research.bounded_degree import bounded_degree_from_cnf
from veritas.research.graph_decomposition import primal_graph, from_elimination_order


class ContractLimit(RuntimeError):
    """The exact result is unknown because the execution budget was exhausted."""


@dataclass(frozen=True)
class FactorModel:
    variables: tuple[int, ...]
    factors: tuple[Factor, ...]
    representation: str


def original_cnf_model(cnf: CNF, *, max_clause_width: int = 12,
                       max_total_input_entries: int = 131072) -> FactorModel:
    """Use original Boolean variables, not the occurrence/COPY3 network.

    Deduplicate literals, remove tautological clauses, retain empty clauses
    (constant zero) and explicitly account for declared-but-unused variables.
    """
    factors=[]
    appeared=set()
    allocated=0
    for j,clause in enumerate(cnf.clauses):
        lits=set(clause)
        if any(-lit in lits for lit in lits):
            continue
        ordered=tuple(sorted(lits,key=lambda lit:(abs(lit),lit)))
        if len(ordered)>max_clause_width:
            raise ValueError('clause width exceeds dense factor cap')
        variables=tuple(sorted({abs(lit)-1 for lit in ordered}))
        allocated+=1<<len(variables)
        if allocated>max_total_input_entries:
            raise ValueError('input factors exceed aggregate memory cap')
        appeared.update(variables)
        values=[]
        for mask in range(1<<len(variables)):
            assignment={v:bool(mask&(1<<i)) for i,v in enumerate(variables)}
            values.append(int(any(assignment[abs(l)-1] == (l>0) for l in ordered)))
        factors.append(Factor(variables,tuple(values),f'clause:{j}'))
    for v in range(cnf.n):
        if v not in appeared:
            factors.append(Factor((v,),(1,1),f'free:{v}'))
    return FactorModel(tuple(range(cnf.n)),tuple(factors),'ORIGINAL_CNF_VARIABLES')


def copy3_model(cnf: CNF, *, max_wires: int = 1800, max_factors: int = 2500) -> FactorModel:
    network,_=bounded_degree_from_cnf(cnf,max_wires=max_wires,max_factors=max_factors)
    return FactorModel(tuple(range(network.edges)),network.factors,'COPY3_OCCURRENCE_NETWORK')


@dataclass(frozen=True)
class ContractionPlan:
    representation: str
    heuristic: str
    order: tuple[int,...]
    induced_width: int
    peak_table_entries: int
    estimated_assignments: int
    treewidth_verified: bool


def elimination_order(model: FactorModel, heuristic: str = 'min_fill',
                      deadline: float | None = None) -> ContractionPlan:
    if heuristic not in ('min_degree','min_fill','weighted_min_fill'):
        raise ValueError('unknown planning heuristic')
    graph=primal_graph(model.variables,model.factors)
    working={v:set(ns) for v,ns in graph.items()}
    order=[]; width=0; work=0
    while working:
        if deadline is not None and monotonic()>deadline:
            raise ContractLimit('contraction planning deadline exceeded')
        def score(v):
            ns=working[v]
            if heuristic=='min_degree':
                return (len(ns), v)
            sorted_ns=sorted(ns)
            missing=sum(w not in working[u] for i,u in enumerate(sorted_ns) for w in sorted_ns[i+1:])
            if heuristic=='min_fill':return missing,len(ns),v
            return (missing*(len(ns)+1),len(ns),v)
        vertex=min(working,key=score)
        neighbors=sorted(working[vertex]); d=len(neighbors)
        width=max(width,d)
        work+=1<<(d+1)
        for i,u in enumerate(neighbors):
            working[u].discard(vertex)
            working[u].update(neighbors[:i]+neighbors[i+1:])
        del working[vertex]
        order.append(vertex)
    # This is a structural check, not a proof of optimal treewidth.
    decomposition=from_elimination_order(graph,tuple(order))
    return ContractionPlan(model.representation,heuristic,tuple(order),width,
                           1<<width,work,decomposition.width==width)


@dataclass(frozen=True)
class ExactStats:
    peak_table_entries: int
    evaluated_assignments: int
    factor_lookups: int
    variables_eliminated: int
    elapsed_seconds: float
    method: str = 'EXACT_DENSE_FACTOR_ELIMINATION'


def contract_order(model: FactorModel, plan: ContractionPlan, *, modulus: int | None = None,
                   max_table_entries: int = 65536, max_work_assignments: int = 2_000_000,
                   deadline: float | None = None) -> tuple[int,ExactStats]:
    if type(max_table_entries) is not int or not 1<=max_table_entries<=1<<20:
        raise ValueError('bad table-entry budget')
    if type(max_work_assignments) is not int or not 1<=max_work_assignments<=20_000_000:
        raise ValueError('bad evaluation budget')
    if modulus is not None and (type(modulus) is not int or not 2<=modulus<=2**256):
        raise ValueError('modulus must be an integer in 2..2**256')
    if set(plan.order)!=set(model.variables) or len(plan.order)!=len(model.variables):
        raise ValueError('invalid elimination plan')
    for f in model.factors:
        if len(f.table)>max_table_entries:
            raise ContractLimit('input factor exceeds table budget')
    if plan.peak_table_entries>max_table_entries or plan.estimated_assignments>max_work_assignments:
        raise ContractLimit('predicted contraction exceeds resource budget')
    start=monotonic()
    if deadline is None: deadline=start+15
    factors=list(model.factors)
    peak=max((len(f.table) for f in factors), default=1)
    work=0;lookups=0
    for edge in plan.order:
        if monotonic()>deadline:raise ContractLimit('deadline exceeded')
        touched=[f for f in factors if edge in f.ports]
        factors=[f for f in factors if edge not in f.ports]
        neighbors=tuple(sorted({p for f in touched for p in f.ports}-{edge}))
        entries=1<<len(neighbors)
        if entries>max_table_entries or work+2*entries>max_work_assignments:
            raise ContractLimit('intermediate exceeds resource budget')
        values=[]
        for bits in range(entries):
            if bits%512==0 and monotonic()>deadline:
                raise ContractLimit('deadline exceeded')
            assignment={v:bool(bits&(1<<j)) for j,v in enumerate(neighbors)}
            subtotal=0
            for bit in (False,True):
                assignment[edge]=bit
                prod=1
                for factor in touched:
                    prod*=factor.value(assignment)
                    lookups+=1
                    if not prod:break
                    if modulus is not None:prod%=modulus
                subtotal+=prod
            values.append(subtotal%modulus if modulus else subtotal)
        work+=2*entries
        peak=max(peak,entries)
        factors.append(Factor(neighbors,tuple(values),f'v15:{edge}'))
    count=1
    for f in factors:
        if f.ports:raise AssertionError('uneliminated factors')
        count*=f.table[0]
        if modulus is not None:count%=modulus
    return count,ExactStats(peak,work,lookups,len(plan.order),monotonic()-start)


def plan_portfolio(model: FactorModel, *, deadline:float|None=None) -> tuple[ContractionPlan,...]:
    return tuple(elimination_order(model,h,deadline=deadline) for h in ('min_degree','min_fill','weighted_min_fill'))


def choose_plan(cnf: CNF, *, max_table_entries: int = 65536,
                max_work_assignments: int = 2_000_000,
                include_copy3: bool = True,
                max_wires: int = 1800,
                max_factors: int = 2500,
                allow_infeasible: bool = False,
                deadline: float|None = None,
                portfolio_mode: str = 'auto') -> tuple[FactorModel,ContractionPlan,list[dict]]:
    if portfolio_mode not in ('auto', 'thorough', 'optimal_small'):
        raise ValueError('portfolio_mode must be auto, thorough or optimal_small')
    # Explicit globally optimal dense-work planning on <=12 original CNF bits.
    # Deliberately not the default: subset DP itself can be expensive.
    if portfolio_mode == 'optimal_small':
        from veritas.research.optimal_order import optimize_small_model
        if len(cnf.clauses)>max_factors:
            raise ContractLimit('too many clauses for exact-order planning')
        model=original_cnf_model(cnf)
        if len(model.variables)>max_wires or len(model.factors)>max_factors:
            raise ContractLimit('model exceeds planning caps')
        plan,evidence=optimize_small_model(model,deadline=deadline)
        feasible=(plan.peak_table_entries<=max_table_entries
                  and plan.estimated_assignments<=max_work_assignments
                  and max((len(f.table) for f in model.factors),default=1)<=max_table_entries)
        if not feasible and not allow_infeasible:
            raise ContractLimit('globally optimal order still exceeds resource caps')
        return model,plan,[{'representation':model.representation,
            'heuristic':plan.heuristic,'induced_width':plan.induced_width,
            'peak_table_entries':plan.peak_table_entries,
            'estimated_assignments':plan.estimated_assignments,
            'feasible':feasible,'globally_optimal_dense_work':True,
            'states_evaluated':evidence.states_evaluated,
            'certificate_type':evidence.certificate_type}]
    # Fast path: a low-cost original-CNF plan is sufficient whenever it fits.
    # Thorough mode retains the complete v1.5 portfolio for quality comparison.
    if portfolio_mode == 'auto':
        try:
            model = original_cnf_model(cnf)
            if len(cnf.clauses) <= max_factors and len(model.variables) <= max_wires and len(model.factors) <= max_factors:
                plan = elimination_order(model, 'min_degree', deadline=deadline)
                feasible = (plan.peak_table_entries <= max_table_entries and
                            plan.estimated_assignments <= max_work_assignments and
                            max((len(f.table) for f in model.factors), default=1) <= max_table_entries)
                if feasible:
                    return model, plan, [{'representation':plan.representation,
                       'heuristic':plan.heuristic,'induced_width':plan.induced_width,
                       'peak_table_entries':plan.peak_table_entries,
                       'estimated_assignments':plan.estimated_assignments,
                       'feasible':True,'fast_path':True}]
        except (ValueError, ContractLimit):
            pass
    candidates=[]
    available=[]
    all_candidates=[]
    models=[]
    errors=[]
    for label,build in [('ORIGINAL_CNF_VARIABLES',lambda:original_cnf_model(cnf)),
                        ('COPY3_OCCURRENCE_NETWORK',lambda:copy3_model(cnf,max_wires=max_wires,max_factors=max_factors))]:
        if label=='COPY3_OCCURRENCE_NETWORK' and not include_copy3:continue
        try:
            if deadline is not None and monotonic()>deadline:
                raise ContractLimit('planning deadline exceeded')
            if len(cnf.clauses)>max_factors:
                raise ContractLimit('too many input clauses for planner')
            model=build()
            if len(model.variables)>max_wires or len(model.factors)>max_factors:
                raise ContractLimit('network size exceeds planning cap')
            models.append(model)
        except (ValueError,ContractLimit) as e:
            errors.append({'representation':label,'error':str(e)})
    for model in models:
        for plan in plan_portfolio(model,deadline=deadline):
            feasible=(plan.peak_table_entries<=max_table_entries
                      and plan.estimated_assignments<=max_work_assignments
                      and max((len(f.table) for f in model.factors),default=1)<=max_table_entries)
            candidates.append({'representation':plan.representation,'heuristic':plan.heuristic,
                'induced_width':plan.induced_width,'peak_table_entries':plan.peak_table_entries,
                'estimated_assignments':plan.estimated_assignments,'feasible':feasible})
            if feasible or allow_infeasible:
                all_candidates.append((plan.estimated_assignments,plan.peak_table_entries,
                                  0 if model.representation=='ORIGINAL_CNF_VARIABLES' else 1,
                                  plan.heuristic, model, plan))
            if feasible:
                available.append((plan.estimated_assignments,plan.peak_table_entries,
                    0 if model.representation=='ORIGINAL_CNF_VARIABLES' else 1,plan.heuristic,model,plan))
    if not available and not allow_infeasible:
        raise ContractLimit(f'no plan fits execution caps; candidates={candidates[:8]}; errors={errors}')
    if not all_candidates:
        raise ContractLimit(f'no valid representations; errors={errors}')
    _,_,_,_,model,plan=min(available if available else all_candidates,key=lambda x:x[:4])
    return model,plan,candidates
