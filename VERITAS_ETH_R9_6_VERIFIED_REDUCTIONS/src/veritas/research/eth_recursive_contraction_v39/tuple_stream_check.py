"""Independent finite cardinality and streaming checks for structural tuples.

The generator traverses a depth-first tree. This checker instead builds
bounded per-(packet,target) generating functions and convolves their weight
coefficients, then checks each emitted tuple for membership and strict lexical
order. Equal independent cardinality and strictly ordered membership imply
that every vector satisfying these finite structural constraints appears once.
They do not prove mode support completeness or that all discarded terms vanish.
"""
from collections import defaultdict
from dataclasses import dataclass

from veritas.research.eth_modes_v27.enumeration import ModeBudgetExceeded


@dataclass(frozen=True)
class TupleConstraints:
    precision: int
    weights: tuple[int, ...]
    individual_caps: tuple[int, ...]
    group_ids: tuple[int, ...]
    group_capacities: tuple[int, ...]


def tuple_constraints(modes, precision, *, max_modes=4096, on_step=None):
    if type(precision) is not int or not 1 <= precision <= 1024:
        raise ValueError('precision must be in 1..1024')
    if type(max_modes) is not int or not 0 <= max_modes <= 100_000:
        raise ValueError('invalid mode cap')
    if not isinstance(modes, (tuple, list)):
        raise ValueError('mode sequence required')
    if len(modes) > max_modes:
        raise ModeBudgetExceeded('independent tuple mode cap exceeded')
    if on_step is not None and not callable(on_step):
        raise ValueError('tuple checker callback must be callable')
    groups, items = {}, []
    for mode in modes:
        if on_step is not None: on_step()
        if (not isinstance(mode, dict) or type(mode.get('packet')) is not int or
                type(mode.get('target_group')) is not int or
                type(mode.get('weight')) is not int or mode['weight'] < 1 or
                not isinstance(mode.get('rows'), (tuple, list))):
            raise ValueError('invalid tuple mode metadata')
        rows = []
        for row in mode['rows']:
            if on_step is not None: on_step()
            if not isinstance(row, (tuple, list)) or len(row) != 2 or type(row[0]) is not int:
                raise ValueError('invalid mode row')
            rows.append(row[0])
        if len(rows) != len(set(rows)):
            raise ValueError('mode row identifiers must be distinct')
        key = (mode['packet'], mode['target_group'])
        groups.setdefault(key, set()).update(rows)
        items.append((key, mode['weight'], len(rows)))
    keys = sorted(groups)
    indices = {key: i for i, key in enumerate(keys)}
    return TupleConstraints(precision, tuple(weight for _, weight, _ in items),
                            tuple(cap for _, _, cap in items),
                            tuple(indices[key] for key, _, _ in items),
                            tuple(len(groups[key]) for key in keys))


def independently_valid_tuple(beta, modes_or_constraints, precision=None, *, on_step=None):
    """Check membership without calling or trusting the DFS generator."""
    if isinstance(modes_or_constraints, TupleConstraints):
        if precision is not None:
            raise ValueError('precision is already bound to the constraints')
        constraints = modes_or_constraints
    else:
        constraints = tuple_constraints(modes_or_constraints, precision, on_step=on_step)
    if type(beta) is not tuple or len(beta) != len(constraints.weights):
        return False
    group_degrees = [0] * len(constraints.group_capacities)
    weight = 0
    for exponent, w, cap, group in zip(beta, constraints.weights,
                                        constraints.individual_caps, constraints.group_ids):
        if on_step is not None: on_step()
        if type(exponent) is not int or exponent < 0 or exponent > cap:
            return False
        weight += exponent * w
        if weight >= constraints.precision:
            return False
        group_degrees[group] += exponent
        if group_degrees[group] > constraints.group_capacities[group]:
            return False
    return True


