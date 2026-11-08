from copy import deepcopy
from dataclasses import replace
import pytest
from veritas.research.parent_child_r98.model import canonical,decode,Refusal
from veritas.research.parent_child_r912.coefficient_writer import encode_point
from veritas.research.parent_child_r912.coefficient_reader import expand_point


def point():
    local=[[i,i,[[2**1024+17,0]]] for i in range(44)]
    return {'kind':'point','original':{'local':local},'folded':{'local':deepcopy(local)},'support':{}}


def test_exact_reconstruction_and_storage():
    original=point();packed=decode(canonical(encode_point(original)))
    assert len(packed['coefficients'])==1
    assert canonical(expand_point(packed,max_expanded_bytes=1000000))==canonical(original)
    assert len(canonical(packed))*3<len(canonical(original))


@pytest.mark.parametrize('attack',['missing','altered','reference','unused','fields'])
def test_tampering(attack):
    packed=decode(canonical(encode_point(point())))
    key=next(iter(packed['coefficients']))
    if attack=='missing':del packed['coefficients'][key]
    elif attack=='altered':packed['coefficients'][key][0][0]+=1
    elif attack=='reference':packed['point']['folded']['local'][0][2]['coefficient_sha256']='f'*64
    elif attack=='unused':
        from hashlib import sha256
        value=[[7]];packed['coefficients'][sha256(canonical(value)).hexdigest()]=value
    else:packed['point']['original']['local'][0][2]['extra']=True
    with pytest.raises(ValueError):expand_point(packed,max_expanded_bytes=1000000)


def test_expansion_cap():
    with pytest.raises(Refusal):expand_point(decode(canonical(encode_point(point()))),max_expanded_bytes=100)


@pytest.mark.parametrize("compress_records",[False,True])
def test_compressed_uncompressed_numerical_equivalence(tmp_path,monkeypatch,compress_records):
    from veritas.research.parent_child_r98.shrinking_cli import load_input
    from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
    from veritas.research.parent_child_r910.engine import contract
    from veritas.research.parent_child_r910.checker import verify
    p=tmp_path/'network.json'
    p.write_bytes(canonical({'root_s':32,'precision':32,'extension_degree':3,'edges':22,
        'vertices':[{'side':side,'ports':[i],'table':values if i==0 else [1,1]}
                    for side,values in [('row',[1,3]),('column',[2,5])] for i in range(22)]}))
    parent=load_input(p);policy=replace(DEFAULT_SHRINKING_POLICY,max_certificate_bytes=100000000)
    plain=[];compact=[]
    a=contract(parent,policy=policy,evidence_sink=plain.append)
    b=contract(parent,policy=policy,evidence_sink=compact.append,coefficient_encoding=True,compressed_records=compress_records)
    assert a['status']==b['status']=='PASS_FINITE_TWO_LEVEL_CAPABLE_RECURSION'
    assert a['result']==b['result']==((17*2**21,0,0),)
    for x,y in zip(plain,compact):
        event=decode(y)
        if event['kind']=='compressed_record':
            from veritas.research.parent_child_r912.record_reader import unpack_record
            event=unpack_record(event,max_expanded_bytes=20000000)
        if event['kind']=='coefficient_point':event=expand_point(event,max_expanded_bytes=100000000)
        assert x==canonical(event)
    import veritas.research.parent_child_r912.coefficient_writer as writer
    monkeypatch.setattr(writer,'encode_point',lambda *args:pytest.fail('reader called producer'))
    assert verify(parent,compact,b,policy=policy)['status']=='PASS_INDEPENDENT_NUMERICAL_REPLAY'
    assert verify(parent,plain,a,policy=policy)['status']=='PASS_INDEPENDENT_NUMERICAL_REPLAY'
