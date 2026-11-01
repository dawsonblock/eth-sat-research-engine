"""Finite weighted mode tuples after exact affine-degree pruning."""
from __future__ import annotations

from veritas.research.eth_modes_v27.enumeration import ModeBudgetExceeded


def structural_tuples(modes, precision, *, max_tuples=3000):
    """Stream tuples satisfying weight and necessary target-row degree bounds.

    A packet/group row product has one affine factor per target row.  Hence
    its total degree in all targeted modes is at most the number of rows
    which actually contain such a mode.  A particular mode's exponent is at
    most the number of rows containing it.  Tuples outside either bound have
    zero coefficients before source-mode substitution.
    """
    if type(precision) is not int or not 1 <= precision <= 1024:
        raise ValueError('precision must be in 1..1024')
    if type(max_tuples) is not int or max_tuples < 1:
        raise ValueError('positive tuple budget required')
    mode_list = tuple(modes)
    groups = {}
    rows_by_mode = []
    for mode in mode_list:
        if (not isinstance(mode, dict) or type(mode.get('weight')) is not int or
                mode['weight'] < 1 or type(mode.get('packet')) is not int or
                type(mode.get('target_group')) is not int or not isinstance(mode.get('rows'), list)):
            raise ValueError('invalid mode metadata')
        rows = tuple(row[0] for row in mode['rows'])
        if any(type(row) is not int for row in rows) or len(set(rows)) != len(rows):
            raise ValueError('mode rows must be distinct integer indices')
        key = (mode['packet'], mode['target_group'])
        groups.setdefault(key, set()).update(rows)
        rows_by_mode.append((key, len(rows)))
    capacity = {key: len(rows) for key, rows in groups.items()}
    state = [0] * len(mode_list)
    yielded = 0

    def visit(index, remaining):
        nonlocal yielded
        if index == len(mode_list):
            yielded += 1
            if yielded > max_tuples:
                raise ModeBudgetExceeded('structural tuple count exceeds budget')
            yield tuple(state)
            return
        mode = mode_list[index]
        key, row_count = rows_by_mode[index]
        limit = min(row_count, capacity[key], (remaining - 1) // mode['weight'])
        for exponent in range(limit + 1):
            state[index] = exponent
            capacity[key] -= exponent
            yield from visit(index + 1, remaining - mode['weight'] * exponent)
            capacity[key] += exponent
        state[index] = 0

    yield from visit(0, precision)
