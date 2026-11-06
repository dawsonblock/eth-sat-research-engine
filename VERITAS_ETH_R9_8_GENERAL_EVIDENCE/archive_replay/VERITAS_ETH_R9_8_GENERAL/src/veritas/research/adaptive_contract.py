"""Resource-guarded, planner-selected exact #SAT via Boolean factor networks."""
from __future__ import annotations
from dataclasses import asdict
from time import monotonic
from veritas.core.cnf import CNF
from veritas.research.contraction_planner import (choose_plan, contract_order, ContractLimit)
from veritas.research.graph_decomposition import primal_graph, small_separator, components
from veritas.research.boundary_dp import boundary_contract
from veritas.research.indexed_contract import indexed_contract_order
from veritas.research.sparse_contract import sparse_contract_order


def adaptive_count(cnf:CNF, *, precision_bits:int|None=None, include_copy3:bool=True,
                   enable_separators:bool=True, max_separator:int=2,
                   max_slices:int=3,
                   max_table_entries:int=65536, max_work_assignments:int=2_000_000,
                   timeout_s:float=15, max_wires:int=1800,
                   max_factors:int=2500, portfolio_mode:str='auto',
                   execution_mode:str='indexed')->dict:
    if type(timeout_s) not in (int,float) or not 0<timeout_s<=60:
        raise ValueError('timeout_s must be in (0,60]')
    if precision_bits is not None and (type(precision_bits) is not int or not 1<=precision_bits<=128):
        raise ValueError('precision_bits must be 1..128')
    if type(max_slices) is not int or not 0<=max_slices<=8:
        raise ValueError('max_slices must be 0..8')
    if type(include_copy3) is not bool or type(enable_separators) is not bool:
        raise ValueError('boolean flags required')
    if portfolio_mode not in ('auto','thorough','optimal_small'):
        raise ValueError('invalid portfolio_mode')
    if execution_mode not in ('indexed','legacy','sparse'):
        raise ValueError('invalid execution_mode')
    start=monotonic();deadline=start+timeout_s
    modulus=1<<precision_bits if precision_bits is not None else None
    model,plan,portfolio=choose_plan(cnf,max_table_entries=max_table_entries,
        max_work_assignments=max_work_assignments,include_copy3=include_copy3,
        max_wires=max_wires,max_factors=max_factors,allow_infeasible=enable_separators or max_slices>0 or execution_mode=='sparse',deadline=deadline,
        portfolio_mode=portfolio_mode)
    graph=primal_graph(model.variables,model.factors)
    groups=components(graph)
    separator=small_separator(graph,max_size=max_separator) if enable_separators and max_separator else None
    # Separator conditioning is selected if there are independent groups or a
    # small separating set AND its exhaustive 2^k assignments remain bounded.
    use_dp=enable_separators and (len(groups)>1 or (separator is not None and
                len(separator.variables)<=max_separator))
    plan_feasible=plan.peak_table_entries<=max_table_entries and plan.estimated_assignments<=max_work_assignments
    use_dp=use_dp or (not plan_feasible and max_slices>0 and execution_mode!='sparse')
    # Honour the exact-order request rather than silently swapping execution
    # to an unrelated separator/slicing algorithm.
    if portfolio_mode=='optimal_small':
        use_dp=False
    if not use_dp and not plan_feasible and execution_mode!='sparse':
        raise ContractLimit('no feasible plan and no usable separator')
    if use_dp:
        count,stats=boundary_contract(model,modulus=modulus,
            max_separator=max_separator if enable_separators else 0, max_slices=max_slices,
            max_table_entries=max_table_entries,max_work_assignments=max_work_assignments,
            deadline=deadline,execution_mode=execution_mode)
        actual=asdict(stats)
        engine='EXACT_BOUNDARY_DP'
    else:
        engine_fn = {'indexed':indexed_contract_order,'legacy':contract_order,'sparse':sparse_contract_order}[execution_mode]
        count,stats=engine_fn(model,plan,modulus=modulus,
            max_table_entries=max_table_entries,max_work_assignments=max_work_assignments,
            deadline=deadline)
        actual=asdict(stats)
        engine='EXACT_VARIABLE_ELIMINATION'
    return {'status':'COUNT_RESIDUE' if modulus else 'EXACT_COUNT',
            'count':str(count),'precision_bits':precision_bits,
            'engine':engine,'representation':model.representation,
            'selected_heuristic':plan.heuristic,'planning':asdict(plan),
            'candidates':portfolio,'execution':actual,
            'portfolio_mode':portfolio_mode,'execution_mode':execution_mode,
            'independent_count_checked':False,
            'optimal_order_work_certified':portfolio_mode=='optimal_small',
            'formula_sha256':cnf.digest(),
            'elapsed_seconds':monotonic()-start,
            'warning':'Conventional exact treewidth-dependent algorithms, exponential worst case; not the paper D.4.4 or an ETH breakthrough.'}
