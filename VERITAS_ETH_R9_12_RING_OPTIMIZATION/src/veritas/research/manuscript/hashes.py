"""sec:hashes: the parity-check reduction from sparse #k-SAT to common zeros.

`lem:sparse-checks` constructs the initial Tanner-code check matrix A^(0):
a d_G-regular bipartite graph on two copies of {0,1}^{ell_G} with
epsilon-biased port shifts, a local code A_loc whose kernel has minimum
weight delta*d_G, vertex checks restricted to m retained edge coordinates.
For m <= D_0 the construction degenerates to q_G=1 (no shift condition,
d_G=m, two copies of A_loc). `lem:greedy-hashes` appends 3n rows of list
length P, each minimizing the common-zero count among the (2m)^P ordered
lists; every candidate count is computed by the sparse-polynomial counter.
All enumeration is sequential and budget-bounded; at paper-scale parameters
P>=20000, so candidate enumeration exceeds the configured practical
allowance and the procedure correctly reports INCONCLUSIVE. The q_G>1
expander path is implemented but verified only on scaled fixtures; the
paper-scale expander and active-recursion path are not validated.
"""
from itertools import combinations, product

from .cnf import clause_violation_polynomial
from .parameters import natural
from .resources import Budget, Limits, ResourceLimit
from .sparse_query import common_zeros


def sparse_check_parameters(m, B, n):
    """mu, P, D_0 of lem:sparse-checks."""
    natural(m, 'clause count', 1)
    natural(B, 'clause density', 1)
    mu = m.bit_length()  # floor(log2 m) + 1 for m >= 1
    P = 20000 * B * B * mu * mu
    D0 = 320000 * B * B * mu * mu * mu
    return mu, P, D0


def _walsh_sum(shifts, b, d_G):
    total = 0
    for s in shifts:
        parity = (s & b).bit_count() & 1
        total += -1 if parity else 1
    return total


