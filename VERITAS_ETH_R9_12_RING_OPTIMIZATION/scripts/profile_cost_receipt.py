#!/usr/bin/env python3
"""Emit a compact cost receipt for hybrid or structure-aware exact counting."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from veritas.core.cnf import CNF
from veritas.research.cnf_structure import structure_aware_count
from veritas.research.hybrid_router import hybrid_count


def load_cnf(path: Path) -> CNF:
    text = path.read_text()
    if 'p cnf' in text:
        return CNF.from_dimacs(text)
    data = json.loads(text)
    return CNF.from_lists(data['n'], data['clauses'])


def receipt(result: dict) -> dict:
    routing = result.get('routing') or {}
    structure = result.get('structure') or {}
    return {
        'schema': 'VERITAS_COST_RECEIPT_V1',
        'status': result.get('status'),
        'count': result.get('count'),
        'engine': result.get('engine'),
        'chosen_backend': routing.get('chosen_backend'),
        'decomposed': structure.get('decomposed'),
        'elapsed_seconds': result.get('elapsed_seconds'),
        'evaluated_assignments': (result.get('execution') or {}).get('evaluated_assignments'),
        'independent_count_checked': result.get('independent_count_checked'),
        'complexity_claim': False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('cnf', type=Path)
    parser.add_argument('--structure', action='store_true', help='use structure_aware_count')
    parser.add_argument('--timeout', type=float, default=15)
    args = parser.parse_args()
    cnf = load_cnf(args.cnf)
    result = (
        structure_aware_count(cnf, timeout_s=args.timeout)
        if args.structure
        else hybrid_count(cnf, timeout_s=args.timeout)
    )
    print(json.dumps(receipt(result), indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
