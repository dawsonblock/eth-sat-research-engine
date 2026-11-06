"""Kernel-check concrete Python child tables and port numbering against the Lean model."""

import argparse
from hashlib import sha256
from itertools import product
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from veritas.research.tensor import Factor, TensorNetwork
from veritas.research.finite_reductions.boundary import (
    _child,
    _check_cut,
    _Run,
    BoundaryPolicy,
)
from validate_conditional_expectation_lean import (
    check_axiom_reports,
    check_lean_version,
)


def generate(corrupt=False):
    # Strongly asymmetric tables, noncontiguous free wire IDs and a reversed port order.
    scopes = ((4, 0, 2), (1, 3, 5), (2, 1, 0), (5, 4, 3))
    net = TensorNetwork(
        6,
        tuple(
            Factor(ports, tuple(((i + 2) * j - 9) ** 2 - 35 for j in range(8)), str(i))
            for i, ports in enumerate(scopes)
        ),
    )
    groups = ((0, 2), (1, 3))
    wires = ((0, 2), (3, 5), (1, 4))
    _check_cut(net, groups, wires)
    code = ["import BoundaryGather", "open BoundaryGather"]
    names = []
    for mask, bits in enumerate(product((0, 1), repeat=2)):
        fixed = dict(zip(wires[2], bits))
        fixed_expr = (
            "fun w => "
            + "".join(
                f"if w={k} then some {str(bool(b)).lower()} else "
                for k, b in fixed.items()
            )
            + "none"
        )
        for side, indices in enumerate(groups):
            free = wires[side]
            child = _child(net, indices, free, fixed, _Run(BoundaryPolicy()))
            num_expr = (
                "fun w => "
                + "".join(f"if w={w} then {i} else " for i, w in enumerate(free))
                + "0"
            )
            for original_id, actual in zip(indices, child.factors):
                parent = net.factors[original_id]
                tag = f"f{mask}_{side}_{original_id}"
                code.append(
                    f"def {tag} : Factor := ⟨{list(parent.ports)}, {list(parent.table)}⟩"
                )
                name = "bridge_" + tag
                expected = list(actual.table)
                if corrupt and not names:
                    expected[0] += 1
                code.append(
                    f"theorem {name} : ((freePorts ({fixed_expr}) {tag}.ports).map ({num_expr}) : List Nat) = {list(actual.ports)} ∧ ((List.range {len(expected)}).map (gather {tag} ({fixed_expr}))) = ({expected} : List Int) := by decide"
                )
                code.append("#print axioms " + name)
                names.append(name)
    return "\n".join(code) + "\n", names


def run(output, corrupt=False):
    evidence = {"status": "INCOMPLETE", "universal_executable_refinement": False}
    started = time.monotonic()
    try:
        lean = os.environ.get("LEAN_BIN") or shutil.which("lean")
        if not lean:
            raise ValueError("missing Lean compiler")
        version = subprocess.check_output(
            [lean, "--version"], text=True, timeout=30
        ).strip()
        if not check_lean_version(
            (ROOT / "lean-toolchain").read_text().strip(), version
        ):
            raise ValueError("wrong Lean toolchain")
        code, names = generate(corrupt)
        evidence.update(
            lean_version=version,
            fixtures=len(names),
            sha256=sha256(code.encode()).hexdigest(),
            model_source={
                n: sha256((ROOT / "proofs" / n).read_bytes()).hexdigest()
                for n in ("FiniteBoundaryReduction.lean", "BoundaryGather.lean")
            },
        )
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)
            env = {**os.environ, "LEAN_PATH": str(path)}
            for name in ("FiniteBoundaryReduction", "BoundaryGather", "ConcreteChecks"):
                src = path / (name + ".lean")
                if name == "ConcreteChecks":
                    src.write_text(code, encoding="utf-8")
                else:
                    shutil.copyfile(ROOT / "proofs" / src.name, src)
                proc = subprocess.run(
                    [lean, "-o", name + ".olean", src.name],
                    cwd=path,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=90,
                )
                evidence["compiler_output"] = proc.stdout
                if proc.returncode:
                    raise ValueError("compiler rejected " + name)
            audit = check_axiom_reports(proc.stdout, names)
            if not audit["passed"]:
                raise ValueError("axiom audit failed")
            evidence.update(
                status="KERNEL_CHECKED_CONCRETE_CHILD_TABLES", axiom_audit=audit
            )
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        evidence.update(status="INCONCLUSIVE_OR_REJECTED", reason=str(exc))
    evidence["wall_seconds"] = time.monotonic() - started
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2) + "\n")
    return evidence["status"] == "KERNEL_CHECKED_CONCRETE_CHILD_TABLES"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path, default=Path("validation/r97_concrete_bridge.json")
    )
    parser.add_argument("--inject-table-fault", action="store_true")
    args = parser.parse_args()
    raise SystemExit(0 if run(args.output, args.inject_table_fault) else 1)
