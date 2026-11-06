"""Opt-in Hall-obstruction check for one finite packet-mode tuple.

The supplied mode-row supports must be complete and belong to an already
verified mode expansion.  This module does not validate that provenance,
decide whether a feasible coefficient cancels, or run a child contraction.
"""
from __future__ import annotations

from collections import deque


class _BudgetExceeded(Exception):
    pass


class _Work:
    def __init__(self, maximum, on_step=None):
        self.maximum = maximum
        self.used = 0
        self.on_step = on_step

    def tick(self):
        if self.used >= self.maximum:
            raise _BudgetExceeded
        if self.on_step is not None:
            self.on_step()
        self.used += 1


def certify_structural_tuple_matching(modes, beta, *, max_work=100_000, _on_step=None):
    """Check whether row selections can supply the requested exponents.

    A mode can use a row only when its supplied ``rows`` support contains
    that row, and each row factor supplies at most one mode selection.
    Failure of an integral bipartite matching gives a Hall-deficiency witness
    and forces the coefficient to zero, conditional on complete supports.
    A feasible matching does *not* prove nonzero coefficient: contributions
    may vanish or cancel in the coefficient ring.

    This bounded utility is opt-in and does not itself alter tuple enumeration.
    The finite recursor may request it after checking the mode certificate.
    Work units count selected scans, not all bit or memory costs.
    """
    if type(max_work) is not int or not 1 <= max_work <= 2_000_000:
        raise ValueError('max_work must be an integer in 1..2000000')
    if _on_step is not None and not callable(_on_step):
        raise ValueError('matching work callback must be callable')
    if not isinstance(modes, (tuple, list)) or not isinstance(beta, (tuple, list)):
        raise ValueError('immutable or finite mode and exponent sequences required')
    if len(modes) != len(beta):
        raise ValueError('one exponent is required per mode')
    work = _Work(max_work, _on_step)
    scope = {'support_provenance_verified': False,
             'nonzero_proven': False, 'uniform_complexity_proven': False}
    try:
        groups = {}
        for index, (mode, demand) in enumerate(zip(modes, beta)):
            work.tick()
            if (not isinstance(mode, dict) or type(demand) is not int or demand < 0 or
                    type(mode.get('packet')) is not int or mode['packet'] < 0 or
                    type(mode.get('target_group')) is not int or mode['target_group'] < 0 or
                    not isinstance(mode.get('rows'), (tuple, list))):
                raise ValueError('invalid mode or nonnegative integer exponent required')
            rows = []
            seen = set()
            for item in mode['rows']:
                work.tick()
                if (not isinstance(item, (tuple, list)) or len(item) != 2 or
                        type(item[0]) is not int or item[0] < 0 or item[0] in seen):
                    raise ValueError('mode rows must have unique nonnegative integer ids')
                seen.add(item[0])
                rows.append(item[0])
            if demand:
                key = (mode['packet'], mode['target_group'])
                groups.setdefault(key, []).append((index, demand, tuple(rows)))

        group_matchings = []
        for (packet, target), active in sorted(groups.items()):
            adjacency = {index: rows for index, _, rows in active}
            demands = {index: demand for index, demand, _ in active}
            owner = {}
            for start, demand, _ in active:
                for _ in range(demand):
                    work.tick()
                    queue = deque([start])
                    reached = {start}
                    row_predecessor = {}
                    mode_predecessor = {}
                    free = None
                    while queue and free is None:
                        current = queue.popleft()
                        work.tick()
                        for row in adjacency[current]:
                            work.tick()
                            if row in row_predecessor:
                                continue
                            row_predecessor[row] = current
                            previous_owner = owner.get(row)
                            if previous_owner is None:
                                free = row
                                break
                            if previous_owner not in reached:
                                reached.add(previous_owner)
                                mode_predecessor[previous_owner] = row
                                queue.append(previous_owner)
                    if free is None:
                        # All neighbors of reachable modes are owned by a
                        # reachable mode, while the root is still deficient.
                        modes_in_witness = sorted(reached)
                        rows_in_witness = sorted(row_predecessor)
                        total_demand = sum(demands[i] for i in modes_in_witness)
                        if total_demand <= len(rows_in_witness):
                            raise ArithmeticError('invalid matching deficiency witness')
                        return {'status': 'ZERO_IF_SUPPLIED_SUPPORT_COMPLETE',
                                'zero_from_supplied_support': True,
                                'work_units': work.used, **scope,
                                'witness': {'packet': packet, 'target_group': target,
                                            'mode_indices': modes_in_witness,
                                            'row_ids': rows_in_witness,
                                            'demand': total_demand,
                                            'available_rows': len(rows_in_witness)}}
                    row = free
                    while True:
                        work.tick()
                        current = row_predecessor[row]
                        owner[row] = current
                        if current == start:
                            break
                        row = mode_predecessor[current]
            assignment = {index: [] for index, _, _ in active}
            for row, index in sorted(owner.items()):
                work.tick()
                assignment[index].append(row)
            group_matchings.append({'packet': packet, 'target_group': target,
                                    'assigned_rows': assignment})
        return {'status': 'MATCHING_FEASIBLE_ONLY',
                'zero_from_supplied_support': False, 'work_units': work.used,
                'group_matchings': group_matchings, **scope}
    except _BudgetExceeded:
        return {'status': 'INCONCLUSIVE_RESOURCE_LIMIT', 'work_units': work.used, **scope}
