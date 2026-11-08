"""Exact bounded-width wire elimination in the call's coefficient ring.

Each wire x is summed out once: the factors f_1..f_k containing x are replaced
by g(y) = sum_{x in {0,1}} prod_i f_i(x, y). An ordering is admitted only after
a separate symbolic replay checks its width, every table size, the peak live
table entries and the predicted work against an explicit budget; no table is
allocated before that check. Cost is O(N 2^(w+1)) ring operations for width w.

This is a conventional variable-elimination contraction. It neither uses nor
supports the source recursion, and its results are classified separately.
"""
from dataclasses import asdict, dataclass
from time import monotonic

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.parent_child_r98.model import Refusal
from veritas.research.tapered_v4.source_recipes import EntryBudget, EntryLimits, compile_entry, evaluate_compiled

HEURISTICS = ('min_fill', 'min_degree')


@dataclass(frozen=True)
class EliminationBudget:
    max_width: int = 20
    max_table_entries: int = 1 << 21
    max_live_entries: int = 1 << 23
    max_work: int = 500_000_000
    max_seconds: int = 3600
    heuristic: str = 'min_fill'

    def __post_init__(self):
        for name, high in (('max_width', 30), ('max_table_entries', 1 << 30), ('max_live_entries', 1 << 32),
                           ('max_work', 1 << 40), ('max_seconds', 86_400)):
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= high:
                raise ValueError('invalid elimination ' + name)
        if self.heuristic not in HEURISTICS:
            raise ValueError('unknown elimination ordering heuristic')

    def record(self):
        return asdict(self)


class Meter:
    def __init__(self, budget):
        self.budget, self.work, self.started = budget, 0, monotonic()

    def tick(self, n=1):
        self.work += n
        if self.work > self.budget.max_work:
            raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'elimination work budget')
        if monotonic() - self.started > self.budget.max_seconds:
            raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'elimination time budget')

    def elapsed(self):
        return monotonic() - self.started


def call_scopes(call):
    """Each vertex is one factor over its ordered ports; every wire is a variable."""
    return tuple(tuple(v.ports) for v in call.vertices), tuple(range(call.edge_count))


def plan_order(scopes, variables, heuristic='min_fill'):
    """Greedy min-fill or min-degree order on the wire interaction graph."""
    if heuristic not in HEURISTICS:
        raise ValueError('unknown elimination ordering heuristic')
    adjacent = {v: set() for v in variables}
    for scope in scopes:
        for v in scope:
            if v not in adjacent:
                raise ValueError('factor port outside the variable set')
            adjacent[v].update(x for x in scope if x != v)
    order = []
    while adjacent:
        def fill(v):
            near = sorted(adjacent[v])
            return sum(1 for i, a in enumerate(near) for b in near[i+1:] if b not in adjacent[a])
        if heuristic == 'min_fill':
            v = min(adjacent, key=lambda x: (fill(x), len(adjacent[x]), x))
        else:
            v = min(adjacent, key=lambda x: (len(adjacent[x]), fill(x), x))
        near = adjacent.pop(v)
        for a in near:
            adjacent[a].discard(v)
            adjacent[a].update(b for b in near if b != a)
        order.append(v)
    return tuple(order)


def verify_order(scopes, variables, order, budget):
    """Symbolic bucket replay. Recomputes every step; trusts no planner output."""
    if type(budget) is not EliminationBudget:
        raise TypeError('EliminationBudget required')
    variables = tuple(variables)
    if (type(order) is not tuple or any(type(v) is not int for v in order) or
            len(order) != len(variables) or set(order) != set(variables)):
        raise ValueError('elimination order must be a permutation of every wire')
    known = set(variables)
    factors = []
    for scope in scopes:
        if len(set(scope)) != len(scope) or not set(scope) <= known:
            raise ValueError('invalid factor scope')
        factors.append(frozenset(scope))
    reason = None
    initial = max((1 << len(f) for f in factors), default=1)
    live = peak = sum(1 << len(f) for f in factors)
    work = sum(1 << len(f) for f in factors)
    width, largest, steps = 0, initial, []
    if initial > budget.max_table_entries:
        reason = 'input factor table exceeds table budget'
    for x in order:
        joined = [f for f in factors if x in f]
        if not joined:
            raise ValueError('wire has no factor')
        frontier = frozenset().union(*joined) - {x}
        width, largest = max(width, len(frontier)), max(largest, 1 << len(frontier))
        live += 1 << len(frontier)
        peak = max(peak, live)
        live -= sum(1 << len(f) for f in joined)
        work += (1 << (len(frontier) + 1)) * len(joined)
        steps.append([x, len(frontier), len(joined)])
        factors = [f for f in factors if x not in f] + [frontier]
        if reason is None:
            if len(frontier) > budget.max_width:
                reason = 'elimination width exceeds width budget'
            elif 1 << len(frontier) > budget.max_table_entries:
                reason = 'elimination table exceeds table budget'
            elif peak > budget.max_live_entries:
                reason = 'live table entries exceed memory budget'
    if any(factors):
        raise ValueError('nonempty scope after eliminating every wire')
    work += len(factors)
    if reason is None and work > budget.max_work:
        reason = 'predicted elimination work exceeds work budget'
    return {'order': list(order), 'steps': steps, 'width': width, 'max_table_entries': largest,
            'peak_live_entries': peak, 'predicted_work': work, 'fits': reason is None,
            'reason': reason, 'budget': budget.record(), 'width_definition': 'MAX_FRONTIER_WIRES_AFTER_ELIMINATION',
            'width_is_treewidth_lower_bound': False}


