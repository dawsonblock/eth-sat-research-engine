#!/usr/bin/env python3
"""Finite whole-run and complete padded-domain differential checks.

Freshly compiles Lean dependencies. #eval is executable evidence; the separate
Lean gate kernel-checks the general model theorems. CPython is not extracted.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from itertools import product
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from veritas.research.eth_packing_v26.streaming import construct_streaming_d3_packing
from veritas.research.eth_packing_v26.streaming_check import verify_streaming_d3_certificate
import validate_conditional_expectation_lean as gate
from validate_r93_packet_model import source_manifest as base_manifest

POLICY = {"seed": 9404, "random_cases": 16, "max_edges": 14, "max_work": 3_000_000,
          "command_timeout_seconds": 120, "hard_memory_limit_enforced": False,
          "theorem_mode_enabled": False}


def manifest():
    files = base_manifest()
    for path in ("scripts/validate_r94_foundation.py", "scripts/validate_r93_packet_model.py",
                 "tests/test_r94_source_state.py", "tests/test_r94_foundation_validation.py"):
        files[path] = gate.sha256(ROOT / path)
    return dict(sorted(files.items()))


def corpus():
    cases = [([],2,1), ([(0,0)],2,1), ([(0,0),(1,1),(0,1)],2,1),
             ([(0,0),(0,0),(1,2),(0,2),(1,1)],2,2),
             ([(0,i) for i in range(12)] + [(0,0)]*2,2,1),
             ([(0,1),(1,0),(0,1),(2,0)],3,2)]
    rng = random.Random(POLICY["seed"])
    for _ in range(POLICY["random_cases"]):
        edges=[(rng.randrange(3),rng.randrange(3)) for _ in range(rng.randrange(8))]
        cases.append((edges,rng.choice((2,3)),rng.choice((1,2))))
    edges,r,a=cases[3]
    cases.append((list(reversed(edges)),r,a))
    return cases


def assert_complete(actual, expected):
    if len(actual) != len(expected) or actual != expected:
        bad=[i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b]
        raise ValueError(f"complete sequence mismatch: {bad[:8]}, lengths={len(actual)}/{len(expected)}")


def word_text(w):
    return ",".join(map(str,w))


def generate():
    lines=["import D3KeyedRun", "import D3FinitePacketDomain",
      'def wordText (w : List Nat) := String.intercalate "," (w.map toString)',
      'def sideText : PackingSide → String | .row => "R" | .col => "C"',
      'def stepText (t : PackingVertex × List Nat × Nat) := "R94T:" ++ sideText t.1.1 ++ ":" ++ toString t.1.2 ++ ":" ++ wordText t.2.1 ++ ":" ++ toString t.2.2',
      'def addressText (ad : D3FullPacketModel.Address) := "R94A:" ++ String.intercalate "," (ad.pattern.map (fun p => toString p.1 ++ "-" ++ toString p.2)) ++ ":" ++ toString ad.packet ++ ":" ++ toString ad.slot']
    expected=[];records=[]
    for n,(edges,r,a) in enumerate(corpus()):
        built=construct_streaming_d3_packing(edges,r=r,a=a,max_work=POLICY["max_work"],score_backend="python")
        cert=built.certificate
        replay=verify_streaming_d3_certificate(cert)
        if not replay["valid"]:
            raise ValueError("independent rational replay failed")
        term="["+",".join(f"({u},{v})" for u,v in edges)+"]"
        lines += [f'def edges{n} : List PackingEdge := {term}',
                  f'def vertices{n} := d3PythonOrderedVertices edges{n}',
                  f'def final{n} := D3KeyedRun.run {r} {a} (by decide) edges{n} vertices{n} D3KeyedRun.empty',
                  f'#eval (D3CandidateOrder.productWords {r} {a}).forM (fun w => IO.println ("R94W:" ++ wordText w))',
                  f'#eval (D3KeyedRun.trace {r} {a} (by decide) edges{n} vertices{n} D3KeyedRun.empty).forM (fun t => IO.println (stepText t))']
        expected.extend("R94W:"+word_text(w) for w in product(range(r),repeat=a))
        expected.extend(f'R94T:{t["side"]}:{t["vertex"]}:{word_text(t["label"])}:{t["expected_square_scaled"]}' for t in cert["steps"])
        for side,labels in (("R",built.packing.rows),("C",built.packing.cols)):
            lean_side="row" if side=="R" else "col"
            for ident,label in sorted(labels.items()):
                for d,value in enumerate(label):
                    lines.append(f'#eval IO.println ("R94S:" ++ toString (final{n} (.{lean_side},{ident},{d})))')
                    expected.append(f'R94S:(some {value})')
                lines.append(f'#eval IO.println ("R94S:" ++ toString (final{n} (.{lean_side},{ident},{a})))')
                expected.append('R94S:none')
        lines.append(f'#eval IO.println ("R94F:" ++ toString ({r}^(2*{a}) * d3EdgeClassSquareSum edges{n} (d3PartialColor (D3KeyedRun.view final{n}) {a})))')
        expected.append(f'R94F:{cert["final_square_scaled"]}')
        records.append({"edges":edges,"r":r,"a":a,"steps":cert["steps"],
                        "initial_score":cert["initial_expected_square_scaled"],
                        "final_score":cert["final_square_scaled"],"independent_rational_replay":True})
    domains=[]
    for r,a,H in ((0,0,0),(0,1,2),(1,0,1),(1,2,4),(2,1,2),(2,2,4),(3,2,4)):
        lines.append(f'#eval (D3FinitePacketDomain.addresses {r} {a} {H}).forM (fun ad => IO.println (addressText ad))')
        count=0
        for pattern in product([(x,y) for x in range(r) for y in range(x,r)],repeat=a):
            copies=2**sum(x==y for x,y in pattern)
            for packet in range(H//copies):
                for slot in range(2**a):
                    expected.append("R94A:"+",".join(f"{x}-{y}" for x,y in pattern)+f":{packet}:{slot}")
                    count+=1
        if count != r**(2*a)*H:
            raise ValueError("independent finite domain cardinality failed")
        domains.append({"r":r,"a":a,"H":H,"addresses":count,"complete_domain_checked":True})
    return "\n".join(lines)+"\n",expected,records,domains


def run():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output", default=str(Path(os.environ["VERITAS_EVIDENCE_DIR"]) / "r9_4_differential.json")
                        if os.environ.get("VERITAS_EVIDENCE_DIR") else "validation/r9_4_differential.json")
    args=parser.parse_args()
    output=ROOT / args.output
    report={"schema":"VERITAS_R94_FOUNDATION_V1","status":"NOT_RUN","policy":POLICY,
      "python":platform.python_version(),"platform":platform.platform(),"commands":[],
      "checks_executed":0,"executable_refinement_proven":False,"theorem_mode_enabled":False,
      "limitations":["#eval and CPython are executable tests, not a kernel proof of their runtimes.",
        "Finite rational replay shares representation conventions but not the production scorer.",
        "No source-active graph, recursive contraction, complete bit work or space proof."]}
    start=time.perf_counter()
    try:
        before=manifest();report["source_manifest"]=before
        report["source_manifest_sha256"]=hashlib.sha256(json.dumps(before,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        lean=os.environ.get("LEAN_BIN") or shutil.which("lean")
        if not lean: raise ValueError("Lean unavailable")
        version=subprocess.run([lean,"--version"],capture_output=True,text=True,timeout=30,check=True).stdout.strip()
        report["lean_version"]=version
        if not gate.check_lean_version((ROOT/"lean-toolchain").read_text().strip(),version):
            raise ValueError("wrong compiler version")
        source,expected,records,domains=generate()
        report.update(cases=records,domains=domains,checks_expected=len(expected),
                      generated_source_sha256=hashlib.sha256(source.encode()).hexdigest())
        with tempfile.TemporaryDirectory(prefix="veritas-r94-") as tmp:
            env={**os.environ,"LEAN_PATH":tmp}
            for rel in gate.PROOF_FILES:
                dest=gate.PROOF_OUTPUTS.get(rel)
                if not dest: raise ValueError("missing module output")
                t=time.perf_counter()
                result=subprocess.run([lean,"-o",str(Path(tmp)/dest),rel],cwd=ROOT,env=env,text=True,
                                      capture_output=True,timeout=POLICY["command_timeout_seconds"])
                report["commands"].append({"file":rel,"exit_code":result.returncode,"seconds":time.perf_counter()-t})
                if result.returncode: raise ValueError(result.stdout[-3000:])
                if rel=="proofs/D3FinitePacketDomain.lean": break
            path=Path(tmp)/"FoundationVectors.lean";path.write_text(source)
            result=subprocess.run([lean,str(path)],cwd=ROOT,env=env,text=True,capture_output=True,
                                  timeout=POLICY["command_timeout_seconds"])
            report["evaluation_exit_code"]=result.returncode
            if result.returncode: raise ValueError(result.stdout[-4000:])
            actual=[line.strip() for line in result.stdout.splitlines() if line.startswith("R94")]
            report["checks_executed"]=len(actual)
            assert_complete(actual,expected)
        if manifest()!=before: raise ValueError("source changed during validation")
        report["status"]="PASS_FINITE_DIFFERENTIAL"
    except (OSError,ValueError,subprocess.SubprocessError) as exc:
        report.update(status="FAIL_OR_INCOMPLETE",error=str(exc).replace(str(ROOT),"<repository>"))
    report["elapsed_seconds"]=time.perf_counter()-start
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:report[k] for k in ("status","checks_executed","elapsed_seconds")}))
    return 0 if report["status"]=="PASS_FINITE_DIFFERENTIAL" else 1

if __name__=="__main__":
    raise SystemExit(run())
