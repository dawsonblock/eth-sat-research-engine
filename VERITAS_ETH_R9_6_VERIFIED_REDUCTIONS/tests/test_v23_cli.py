import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ENV = {**os.environ, 'PYTHONPATH': str(ROOT/'src')}


def run(*args):
    return subprocess.run([sys.executable, '-m', 'veritas.cli', *map(str,args)], cwd=ROOT,
                          env=ENV, capture_output=True, text=True, timeout=20)


def test_weighted_cli_generation_verification_and_conditional(tmp_path):
    proof = run('cnf','examples/example.cnf','--certify-weighted-dag','examples/weights_v23.json')
    assert proof.returncode == 0,proof.stderr
    info = json.loads(proof.stdout)
    assert info['status'] == 'WEIGHTED_COUNT' and info['evidence_level']=='WEIGHTED_COUNT_PROOF_CHECKED'
    dest=tmp_path/'proof.json';dest.write_text(proof.stdout, encoding='utf8')
    check=run('check-weighted-dag','examples/example.cnf','examples/weights_v23.json',dest)
    assert check.returncode == 0,check.stderr
    assert json.loads(check.stdout)['status'] == 'VALID'
    forged=json.loads(proof.stdout); forged['certificate']['count']='99'
    dest.write_text(json.dumps(forged),encoding='utf8')
    check=run('check-weighted-dag','examples/example.cnf','examples/weights_v23.json',dest)
    assert check.returncode == 2
    assert json.loads(check.stdout)['status'] == 'REJECTED'
    posterior=run('cnf','examples/example.cnf','--conditional-query','examples/query_v23.cnf',
                  '--weights','examples/weights_v23.json')
    assert posterior.returncode == 0,posterior.stderr
    assert json.loads(posterior.stdout)['status'] == 'PROBABILITY'
