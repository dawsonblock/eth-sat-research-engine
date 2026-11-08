"""Counting sparse polynomial systems by tensor contraction.

`lem:tensor-sparse-query`: given degree-at-most-k equations P_i over F2 on n
declared variables, count their common zeros by summing contractions of indexed
bipartite networks. The construction follows the proof: heavy-scope branching
(D_*), test/variable groups, degree-array enumeration, Boolean-wire subset
indexing, test-group coefficient extraction by subset inversion, and the
variable-group free-variable entries. Enumerating only arrays realized by
actual incidence monomials preserves the sum exactly, since an unrealized array
indexes monomials whose coefficient in the product is zero. All enumeration is
budget-bounded and fails closed; no asymptotic bound is claimed for finite runs.
"""
from math import isqrt

from .executor import contract
from .model import Network, OriginalTensor, Vertex
from .parameters import natural, Schedule
from .resources import Budget, Limits, ResourceLimit
from .sparse import (
    comb_cached,
    idempotent_coefficients,
    incidence_coefficient,
    normalize_system,
    scopes,
    subset_unrank,
    truncated_multiply,
    wire_bits,
)


def _partition(count, parts):
    """Contiguous blocks of sizes differing by at most one."""
    base, extra = divmod(count, parts)
    return tuple(base + (1 if i < extra else 0) for i in range(parts))


def _blocks(items, parts):
    sizes = _partition(len(items), parts)
    out, at = [], 0
    for size in sizes:
        out.append(tuple(items[at:at + size]))
        at += size
    return tuple(out)


def _incidences(system, test_group, variable_set):
    """Sorted (i, v) pairs with test i in test_group and v in the variable set."""
    return tuple(sorted(
        (i, v) for i in test_group
        for v in (set().union(*system[i]) if system[i] else set())
        if v in variable_set))


def _enumerate_arrays(system, test_groups, variable_groups, k_bound, ell, budget):
    """Stream degree arrays (d_gh) with 0<=d<=N_gh and sum<=K via J^2 counters.

    The paper enumerates the at-most-(K+1)^{J^2} arrays with a bounded number
    of counters; this yields them lazily with O(J^2) counters so the working
    space stays polynomial rather than materializing the index set.
    """
    a = len(system)
    K = k_bound * (a + 2 * (ell - 1))
    bounds = [
        [_incidences(system, test_groups[g], set(variable_groups[h]))
         for h in range(len(variable_groups))]
        for g in range(len(test_groups))]
    limits = tuple(tuple(len(pair) for pair in row) for row in bounds)
    counters = [0] * (len(test_groups) * len(variable_groups))
    J2 = len(counters)
    while True:
        budget.tick(J2 + 1)
        total = 0
        d = []
        overflow = True
        for g in range(len(test_groups)):
            row = []
            for h in range(len(variable_groups)):
                row.append(counters[g * len(variable_groups) + h])
                total += row[-1]
            d.append(tuple(row))
        if total <= K:
            yield tuple(d)
        # odometer advance: least significant counter is the last pair
        pos = J2 - 1
        while pos >= 0:
            g, h = divmod(pos, len(variable_groups))
            if counters[pos] < limits[g][h]:
                counters[pos] += 1
                overflow = False
                break
            counters[pos] = 0
            pos -= 1
        if overflow:
            return


def _decode_block(bits, incidences, d):
    """Decode wire bits into the indexed subset; None marks an invalid index."""
    index = 0
    for j, bit in enumerate(bits):
        index |= bit << j
    count = comb_cached(len(incidences), d)
    if index >= count:
        return None
    if count == 1:
        return set(incidences) if d else set()
    return {incidences[j] for j in subset_unrank(len(incidences), d, index)}


