"""Finite weighted mode tuples after exact affine-degree pruning."""
from __future__ import annotations

from veritas.research.eth_modes_v27.enumeration import ModeBudgetExceeded


def structural_tuples(modes, precision, *, max_tuples=3000, _on_step=None):
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
    if _on_step is not None and not callable(_on_step):
        raise ValueError('tuple work callback must be callable')

    def tick():
        if _on_step is not None:
            _on_step()

    tick()  # Check the cooperative budget even for an empty mode set.
    mode_list = []
    for mode in modes:
        tick()
        mode_list.append(mode)
    mode_list = tuple(mode_list)
    groups = {}
    rows_by_mode = []
    for mode in mode_list:
        tick()
        if (not isinstance(mode, dict) or type(mode.get('weight')) is not int or
                mode['weight'] < 1 or type(mode.get('packet')) is not int or
                type(mode.get('target_group')) is not int or not isinstance(mode.get('rows'), list)):
            raise ValueError('invalid mode metadata')
        rows = []
        for row in mode['rows']:
            tick()
            rows.append(row[0])
        rows = tuple(rows)
        if any(type(row) is not int for row in rows) or len(set(rows)) != len(rows):
            raise ValueError('mode rows must be distinct integer indices')
        key = (mode['packet'], mode['target_group'])
        groups.setdefault(key, set()).update(rows)
        rows_by_mode.append((key, len(rows)))
    capacity = {key: len(rows) for key, rows in groups.items()}
    size = len(mode_list)
    if size == 0:
        yield ()
        return
    state = [0] * size
    next_exponent = [0] * size
    remaining = [precision] * (size + 1)
    yielded = 0
    depth = 0
    # Iterative depth-first search keeps one exponent and remaining capacity
    # per level.  Restoring the chosen exponent when returning to a parent is
    # essential when several modes target the same packet/group row factors.
    while depth >= 0:
        tick()
        if depth == size:
            yielded += 1
            if yielded > max_tuples:
                raise ModeBudgetExceeded('structural tuple count exceeds budget')
            yield tuple(state)
            depth -= 1
            capacity[rows_by_mode[depth][0]] += state[depth]
            continue
        mode = mode_list[depth]
        key, row_count = rows_by_mode[depth]
        limit = min(row_count, capacity[key],
                    (remaining[depth] - 1) // mode['weight'])
        if next_exponent[depth] > limit:
            next_exponent[depth] = 0
            depth -= 1
            if depth >= 0:
                capacity[rows_by_mode[depth][0]] += state[depth]
            continue
        exponent = next_exponent[depth]
        next_exponent[depth] += 1
        state[depth] = exponent
        capacity[key] -= exponent
        remaining[depth + 1] = remaining[depth] - mode['weight'] * exponent
        depth += 1
