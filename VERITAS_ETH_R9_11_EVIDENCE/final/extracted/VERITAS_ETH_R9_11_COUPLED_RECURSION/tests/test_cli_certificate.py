from pathlib import Path
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def run(args):
    env = dict(os.environ)
    env['PYTHONPATH'] = str(ROOT/'src')
    return subprocess.run([sys.executable,'-m','veritas.cli',*map(str,args)],
                          capture_output=True,text=True,cwd=ROOT,env=env,timeout=15)


def test_cli_generated_proof_can_be_independently_rechecked(tmp_path):
    cnf = ROOT/'examples'/'contradiction.cnf'
    created = run(['cnf',cnf,'--certify-unsat'])
    assert created.returncode == 0,created.stderr
    assert json.loads(created.stdout)['status'] == 'UNSAT'
    proof = tmp_path/'proof.json'
    proof.write_text(created.stdout)
    check = run(['check-proof',cnf,proof])
    assert check.returncode == 0, check.stderr + check.stdout
    assert json.loads(check.stdout)['status'] == 'VALID'
    raw = tmp_path/'raw.json'
    raw.write_text(json.dumps(json.loads(created.stdout)['certificate']))
    assert run(['check-proof',cnf,raw]).returncode == 0
    fake = tmp_path/'fake.json'
    fake.write_text('{}')
    assert run(['check-proof',cnf,fake]).returncode != 0
