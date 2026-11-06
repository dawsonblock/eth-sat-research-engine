"""Execute the two-level fixture, independent replay and factorized exact oracle."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from veritas.research.parent_child_r98.model import canonical
from veritas.research.parent_child_r98.shrinking_cli import load_input, _check_output
from veritas.research.parent_child_r99.cli import load_execution_report
from veritas.research.parent_child_r910.reference import matching_reference
from veritas.research.tapered_v4.provenance import source_binding


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    args = parser.parse_args()
    _check_output(args.output_dir)
    args.output_dir.mkdir(parents=True,exist_ok=False)
    binding = source_binding()['digest']
    env = dict(os.environ,PYTHONPATH=str(ROOT/'src'))
    command = [sys.executable,'-m','veritas.research.parent_child_r910.cli',
        str(ROOT/'examples/r910_matching235.json'), '--layout-file',
        str(ROOT/'examples/r910_matching235_layout.json'), '--levels','2',
        '--verify','--output-dir',str(args.output_dir/'run')]
    with (args.output_dir/'run.log').open('w') as log:
        code = subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT).returncode
    report = load_execution_report(args.output_dir/'run/report.json',max_bytes=100_000_000)
    reference = matching_reference(load_input(ROOT/'examples/r910_matching235.json'))
    (args.output_dir/'reference.json').write_bytes(canonical(reference))
    passed = (code==0 and canonical(reference['result'])==canonical(report.get('result'))
        and report['active_calls_by_depth'].get('1',0)>0
        and report['largest_active_edges_by_depth']=={'0':235,'1':22}
        and report['point_predictions_reconcile'] and report['ledger']['stage_sum_reconciles']
        and source_binding()['digest']==binding)
    result = {'status':'PASS_FINITE_R910_NUMERICAL_GATES' if passed else 'FAILED',
        'command':command,'exit_code':code,'source_sha256':binding,
        'result':report.get('result'), 'source_qualified':False, 'theorem_mode_enabled':False,
        'bit_operations':'NOT_INSTRUMENTED','complexity':'NOT_ESTABLISHED',
        'full_r910_resource_contract':'PARTIAL_WORK_UNITS_AND_PROCESS_RSS_ONLY'}
    (args.output_dir/'summary.json').write_bytes(canonical(result))
    print(json.dumps(result))
    return 0 if passed else 2


if __name__=='__main__':
    raise SystemExit(main())