def build_network(n, system, degree_array, modulus, ell, es, J, free, budget):
    """One indexed bipartite network for a fixed degree array."""
    natural(ell, 'truncation order', 1)
    natural(J, 'group count', 1)
    test_groups = _blocks(range(len(system)), J)
    variable_groups = _blocks(free, J)
    incidence = [[_incidences(system, test_groups[g], set(variable_groups[h]))
                 for h in range(J)] for g in range(J)]
    widths = [[wire_bits(comb_cached(len(incidence[g][h]), degree_array[g][h]))
               for h in range(J)] for g in range(J)]
    ports = {}
    wire = 0
    for g in range(J):
        for h in range(J):
            ports[('row', g, h)] = tuple(range(wire, wire + widths[g][h]))
            ports[('column', h, g)] = ports[('row', g, h)]
            wire += widths[g][h]
    vertices = []
    zero = (0,) * ell
    for g in range(J):
        w_order = tuple(ports['row', g, h] for h in range(J))
        arity = sum(widths[g][h] for h in range(J))

        def make_test_entry(g=g, w_order=w_order):
            def evaluate(bits, budget):
                budget.tick()
                selected = {}
                for h in range(J):
                    offset = sum(widths[g][hh] for hh in range(h))
                    block = tuple(bits[offset + j] for j in range(len(w_order[h])))
                    subset = _decode_block(block, incidence[g][h],
                                           degree_array[g][h])
                    if subset is None:
                        return zero
                    for i, v in subset:
                        selected.setdefault(i, set()).add(v)
                entry = (1,) + (0,) * (ell - 1)
                for i in sorted(test_groups[g]):
                    c = incidence_coefficient(
                        system[i], selected.get(i, ()), modulus, ell, es, budget)
                    entry = truncated_multiply(entry, c, modulus, ell)
                return entry
            return evaluate

        vertices.append(Vertex('row', g, tuple(w for block in w_order for w in block),
                            OriginalTensor(arity, p_from(modulus), ell,
                                           b'sparse-test-group', make_test_entry())))
    for h in range(J):
        w_order = tuple(ports['column', h, g] for g in range(J))
        arity = sum(widths[g][h] for g in range(J))
        variables = set(variable_groups[h])

        def make_variable_entry(h=h, w_order=w_order, variables=variables):
            def evaluate(bits, budget):
                budget.tick()
                counts = {v: 0 for v in variables}
                for g in range(J):
                    offset = sum(widths[gg][h] for gg in range(g))
                    block = tuple(bits[offset + j] for j in range(len(w_order[g])))
                    subset = _decode_block(block, incidence[g][h],
                                           degree_array[g][h])
                    if subset is None:
                        return zero
                    for _, v in subset:
                        counts[v] += 1
                free = sum(1 for v in variables if counts[v] == 0)
                return (pow(2, free, modulus),) + (0,) * (ell - 1)
            return evaluate

        vertices.append(Vertex('column', h,
                            tuple(w for block in w_order for w in block),
                            OriginalTensor(arity, p_from(modulus), ell,
                                           b'sparse-variable-group', make_variable_entry())))
    return Network(wire, tuple(vertices))


def p_from(modulus):
    return modulus.bit_length() - 1


