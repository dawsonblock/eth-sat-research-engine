"""Reproduce finite R9 streaming-packing construction and independent replay."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import platform
from time import monotonic

from veritas.research.eth_packing_v26.streaming import (
    construct_active_call_streaming_packing,
    construct_streaming_d3_packing,
)
from veritas.research.eth_packing_v26.streaming_check import (
    verify_streaming_d3_certificate,
)
from veritas.research.tapered_v4.provenance import manuscript_binding, source_binding


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="validation/r9_streaming_packing.json")
    args = parser.parse_args()
    started = monotonic()

    small_fixtures = []
    for name, edges, radix, dimension in (
        ("empty", [], 2, 1),
        ("parallel_edges", [(0, 0), (0, 0), (1, 1)], 2, 1),
        ("mixed_sides", [(0, 0), (0, 1), (1, 0), (2, 1)], 3, 2),
    ):
        built = construct_streaming_d3_packing(
            edges, r=radix, a=dimension, max_work=2_000_000,
            max_candidate_evaluations=100_000)
        replay = verify_streaming_d3_certificate(
            built.certificate, max_work=2_000_000,
            max_candidate_evaluations=100_000)
        small_fixtures.append({
            "name": name,
            "edges": len(edges),
            "r": radix,
            "a": dimension,
            "certificate_replay": replay,
            "construction_work_units": built.work_units,
            "estimated_work_units": built.estimated_work_units,
        })

    # A 4-regular bipartite graph with r=2,a=1 satisfies the numeric
    # inequalities. It is only a generic-radix mechanism fixture.
    eligible_edges = [(i, (i + shift) % 32)
                      for i in range(32) for shift in range(4)]
    eligible_build = construct_streaming_d3_packing(
        eligible_edges, r=2, a=1, max_work=4_000_000,
        max_candidate_evaluations=1_000)
    eligible_replay = verify_streaming_d3_certificate(
        eligible_build.certificate, max_work=4_000_000,
        max_candidate_evaluations=1_000)

    # This confirms the theorem wrapper rejects before constructing a labeler
    # certificate at ordinary fixture sizes.
    paper_gate = construct_active_call_streaming_packing(
        [(i, i) for i in range(8)], a=1)

    source = source_binding()
    manuscript = manuscript_binding()
    repository_root = Path(__file__).resolve().parents[1]
    proof_hashes = {
        name: sha256((repository_root / name).read_bytes()).hexdigest()
        for name in (
            "proofs/ConditionalExpectationSelection.lean",
            "proofs/ConditionalChildShrink.lean",
            "proofs/ConditionalExpectationAverage.lean",
            "proofs/ConcreteD3ConditionalExpectation.lean",
            "proofs/D3VarianceBound.lean",
            "proofs/D3PotentialIdentity.lean",
            "proofs/D3CollisionBridge.lean",
            "proofs/D3InitialScore.lean",
            "proofs/D3CanonicalSequence.lean",
            "proofs/D3StateInvariants.lean",
            "proofs/D3ParentScoreIndependence.lean",
            "proofs/D3ChildTransition.lean",
            "proofs/D3RealizedLoads.lean",
            "proofs/D3ClassAccounting.lean",
            "proofs/D3VarianceAlgebra.lean",
            "proofs/D3SymbolPorts.lean",
            "proofs/D3PythonOrder.lean",
            "proofs/D3SlotSplit.lean",
            "proofs/D3ExpectedContracts.lean",
            "proofs/D3SelectionBridge.lean",
            "lean-toolchain",
        )
    }
    success = (
        all(item["certificate_replay"].get("valid") is True
            for item in small_fixtures) and
        eligible_replay.get("valid") is True and
        eligible_replay.get("numeric_active_call_inequalities") is True and
        eligible_replay.get("paper_active_call_eligible") is False and
        paper_gate.get("status") == "INCONCLUSIVE_D3_PRECONDITIONS" and
        source.get("digest") is not None and manuscript.get("pin_matches") is True
    )
    record = {
        "schema": "VERITAS_ETH_R9_STREAMING_PACKING_EVIDENCE_V1",
        "status": "PASS_FINITE_PACKING_STAGE" if success else "FAIL_OR_INCONCLUSIVE",
        "python": platform.python_version(),
        "platform": platform.platform(),
        "source_binding": {
            "digest": source["digest"],
            "file_count": len(source["files"]),
            "signature_status": source["signature_status"],
        },
        "manuscript_binding": {
            "tree_digest": manuscript["tree_digest"],
            "contraction_source_sha256": manuscript["contraction_source_sha256"],
            "pin_matches": manuscript["pin_matches"],
        },
        "formal_artifact_hashes": proof_hashes,
        "small_fixtures": small_fixtures,
        "generic_radix_numeric_eligible_fixture": {
            "edge_count": len(eligible_edges),
            "radix": 2,
            "dimension": 1,
            "numeric_preconditions": eligible_build.certificate["preconditions"],
            "independent_replay": eligible_replay,
            "construction_work_units": eligible_build.work_units,
            "estimated_work_units": eligible_build.estimated_work_units,
            "paper_fixed_radix_eligible": False,
        },
        "fixed_radix_active_call_gate": {
            "edge_count": 8,
            "radix": 64,
            "status": paper_gate["status"],
            "preconditions": paper_gate["preconditions"],
            "returned_packing": paper_gate["packing"] is not None,
        },
        "limits_and_claims": {
            "universal_packing_lemma_proven": False,
            "theorem_recursion_qualified": False,
            "work_units_are_bit_complexity": False,
            "hard_memory_limit_enforced": False,
        },
        "elapsed_seconds": round(monotonic() - started, 6),
    }
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record, sort_keys=True, indent=2) + "\n",
                      encoding="utf-8")
    print(json.dumps(record, sort_keys=True, indent=2))
    if not success:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
