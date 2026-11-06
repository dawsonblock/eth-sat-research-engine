"""Independent source replay tests for manuscript-relevant structural ledger."""
from copy import deepcopy
from random import Random
from itertools import product
import pytest
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_packing_v26.constructor import construct_d3_packing
from veritas.research.eth_recursion_v30.implicit_children import make_bipartite_edges
from veritas.research.eth_modes_v31 import make_jet_tile_modes
from veritas.research.eth_child_topology_v34 import construct_topology_certificate,check_topology_certificate


def setup(n=2,clauses=((1,2),),r=2,a=1,with_modes=True):
    net=from_cnf(CNF.from_lists(n,[list(q) for q in clauses]))
    d3=construct_d3_packing(make_bipartite_edges(net),r=r,a=a,max_packets=256)
    modes=make_jet_tile_modes(d3,node=1,precision=5,extension_degree=3,jet_length=2) if with_modes else None
    return d3,modes


def test_complete_exact_port_accounting():
    d3,modes=setup()
    cert=construct_topology_certificate(d3,mode_certificate=modes)
    assert check_topology_certificate(cert)['valid']
    assert cert['summary']['total_original_half_ports']==2*d3['M']
    assert sum(len(p['real_slots']) for p in cert['packet_real_slot_ledger'])==d3['M']
    assert cert['summary']['actual_recursive_child_wires_verified'] is False
    assert cert['summary']['m_over_8_child_wire_theorem_proven'] is False
    assert cert['scope']['subexponential_runtime_proven'] is False
    assert cert['summary']['manuscript_parameter_gate'] is False  # scaled radix 2
    for g in cert['groups']:
        assert g['real_half_ports']==len(g['row_edges'])+len(g['column_edges'])
    for mid,m in enumerate(cert['mode_ledger']):
        hits=[g['group'] for g in cert['groups'] if mid in g['incident_mode_ids']]
        assert hits==sorted([m['source_group'],m['target_group']])


def test_no_modes_and_other_coordinate():
    d3,_=setup(with_modes=False)
    cert=construct_topology_certificate(d3)
    assert cert['mode_ledger']==[]
    assert check_topology_certificate(cert)['valid']
    with pytest.raises(ValueError):
        construct_topology_certificate(d3,coordinate=1)


def test_fail_closed_tampering():
    d3,modes=setup()
    cert=construct_topology_certificate(d3,mode_certificate=modes)
    edits=('group_ports','mode_endpoint','packet_slot','mode_weight','false_proof',
           'false_eligibility','wrong_coordinate','d3_edge','mode_d3','claim','scope')
    for kind in edits:
        bad=deepcopy(cert)
        if kind=='group_ports':bad['groups'][0]['real_half_ports']+=1
        if kind=='mode_endpoint':
            if not bad['mode_ledger']:continue
            bad['mode_ledger'][0]['source_group']+=1
        if kind=='packet_slot':
            first=next(p for p in bad['packet_real_slot_ledger'] if p['real_slots'])
            first['real_slots'][0]['edge']=10_000
        if kind=='mode_weight':
            if not bad['mode_ledger']:continue
            bad['mode_ledger'][0]['weight']+=1
        if kind=='false_proof':bad['summary']['m_over_8_child_wire_theorem_proven']=True
        if kind=='false_eligibility':bad['summary']['manuscript_parameter_gate']=True
        if kind=='wrong_coordinate':bad['coordinate']=1
        if kind=='d3_edge':bad['d3_certificate']['edges'][0][0]+=15
        if kind=='mode_d3':bad['mode_certificate']['d3_certificate']['edges'][0][1]+=5
        if kind=='claim':bad['claim']='ETH_PROVEN'
        if kind=='scope':bad['scope']['subexponential_runtime_proven']=True
        assert not check_topology_certificate(bad)['valid'],kind


def test_random_small_port_layouts():
    rng=Random(34004);done=0
    for _ in range(36):
        n=rng.randint(1,3)
        clauses=[[rng.choice((-1,1))*rng.randint(1,n)
           for _ in range(rng.randint(1,2))] for _ in range(rng.randint(1,2))]
        d3,_=setup(n,clauses,with_modes=False)
        cert=construct_topology_certificate(d3)
        assert check_topology_certificate(cert)['valid']
        assert sum(g['real_half_ports'] for g in cert['groups'])==2*d3['M']
        # A half-port occurs precisely once on its own side of the network.
        assert sorted(e for g in cert['groups'] for e in g['row_edges'])==list(range(d3['M']))
        assert sorted(e for g in cert['groups'] for e in g['column_edges'])==list(range(d3['M']))
        done+=1
    assert done==36


def test_api_and_cli(tmp_path):
    from fastapi.testclient import TestClient
    from veritas.api.main import app
    c=TestClient(app)
    assert c.get('/v1/research/eth/v34/status').json()['version']=='3.4.0'
    res=c.post('/v1/research/eth/child-topology',json={'n':2,'clauses':[[1,2]],'with_modes':True})
    assert res.status_code==200,res.text
    cert=res.json()['certificate']
    assert c.post('/v1/research/eth/child-topology/check',json={'certificate':cert}).json()['valid']
    from veritas.research.eth_child_topology_v34.cli import main
    path=tmp_path/'child-topology.json'
    assert main(['construct','--output',str(path),'--with-modes'])==0
    assert main(['check','--certificate',str(path)])==0
