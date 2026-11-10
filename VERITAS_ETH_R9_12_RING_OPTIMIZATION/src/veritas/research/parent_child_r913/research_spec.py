"""Exact quantity schemas for R9.13 (specification only, no theorems).

Distinguishes the precision-truncated weighted aggregate from the single target
coefficient required by production packet evaluation. No ETH, subexponential, or
source-qualification claim.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Tuple


class PacketQuantityKind(str, Enum):
    """Which mathematical object a computation must preserve."""

    TRUNCATED_WEIGHTED_AGGREGATE = "truncated_weighted_aggregate"
    TARGET_COEFFICIENT = "target_coefficient"
    FULL_SUBSTITUTION = "full_substitution"  # diagnostic only; not production


@dataclass(frozen=True)
class PreservationObligation:
    """One equality the pipeline must establish (proof status external)."""

    schema: str
    kind: PacketQuantityKind
    description: str
    proved_in_this_repo: bool
    qualification: str


PIPELINE_OBLIGATIONS: Tuple[PreservationObligation, ...] = (
    PreservationObligation(
        schema="VERITAS_R913_OBLIGATION_AGGREGATE_V1",
        kind=PacketQuantityKind.TRUNCATED_WEIGHTED_AGGREGATE,
        description="Supported sum Σ_β A_β s^β with Σ w_j β_j < P matches truncated DP.",
        proved_in_this_repo=False,
        qualification="bounded_packet_fixtures_and_integer_oracle_only",
    ),
    PreservationObligation(
        schema="VERITAS_R913_OBLIGATION_TARGET_COEFFICIENT_V1",
        kind=PacketQuantityKind.TARGET_COEFFICIENT,
        description="Expanded oracle A_β matches evaluate_compiled at declared β.",
        proved_in_this_repo=False,
        qualification="small_packets_cross_check_not_separator_extractor",
    ),
    PreservationObligation(
        schema="VERITAS_R913_OBLIGATION_PARENT_CHILD_V1",
        kind=PacketQuantityKind.TARGET_COEFFICIENT,
        description="Recursive child contraction preserves parent prescribed value.",
        proved_in_this_repo=False,
        qualification="not_established",
    ),
    PreservationObligation(
        schema="VERITAS_R913_OBLIGATION_PRECISION_V1",
        kind=PacketQuantityKind.TARGET_COEFFICIENT,
        description="Precision reduction and modular reconstruction preserve semantics.",
        proved_in_this_repo=False,
        qualification="not_established",
    ),
    PreservationObligation(
        schema="VERITAS_R913_OBLIGATION_SAT_DECISION_V1",
        kind=PacketQuantityKind.TARGET_COEFFICIENT,
        description="Final SAT decision matches model count / modular test without false negatives.",
        proved_in_this_repo=False,
        qualification="not_established",
    ),
)


def obligations_record() -> Dict[str, object]:
    return {
        "schema": "VERITAS_R913_PRESERVATION_SPEC_V1",
        "obligations": [
            {
                "schema": o.schema,
                "kind": o.kind.value,
                "description": o.description,
                "proved_in_this_repo": o.proved_in_this_repo,
                "qualification": o.qualification,
            }
            for o in PIPELINE_OBLIGATIONS
        ],
        "source_qualified": False,
        "subexponential_bound_evidence": False,
        "note": "Fast aggregate DP does not imply fast target coefficient extraction.",
    }
