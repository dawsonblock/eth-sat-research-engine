"""Factorized representation of the affine-row support; the support is unchanged.

The explicit support is the Boolean support of
G(X, z) = prod_r (1 + sum_{j in I_r} X_j z^{w_j}) mod z^P.
Rows with identical incidence are one power node. Rows sharing no mode split
G into components on disjoint coordinates. Components are joined by a layered
decision diagram whose state is the accumulated weight below P. States merge
by weight, but distinct exponent vectors remain distinct paths: no two terms
are ever identified, and counting is over paths.
"""
from veritas.research.parent_child_r98.model import Refusal


def affine_incidence(modes, row_certificate=None):
    """The same incidence rule as build_support: one (packet, row) per factor."""
    incidence = {}
    active = None if row_certificate is None else set(row_certificate['nonconstant_row_ports'])
    for mid, mode in enumerate(modes):
        for row, _ in mode['rows']:
            if active is None or row in active:
                incidence.setdefault((mode['packet'], row), []).append(mid)
    return incidence


class SupportCircuit:
    def __init__(self, modes, precision, *, budget, row_certificate=None, max_local_states=100_000):
        if type(precision) is not int or precision < 1:
            raise ValueError('positive precision required')
        weights = tuple(mode['weight'] for mode in modes)
        if any(type(w) is not int or w < 0 for w in weights):
            raise ValueError('nonnegative integer mode weights required')
        self.mode_count, self.precision, self.weights = len(modes), precision, weights
        powers = {}
        for row in sorted(affine_incidence(modes, row_certificate).items()):
            key = tuple(row[1])
            powers[key] = powers.get(key, 0) + 1
            budget.tick(len(key) + 1)
        parent = list(range(len(modes)))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        for key in powers:
            for mid in key[1:]:
                parent[find(mid)] = find(key[0])
        grouped = {}
        for key, multiplicity in sorted(powers.items()):
            grouped.setdefault(find(key[0]), []).append((key, multiplicity))
        self.components = []
        for root in sorted(grouped):
            nodes = grouped[root]
            coordinates = tuple(sorted({mid for key, _ in nodes for mid in key}))
            self.components.append((coordinates, tuple(nodes),
                                    self._local(coordinates, nodes, budget, max_local_states)))
        self._diagram(budget)

    def _local(self, coordinates, nodes, budget, cap):
        """Explicit local support of one component, truncated by weight."""
        position = {mid: i for i, mid in enumerate(coordinates)}
        states = {(0,) * len(coordinates): 0}
        for key, multiplicity in nodes:
            for _ in range(multiplicity):
                updated = dict(states)
                for beta, weight in states.items():
                    for mid in key:
                        budget.tick(len(coordinates) + 1)
                        if weight + self.weights[mid] >= self.precision:
                            continue
                        value = list(beta)
                        value[position[mid]] += 1
                        updated[tuple(value)] = weight + self.weights[mid]
                        if len(updated) > cap:
                            raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'factorized local support cap')
                states = updated
        return tuple(sorted(states.items()))

    def _diagram(self, budget):
        """Layer c maps accumulated weight to its number of distinct partial paths."""
        layers = [{0: 1}]
        for _, _, local in self.components:
            following = {}
            for weight, paths in layers[-1].items():
                for _, extra in local:
                    budget.tick()
                    if weight + extra < self.precision:
                        following[weight + extra] = following.get(weight + extra, 0) + paths
            layers.append(following)
        self.layers = layers

    def count(self):
        return sum(self.layers[-1].values())

    def contains(self, beta):
        if type(beta) is not tuple or len(beta) != self.mode_count or any(type(x) is not int or x < 0 for x in beta):
            return False
        covered, total = set(), 0
        for coordinates, _, local in self.components:
            covered.update(coordinates)
            part = tuple(beta[mid] for mid in coordinates)
            weight = dict(local).get(part)
            if weight is None:
                return False
            total += weight
        return all(beta[mid] == 0 for mid in range(self.mode_count) if mid not in covered) and total < self.precision

    def tuples(self, *, limit):
        """Enumerate every path once, refusing above an explicit size limit."""
        if self.count() > limit:
            raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'factorized support expansion limit')
        result = []

        def walk(c, weight, beta):
            if c == len(self.components):
                result.append(tuple(beta))
                return
            coordinates, _, local = self.components[c]
            for part, extra in local:
                if weight + extra < self.precision:
                    for mid, x in zip(coordinates, part):
                        beta[mid] = x
                    walk(c + 1, weight + extra, beta)
            for mid in coordinates:
                beta[mid] = 0
        walk(0, 0, [0] * self.mode_count)
        return sorted(result)

    def summary(self):
        return {'schema': 'VERITAS_R912_FACTORIZED_SUPPORT_V1', 'support_size': self.count(),
                'components': len(self.components),
                'power_nodes': sum(len(nodes) for _, nodes, _ in self.components),
                'rows': sum(m for _, nodes, _ in self.components for _, m in nodes),
                'largest_local_support': max((len(local) for _, _, local in self.components), default=1),
                'diagram_states': sum(len(layer) for layer in self.layers),
                'representation_only': True, 'support_semantics': 'IDENTICAL_TO_EXPLICIT_AFFINE_ROW_SUPPORT',
                'source_qualified': False}
