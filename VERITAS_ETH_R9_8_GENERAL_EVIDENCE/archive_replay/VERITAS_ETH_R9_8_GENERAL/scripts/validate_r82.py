"""Run reproducible bounded R8.2 mode, pruning, and selected-point audits."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from time import monotonic

try:
    import resource
except ImportError:
    resource = None

from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.residue_points import distinct_residue_points
from veritas.research.eth_interpolation.source_hermite import make_source_tapered_plan
from veritas.research.eth_packing_v26.implicit import (
    construct_implicit_packing, implicit_sparse_mode_source,
)
from veritas.research.eth_recursive_contraction_v39 import describe_integer_network
from veritas.research.eth_recursive_contraction_v39.point_children import contract_point_child_expansion
from veritas.research.eth_recursive_contraction_v39.point_modes import make_point_modes
from veritas.research.eth_recursive_contraction_v39.structural_tuples import structural_tuples
from veritas.research.independent_r82 import (
    audit_finite_pruning, independent_parent_point, verify_point_mode_action,
)
from veritas.research.tapered_v4.provenance import manuscript_binding, source_binding


LEGACY_SCHEMA = "VERITAS_ETH_R82_SELECTED_POINT_EVIDENCE_V1"
SCHEMA = "VERITAS_ETH_R82_SELECTED_POINT_EVIDENCE_V2"
LIMITS = {
    "parent_edges": 8,
    "packet_entries": 4096,
    "tuples": 100_000,
    "mode_oracle_work_units": 1_000_000,
    "child_expansion_work_units": 2_000_000,
    "direct_parent_work_units": 5_000_000,
    "timeout_seconds_per_oracle": 30,
    "hard_memory_limit_bytes": None,
    "hard_memory_limit_enforced": False,
}


def _case(n):
    clause = [i for i in range(1, n + 1)]
    cnf = CNF.from_lists(n, [[i] for i in clause])
    f = first_irreducible(5)
    network = describe_integer_network(from_cnf(cnf), creation_precision=n + 1,
                                      defining_polynomial=f)
    plan = make_source_tapered_plan(M=network.edges, a=1, u=1,
                                    p=n + 1, max_precision_bits=1024)
    node = next(item for item in plan.nodes if item.t == -1)
    points = distinct_residue_points(ExtensionRing(node.precision_bits, f),
                                     plan.degree_bound + 1, max_points=32)
    zeta = points[1]
    packing = construct_implicit_packing(network.bipartite_edges(), r=4, a=1,
                                         max_work=3_000_000)
    source = implicit_sparse_mode_source(packing, max_work=3_000_000)
    cert = make_point_modes(source, node=-1, precision=node.precision_bits,
                            extension_degree=5, zeta=zeta,
                            max_tuples=LIMITS["tuples"], max_parent_wires=8)
    return cnf, network, source, cert


def _check_size(n):
    started = monotonic()
    cnf, network, source, cert = _case(n)
    mode_check = verify_point_mode_action(source, cert,
                                          max_entries=LIMITS["packet_entries"],
                                          max_work=LIMITS["mode_oracle_work_units"],
                                          timeout_s=LIMITS["timeout_seconds_per_oracle"])
    tuples = tuple(structural_tuples(cert["modes"], cert["precision"],
                                     max_tuples=LIMITS["tuples"]))
    pruning = audit_finite_pruning(cert["modes"], cert["precision"],
                                   emitted_tuples=tuples,
                                   max_vectors=LIMITS["tuples"])
    child = contract_point_child_expansion(
        network, cert, max_parent_wires=8, max_tuples=LIMITS["tuples"],
        max_work=LIMITS["child_expansion_work_units"],
        timeout_s=LIMITS["timeout_seconds_per_oracle"])
    parent = independent_parent_point(
        network, source, cert, max_edges=8,
        max_work=LIMITS["direct_parent_work_units"],
        timeout_s=LIMITS["timeout_seconds_per_oracle"])
    success = (mode_check.get("valid") is True and pruning.get("valid") is True and
               child.get("direct_oracle_matches") is True and parent.get("valid") is True and
               tuple(parent.get("result", ())) == child.get("result", ())[0])
    if n == 8:
        success = success and len(cert["modes"]) == 6 and cert["structural_tuple_count"] == 64
        success = success and child["result"] == ((169600000000, 0, 0, 0, 0),)
        success = success and tuple(parent["result"]) == (169600000000, 0, 0, 0, 0)
    return {
        "parent_variables": cnf.n,
        "parent_edges": network.edges,
        "node": cert["node"],
        "precision_bits": cert["precision"],
        "extension_polynomial": cert["irreducible_polynomial"],
        "extension_degree": cert["extension_degree"],
        "zeta": cert["zeta"],
        "mode_count": len(cert["modes"]),
        "structural_tuple_count": cert["structural_tuple_count"],
        "mode_action_oracle": mode_check,
        "tuple_pruning_audit": pruning,
        "child_expansion": {
            "result": child.get("result"),
            "direct_oracle_result": child.get("direct_oracle_result"),
            "direct_oracle_matches": child.get("direct_oracle_matches"),
            "tuples_processed": len(child.get("tuples", ())),
            "work_units": child.get("algorithm_work_units"),
            "direct_oracle_work_units": child.get("independent_oracle_work_units"),
        },
        "independent_parent_oracle": parent,
        "status": "PASS" if success else "FAIL_OR_INCONCLUSIVE",
        "elapsed_seconds": round(monotonic() - started, 6),
    }


def digest(payload):
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                     allow_nan=False).encode("ascii")
    return sha256(raw).hexdigest()


def semantic_payload(record, *, legacy_digest=False):
    # V1 included the interpreter and RSS unit. Verify its original digest
    # before comparing portable content under the current schema.
    payload = dict(record)
    for field in ("evidence_sha256", "semantic_sha256", "elapsed_seconds",
                  "peak_rss_bytes_process_lifetime"):
        payload.pop(field, None)
    if not legacy_digest:
        payload["schema"] = SCHEMA
        del payload["python"], payload["peak_rss_unit"]
    payload["cases"] = [{k: v for k, v in case.items() if k != "elapsed_seconds"}
                        for case in record["cases"]]
    return payload


def seal(record):
    record = dict(record)
    record.pop("evidence_sha256", None)
    record["semantic_sha256"] = digest(semantic_payload(record))
    record["evidence_sha256"] = digest(record)
    return record


def check_saved(saved, fresh):
    if not isinstance(saved, dict) or saved.get("schema") not in (SCHEMA, LEGACY_SCHEMA):
        return False
    try:
        fields = set(fresh)
        if saved["schema"] == LEGACY_SCHEMA:
            fields.discard("semantic_sha256")
        if set(saved) != fields or type(saved["cases"]) is not list or len(saved["cases"]) != 3:
            return False
        if any(not isinstance(case, dict) or set(case) != set(current)
               for case, current in zip(saved["cases"], fresh["cases"])):
            return False
        elapsed = [saved["elapsed_seconds"], *(case["elapsed_seconds"] for case in saved["cases"])]
        if any(type(t) not in (int, float) or not 0 <= t < float("inf") for t in elapsed):
            return False
        rss = saved["peak_rss_bytes_process_lifetime"]
        if rss is not None and (type(rss) is not int or rss < 0):
            return False
        if type(saved["peak_rss_unit"]) is not str or not saved["peak_rss_unit"]:
            return False
        if saved["schema"] == LEGACY_SCHEMA:
            if "semantic_sha256" in saved or saved["evidence_sha256"] != digest(
                    semantic_payload(saved, legacy_digest=True)):
                return False
        else:
            if saved["evidence_sha256"] != digest({k: v for k, v in saved.items()
                                                  if k != "evidence_sha256"}):
                return False
            if saved["semantic_sha256"] != digest(semantic_payload(saved)):
                return False
        return (isinstance(saved["python"], str) and bool(saved["python"]) and
                fresh["manuscript_binding"]["pin_matches"] is True and
                fresh["points_checked"] == fresh["points_total"] == 3 and
                digest(semantic_payload(saved)) == digest(semantic_payload(fresh)))
    except (AttributeError, KeyError, TypeError, ValueError, RecursionError):
        return False


def unique_fields(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", type=Path)
    group.add_argument("--replay", type=Path)
    args = parser.parse_args()
    start = monotonic()
    cases = [_check_size(n) for n in (4, 6, 8)]
    checked = sum(case["status"] == "PASS" for case in cases)
    record = {
        "schema": SCHEMA,
        "source_binding": source_binding(),
        "manuscript_binding": manuscript_binding(),
        "limits": LIMITS,
        "points_total": len(cases),
        "points_checked": checked,
        "points_skipped": len(cases) - checked,
        "coverage_classification": "SELECTED_FINITE_CASES_ONLY",
        "coverage_reasons": ["one deterministic node and extension point per parent size",
                              "not all Hermite nodes or all extension points"],
        "cases": cases,
        "peak_rss_bytes_process_lifetime": (None if resource is None else
                                             resource.getrusage(resource.RUSAGE_SELF).ru_maxrss *
                                             (1 if sys.platform == "darwin" else 1024)),
        "peak_rss_unit": ("unavailable" if resource is None else
                          "bytes"),
        "peak_rss_hard_limit_enforced": False,
        "complete_bit_work_accounting": False,
        "universal_theorem_proven": False,
        "theorem_mode_enabled": False,
        "elapsed_seconds": round(monotonic() - start, 6),
        "python": sys.version,
    }
    record = seal(record)
    old = None
    if args.write:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_text(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n",
                              encoding="utf-8")
        output_path = str(args.write)
        valid = checked == len(cases) and record["manuscript_binding"]["pin_matches"] is True
        status = "PASS" if valid else "BLOCKED"
    else:
        try:
            if args.replay.stat().st_size > 4_000_000:
                raise ValueError("selected-point record exceeds size limit")
            old = json.loads(args.replay.read_text(encoding="utf-8"), object_pairs_hook=unique_fields)
        except (OSError, ValueError, UnicodeError, RecursionError):
            old = None
        output_path = str(args.replay)
        valid = check_saved(old, record)
        status = "FINITE_R82_EVIDENCE_REPLAYED" if valid else "INVALID_OR_INCONCLUSIVE_EVIDENCE"
    print(json.dumps({"status": status, "path": output_path,
                      "legacy_evidence": isinstance(old, dict) and old.get("schema") == LEGACY_SCHEMA,
                      "environment_differs": isinstance(old, dict) and any(
                          old.get(key) != record[key] for key in ("python", "peak_rss_unit")),
                      "submitted_digest": old.get("evidence_sha256") if isinstance(old, dict) else None,
                      "fresh_artifact_sha256": record["evidence_sha256"],
                      "semantic_sha256": record["semantic_sha256"],
                      "points_total": len(cases), "points_checked": checked,
                      "points_skipped": len(cases) - checked,
                      "evidence_sha256": record["evidence_sha256"],
                      "elapsed_seconds": record["elapsed_seconds"]}))
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
