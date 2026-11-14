"""Tiered admission and actionable hints for the source-finite count lane."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from veritas.core.cnf import CNF
from veritas.research.sat_cnf_parent_bridge import (
    DEFAULT_TINY_CNF_CLASS,
    TinyFixedCnfClass,
    admit_tiny_fixed_cnf_class,
)
from veritas.research.tapered_v4.cnf_count import count_source_cnf_finite
from veritas.research.tapered_v4.model import RecursionPolicy

_ADMISSION_STEPS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (
        re.compile(r"precision exceeds cap|root precision cap exceeded", re.I),
        "RAISE_MAX_PRECISION_BITS",
        "Increase RecursionPolicy.max_precision_bits or reduce n.",
    ),
    (
        re.compile(r"edge cap exceeded|edges >", re.I),
        "REDUCE_ENCODED_EDGES_OR_RAISE_WIRE_CAP",
        "Shrink CNF / encoding or raise max_wires for finite contraction.",
    ),
    (
        re.compile(r"max_vars|max_clauses|OUT_OF_CLASS|> max_", re.I),
        "SHRINK_TO_ADMITTED_CNF_CLASS",
        "Formula must fit TinyFixedCnfClass (or MICRO tier) caps.",
    ),
    (
        re.compile(r"max_active_wires", re.I),
        "RELAX_MAX_ACTIVE_WIRES_POLICY",
        "Finite recursion policy max_active_wires blocks this network shape.",
    ),
    (
        re.compile(r"structure did not pass|INVARIANT_FAILURE", re.I),
        "FIX_ENCODE_OR_STRUCTURAL_CHECK",
        "Encoding failed structural check; verify normalization and COPY3 network.",
    ),
    (
        re.compile(r"oracle variable cap|oracle work cap", re.I),
        "RELAX_ORACLE_CAPS_OR_USE_LARGER_TIER",
        "Exhaustive verification tier cap; try STANDARD tier without verify or smaller n.",
    ),
    (
        re.compile(r"resources exhausted|construction resources", re.I),
        "RELAX_WORK_OR_TIME_POLICY",
        "Raise max_work / max_seconds or reduce instance size.",
    ),
)


def next_admission_step(*, status: str, reason: str | None) -> dict[str, Any]:
    text = reason or status or ""
    for pattern, step, hint in _ADMISSION_STEPS:
        if pattern.search(text):
            return {
                "schema": "VERITAS_SOURCE_FINITE_NEXT_STEP_V1",
                "step": step,
                "hint": hint,
                "reason_matched": text[:240],
            }
    return {
        "schema": "VERITAS_SOURCE_FINITE_NEXT_STEP_V1",
        "step": "REVIEW_FINITE_POLICY_CAPS",
        "hint": "Inspect tapered_v4 policy, encode caps, and CNF class.",
        "reason_matched": text[:240] if text else None,
    }


@dataclass(frozen=True)
class SourceFiniteTier:
    name: str
    cnf_class: TinyFixedCnfClass
    max_wires: int
    max_active_wires: int
    max_work: int
    max_seconds: float
    verify_exhaustive: bool
    oracle_max_variables: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "cnf_class": self.cnf_class.to_dict(),
            "max_wires": self.max_wires,
            "max_active_wires": self.max_active_wires,
            "max_work": self.max_work,
            "max_seconds": self.max_seconds,
            "verify_exhaustive": self.verify_exhaustive,
            "oracle_max_variables": self.oracle_max_variables,
        }


MICRO_SOURCE_FINITE_TIER = SourceFiniteTier(
    name="MICRO",
    cnf_class=TinyFixedCnfClass(max_vars=8, max_clauses=16, max_clause_width=3),
    max_wires=64,
    max_active_wires=8,
    max_work=300_000,
    max_seconds=12.0,
    verify_exhaustive=True,
    oracle_max_variables=8,
)

STANDARD_SOURCE_FINITE_TIER = SourceFiniteTier(
    name="STANDARD",
    cnf_class=DEFAULT_TINY_CNF_CLASS,
    max_wires=64,
    max_active_wires=8,
    max_work=500_000,
    max_seconds=15.0,
    verify_exhaustive=False,
    oracle_max_variables=16,
)

DEFAULT_SOURCE_FINITE_TIERS = (MICRO_SOURCE_FINITE_TIER, STANDARD_SOURCE_FINITE_TIER)


def run_source_finite_for_tier(
    cnf: CNF,
    tier: SourceFiniteTier,
) -> dict[str, Any]:
    refusal = admit_tiny_fixed_cnf_class(cnf, tier.cnf_class)
    if refusal:
        return {
            "schema": "VERITAS_SOURCE_FINITE_TIER_ATTEMPT_V1",
            "tier": tier.name,
            "status": "REFUSED_TIER_CLASS",
            "reason": refusal["reason"],
            "admitted_class": refusal.get("admitted_class"),
            "next_admission_step": next_admission_step(
                status="REFUSED", reason=refusal["reason"]
            ),
        }
    policy = RecursionPolicy(
        max_active_wires=tier.max_active_wires,
        max_precision_bits=min(1024, max(8, cnf.n + 1)),
        max_work=tier.max_work,
        max_seconds=tier.max_seconds,
    )
    result = count_source_cnf_finite(
        cnf,
        policy,
        max_wires=tier.max_wires,
        max_factors=10_000,
        max_clause_width=3,
        verify_exhaustive=tier.verify_exhaustive,
        oracle_max_variables=tier.oracle_max_variables,
    )
    status = str(result.get("status", "UNKNOWN"))
    reason = result.get("reason")
    detail: dict[str, Any] = {
        "schema": "VERITAS_SOURCE_FINITE_TIER_ATTEMPT_V1",
        "tier": tier.name,
        "tier_spec": tier.to_dict(),
        "status": status,
        "count": result.get("count"),
        "reason": reason,
        "network_edges": result.get("network_edges"),
        "original_edges": result.get("original_edges"),
        "independent_exhaustive_oracle_used": result.get("independent_exhaustive_oracle_used"),
    }
    if status.startswith("INCONCLUSIVE") or status == "REFUSED_TIER_CLASS":
        detail["next_admission_step"] = next_admission_step(status=status, reason=reason)
    return detail


def try_source_finite_tiered(
    cnf: CNF,
    *,
    tiers: tuple[SourceFiniteTier, ...] = DEFAULT_SOURCE_FINITE_TIERS,
) -> dict[str, Any]:
    """Try tiers in order; return first EXACT or aggregated inconclusive with attempts."""
    attempts: list[dict[str, Any]] = []
    for tier in tiers:
        attempt = run_source_finite_for_tier(cnf, tier)
        attempts.append(attempt)
        if attempt.get("status") == "EXACT_COUNT_FINITE":
            return {
                "schema": "VERITAS_SOURCE_FINITE_COUNT_LANE_V2",
                "status": "EXACT_COUNT_FINITE",
                "count": attempt.get("count"),
                "admission_tier": tier.name,
                "tier_attempts": attempts,
                "theorem_backed": False,
                "universal_speedup_claimed": False,
            }
    last = attempts[-1] if attempts else {}
    step = last.get("next_admission_step") or next_admission_step(
        status=str(last.get("status", "UNKNOWN")),
        reason=last.get("reason"),
    )
    return {
        "schema": "VERITAS_SOURCE_FINITE_COUNT_LANE_V2",
        "status": last.get("status", "UNKNOWN"),
        "count": None,
        "reason": last.get("reason"),
        "admission_tier": None,
        "tier_attempts": attempts,
        "next_admission_step": step,
        "theorem_backed": False,
        "universal_speedup_claimed": False,
    }
