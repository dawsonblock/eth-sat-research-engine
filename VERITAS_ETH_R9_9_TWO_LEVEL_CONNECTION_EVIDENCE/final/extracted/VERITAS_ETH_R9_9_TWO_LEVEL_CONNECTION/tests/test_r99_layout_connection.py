from pathlib import Path
from dataclasses import replace
import pytest
from veritas.research.parent_child_r98.model import Budget, canonical, decode, digest
from veritas.research.parent_child_r98.shrinking_cli import load_input
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r99.stream_cli import prepare_layout_input, streaming_preflight, main
ROOT=Path(__file__).resolve().parents[1]
POLICY=replace(DEFAULT_SHRINKING_POLICY,max_certificate_bytes=100_000_000)

def inputs():
    return load_input(ROOT/'examples/r99_nonconstant_matching242.json'), ROOT/'examples/r99_nonconstant_matching242_layout.json'

def test_prepared_layout_and_two_level_topology():
    root,path=inputs();parent,layout=prepare_layout_input(root,path,budget=Budget(POLICY))
    assert parent.content_digest!=root.content_digest and layout.parent_digest==parent.content_digest
    assert parent.defining_polynomial.bit_length()-1==10
    result=streaming_preflight(parent,layout,2,4096,POLICY)
    assert result['streaming_topology_admitted'],result
    assert max(max(c['child_edges']) for c in result['nodes'][0]['coordinates'])==22
    assert max(max(c['child_edges']) for n in result['nodes'] if n['depth']==1 for c in n['coordinates'])==2
    assert result['legacy_executor_advisories'] and not result['blockers']
    assert result['report_digest'] == digest(canonical({k:v for k,v in result.items() if k != 'report_digest'}))
    assert result['report_digest'] != result['original_preflight_digest']
    assert not streaming_preflight(parent,layout,1,4096,POLICY)['streaming_topology_admitted']

@pytest.mark.parametrize('fault',['digest','coverage','schedule'])
def test_invalid_original_layout_is_not_reauthenticated(tmp_path,fault):
    root,path=inputs();data=decode(path.read_bytes())
    if fault=='digest':data['parent_digest']='0'*64
    elif fault=='coverage':data['source']['packets'][0]['occupied_slots']=[]
    else:data['u']=2
    path=tmp_path/'bad.json';path.write_bytes(canonical(data))
    with pytest.raises(ValueError):prepare_layout_input(root,path,budget=Budget(POLICY))

def test_cli_preflight_never_starts_contraction(tmp_path,monkeypatch):
    import veritas.research.parent_child_r99.stream_cli as cli
    monkeypatch.setattr(cli,'contract_streaming',lambda *a,**k:pytest.fail('arithmetic launched'))
    output=tmp_path/'preview'
    assert main([str(ROOT/'examples/r99_nonconstant_matching242.json'),'--layout-file',str(ROOT/'examples/r99_nonconstant_matching242_layout.json'),'--levels','2','--preflight-only','--max-certificate-bytes','100000000','--output-dir',str(output)])==0
    assert 'result' not in decode((output/'report.json').read_bytes())
    assert not (output/'events.jsonl').exists()
