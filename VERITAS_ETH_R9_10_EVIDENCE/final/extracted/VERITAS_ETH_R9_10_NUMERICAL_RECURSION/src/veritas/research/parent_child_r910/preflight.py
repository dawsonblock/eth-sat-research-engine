"""Checked root grid and independent descendant topology; no total cost promise."""
from veritas.research.parent_child_r98.model import Budget, canonical, digest
from veritas.research.parent_child_r99.execution import ExecutionSpec, TupleStrategy
from veritas.research.parent_child_r99.preflight import preflight_packet_recursion
from veritas.research.parent_child_r99.row_degree import certify_row_degree, verify_row_degree


def preflight(parent, layout, *, levels, max_points, policy):
    generic = preflight_packet_recursion(parent, layout,
        ExecutionSpec(schedule=((1,1),)*levels, tuples=TupleStrategy.SUPPORT, max_points=max_points),
        policy=policy, descendant_strategy='singleton_first_fit')
    # These conditions refer to generic grids, not the degree-certified executor.
    # Descendant degrees depend on numerical recipes, and remain runtime checks.
    advisory_codes = {'RECURSIVE_CALL_LOWER_BOUND','DENSE_GRID_POLICY_ESTIMATE',
                      'POINT_GRID_CAP','RESIDUE_FIELD_TOO_SMALL'}
    blockers = [b for b in generic.get('blockers',[]) if b['code'] not in advisory_codes]
    budget = Budget(policy)
    degree = certify_row_degree(parent, 1, budget=budget)
    verify_row_degree(parent, 1, degree, budget=budget)
    count = degree['degree_bound']+1
    if count > min(max_points, 1 << (parent.defining_polynomial.bit_length()-1)):
        blockers.append({'code':'CERTIFIED_ROOT_GRID_EXCEEDS_CAP','required':count})
    admitted = generic.get('descendant_topologies_complete') is True and not blockers
    result = {'status': 'PASS_FINITE_ROOT_AND_TOPOLOGY' if admitted else 'INCONCLUSIVE_PREFLIGHT',
        'parent_digest':parent.content_digest, 'layout_digest':layout.content_digest,
        'root_degree_certificate':degree, 'root_expected_points':2*count,
        'root_generic_points':2*(3*parent.edge_count+1),
        'root_original_plan_admission_charge':64*(3*parent.edge_count+1)**2,
        'root_prefix_binomial_steps':3*parent.edge_count,
        'descendant_topology':generic, 'blockers':blockers,
        'generic_grid_advisories':[b for b in generic.get('blockers',[]) if b['code'] in advisory_codes],
        'admitted':admitted, 'descendant_grid_feasibility':'RUNTIME_CERTIFICATION_REQUIRED',
        'total_work_bound':'NOT_ESTABLISHED', 'bit_operation_bound':'NOT_ESTABLISHED',
        'preflight_work_units':generic.get('preflight_work_units',0)+budget.work,
        'source_qualified':False, 'theorem_mode_enabled':False}
    result['digest'] = digest(canonical(result))
    return result
