"""Exact, resource-bounded factor elimination for fixed-beta D.4.4 child networks.

A *finite reference* contraction, not the manuscript's recursive complexity algorithm.
Mode exponents are fixed metadata, and group-local child tensors contain ONLY
original half-port wires. All arithmetic is over the original extension jet ring.
The original exhaustive v3.7 and direct half-edge oracles remain independent.
"""
from __future__ import annotations
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from itertools import product
from time import monotonic

from veritas.research.eth_d44_child_reference.children import (
    _data, _packet_value, construct_child_reference, ResourceLimit, Meter)
from veritas.research.eth_modes_v31.jet_tiles import (
    check_jet_tile_modes, _serialize_net, _deserialize_net)
from veritas.research.eth_modes_v27.enumeration import weighted_tuples, count_tuples, ModeBudgetExceeded
from veritas.research.eth_recursion_v30.implicit_children import (
    _check_inputs, make_bipartite_edges, _direct_oracle, ImplicitBudgetExceeded)
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_arithmetic.jets import JetRing

SCHEMA = 'VERITAS_EXACT_FINITE_D44_CHILD_ELIMINATION_V381'
CLAIM = 'FINITE_FIXED_BETA_EXACT_JET_CHILD_ELIMINATION_ONLY'
SCOPE = {
    'fixed_beta_child_no_mode_bond_wires': True,
    'factor_bucket_elimination': True,
    'exact_extension_ring_arithmetic': True,
    'bounded_memoized_packet_tables': True,
    'independent_direct_halfedge_comparison': True,
    'complete_manuscript_recursive_algorithm': False,
    'M_over_8_theorem_proven': False,
    'subexponential_runtime_proven': False,
}


class SharedMeter(Meter):
    """One cooperative budget, with deterministic charged-work phase totals.

    Counts checkpoints, table/assignment steps and selected ring operations,
    not bit operations or all interpreter work. It cannot preempt C code.
    """
    def __init__(self, work, seconds):
        if type(work) is not int or not 100 <= work <= 2_000_000:
            raise ValueError('max_work must be integer in 100..2_000_000')
        if type(seconds) not in (int, float) or not 0 < seconds <= 30:
            raise ValueError('timeout_s must be in (0,30]')
        super().__init__(work, seconds)
        self.phase = 'preflight'
        self.phase_work = {}

    def tick(self, n=1):
        super().tick(n)
        self.phase_work[self.phase] = self.phase_work.get(self.phase, 0) + n


class MeteredJets:
    """Count public jet operations on the v3.8 elimination/oracle paths."""
    def __init__(self, jets, meter):
        self.jets, self.meter, self.base, self.length = jets, meter, jets.base, jets.length

    @property
    def zero(self): return self.jets.zero
    @property
    def one(self): return self.jets.one
    def elem(self, value):
        self.meter.tick(); return self.jets.elem(value)
    def add(self, a, b):
        self.meter.tick(); return self.jets.add(a, b)
    def neg(self, a):
        self.meter.tick(); return self.jets.neg(a)
    def sub(self, a, b):
        self.meter.tick(); return self.jets.sub(a, b)
    def mul(self, a, b):
        self.meter.tick(); return self.jets.mul(a, b)

@dataclass(frozen=True)
class Table:
    scope: tuple[int, ...]
    values: tuple[tuple, ...]

    def __post_init__(self):
        if len(self.values) != (1 << len(self.scope)) or len(set(self.scope)) != len(self.scope):
            raise ValueError('malformed factor table')

    def at(self, assignment):
        return self.values[sum((1 << j) for j, v in enumerate(self.scope) if assignment[v])]


