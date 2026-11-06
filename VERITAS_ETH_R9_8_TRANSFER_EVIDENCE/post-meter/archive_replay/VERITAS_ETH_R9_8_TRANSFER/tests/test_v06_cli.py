import json
import subprocess
import sys
from pathlib import Path
from veritas.core.cnf import CNF


def cli(*args):
    return subprocess.run([sys.executable, '-m', 'veritas.cli', *map(str,args)], capture_output=True,text=True)


def test_cli_certified_count_and_offline_checker(tmp_path: Path):
    cnf=tmp_path/'example.cnf'
    cnf.write_text(CNF.from_lists(3,[[1,2],[-1,3]]).to_dimacs())
    result=cli('cnf',cnf,'--certify-count')
    assert result.returncode==0,result.stderr
    record=json.loads(result.stdout)
    assert record['status']=='COUNT' and record['count']=='4' and record['evidence_level']=='COUNT_PROOF_CHECKED'
    proof=tmp_path/'count.json'
    proof.write_text(json.dumps(record))
    checked=cli('check-count',cnf,proof)
    assert checked.returncode==0,checked.stderr
    assert json.loads(checked.stdout)['count']=='4'
    bad=json.loads(proof.read_text()); bad['certificate']['count']='5'
    proof.write_text(json.dumps(bad))
    assert cli('check-count',cnf,proof).returncode==2


def test_cli_spectrum(tmp_path: Path):
    cnf=tmp_path/'example.cnf'
    cnf.write_text(CNF.from_lists(2,[[1],[-1]]).to_dimacs())
    exact=cli('cnf',cnf,'--spectrum')
    assert exact.returncode==0,exact.stderr
    assert json.loads(exact.stdout)['coefficients']==['0','4','0']
    modular=cli('cnf',cnf,'--spectrum','--precision-bits','1')
    assert modular.returncode==0,modular.stderr
    assert json.loads(modular.stdout)['coefficients']==['0','0','0']