def independent_weighted_tuple_count(modes_or_constraints, precision=None, *, max_tuples=100_000,
                                     max_states=100_000, on_step=None):
    """Count the constrained set via truncated group polynomials.

    Each local DP tracks total group exponent and weight, honoring each mode's
    individual capacity. The final sparse convolution counts all combinations
    with total weight below precision. Caps fail closed; no count is returned.
    """
    if isinstance(modes_or_constraints, TupleConstraints):
        if precision is not None:
            raise ValueError('precision is already bound to the constraints')
        constraints = modes_or_constraints
    else:
        constraints = tuple_constraints(modes_or_constraints, precision, on_step=on_step)
    if type(max_tuples) is not int or max_tuples < 1:
        raise ValueError('positive tuple cap required')
    if type(max_states) is not int or not 1 <= max_states <= 1_000_000:
        raise ValueError('state cap must be in 1..1000000')
    if on_step is not None and not callable(on_step):
        raise ValueError('tuple checker callback must be callable')
    grouped = [[] for _ in constraints.group_capacities]
    for weight, individual, group in zip(constraints.weights, constraints.individual_caps,
                                          constraints.group_ids):
        if on_step is not None: on_step()
        grouped[group].append((weight, individual))
    combined = {0: 1}
    for group, modes in enumerate(grouped):
        # Local states are (total exponent, weight) -> number of vectors.
        local = {(0, 0): 1}
        capacity = constraints.group_capacities[group]
        for weight, individual in modes:
            updated = defaultdict(int)
            for (degree, total_weight), count in local.items():
                upper = min(individual, capacity-degree,
                            (constraints.precision-1-total_weight)//weight)
                for exponent in range(upper+1):
                    if on_step is not None: on_step()
                    key = (degree+exponent, total_weight+exponent*weight)
                    updated[key] += count
                    if updated[key] > max_tuples or len(updated) > max_states:
                        raise ModeBudgetExceeded('independent tuple count or state cap exceeded')
            local = updated
        polynomial = defaultdict(int)
        for (_, weight), count in local.items():
            if on_step is not None: on_step()
            polynomial[weight] += count
            if polynomial[weight] > max_tuples:
                raise ModeBudgetExceeded('independent tuple count cap exceeded')
        next_combined = defaultdict(int)
        for left_weight, left_count in combined.items():
            for right_weight, right_count in polynomial.items():
                if on_step is not None: on_step()
                weight = left_weight + right_weight
                if weight >= constraints.precision:
                    continue
                next_combined[weight] += left_count * right_count
                if next_combined[weight] > max_tuples or len(next_combined) > max_states:
                    raise ModeBudgetExceeded('independent tuple count or state cap exceeded')
        combined = next_combined
        if sum(combined.values()) > max_tuples:
            raise ModeBudgetExceeded('independent tuple count cap exceeded')
    result = sum(combined.values())
    if result > max_tuples:
        raise ModeBudgetExceeded('independent tuple count cap exceeded')
    return result


class TupleStreamVerifier:
    """Verify membership, strict lexical ordering and independently counted size."""
    def __init__(self, modes, precision, *, max_tuples=100_000, max_states=100_000,
                 on_step=None):
        self.on_step = on_step
        self.constraints = tuple_constraints(modes, precision, on_step=on_step)
        self.expected_count = independent_weighted_tuple_count(
            self.constraints, max_tuples=max_tuples, max_states=max_states, on_step=on_step)
        self.previous = None
        self.actual_count = 0

    def accept(self, beta):
        if self.on_step is not None: self.on_step()
        if not independently_valid_tuple(beta, self.constraints, on_step=self.on_step):
            raise ValueError('tuple violates independent structural constraints')
        if self.previous is not None and beta <= self.previous:
            raise ValueError('duplicate or out-of-order tuple')
        self.previous = beta
        self.actual_count += 1
        if self.actual_count > self.expected_count:
            raise ValueError('tuple stream exceeds independent count')

    def finish(self):
        if self.actual_count != self.expected_count:
            raise ValueError('tuple stream differs from mode certificate: independent count mismatch')
        return self.actual_count