def plan(call, budget):
    scopes, variables = call_scopes(call)
    order = plan_order(scopes, variables, budget.heuristic)
    certificate = verify_order(scopes, variables, order, budget)
    certificate['heuristic'] = budget.heuristic
    return certificate


def _index_maps(scope, full):
    """Split-address tables: index(a) = low[a & mask] | high[a >> half]."""
    position = {v: i for i, v in enumerate(full)}
    half = len(full) // 2

    def table(bits, shift):
        out = []
        for a in range(1 << bits):
            index = 0
            for i, v in enumerate(scope):
                p = position[v] - shift
                if 0 <= p < bits and (a >> p) & 1:
                    index |= 1 << i
            out.append(index)
        return out
    return table(half, 0), table(len(full) - half, half), half


def eliminate(call, certificate, budget):
    """Run an admitted order. Any resource refusal propagates; nothing partial returns."""
    scopes, variables = call_scopes(call)
    order = tuple(certificate['order'])
    replay = verify_order(scopes, variables, order, budget)
    if not replay['fits'] or replay['steps'] != certificate['steps']:
        raise Refusal('INCONCLUSIVE_ELIMINATION_BUDGET', replay['reason'] or 'elimination certificate mismatch')
    meter = Meter(budget)
    bits = max(1024, call.precision)
    ring = JetRing(ExtensionRing(call.precision, call.defining_polynomial, max_precision_bits=bits), call.jet_length)
    entries = EntryBudget(EntryLimits(max_work=100_000_000, max_seconds=60, max_precision_bits=bits))
    factors = []
    for vertex, scope in zip(call.vertices, scopes):
        compiled = compile_entry(vertex.tensor, entries)
        table = []
        for a in range(1 << len(scope)):
            meter.tick()
            table.append(evaluate_compiled(compiled, tuple((a >> i) & 1 for i in range(len(scope))),
                                           call.precision, entries))
        factors.append((scope, table))
    mul, add = ring.mul, ring.add
    live = peak = sum(len(t) for _, t in factors)
    for x in order:
        joined = [f for f in factors if x in f[0]]
        frontier = tuple(sorted(set().union(*(set(s) for s, _ in joined)) - {x}))
        full = frontier + (x,)
        maps = [(_index_maps(scope, full), table) for scope, table in joined]
        top = 1 << len(frontier)
        output = []
        for a in range(top):
            meter.tick(2 * len(joined))
            total = None
            for b in (a, a | top):
                term = None
                for (low, high, half), table in maps:
                    value = table[low[b & ((1 << half) - 1)] | high[b >> half]]
                    term = value if term is None else mul(term, value)
                total = term if total is None else add(total, term)
            output.append(total)
        live += len(output)
        peak = max(peak, live)
        live -= sum(len(t) for _, t in joined)
        factors = [f for f in factors if x not in f[0]] + [(frontier, output)]
    result = ring.one
    for scope, table in factors:
        meter.tick()
        result = mul(result, table[0])
    if peak != replay['peak_live_entries'] or meter.work != replay['predicted_work']:
        raise ArithmeticError('allocated tables or work differ from the admitted plan')
    return result, {'work_units': meter.work, 'entry_work_units': entries.used,
                    'peak_live_entries': peak, 'elapsed_seconds': meter.elapsed()}