class Executor:
    def __init__(self, jr, meter, max_entries, max_cache_entries):
        self.jr, self.meter = jr, meter
        if type(max_entries) is not int or not 2 <= max_entries <= 32768:
            raise ValueError('max_entries must be 2..32768')
        if type(max_cache_entries) is not int or not 0 <= max_cache_entries <= 65536:
            raise ValueError('max_cache_entries must be 0..65536')
        self.max_entries = max_entries
        self.max_cache_entries = max_cache_entries
        self.cache = {}
        self.cached_entries = 0
        self.cache_hits = 0
        self.max_intermediate_entries = 0
        self.generated_tables = 0
        self.elimination_steps = 0
        self.components = 0

    def table(self, scope, evaluator, cache_key=None):
        scope = tuple(sorted(scope))
        size = 1 << len(scope)
        if size > self.max_entries:
            raise ResourceLimit('packet/vertex factor exceeds intermediate table cap')
        if cache_key is not None and cache_key in self.cache:
            self.cache_hits += 1
            return self.cache[cache_key]
        values = []
        for mask in range(size):
            self.meter.tick()
            value = evaluator({v: int(bool(mask & (1 << j))) for j, v in enumerate(scope)})
            values.append(value)
        result = Table(scope, tuple(values))
        self.generated_tables += 1
        self.max_intermediate_entries = max(self.max_intermediate_entries, size)
        if cache_key is not None and self.cached_entries + size <= self.max_cache_entries:
            self.cache[cache_key] = result
            self.cached_entries += size
        return result

    def _components(self, tables):
        """Split disjoint factor components; scalar factors are handled separately."""
        scalars = [t for t in tables if not t.scope]
        nonscalars = [t for t in tables if t.scope]
        adjacency = defaultdict(set)
        for t in nonscalars:
            for v in t.scope:
                adjacency[v].update(t.scope)
        found = set()
        groups = []
        for v in sorted(adjacency):
            if v in found:
                continue
            todo = [v]
            block = set()
            while todo:
                cur = todo.pop()
                if cur in found: continue
                found.add(cur)
                block.add(cur)
                todo.extend(sorted(adjacency[cur] - found))
            groups.append([t for t in nonscalars if t.scope[0] in block])
        return scalars, groups

    def contract(self, tables):
        scalars, groups = self._components(tables)
        self.components += len(groups)
        result = self.jr.one
        for t in scalars:
            result = self.jr.mul(result, t.values[0])
        for group in groups:
            result = self.jr.mul(result, self._eliminate(group))
        return result

    def _eliminate(self, factors):
        factors = list(factors)
        while any(t.scope for t in factors):
            vars_ = set().union(*(set(t.scope) for t in factors))
            def cost(v):
                relevant = [t for t in factors if v in t.scope]
                nbr = set().union(*(set(t.scope) for t in relevant)) - {v}
                return (len(nbr), len(relevant), v)
            chosen = min(vars_, key=cost)
            selected = [t for t in factors if chosen in t.scope]
            factors = [t for t in factors if chosen not in t.scope]
            scope = tuple(sorted(set().union(*(set(t.scope) for t in selected)) - {chosen}))
            size = 1 << len(scope)
            if size > self.max_entries:
                raise ResourceLimit('intermediate table exceeds cap')
            output = []
            for mask in range(size):
                assignment = {v: int(bool(mask & (1 << j))) for j, v in enumerate(scope)}
                total = self.jr.zero
                for bit in (0, 1):
                    self.meter.tick()
                    assignment[chosen] = bit
                    prod = self.jr.one
                    for table in selected:
                        prod = self.jr.mul(prod, table.at(assignment))
                        if prod == self.jr.zero: break
                    total = self.jr.add(total, prod)
                output.append(total)
            factors.append(Table(scope, tuple(output)))
            self.max_intermediate_entries = max(self.max_intermediate_entries, size)
            self.elimination_steps += 1
        result = self.jr.one
        for table in factors:
            result = self.jr.mul(result, table.values[0])
        return result


