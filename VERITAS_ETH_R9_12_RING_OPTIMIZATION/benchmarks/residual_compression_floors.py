"""Minimum residual_compression_vs_brute for regression gates (engineering, not worst-case)."""

from __future__ import annotations

# Only cases where we expect strong collapse; adversarial families are omitted on purpose.
COMPRESSION_RATIO_FLOORS: dict[str, float] = {
    'independent_pairs_6': 100.0,
    'network_block_motif_4': 30.0,
    'dimacs_network_block_motif_4': 30.0,
    'star_coupled_8': 100.0,
    'layered_bridge_4x3': 80.0,
    'chain_8': 20.0,
}