"""lem:sparsify: the disjoint sparsification tree of app:sparsify.

Repeatedly splits a k-CNF into two cases whose satisfying assignments
partition the parent's: F_A = G wedge H and F_B = G wedge wedge_a P_a
wedge wedge_{l in H} {not l}, where H is a nonempty proper subset of a
width-c clause occurring in at least theta_{c-|H|} = M^{c-|H|} clauses.
The smallest c and largest |H| are chosen; remaining ties are broken
deterministically by literal order. Leaves satisfy the occurrence bound
B = 2*sum_{j<k} M^j. Every resource is budget-capped and fails closed.
"""
from itertools import combinations

from .parameters import natural
from .resources import Budget, Limits, ResourceLimit


def normalize_antichain(clauses):
    """Drop tautologies, duplicates, and clauses containing another clause."""
    kept = {frozenset(c) for c in clauses}
    kept = {c for c in kept if not any(-x in c for x in c)}
    return frozenset(
        c for c in kept if not any(d != c and d <= c for d in kept))


def select_M(k, sigma_num, sigma_den, budget):
    """Smallest power-of-two M >= Gamma with Gamma*h <= sigma*M."""
    natural(k, 'clause width bound', 2)
    natural(sigma_num, 'sigma numerator', 1)
    natural(sigma_den, 'sigma denominator', 1)
    gamma = 4 * sum(3 ** j for j in range(k - 1))  # = 2*(3^{k-1}-1)
    M = 1
    while M < gamma:
        M *= 2
    while True:
        budget.tick(k + 1)
        C = 4 * sum((3 * M) ** j for j in range(k - 1))
        h = (4 * C * M - 1).bit_length()  # exact ceil(log2(4CM))
        if gamma * h * sigma_den <= M * sigma_num:
            return M
        M *= 2
        budget.bits(M.bit_length() + 1, 'sparsification parameter')


def _deg_c(clauses, c, H, budget):
    budget.tick(len(clauses))
    return sum(1 for C in clauses if len(C) == c and H <= C)


def _find_violation(clauses, M, budget):
    """Smallest c then largest |H| with deg_c(H) >= M^{c-|H|}; deterministic."""
    for c in sorted({len(C) for C in clauses}):
        if c < 2:
            continue
        subsets = set()
        for C in clauses:
            if len(C) != c:
                continue
            budget.tick(1 << c)
            for r in range(1, c):
                subsets.update(frozenset(comb) for comb in combinations(sorted(C), r))
        budget.items(len(subsets), 'candidate shared subsets')
        for size in range(c - 1, 0, -1):
            for H in sorted((s for s in subsets if len(s) == size),
                            key=lambda s: sorted(s)):
                if _deg_c(clauses, c, H, budget) >= M ** (c - size):
                    return c, H
    return None


def _children(clauses, c, H, budget):
    """eq:spar-children: selected = width-c clauses containing H."""
    selected = tuple(C for C in clauses if len(C) == c and H <= C)
    G = frozenset(C for C in clauses if C not in selected)
    petals = {frozenset(C - H) for C in selected}
    units = {frozenset({-lit}) for lit in H}
    child_a = normalize_antichain(set(G) | {H})
    child_b = normalize_antichain(set(G) | petals | units)
    budget.items(len(child_a) + len(child_b), 'sparsification children')
    return child_a, child_b


def sparsification_leaves(clauses, k, sigma_num, sigma_den,
                          *, limits=Limits(), budget=None):
    """Stream the lem:sparsify leaves depth first without retaining them.

    Yields leaf formulas (frozensets of literal frozensets); the tree is
    traversed depth first so working space is one path plus the DFS
    stack, matching the paper's node-processing account.
    """
    budget = Budget(limits) if budget is None else budget
    M = select_M(k, sigma_num, sigma_den, budget)
    stack = [normalize_antichain(set(map(frozenset, clauses)))]
    nodes = 0
    while stack:
        budget.tick(len(stack))
        nodes += 1
        budget.items(nodes, 'sparsification nodes')
        formula = stack.pop()
        found = _find_violation(formula, M, budget)
        if found is None:
            yield formula
            continue
        child_a, child_b = _children(formula, found[0], found[1], budget)
        stack.extend((child_a, child_b))


def occurrence_bound(k, M):
    """B = 2*sum_{j<k} M^j, the per-variable occurrence bound of a leaf."""
    natural(k, 'clause width bound', 2)
    natural(M, 'sparsification parameter', 2)
    return 2 * sum(M ** j for j in range(k))
