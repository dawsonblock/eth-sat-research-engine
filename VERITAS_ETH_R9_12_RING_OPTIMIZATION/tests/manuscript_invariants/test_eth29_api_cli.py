import json
from fastapi.testclient import TestClient
from veritas.api.main import app
from veritas.research.eth_interpolation.cli_v29 import main

client=TestClient(app)

def test_v29_tapered_api_and_rejection():
    x=client.post('/v1/research/eth/tapered-reference',json={
       'wires':2,'a':1,'u':1,'precision':8,'coefficients':[12,9,-3,0,2]})
    assert x.status_code==200,x.text
    assert x.json()['result_mod_2p']==12
    assert x.json()['recovery']['valid']
    bad=client.post('/v1/research/eth/tapered-reference',json={'wires':8,'a':5})
    assert bad.status_code==422

def test_v29_mode_api_and_tamper():
    x=client.post('/v1/research/eth/extension-modes',json={
      'edges':[[0,0],[1,1],[0,1],[1,0]],'a':1,'radix':2,
      'node':1,'precision':8,'extension_degree':4,'jet_length':3})
    assert x.status_code==200,x.text
    body=x.json()
    assert body['checker']['valid']
    assert client.post('/v1/research/eth/extension-modes/check',json={'certificate':body['certificate']}).json()['valid']
    body['certificate']['scope']['subexponential_runtime_proven']=True
    assert not client.post('/v1/research/eth/extension-modes/check',json={'certificate':body['certificate']}).json()['valid']
    assert client.get('/v1/research/eth/v29/status').json()['version']=='2.9.0'

def test_v29_cli(capsys,tmp_path):
    assert main(['tapered','--wires','2','--coefficients-json','[12,9,-3,0,2]'])==0
    assert json.loads(capsys.readouterr().out)['recovered_mod_2p']==12
    file=tmp_path/'modes.json'
    assert main(['modes','--output',str(file)])==0
    assert json.loads(capsys.readouterr().out)['checker']['valid']
    assert main(['check-modes','--certificate',str(file)])==0
    assert json.loads(capsys.readouterr().out)['valid']
    cert=json.loads(file.read_text());cert['scope']['subexponential_runtime_proven']=True;file.write_text(json.dumps(cert))
    assert main(['check-modes','--certificate',str(file)])==1
    assert not json.loads(capsys.readouterr().out)['valid']