def _local_code(c_G, d_G, delta_num, delta_den, budget):
    """Smallest c_G x d_G binary matrix whose kernel has weight >= delta*d_G.

    Enumerates matrices in row-major binary order; for delta*d_G<1 every
    nonzero word already exceeds the bound, so the enumeration returns at once.
    """
    # h = ceil(delta*d_G)-1: words of weight <= h must be rejected.
    # Fixed-weight words are regenerated lazily per candidate matrix
    # (position subsets only), so working space stays O(d_G).
    threshold = -(-delta_num * d_G // delta_den) - 1
    if threshold <= 0:
        budget.items(c_G, 'local-code zero rows')
        return tuple(0 for _ in range(c_G))
    budget.items(c_G, 'local-code row count')
    budget.items(d_G, 'local-code word positions')
    budget.bits(c_G * d_G + 1, 'local-code matrix index')
    for bits in range(1 << (c_G * d_G)):
        budget.tick(c_G * d_G)
        rows = [(bits >> (r * d_G)) & ((1 << d_G) - 1) for r in range(c_G)]
        accepted = True
        for weight in range(1, threshold + 1):
            for positions in combinations(range(d_G), weight):
                budget.tick()
                word = 0
                for pos in positions:
                    word |= 1 << pos
                # A_loc z != 0 means some check row has nonzero syndrome
                if not any((row & word).bit_count() & 1 for row in rows):
                    accepted = False
                    break
            if not accepted:
                break
        if accepted:
            return tuple(rows)
    raise ResourceLimit('local-code matrix enumeration exceeds allowance')


def sparse_checks(n, clauses, B, *, limits=Limits(), budget=None):
    """Construct A^(0) of lem:sparse-checks: all 2*q_G*c_G Tanner rows.

    Edge (u,j) joins left vertex u to right vertex u XOR s_j and carries
    coordinate u*d_G+j; the deterministic shortening retains the first m
    coordinates. For m<=D_0, q_G=1 (no shift condition, d_G=m). For m>D_0
    the epsilon-biased shift tuple is enumerated sequentially and is
    budget-bounded (eq:hash-walsh); it fails closed, never silently skips.
    """
    budget = Budget(limits) if budget is None else budget
    m = len(clauses)
    if m == 0:
        return ()
    mu, P, D0 = sparse_check_parameters(m, B, n)
    d_G = min(m, D0)
    q_G = 1  # smallest 2^a with 2^a * d_G >= m
    while q_G * d_G < m:
        q_G *= 2
    c_G = -(-d_G // (8 * B))
    delta_num, delta_den = 1, 100 * B * mu
    rows_loc = _local_code(c_G, d_G, delta_num, delta_den, budget)
    if q_G == 1:
        budget.items(d_G, 'identity shifts')
        shifts = (0,) * d_G
    else:
        ell_G = q_G.bit_length() - 1
        eps_num, eps_den = 1, 200 * B * mu
        shifts = _biased_shifts(d_G, ell_G, eps_num, eps_den, budget)
        if shifts is None:
            raise ResourceLimit('expander shift search exceeds allowance')
    budget.items(2 * q_G * c_G, 'initial parity-check rows')
    budget.bits(m, 'retained edge coordinates')
    A0 = []
    for u in range(q_G):  # left-vertex checks on incident edge coords
        for r in rows_loc:
            budget.tick(d_G)
            word = 0
            for j in range(d_G):
                e = u * d_G + j
                if e < m and (r >> j) & 1:
                    word |= 1 << e
            A0.append(word)
    for v in range(q_G):  # right-vertex checks: edge (v XOR s_j, j)
        for r in rows_loc:
            budget.tick(d_G)
            word = 0
            for j in range(d_G):
                e = (v ^ shifts[j]) * d_G + j
                if e < m and (r >> j) & 1:
                    word |= 1 << e
            A0.append(word)
    return tuple(A0)


def _biased_shifts(d_G, ell_G, eps_num, eps_den, budget):
    """First d_G-tuple of shifts whose Walsh sums are eps*d_G-biased.

    The test is the exact rational inequality |sum_j (-1)^{b.s_j}| <=
    (eps_num/eps_den)*d_G, checked as abs(W)*eps_den <= eps_num*d_G.
    """
    budget.bits(ell_G + 1, 'nonzero b vector count')
    budget.bits(d_G * ell_G + 1, 'expander shift tuple')
    q_bound = 1 << ell_G
    budget.items(q_bound - 1, 'nonzero b vectors')
    nonzero_b = tuple(range(1, q_bound))
    mask = q_bound - 1
    for bits in range(1 << (d_G * ell_G)):
        budget.tick(d_G * ell_G)
        shifts = [(bits >> (j * ell_G)) & mask for j in range(d_G)]
        ok = True
        for b in nonzero_b:
            budget.tick(d_G)
            if abs(_walsh_sum(shifts, b, d_G)) * eps_den > eps_num * d_G:
                ok = False
                break
        if ok:
            return tuple(shifts)
    return None


def _row_equation(row, violation_monomials):
    """P_i(x) = sum_{e:row bit=1} v_e(x), monomials combined modulo 2."""
    parity = {}
    for e in range(len(violation_monomials)):
        if (row >> e) & 1:
            for m in violation_monomials[e]:
                parity[m] = parity.get(m, 0) ^ 1
    return [m for m, q in parity.items() if q]


def system_equations(rows, violation_monomials):
    return tuple(_row_equation(row, violation_monomials) for row in rows)


def greedy_rows(n, clauses, A0, P, *, limits=Limits(), budget=None):
    """lem:greedy-hashes: append 3n rows of list length P minimizing D(A).

    Enumerates the (2m)^P ordered lists sequentially; each candidate's
    common-zero count comes from `common_zeros`. The least count wins, ties
    broken by enumeration order. Budget-bounded: P>=20000 means the candidate
    enumeration alone exceeds the configured practical allowance.
    """
    budget = Budget(limits) if budget is None else budget
    m = len(clauses)
    violation = [clause_violation_polynomial(c) for c in clauses]
    rows = list(A0)
    # (2m)^P >= 2^P candidate steps: fail closed by bit-length comparison,
    # without constructing the (2m)^P integer itself.
    cap = budget.limits.max_work
    if cap is not None and P >= cap.bit_length():
        raise ResourceLimit('greedy candidate enumeration exceeds allowance')
    # product(repeat=P) pools a P-length list and 2m-entry pool before
    # yielding anything: charge the allocations before constructing it.
    budget.items(P, 'greedy candidate list')
    budget.items(2 * m, 'greedy candidate pool')
    budget.bits(m, 'greedy row')
    for _round in range(3 * n):
        budget.tick()
        best_row = None
        best_count = None
        # enumerate ordered lists gamma in ([m]x{0,1})^P lexicographically
        for gamma in product(range(2 * m), repeat=P):
            budget.tick()
            word = 0
            for j, code in enumerate(gamma):
                e, c = divmod(code, 2)
                if c:
                    word ^= 1 << e
            result = common_zeros(
                n, system_equations(rows + [word], violation),
                limits=limits, budget=budget)
            if result['status'] != 'PASS_EXACT_COUNT':
                raise ResourceLimit('candidate count: ' + str(result.get('status')))
            count = result['count']
            if best_count is None or count < best_count:
                best_count = count
                best_row = word
        rows.append(best_row)
    return tuple(rows)


def count_sparse_formula(n, clauses, B, k_bound, *, limits=Limits(),
                         budget=None, event_sink=None):
    """subsec:count-sparse: sparse-checks, greedy rows, final common-zero count."""
    budget = Budget(limits) if budget is None else budget
    try:
        m = len(clauses)
        if m == 0:
            budget.bits(n + 1, 'trivial clause count')
            return {'status': 'PASS_EXACT_COUNT', 'count': 1 << n,
                    'route': 'TRIVIAL_CNF', 'ledger': budget.report(),
                    'source_qualified': False}
        if any(len(c) == 0 for c in clauses):
            return {'status': 'PASS_EXACT_COUNT', 'count': 0,
                    'route': 'TRIVIAL_CNF', 'ledger': budget.report(),
                    'source_qualified': False}
        mu, P, D0 = sparse_check_parameters(m, B, n)
        A0 = sparse_checks(n, clauses, B, limits=limits, budget=budget)
        rows = greedy_rows(n, clauses, A0, P, limits=limits, budget=budget)
        violation = [clause_violation_polynomial(c) for c in clauses]
        result = common_zeros(n, system_equations(rows, violation),
                              limits=limits, budget=budget,
                              event_sink=event_sink)
        if result['status'] != 'PASS_EXACT_COUNT':
            return result
        receipt = {'status': 'PASS_EXACT_COUNT', 'count': result['count'],
                   'route': 'PARITY_CHECKS_SPARSE_QUERY',
                   'ledger': result['ledger'], 'source_qualified': False,
                   'complexity_proven': False}
        if result.get('degree_admission_fallback_branches'):
            receipt['final_query_degree_fallback'] = dict(
                route=result.get('inner_route', result['route']),
                **{key: result[key] for key in ('degree_admission_fallback_branches',
                   'largest_fallback_degree', 'source_degree_limit', 'fallback_policy')})
        return receipt
    except ResourceLimit as exc:
        return {'status': 'INCONCLUSIVE_RESOURCE_LIMIT', 'reason': str(exc),
                'ledger': budget.report(), 'source_qualified': False}
