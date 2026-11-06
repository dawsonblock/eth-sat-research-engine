import json
import subprocess
import sys
from pathlib import Path
from fastapi.testclient import TestClient
from veritas.api.main import app

client=TestClient(app)


def test_d3_api_construct_check_and_status():
    r=client.post('/v1/research/eth/d3/construct',json={
        'edges':[[0,1],[1,0],[0,0],[1,1]],'r':2,'a':1})
    assert r.status_code==200,r.text
    cert=r.json()
    assert cert['verification']['valid']
    chk=client.post('/v1/research/eth/d3/check',json={'certificate':cert})
    assert chk.status_code==200 and chk.json()['valid']
    status=client.get('/v1/research/eth/d3/status')
    assert status.status_code==200 and status.json()['version']=='2.6.0'
    assert 'no original asymptotic runtime claim' in status.json()['limitations']


def test_api_refuses_unsafe_size_and_infeasible_preconditions():
    req={'edges':[[0,0]],'r':2,'a':1,'require_theorem_preconditions':True}
    r=client.post('/v1/research/eth/d3/construct',json=req)
    assert r.status_code==422
    req.pop('require_theorem_preconditions')
    req['max_work']=1
    assert client.post('/v1/research/eth/d3/construct',json=req).status_code==422


def test_cli_roundtrip(tmp_path):
    file=tmp_path/'cert.json'
    invoke=[sys.executable,'-m','veritas.research.eth_packing_v26.cli']
    proc=subprocess.run(invoke+['pack','--edges-json','[[0,1],[1,0],[0,0]]',
                                '--output',str(file)],capture_output=True,text=True,check=True)
    assert file.is_file()
    assert json.loads(proc.stdout)['verification']['valid']
    verified=subprocess.run(invoke+['check','--certificate',str(file)],capture_output=True,text=True)
    assert verified.returncode==0 and json.loads(verified.stdout)['valid']
    cert=json.loads(file.read_text())
    cert['packets'][0]['slots']=[None]*cert['L']
    file.write_text(json.dumps(cert))
    failed=subprocess.run(invoke+['check','--certificate',str(file)],capture_output=True,text=True)
    assert failed.returncode==2