def _maximum_indexed_degree(incidence_sizes, K, budget):
    """Exact maximum of sum ceil(log2 binom(N_i,d_i)) for sum d_i<=K.

    Replacing d>N/2 by N-d keeps its binomial coefficient and uses no more
    degree. A budgeted knapsack therefore needs only 0..floor(N/2) choices.
    dp[b] is the maximum attainable with AT MOST b selected incidences.
    This is an admission calculation, not an asymptotic resource certificate.
    """
    natural(K, 'incidence degree cap')
    if type(incidence_sizes) not in (tuple, list):
        raise ValueError('finite incidence-size sequence required')
    for N in incidence_sizes:natural(N, 'incidence size')
    capacity = min(K, sum(N // 2 for N in incidence_sizes))
    budget.items(3 * (capacity + 1), 'degree-admission dynamic program')
    budget.tick(len(incidence_sizes) + 1)
    dp = [0] * (capacity + 1)
    for N in incidence_sizes:
        last = min(N // 2, capacity)
        if not last:continue
        widths = [0]
        coefficient = 1
        for d in range(1, last + 1):
            budget.tick()
            budget.bits(coefficient.bit_length() + N.bit_length(), 'degree-admission binomial intermediate')
            coefficient = coefficient * (N - d + 1) // d
            widths.append((coefficient - 1).bit_length())
        following = [0] * (capacity + 1)
        for available in range(capacity + 1):
            best = 0
            for d in range(min(last, available) + 1):
                budget.tick()
                best = max(best, dp[available - d] + widths[d])
            following[available] = best
        dp = following
    return dp[-1]


def _degree_admission(system, test_groups, variable_groups, k_bound, ell, s, budget):
    """Check every array's degree before any tensor contraction is attempted.

    A maximizing choice for one vertex extends to a valid full array by setting
    all other pairs to zero. Failure is thus an attainable excessive degree,
    not merely a loose upper bound. Report the true maximum over all vertices.
    """
    K = k_bound * (len(system) + 2 * (ell - 1))
    budget.items(len(test_groups) * len(variable_groups), 'incidence size grid')
    sizes = []
    for tests in test_groups:
        row = []
        for variables in variable_groups:
            N = len(_incidences(system, tests, set(variables)))
            budget.tick(N + 1)
            row.append(N)
        sizes.append(row)
    limit = Schedule(s).delta
    checked = 0
    witness = None
    for side, groups in (('row', sizes), ('column', tuple(zip(*sizes)))):
        for index, incidences in enumerate(groups):
            degree = _maximum_indexed_degree(incidences, K, budget)
            if degree > checked:
                checked = degree
                witness = (side, index)
    if checked > limit:
        return dict(admitted=False, degree=checked, limit=limit,
                    side=witness[0], group=witness[1], degree_cap=K)
    return dict(admitted=True, degree=checked, limit=limit)


def _exhaustive_free_zeros(system, free, budget):
    """Count one already-substituted branch, including every free variable.

    Heavy assignments are separate branches, so there is no heavy-variable
    factor. Free variables absent from the equations remain in the enumeration.
    """
    budget.items(len(free), 'free-variable branch map')
    if (any(type(v) is not int or v < 0 for v in free)
            or len(set(free)) != len(free)):
        raise ValueError('distinct nonnegative free-variable indices required')
    mapping = {v: index for index, v in enumerate(free)}
    if any(v not in mapping for eq in system for monomial in eq for v in monomial):
        raise ArithmeticError('substituted branch still contains a fixed variable')
    budget.tick(sum(1 + len(monomial) for eq in system for monomial in eq))
    remapped = tuple(tuple(frozenset(mapping[v] for v in monomial) for monomial in eq)
                     for eq in system)
    return _exhaustive_zeros(len(free), remapped, budget)


def _branch_count(system, n, free, modulus, ell, es, s, budget, event_sink):
    """One branch of lem:tensor-sparse-query: grouped indexed-wire networks."""
    a = len(system)
    k_bound = max((len(m) for eq in system for m in eq), default=0)
    J = 1
    while J**4 < n:
        J += 1
    test_groups = _blocks(range(a), J)
    variable_groups = _blocks(free, J)
    admission = _degree_admission(system, test_groups, variable_groups,
                                  k_bound, ell, s, budget)
    if not admission['admitted']:
        # lem:tensor-sparse-query uses direct enumeration for bounded
        # exceptional sizes. Replace the ENTIRE branch, never omit an array
        # or add a direct answer to a partial tensor sum. The same budget
        # covers the preflight and the original free-variable enumeration.
        return _exhaustive_free_zeros(system, free, budget), admission
    accumulator = (0,) * ell
    for array in _enumerate_arrays(system, test_groups, variable_groups,
                                   k_bound, ell, budget):
        network = build_network(n, system, [list(r) for r in array],
                                modulus, ell, es, J, list(free), budget)
        if network.maximum_degree > admission['limit']:
            raise ArithmeticError('indexed degree exceeded its admission certificate')
        size_constant = max(1, -(-max(network.wires, p_from(modulus), ell) // s))
        receipt = contract(network, s=s, precision=p_from(modulus), ell=ell,
                           size_constant=size_constant, budget=budget,
                           event_sink=event_sink)
        if receipt['status'] != 'PASS_MANUSCRIPT_CONSTRUCTION_EXECUTION':
            raise ResourceLimit('sparse network contraction: ' + str(receipt.get('status')))
        accumulator = tuple((x + y) % modulus
                            for x, y in zip(accumulator,
                                            tuple(row[0] for row in receipt['result'])))
    return sum(accumulator) % modulus, None


def _exhaustive_zeros(n, system, budget):
    budget.bits(n + 1, 'common-zero count')
    total = 0
    for assignment in range(1 << n):
        budget.tick()
        satisfied = True
        for eq in system:
            parity = 0
            for m in eq:
                budget.tick(len(m) + 1)
                parity ^= all((assignment >> v) & 1 for v in m)
            if parity:
                satisfied = False
                break
        total += satisfied
    return total


def common_zeros(n, equations, *, limits=Limits(), budget=None, event_sink=None):
    """Count common zeros of sparse F2 equations via lem:tensor-sparse-query.

    The lemma requires n>=20 declared variables; smaller systems are counted by
    direct enumeration, matching the paper's bounded-exceptional-sizes rule.
    For larger finite inputs an exact grouped-degree preflight checks every
    indexed array's source admission. A failing branch is counted directly on
    its original free variables and reported separately, with the same budget.
    No partial tensor sum or fixed/unused-variable multiplier is retained.
    """
    budget = Budget(limits) if budget is None else budget
    try:
        natural(n, 'declared variables', 1)
        system = normalize_system(n, equations)
        if n < 20:
            count = _exhaustive_zeros(n, system, budget)
            return {'status': 'PASS_EXACT_COUNT', 'count': count,
                    'route': 'BOUNDED_EXHAUSTIVE_SEARCH', 'ledger': budget.report(),
                    'source_qualified': False, 'complexity_proven': False}
        p = ell = n + 1
        budget.bits(p + 1, 'jet modulus')
        modulus = 1 << p
        es = idempotent_coefficients(ell, budget)
        lam = max(1, (n - 1).bit_length())
        nu = max(1, (lam - 1).bit_length())
        s = n * nu
        scope_sizes = scopes(system)
        N0 = sum(len(I) for I in scope_sizes)
        root = isqrt(lam)
        D_star = max(1, -(-N0 // n)) * (root if root * root == lam else root + 1)
        heavy = sorted(v for v in range(n)
                       if sum(1 for I in scope_sizes if v in I) > D_star)
        total = 0
        degree_fallbacks = 0
        largest_fallback_degree = 0
        budget.bits(len(heavy) + 1, 'heavy-variable branch fan-out')
        for assignment in range(1 << len(heavy)):
            budget.tick()
            fixed = {v: (assignment >> j) & 1 for j, v in enumerate(heavy)}
            branch = []
            died = False
            for eq in system:
                kept = []
                parity = {}
                for m in eq:
                    if any(v in fixed and fixed[v] == 0 for v in m):
                        continue
                    shrunk = frozenset(v for v in m if v not in fixed)
                    parity[shrunk] = parity.get(shrunk, 0) ^ 1
                kept = tuple(m for m, q in parity.items() if q)
                if kept == (frozenset(),):
                    died = True
                    break
                # Zero equations contribute the unit and are discarded before
                # defining the remaining equation count and incidence groups
                # (lem:tensor-sparse-query, heavy-variable substitution).
                if kept:
                    branch.append(kept)
            if died:
                continue
            branch = tuple(branch)
            free = tuple(sorted(v for v in range(n) if v not in fixed))
            if not branch:
                total = (total + pow(2, len(free), modulus)) % modulus
                continue
            value, degree_exception = _branch_count(branch, n, free, modulus, ell,
                                                    es, s, budget, event_sink)
            if degree_exception is not None:
                degree_fallbacks += 1
                largest_fallback_degree = max(largest_fallback_degree, degree_exception['degree'])
            total = (total + value) % modulus
        count = total % modulus
        if count > (1 << n):
            raise ArithmeticError('sparse count outside assignment range')
        receipt = {'status': 'PASS_EXACT_COUNT', 'count': count,
                   'route': 'SPARSE_POLY_CONTRACT', 'ledger': budget.report(),
                   'source_qualified': False, 'complexity_proven': False}
        if degree_fallbacks:
            receipt.update(route='SPARSE_POLY_CONTRACT_WITH_DIRECT_BRANCH_COUNT',
                degree_admission_fallback_branches=degree_fallbacks,
                largest_fallback_degree=largest_fallback_degree,
                source_degree_limit=Schedule(s).delta,
                fallback_policy='EXACT_DEGREE_PREFLIGHT_AND_ORIGINAL_FREE_VARIABLE_COUNT')
        return receipt
    except ResourceLimit as exc:
        return {'status': 'INCONCLUSIVE_RESOURCE_LIMIT', 'reason': str(exc),
                'ledger': budget.report(), 'source_qualified': False}
