"""Minimum residual_compression_vs_brute for regression gates (engineering, not worst-case)."""

from __future__ import annotations

import json
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
FLOORS_JSON = PACKAGE_ROOT / 'validation' / 'residual_compression_floors.json'

# Only cases where we expect strong collapse; adversarial families are omitted on purpose.
DEFAULT_COMPRESSION_RATIO_FLOORS: dict[str, float] = {
    'independent_pairs_6': 100.0,
    'network_block_motif_4': 30.0,
    'dimacs_network_block_motif_4': 30.0,
    'star_coupled_8': 100.0,
    'layered_bridge_4x3': 80.0,
    'chain_8': 20.0,
}


def load_compression_floors() -> dict[str, float]:
    merged = dict(DEFAULT_COMPRESSION_RATIO_FLOORS)
    if FLOORS_JSON.is_file():
        data = json.loads(FLOORS_JSON.read_text(encoding='utf-8'))
        merged.update(data.get('floors') or {})
    return merged


COMPRESSION_RATIO_FLOORS = DEFAULT_COMPRESSION_RATIO_FLOORS