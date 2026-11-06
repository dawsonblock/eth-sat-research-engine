"""Recover two bounded parent values entirely from checked recipe-child point sums."""

import argparse
import json
from pathlib import Path
from time import monotonic

from veritas.core.cnf import CNF
from veritas.research.tensor import brute_contract, from_cnf
from veritas.research.finite_reductions.boundary import _digest
from veritas.research.finite_reductions.recipe_point import contract_recipe_point
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_arithmetic.residue_points import distinct_residue_points
from veritas.research.eth_recursive_contraction_v39 import describe_integer_network
from veritas.research.eth_recursive_contraction_v39.point_modes import make_point_modes
from veritas.research.eth_packing_v26.implicit import (
    construct_implicit_packing,
    implicit_sparse_mode_source,
)
from veritas.research.eth_interpolation.extension_lagrange import interpolate_newton
from veritas.research.eth_interpolation.source_hermite import (
    make_source_tapered_plan,
    reconstruct_source_tapered,
)
from veritas.research.tapered_v4.provenance import source_binding


def checked_grid(cnf, row):
    start = monotonic()
    net, p, f = from_cnf(cnf), cnf.n + 1, first_irreducible(5)
    parent = describe_integer_network(net, creation_precision=p, defining_polynomial=f)
    packing = construct_implicit_packing(
        parent.bipartite_edges(), r=4, a=1, max_work=1_000_000
    )
    source = implicit_sparse_mode_source(packing, max_work=1_000_000)
    plan = make_source_tapered_plan(M=net.edges, a=1, u=1, p=p, max_precision_bits=1024)
    order = plan.degree_bound + 1
    row.update(
        cnf=cnf.as_dict(),
        p=p,
        wires=net.edges,
        polynomial=f,
        expected_points=len(plan.nodes) * order,
        checked_points=[],
        source_sha256=source_binding()["digest"],
        status="INCOMPLETE",
    )
    jets, precisions = {}, {}
    for node in plan.nodes:
        ring = ExtensionRing(node.precision_bits, f)
        points = distinct_residue_points(ring, order, max_points=32)
        samples = []
        for z in points:
            if monotonic() - start > 240:
                raise ValueError("finite grid deadline")
            cert = make_point_modes(
                source,
                node=node.t,
                precision=node.precision_bits,
                extension_degree=5,
                zeta=z,
                max_tuples=512,
                max_parent_wires=8,
            )
            report = contract_recipe_point(parent, cert)
            if report["status"] != "EXACT_CHECKED_FINITE_RECIPE_POINT":
                raise ValueError(report.get("reason", "incomplete point"))
            samples.append(report["result"][0])
            proof = report["certificate"]
            row["checked_points"].append(
                {
                    "node": node.t,
                    "zeta": z,
                    "precision": node.precision_bits,
                    "tuples": len(proof["terms"]),
                    "certificate_sha256": _digest(proof),
                    "value": samples[-1],
                    "direct": report["direct_parent_result"],
                }
            )
        jets[node.t] = interpolate_newton(ring, points, samples, max_points=32)[
            : node.multiplicity
        ]
        precisions[node.t] = (node.precision_bits,) * len(jets[node.t])
    if len(row["checked_points"]) != row["expected_points"] or len(jets) != len(
        plan.nodes
    ):
        raise ValueError("incomplete interpolation grid")
    recovered = tuple(
        reconstruct_source_tapered(
            plan,
            {t: tuple(v[i] for v in values) for t, values in jets.items()},
            coefficient_precisions=precisions,
        )
        for i in range(5)
    )
    check = brute_contract(net, max_edges=8, modulus=1 << p)
    if recovered != (check, 0, 0, 0, 0) or monotonic() - start > 240:
        raise ValueError("Hermite recovery mismatch or deadline")
    row.update(
        status="EXACT_FINITE_GRID_RECOVERED",
        result=recovered,
        direct_zero=check,
        elapsed_seconds=monotonic() - start,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path, default=Path("validation/r96_recipe_grid.json")
    )
    path = parser.parse_args().output
    record = {
        "schema": "FINITE_R96_GRID_CHECK_V1",
        "status": "INCOMPLETE",
        "schedule": "FINITE_SCALED_V1",
        "parameters": {"a": 1, "u": 1, "r": 4},
        "theorem_enabled": False,
        "cases": [],
    }
    try:
        for cnf in (
            CNF.from_lists(2, [[1, 2], [-1, 2]]),
            CNF.from_lists(8, [[i] for i in range(1, 9)]),
        ):
            row = {}
            record["cases"].append(row)
            checked_grid(cnf, row)
        record["status"] = "PASS_FINITE_RECOVERY"
    except (ValueError, RuntimeError, OSError, ArithmeticError) as exc:
        record["reason"] = str(exc)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(record, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(record["status"], record.get("reason", ""))
    return int(record["status"] != "PASS_FINITE_RECOVERY")


if __name__ == "__main__":
    raise SystemExit(main())
