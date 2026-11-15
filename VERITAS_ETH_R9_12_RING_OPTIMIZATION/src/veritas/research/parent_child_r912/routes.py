"""Explicit route selection between finite recursion and exact elimination.

The recursive route is the unchanged R9.10/R9.12 numerical executor. The
elimination route runs only when a verified ordering fits its explicit budget.
An elimination result is an ordinary exact contraction: it is classified
separately and is never evidence for the source-recursive or subexponential
bound. Neither route sets a source-qualified or theorem-aligned flag.
"""
from enum import Enum

from veritas.research.parent_child_r98.model import Refusal, Semantics
from veritas.research.tapered_v4.provenance import source_binding
from .elimination import EliminationBudget, eliminate, plan
from .preflight import elimination_preflight, preflight_to_dict


class Route(str, Enum):
    RECURSIVE = 'recursive'
    ELIMINATION = 'elimination'
    AUTO = 'auto'


class Classification(str, Enum):
    RECURSIVE = 'FINITE_TAPERED_RECURSION'
    EXACT_ELIMINATION = 'EXACT_ELIMINATION'


NOT_EVIDENCE = {'source_qualified': False, 'theorem_mode_enabled': False, 'theorem_aligned': False,
                'source_recursive_bound_evidence': False, 'subexponential_bound_evidence': False}


def select_route(parent, route=Route.AUTO, elimination_budget=None, *, preflight_layout=None, shrink_budget=None):
    """Return the chosen route and the symbolic ordering check; allocates no table."""
    if type(route) is not Route:
        raise TypeError('typed Route required')
    if route is Route.RECURSIVE:
        return {'route': Route.RECURSIVE.value, 'requested': route.value, 'ordering': None,
                'reason': 'explicit recursive request', 'preflight': None}
    if parent.semantics is not Semantics.FINITE_SCALED_EXPERIMENT:
        raise Refusal('INCONCLUSIVE_SOURCE_REFINEMENT', 'elimination routing is finite only')
    budget = EliminationBudget() if elimination_budget is None else elimination_budget
    if type(budget) is not EliminationBudget:
        raise TypeError('EliminationBudget required')
    ordering = plan(parent, budget)
    preflight = preflight_to_dict(
        elimination_preflight(parent, budget, layout=preflight_layout, shrink_budget=shrink_budget)
    )
    if ordering['fits']:
        return {'route': Route.ELIMINATION.value, 'requested': route.value, 'ordering': ordering,
                'reason': 'verified ordering fits the explicit elimination budget',
                'preflight': preflight}
    if route is Route.ELIMINATION:
        return {'route': None, 'requested': route.value, 'ordering': ordering, 'reason': ordering['reason'],
                'preflight': preflight}
    return {'route': Route.RECURSIVE.value, 'requested': route.value, 'ordering': ordering,
            'reason': 'elimination refused before allocation: ' + ordering['reason'],
            'preflight': preflight}


def contract_routed(parent, *, route=Route.AUTO, elimination_budget=None, preflight_layout=None, shrink_budget=None, **recursive):
    """Dispatch one call. Refusals carry no result; partial values are never returned."""
    binding = source_binding()['digest']
    try:
        selection = select_route(
            parent,
            route,
            elimination_budget,
            preflight_layout=preflight_layout,
            shrink_budget=shrink_budget,
        )
    except (ValueError, TypeError, KeyError, RuntimeError, MemoryError) as exc:
        return {'status': getattr(exc, 'status', 'INCONCLUSIVE_ROUTE_SELECTION'), 'reason': str(exc),
                'result_classification': None, **NOT_EVIDENCE}
    if selection['route'] is None:
        return {'status': 'INCONCLUSIVE_ELIMINATION_BUDGET', 'reason': selection['reason'],
                'route_selection': selection, 'result_classification': None, **NOT_EVIDENCE}
    if selection['route'] == Route.RECURSIVE.value:
        from veritas.research.parent_child_r910.engine import contract
        report = contract(parent, **recursive)
        if report.get('source_qualified') is not False or report.get('theorem_mode_enabled') is not False:
            raise ValueError('finite recursive report must not carry qualification')
        classified = report['status'].startswith('PASS')
        payload = {**NOT_EVIDENCE, **report, 'route_selection': selection,
                   'result_classification': Classification.RECURSIVE.value if classified else None}
        if 'decomposition_work' in report:
            payload['decomposition_work'] = report['decomposition_work']
        return payload
    budget = EliminationBudget() if elimination_budget is None else elimination_budget
    try:
        result, ledger = eliminate(parent, selection['ordering'], budget)
        if source_binding()['digest'] != binding:
            raise ValueError('source changed during elimination')
    except (ValueError, TypeError, KeyError, IndexError, ArithmeticError, RuntimeError, MemoryError) as exc:
        return {'status': getattr(exc, 'status', 'INCONCLUSIVE_EXACT_ELIMINATION'), 'reason': str(exc),
                'route_selection': selection, 'result_classification': None, **NOT_EVIDENCE}
    return {'schema': 'VERITAS_R912_EXACT_ELIMINATION_V1', 'status': 'PASS_EXACT_BOUNDED_WIDTH_ELIMINATION',
            'result': result, 'result_classification': Classification.EXACT_ELIMINATION.value,
            'parent_digest': parent.content_digest, 'implementation_source_sha256': binding,
            'route_selection': selection, 'elimination_width': selection['ordering']['width'],
            'ledger': {**ledger, 'bit_operations': None, 'bit_operation_measurement': 'NOT_INSTRUMENTED',
                       'hard_memory_limit_enforced': False,
                       'table_entry_budget_scope': 'RING_ELEMENTS_NOT_BYTES'},
            'recursive_route_used': False, 'source_tapered_functional_used': False,
            'complexity_status': 'EXPONENTIAL_IN_VERIFIED_WIDTH', **NOT_EVIDENCE}
