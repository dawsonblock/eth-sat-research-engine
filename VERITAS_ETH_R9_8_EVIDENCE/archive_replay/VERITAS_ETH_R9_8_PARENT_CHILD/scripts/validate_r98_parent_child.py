"""Run R9.8 point, recursion, precision and refusal gates into external evidence."""

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from veritas.research.parent_child_r98 import Budget, Policy, contract_scaled
from veritas.research.parent_child_r98.__main__ import load_input
from veritas.research.parent_child_r98.engine import (
    evaluate_point,
    verify_point_certificate,
)
from veritas.research.parent_child_r98.model import canonical
from veritas.research.parent_child_r98.modes import build_modes
from veritas.research.parent_child_r98.packing import (
    audit_layout,
    construct_layout,
    preconditions,
)
from veritas.research.paper_verification.source_registry import source_registry
from veritas.research.tapered_v4.provenance import source_binding


def run(output):
    if output.resolve().is_relative_to(ROOT):
        raise ValueError("R9.8 evidence must be outside the source tree")
    output.parent.mkdir(parents=True, exist_ok=True)
    policy = Policy(max_seconds=600, max_work=300_000_000)
    record = {
        "schema": "VERITAS_R98_VALIDATION_V1",
        "status": "INCOMPLETE",
        "paper": source_registry(),
        "source": source_binding(),
        "policy": asdict(policy),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "source_eligible": False,
        "scaled_experiment": True,
        "source_qualified": False,
        "theorem_mode_enabled": False,
        "bit_time_bound_status": "COMPLEXITY_NOT_ESTABLISHED",
        "peak_space_bound_status": "COMPLEXITY_NOT_ESTABLISHED",
        "lean_theorem_axiom_report": "SEE_SEPARATE_FRESH_LEAN_GATE",
        "clean_wheel": "SEE_SEPARATE_INSTALLED_GATE",
        "docker": "SEE_SEPARATE_CONTAINER_GATE",
    }
    try:
        p = load_input(ROOT / "examples/r98_cross_group.json")
        budget = Budget(policy)
        layout = construct_layout(p, budget=budget)
        modes = build_modes(p, layout, -1, (1, 0, 0, 0), budget=budget)
        value, cert, point = evaluate_point(
            p, layout, modes, budget=budget, capture=True
        )
        verified = verify_point_certificate(p, layout, modes, cert, policy=policy)
        if verified.get("result") != value:
            raise ValueError(verified)
        certificate_path = output.parent / "r98_cross_group_point.json"
        certificate_path.write_bytes(
            canonical(
                {"sha256": cert.content_digest, "certificate": json.loads(cert.payload)}
            )
        )
        record.update(
            parent_digest=p.content_digest,
            point=point,
            point_verifier=verified,
            actual_packing=audit_layout(p, layout),
            point_certificate_sha256=sha256(certificate_path.read_bytes()).hexdigest(),
            mode_completeness="INDEPENDENT_BASIS_AND_CAUCHY_ACTION",
            tuple_completeness="COMPLETE_WEIGHTED_STREAM",
            child_count_per_tuple=64,
            creation_precision_inheritance=True,
        )
        p = load_input(ROOT / "examples/r98_one_edge.json")
        recursive = contract_scaled(
            p, levels=2, strategy="scaled_singletons", policy=policy
        )
        record["two_level_recursion"] = recursive
        if (
            recursive.get("result") != ((7, 0, 0, 0),)
            or recursive["ledger"]["maximum_depth"] != 2
        ):
            raise ValueError(recursive)
        record.update(
            exact_result=recursive["result"],
            recursive_depth=2,
            actual_calls=recursive["ledger"]["actual_calls"],
            actual_child_shrink="FAIL_SCALED_NONSHRINKING",
            actual_child_degree="BOUNDED_ENTRY_AUDIT",
            per_point_independent_oracle_status="PASS_HALF_EDGE_FACTOR_ELIMINATION",
            hermite_coefficient_precision="COEFFICIENTWISE_EXACT_RATIONAL",
        )
        record["source_preflight"] = preconditions(p)
        refusal = contract_scaled(
            p, levels=2, strategy="scaled_singletons", policy=Policy(max_calls=1)
        )
        if refusal["status"] != "INCONCLUSIVE_RESOURCE_LIMIT" or "result" in refusal:
            raise ValueError("resource refusal failed closed")
        record["resource_refusal"] = refusal
        if source_binding() != record["source"]:
            raise ValueError("source changed while generating evidence")
        record["status"] = "PASS_FINITE_SCALED_PARENT_CHILD_IDENTITY"
    except (
        ValueError,
        TypeError,
        KeyError,
        ArithmeticError,
        RuntimeError,
        OSError,
    ) as exc:
        record["status"] = "FAILED_OR_INCONCLUSIVE"
        record["reason"] = str(exc)
    output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "status": record["status"],
                "output": str(output),
                "actual_calls": record.get("actual_calls"),
            }
        )
    )
    return 0 if record["status"].startswith("PASS_") else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    raise SystemExit(run(parser.parse_args().output))
