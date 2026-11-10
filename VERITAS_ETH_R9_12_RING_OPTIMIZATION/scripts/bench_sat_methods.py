#!/usr/bin/env python3
"""Benchmark SAT contraction method families on bounded VERITAS R9.12 fixtures.

Compares (where budgets allow):

- **wire_elimination** — production ``Route.ELIMINATION`` with preflight-consistent
  ``EliminationBudget`` (min-fill / min-degree heuristic order).
- **packet_resummation** — R9.13 ``compare_resummation_methods`` (full substitution
  identity) on a toy packet or a multislot jet point from ``fixture_bridge``.
- **support_resummation** — support-filtered vs full substitution at parent precision.
- **mode_width_metadata** — ``dependency_analyzer`` width estimate without enumerating
  mode support (96-wire style metadata).

Qualification (always reported on each record):

- ``source_qualified``: false — no manuscript-active source call.
- ``subexponential_bound_evidence``: false — timings are finite measurements only.
- ``theorem_backed``: false.

Default root is the R9.12 package directory (override with ``VERITAS_R912_ROOT``).

Usage::

    PYTHONPATH=src python scripts/bench_sat_methods.py
    PYTHONPATH=src python scripts/bench_sat_methods.py --smoke --json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import replace
from pathlib import Path

VERITAS_R912_ROOT = Path(
    os.environ.get(
        "VERITAS_R912_ROOT",
        Path(__file__).resolve().parents[1],
    )
)
sys.path.insert(0, str(VERITAS_R912_ROOT / "src"))

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.parent_child_r912.elimination import EliminationBudget
from veritas.research.parent_child_r912.fixture_bridge import compiled_child_packet_at_jet_point
from veritas.research.parent_child_r912.preflight import wire_elimination_preflight
from veritas.research.parent_child_r912.routes import Route, contract_routed
from veritas.research.parent_child_r913.algebraic_resummation import (
    build_packet_reference,
    compare_resummation_methods,
    polynomial_target_value,
    production_packet_value,
)
from veritas.research.parent_child_r913.dependency_analyzer import (
    analyze_mode_certificate,
    report_to_dict,
)
from veritas.research.parent_child_r913.coefficient_extraction import (
    estimate_extraction_state,
    target_coefficient_by_separator_elimination_int,
)
from veritas.research.parent_child_r913.support_resummation import (
    compare_support_aware_resummation,
    support_condition_report,
)
from veritas.research.parent_child_r98.model import Budget, canonical
from veritas.research.parent_child_r98.shrinking_cli import load_input
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r912.elimination import call_scopes, plan_order
from veritas.research.parent_child_r99.cli import load_layout
from veritas.research.parent_child_r99.support_circuit import SupportCircuit
from veritas.research.tapered_v4.source_recipes import EntryLimits

QUALIFICATION = {
    "source_qualified": False,
    "subexponential_bound_evidence": False,
    "theorem_backed": False,
    "qualification": "bounded_benchmark_harness_only",
}

POLICY = replace(DEFAULT_SHRINKING_POLICY, max_work=2_000_000, max_seconds=600)


def _jet(ring: JetRing, scalar: int):
    return ring.elem([[scalar % ring.base.modulus]])


def bench_toy_packet_resummation() -> dict:
    ring = JetRing(ExtensionRing(7, 7), 2)
    data = [
        [0],
        [1, 2],
        [[_jet(ring, 2), _jet(ring, 1)]],
        [[1, [_jet(ring, 5)]]],
        [[2, [1, 2]]],
    ]
    _, compiled = build_packet_reference(
        arity=3, data=data, creation_precision=7, jet_length=2
    )
    bits = (1, 0, 1)
    weights = (_jet(ring, 3),)
    t0 = time.perf_counter()
    result = compare_resummation_methods(
        compiled, bits, weights, limits=EntryLimits(max_work=500_000)
    )
    elapsed = time.perf_counter() - t0
    return {
        "case": "toy_packet_resummation",
        "agree": result.agree,
        "monomial_count": result.monomial_count,
        "row_count": result.row_count,
        "elapsed_seconds": elapsed,
        **QUALIFICATION,
    }


def bench_multislot_support_resummation() -> dict:
    parent = load_input(VERITAS_R912_ROOT / "examples/r99_multislot_crossing2.json")
    layout = load_layout(
        parent,
        VERITAS_R912_ROOT / "examples/r99_multislot_crossing2_layout.json",
        Budget(POLICY),
    )
    t0 = time.perf_counter()
    compiled, row_certificate = compiled_child_packet_at_jet_point(
        parent, layout, budget=Budget(POLICY), point_index=0
    )
    bits = (0,) * compiled.reference.arity
    ring = JetRing(
        ExtensionRing(
            compiled.reference.creation_precision,
            compiled.reference.defining_polynomial,
        ),
        compiled.reference.jet_length,
    )
    n_targets = sum(1 for beta, _ in compiled.data[3] if beta)
    weights = tuple(_jet(ring, 2 + j) for j in range(n_targets))
    base = compare_resummation_methods(
        compiled, bits, weights, limits=EntryLimits(max_work=2_000_000)
    )
    aware = compare_support_aware_resummation(
        compiled,
        bits,
        weights,
        precision=parent.precision,
        limits=EntryLimits(max_work=2_000_000),
        row_certificate=row_certificate,
    )
    prod = production_packet_value(compiled, bits, limits=EntryLimits(max_work=2_000_000))
    poly = polynomial_target_value(compiled, bits, limits=EntryLimits(max_work=2_000_000))
    elapsed = time.perf_counter() - t0
    report = support_condition_report(aware)
    return {
        "case": "multislot_jet_support_resummation",
        "substitution_identity": base.agree,
        "production_matches_polynomial_oracle": prod == poly,
        "full_agrees_with_enumerated": aware.full_agrees_with_enumerated,
        "enumerate_agrees_with_hybrid": aware.enumerate_agrees_with_hybrid,
        "supported_monomials": aware.supported_monomial_count,
        "total_monomials": aware.total_monomial_count,
        "support_report": report,
        "elapsed_seconds": elapsed,
        **QUALIFICATION,
    }


def _load_interaction_probe():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "interaction_probe", VERITAS_R912_ROOT / "scripts/experiment_r912_interaction.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def bench_wire_elimination(
    *,
    temporary_parent_path: Path | None = None,
    n: int = 8,
    offset: int = 3,
    max_width: int = 20,
) -> dict:
    probe = _load_interaction_probe()
    graph = probe.graph
    integer_elimination = probe.integer_elimination

    data = graph(n, offset)
    if temporary_parent_path is None:
        temporary_parent_path = VERITAS_R912_ROOT / ".bench_sat_wire_parent.json"
    temporary_parent_path.write_bytes(canonical(data))
    parent = load_input(temporary_parent_path, max_extension_degree=12)
    budget = EliminationBudget(max_width=max_width)
    t0 = time.perf_counter()
    pre = wire_elimination_preflight(parent, budget)
    routed = contract_routed(parent, route=Route.ELIMINATION, elimination_budget=budget)
    ref = integer_elimination(data, max_work=5_000_000, max_frontier=max_width)
    elapsed = time.perf_counter() - t0
    matches = False
    if routed.get("status") == "PASS_EXACT_BOUNDED_WIDTH_ELIMINATION":
        matches = (
            routed["result"][0][0] == ref["integer"]
            and not any(routed["result"][0][1:])
            and not any(map(any, routed["result"][1:]))
        )
    scopes, variables = call_scopes(parent)
    order = plan_order(scopes, variables, "min_fill")
    return {
        "case": "wire_elimination",
        "wires": parent.edge_count,
        "n_vertices_per_side": n,
        "offset": offset,
        "preflight_status": pre.get("status"),
        "elimination_status": routed.get("status"),
        "elimination_width": routed.get("elimination_width"),
        "matches_integer_reference": matches,
        "reference_work_units": ref.get("work_units"),
        "planned_order_length": len(order),
        "max_width_budget": max_width,
        "elapsed_seconds": elapsed,
        **QUALIFICATION,
    }


def bench_mode_width_metadata(*, mode_count: int = 96, max_width: int = 20) -> dict:
    modes = [
        {
            "packet": index,
            "weight": 1,
            "rows": [[index, None]],
            "target_group": 0,
            "source_group": 0,
        }
        for index in range(mode_count)
    ]
    certificate = {"nonconstant_row_ports": list(range(mode_count))}
    t0 = time.perf_counter()
    circuit = SupportCircuit(
        modes, 512, budget=Budget(POLICY), row_certificate=certificate
    )
    report = analyze_mode_certificate(
        {"modes": modes, "precision": 512},
        1,
        row_certificate=certificate,
        budget=EliminationBudget(max_width=max_width),
    )
    summary = report_to_dict(report)
    elapsed = time.perf_counter() - t0
    return {
        "case": "mode_width_metadata",
        "mode_count": mode_count,
        "support_components": circuit.summary()["components"],
        "elimination_width": summary["elimination_width"],
        "elimination_fits": summary["elimination_fits"],
        "predicted_work": summary["predicted_work"],
        "note": "metadata_only_no_support_enumeration",
        "elapsed_seconds": elapsed,
        **QUALIFICATION,
    }


def bench_coefficient_extract_independent(*, mode_count: int = 96, max_width: int = 20) -> dict:
    """96-wire-style independent row factors: separator A_beta without 2**n expansion."""
    modes = [
        {
            "packet": index,
            "weight": 1,
            "rows": [[index, None]],
            "target_group": 0,
            "source_group": 0,
        }
        for index in range(mode_count)
    ]
    certificate = {"nonconstant_row_ports": list(range(mode_count))}
    target_beta = tuple(1 if index % 2 == 0 else 0 for index in range(mode_count))
    modulus = 1009
    constants = tuple(1 + (index % 5) for index in range(mode_count))
    coefficients = tuple(
        tuple(2 + (index % 3) if index == col else 0 for col in range(mode_count))
        for index in range(mode_count)
    )
    t0 = time.perf_counter()
    estimate = estimate_extraction_state(
        modes,
        target_beta,
        row_certificate=certificate,
        budget=EliminationBudget(max_width=max_width),
    )
    value, stats = target_coefficient_by_separator_elimination_int(
        constants, coefficients, target_beta, modulus
    )
    elapsed = time.perf_counter() - t0
    return {
        "case": "coefficient_extract_independent",
        "mode_count": mode_count,
        "target_beta_ones": sum(target_beta),
        "coefficient_modulus": modulus,
        "coefficient_value_mod": value,
        "separator_max_monomial_table": stats.max_monomial_table,
        "separator_peak_monomial_table": stats.peak_monomial_table,
        "separator_join_count": stats.join_count,
        "separator_elimination_width": stats.elimination_width,
        "mode_graph_elimination_width": estimate.elimination_width,
        "effective_state_upper_bound": (
            estimate.boolean_separator_states * estimate.exponent_tracking_multiplier
        ),
        "problem": "B_target_coefficient",
        "note": "independent_rows_instance_not_interaction_child_packet",
        "elapsed_seconds": elapsed,
        **QUALIFICATION,
    }


CASES = {
    "toy_packet": lambda _args: bench_toy_packet_resummation(),
    "multislot_jet": lambda _args: bench_multislot_support_resummation(),
    "wire_elimination": lambda args: bench_wire_elimination(
        n=args.interaction_vertices,
        offset=args.interaction_offset,
        max_width=args.elimination_max_width,
    ),
    "mode_width_96": lambda args: bench_mode_width_metadata(
        mode_count=96, max_width=args.elimination_max_width
    ),
    "mode_width_192": lambda args: bench_mode_width_metadata(
        mode_count=args.interaction_wires,
        max_width=args.elimination_max_width,
    ),
    "coefficient_extract_96": lambda args: bench_coefficient_extract_independent(
        mode_count=96, max_width=args.elimination_max_width
    ),
}

SMOKE_CASES = ("toy_packet", "mode_width_96", "coefficient_extract_96")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cases",
        type=str,
        default="",
        help="Comma-separated subset of: " + ",".join(CASES),
    )
    parser.add_argument("--smoke", action="store_true", help="Run fast subset only")
    parser.add_argument(
        "--elimination-max-width", type=int, default=20, help="EliminationBudget cap"
    )
    parser.add_argument(
        "--interaction-vertices",
        type=int,
        default=8,
        help="Vertices per side for wire elimination case",
    )
    parser.add_argument("--interaction-offset", type=int, default=3)
    parser.add_argument(
        "--interaction-wires",
        type=int,
        default=96,
        help="Mode count for optional large metadata case",
    )
    parser.add_argument(
        "--json", action="store_true", help="Print one JSON object per line"
    )
    args = parser.parse_args()

    if args.smoke:
        names = list(SMOKE_CASES)
    elif args.cases:
        names = [part.strip() for part in args.cases.split(",") if part.strip()]
    else:
        names = ["toy_packet", "multislot_jet", "wire_elimination", "mode_width_96"]

    results = []
    for name in names:
        if name not in CASES:
            raise SystemExit(f"unknown case {name!r}; choose from {list(CASES)}")
        try:
            record = CASES[name](args)
            record["status"] = "OK"
        except Exception as exc:  # noqa: BLE001 — benchmark harness reports failure
            record = {
                "case": name,
                "status": "ERROR",
                "error": str(exc),
                **QUALIFICATION,
            }
        results.append(record)
        if args.json:
            print(json.dumps(record, sort_keys=True))
        else:
            print(record)

    if args.json and results:
        return 0 if all(r.get("status") == "OK" for r in results) else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
