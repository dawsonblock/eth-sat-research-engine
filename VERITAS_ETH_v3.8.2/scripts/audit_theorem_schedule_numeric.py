"""Check one hypothetical size path; this does not run a tensor contraction."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from veritas.research.appendix_d_schedule import schedule_path_preflight


def audit(exponent: int = 524290) -> dict:
    if type(exponent) is not int or not 10 <= exponent <= 1_000_000 or exponent % 10:
        raise ValueError('exponent must be a multiple of 10 in 10..1000000')
    s = 1 << exponent
    edges = s
    states = []
    for _ in range(4):
        states.append((edges, 1))
        edges = 3 * edges // 32
    result = schedule_path_preflight(s, states, max_size_bits=exponent + 1)
    calls = [{key: call[key] for key in ('depth', 'status', 'u', 'a',
                                          'numeric_preconditions') if key in call}
             for call in result['calls']]
    return {'scope': 'HYPOTHETICAL_NUMERIC_SIZE_PATH_ONLY',
            's_power_of_two_exponent': exponent,
            'path_status': result['status'], 'calls': calls,
            'ends_at_leaf': result.get('ends_at_leaf', False),
            'network_descriptions_verified': False,
            'child_identities_verified': False,
            'all_branches_verified': False,
            'uniform_theorem_proven': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exponent', type=int, default=524290)
    args = parser.parse_args()
    try:
        result = audit(args.exponent)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
