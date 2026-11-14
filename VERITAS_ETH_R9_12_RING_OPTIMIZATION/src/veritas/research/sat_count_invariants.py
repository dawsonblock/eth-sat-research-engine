"""Unified count-invariant labels for universal SAT JSON (scaffold, not Lean)."""
from __future__ import annotations

from typing import Any, Literal

CountInvariantKind = Literal[
    "BIJECTION_ON_DECLARED_VARIABLES",
    "PRODUCT_OVER_PRIMAL_COMPONENTS",
    "STRUCTURAL_BIJECTION_COPY3",
    "RESIDUAL_EQUIVALENCE_MERGE",
    "UNKNOWN",
    "NOT_APPLICABLE",
]

SCHEMA = "VERITAS_COUNT_INVARIANT_REGISTRY_V1"


def invariant_entry(
    *,
    kind: CountInvariantKind,
    stage: str,
    proved_in_repo: bool = False,
    note: str | None = None,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "stage": stage,
        "proved_in_repo": proved_in_repo,
        "theorem_backed": False,
        "note": note,
    }


def collect_count_invariants(reduction: dict[str, Any] | None) -> dict[str, Any]:
    """Aggregate invariants from reduction sub-objects for top-level universal JSON."""
    reduction = reduction or {}
    entries: list[dict[str, Any]] = []

    preprocess = reduction.get("phase_c_split", {}).get("preprocess") or reduction.get(
        "preprocess"
    )
    if preprocess and preprocess.get("schema"):
        entries.append(
            invariant_entry(
                kind=preprocess.get("count_invariant", "UNKNOWN"),
                stage="phase_c_preprocess",
                proved_in_repo=preprocess.get("status") in ("REDUCED", "UNCHANGED", "UNSAT"),
                note=preprocess.get("qualification"),
            )
        )

    phase_c = reduction.get("phase_c_split") or {}
    for stage in phase_c.get("stages") or []:
        if stage.get("count_preservation"):
            entries.append(
                invariant_entry(
                    kind="STRUCTURAL_BIJECTION_COPY3",
                    stage="phase_c_copy3_encode",
                    proved_in_repo=False,
                    note=stage.get("qualification"),
                )
            )
    ci = phase_c.get("count_invariant")
    if isinstance(ci, dict) and ci.get("type"):
        entries.append(
            invariant_entry(
                kind=ci["type"],
                stage="phase_c_outer_reduction",
                proved_in_repo=bool(ci.get("proved_in_repo")),
                note=ci.get("note"),
            )
        )

    residual = reduction.get("residual_compression") or {}
    if residual.get("schema"):
        agreed = residual.get("agreement_with_exhaustive")
        entries.append(
            invariant_entry(
                kind="RESIDUAL_EQUIVALENCE_MERGE",
                stage="residual_compression_probe",
                proved_in_repo=agreed is True,
                note=residual.get("qualification"),
            )
        )

    encode = reduction.get("encode") or {}
    if encode.get("status") == "ENCODED":
        entries.append(
            invariant_entry(
                kind="STRUCTURAL_BIJECTION_COPY3",
                stage="source_cnf_encode",
                proved_in_repo=False,
                note="fixed_density_COPY3_scaffold",
            )
        )

    return {
        "schema": SCHEMA,
        "entries": entries,
        "kinds": sorted({e["kind"] for e in entries}),
    }
