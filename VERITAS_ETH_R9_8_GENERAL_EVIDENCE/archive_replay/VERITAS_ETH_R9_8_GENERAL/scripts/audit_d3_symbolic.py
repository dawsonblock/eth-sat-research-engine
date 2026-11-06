"""Audit a closed-form D.3 packing family; does not contract a network."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from veritas.research.eth_packing_v26.symbolic_regular import RegularPackingWitness


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--radix', type=int, default=64)
    parser.add_argument('--degree', type=int, default=4)
    parser.add_argument('--copies', type=int, default=2048)
    args = parser.parse_args()
    try:
        result = RegularPackingWitness(args.radix, args.degree, args.copies).audit()
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
