"""Check one explicit active-root packing family, without contracting it."""
from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from veritas.research.appendix_d_schedule import schedule_preflight
from veritas.research.eth_packing_v26.symbolic_regular import MultiCoordinateRegularPackingWitness


def audit():
    exponent = 131080
    s = 1 << exponent
    w = MultiCoordinateRegularPackingWitness(64, 2, 8, 1 << 131050)
    packing = w.audit(degree_bound=1 << 117972)
    schedule = schedule_preflight(s, w.edge_count, w.degree, 0,
                                  max_size_bits=exponent + 1)
    boundary_edges = (((0, 0), (0, 0), 0, 0, 0),
                      ((63, 0), (0, 63), w.copies - 1, 7, 7),
                      ((63, 63), (63, 63), w.copies - 1, 7, 7))
    return {
        'scope': 'STRUCTURED_SYMBOLIC_ROOT_PACKING_ONLY',
        'radix': 64, 'a': 2, 'actual_degree': 8,
        's_power_of_two_exponent': exponent,
        'scheduled_degree_bound_exponent': 117972,
        'root_edges_equal_s': w.edge_count == s,
        'schedule_status': schedule['status'],
        'schedule_u': schedule.get('u'), 'schedule_a': schedule.get('a'),
        'schedule_numeric_preconditions': schedule.get('numeric_preconditions'),
        'packing_numeric_conditions': packing['packing_numeric_conditions'],
        'boundary_slot_roundtrips': all(w.slot_to_edge(w.edge_to_slot(e)) == e
                                        for e in boundary_edges),
        'each_side_load_is_M_over_64': packing['row_load_each_group'] == s // 64
                                       and packing['column_load_each_group'] == s // 64,
        'each_group_half_wires_are_M_over_32': packing['child_half_wires_each_group'] == s // 32,
        'strict_one_eighth_shrink': packing['strict_one_eighth_shrink'],
        'deterministic_constructor_replayed': False,
        'children_constructed': False,
        'full_contraction_executed': False,
        'uniform_complexity_proven': False,
    }


if __name__ == '__main__':
    print(json.dumps(audit(), sort_keys=True))