def _group_factors(g, beta, net, mode_cert, data, executor):
    d3, rowgroups, colgroups, original, local, targeted, packets = data
    M = net.edges
    factors = []
    for f in original[g]:
        is_row = f.label.startswith(('row:', 'clause:'))
        scope = tuple(e if is_row else M + e for e in f.ports)
        def evaluate(a, f=f, scope=scope):
            k = sum(int(a[v]) << j for j, v in enumerate(scope))
            return executor.jr.elem([[f.table[k]]])
        # Labels can legitimately repeat for distinct tensor factors. Frozen
        # Factor content and port order identify the actual cached function.
        factors.append(executor.table(scope, evaluate, ('original', f.label, f.ports, f.table)))
    for pid, eds in enumerate(packets):
        rows = [eid for eid in eds if rowgroups[eid] == g]
        cols = [eid for eid in eds if colgroups[eid] == g]
        if not rows and not cols:
            continue
        scope = tuple(rows + [M + cid for cid in cols])
        relevant = tuple((mid, beta[mid]) for mid, m in enumerate(mode_cert['modes'])
                         if m['packet'] == pid and (m['target_group'] == g or m['source_group'] == g))
        def evaluate(a, pid=pid):
            return _packet_value(pid, g, beta, a, mode_cert, data,
                                 executor.jr, executor.meter)
        factors.append(executor.table(scope, evaluate, ('packet', pid, g, relevant)))
    owned = tuple([rid for rid in range(M) if rowgroups[rid] == g] +
                  [M + cid for cid in range(M) if colgroups[cid] == g])
    scopes = set().union(*(set(t.scope) for t in factors)) if factors else set()
    if scopes != set(owned):
        raise ArithmeticError('child factor incidence does not cover its original half-ports')
    return factors, owned


def construct_elimination_reference(net, mode_cert, *, max_work=800_000,
                                    timeout_s=20.0, max_tuples=3000,
                                    max_entries=1024, max_cache_entries=8192,
                                    compare_v37=False, _shared_meter=None):
    meter = _shared_meter if _shared_meter is not None else SharedMeter(max_work, timeout_s)
    start_work = meter.used
    before_phases = dict(meter.phase_work)
    meter.phase = 'validation'
    meter.tick()
    if type(max_tuples) is not int or not 1 <= max_tuples <= 3000:
        raise ValueError('invalid global mode tuple budget')
    if type(max_entries) is not int or not 2 <= max_entries <= 32768:
        raise ValueError('max_entries must be 2..32768')
    if type(max_cache_entries) is not int or not 0 <= max_cache_entries <= 65536:
        raise ValueError('max_cache_entries must be 0..65536')
    if check_jet_tile_modes(mode_cert, _budget=meter).get('valid') is not True:
        raise ValueError('invalid geometric-mode certificate')
    meter.tick()
    d3 = mode_cert['d3_certificate']
    p, e, length = (mode_cert[k] for k in ('precision', 'extension_degree', 'jet_length'))
    _check_inputs(net, d3, mode_cert['node'], p, e, length, _budget=meter)
    if make_bipartite_edges(net) != d3['edges']:
        raise ValueError('mode certificate incidence disagrees with input network')
    data = _data(net, mode_cert)
    meter.tick()
    jr = MeteredJets(JetRing(ExtensionRing(p, first_irreducible(e)), length), meter)
    executor = Executor(jr, meter, max_entries, max_cache_entries)
    total = jr.zero
    meter.phase = 'mode_enumeration_and_elimination'
    meter.tick()
    count = count_tuples([m['weight'] for m in mode_cert['modes']], p, cap=max_tuples)
    meter.tick()
    beta_count = 0
    children = None
    for beta in weighted_tuples([m['weight'] for m in mode_cert['modes']], p, max_tuples=max_tuples):
        meter.tick()
        prod = jr.one
        records = []
        for g in range(d3['r']):
            factors, owned = _group_factors(g, beta, net, mode_cert, data, executor)
            value = executor.contract(factors)
            prod = jr.mul(prod, value)
            records.append({'group':g, 'child_wires':len(owned),
                            'extra_mode_bond_wires':0,
                            'meets_numeric_6M_over_r':len(owned)*d3['r']<=6*net.edges,
                            'meets_strict_M_over_8':8*len(owned)<net.edges})
        if children is None:
            children = records
        total = jr.add(total, prod)
        beta_count += 1
    meter.phase = 'direct_oracle'
    meter.tick()
    reference = _direct_oracle(net, d3, mode_cert['node'], jr, meter)
    meter.tick()
    if total != reference:
        raise ArithmeticError('exact child elimination disagrees with independent half-edge oracle')
    if beta_count != count:
        raise ArithmeticError('weighted mode tuple count mismatch')
    if compare_v37:
        meter.phase = 'v37_comparison'
        meter.tick()
        old = construct_child_reference(net, mode_cert, max_work=max_work, timeout_s=timeout_s,
                                        _shared_meter=meter)
        meter.tick()
        if total != tuple(tuple(c) for c in old['result']):
            raise ArithmeticError('v3.7 exhaustive group oracle disagrees')
    meter.phase = 'finalization'
    meter.tick()
    result = {
        'schema':SCHEMA, 'claim':CLAIM, 'scope':dict(SCOPE),
        'network':_serialize_net(net), 'mode_certificate':deepcopy(mode_cert),
        'result':[list(c) for c in total], 'children':children or [],
        'mode_tuples_evaluated':beta_count,
        'work_measure':'cooperative_charged_events_not_bit_operations',
        'max_tuples_limit':max_tuples,
        'factor_tables_generated':executor.generated_tables,
        'packet_cache_hits':executor.cache_hits,
        'cached_factor_entries':executor.cached_entries,
        'elimination_steps':executor.elimination_steps,
        'components_processed':executor.components,
        'max_intermediate_entries':executor.max_intermediate_entries,
        'max_entries_limit':max_entries, 'max_cache_entries_limit':max_cache_entries,
        'exact_direct_reference_matches':True,
        'v37_cross_check_performed':bool(compare_v37),
        'manuscript_recursive_size_bound_proven':False,
        'subexponential_runtime_proven':False,
    }
    meter.tick()
    result['work'] = meter.used - start_work
    result['work_by_phase'] = {k: v - before_phases.get(k, 0) for k, v in meter.phase_work.items()
                               if v - before_phases.get(k, 0)}
    return result


