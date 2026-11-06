import json
import os
from pathlib import Path
import subprocess
import sys


def test_weighted_recovery_cli(tmp_path):
    p=tmp_path/'sample.cnf'
    p.write_text('p cnf 3 2\n1 2 0\n-1 3 0\n',encoding='utf-8')
    env={**os.environ,'PYTHONPATH':str(Path(__file__).resolve().parents[1]/'src')}
    output=subprocess.check_output([sys.executable,'-m','veritas.cli','cnf',str(p),
                                    '--weighted-recovery','--timeout','10'],
                                   cwd=Path(__file__).resolve().parents[1],
                                   env=env,timeout=20,text=True)
    result=json.loads(output)
    assert result['status']=='EXACT_COUNT'
    assert result['exact_count']==4
    assert result['independent_jet_checked'] and result['independent_count_checked']