def verify_elimination_reference(cert, *, max_work=800_000, timeout_s=20.0, _shared_meter=None):
    """Replay from recorded source data. No trusted client-provided conclusions."""
    try:
        meter = _shared_meter if _shared_meter is not None else SharedMeter(max_work, timeout_s)
        meter.phase = 'replay_preflight'
        meter.tick()
        if (not isinstance(cert, dict) or cert.get('schema') != SCHEMA or
            cert.get('claim') != CLAIM or cert.get('scope') != SCOPE):
            raise ValueError('unsupported schema or claimed theorem scope')
        net = _deserialize_net(cert['network'])
        meter.tick()
        new = construct_elimination_reference(
            net, cert['mode_certificate'], max_work=max_work, timeout_s=timeout_s,
            max_tuples=cert['max_tuples_limit'], _shared_meter=meter,
            max_entries=cert['max_entries_limit'],
            max_cache_entries=cert['max_cache_entries_limit'],
            compare_v37=cert['v37_cross_check_performed'])
        if new != cert:
            raise ValueError('source-replayed certificate mismatch')
        meter.phase = 'replay_finalization'
        meter.tick()
        return {'valid':True,
                'status':'FINITE_FIXED_BETA_CHILD_ELIMINATION_AND_DIRECT_ORACLE_CHECKED',
                'subexponential_runtime_proven':False}
    except (ResourceLimit, ImplicitBudgetExceeded, ModeBudgetExceeded, TimeoutError) as exc:
        return {'valid':False, 'status':'INCONCLUSIVE_RESOURCE_LIMIT', 'reason':str(exc),
                'subexponential_runtime_proven':False}
    except (ValueError, KeyError, IndexError, TypeError, ArithmeticError,
            OverflowError, ZeroDivisionError) as exc:
        return {'valid':False, 'status':'INVALID_OR_INCONCLUSIVE', 'reason':str(exc),
                'subexponential_runtime_proven':False}
