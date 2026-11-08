import itertools
import json
from dataclasses import replace

import pytest
from veritas.research.manuscript import cli,cnf,experimental
from veritas.research.manuscript.cnf import Formula
from veritas.research.manuscript.experimental import ScaledExperiment,count_scaled_cnf
from veritas.research.manuscript.resources import Budget,Limits

EXPERIMENT=ScaledExperiment(certified_support=True)
COMMANDS=('count','count-optimized','count-fixed-density','count-scaled')


def argv(command,text):
    args=[command,'--n','2','--clauses-json',text,'--max-work','100000000']
    if command=='count-scaled':args+=['--a','1','--u','1','--radix','2','--active-depth','1','--column-shift','1','--mode-policy','certified']
    return args


@pytest.mark.parametrize('command',COMMANDS)
@pytest.mark.parametrize('value',[[[1.9]],[[1.0]],[[True]],[[False]],[['1']],[[None]],[[[1]]],{'1':[2]},[{'1':2}],[1,2],None,'12',12])
def test_invalid_json_schema_is_never_coerced(command,value,capsys):
    with pytest.raises(SystemExit) as caught:cli.main(argv(command,json.dumps(value)))
    assert caught.value.code==2
    output=capsys.readouterr();assert 'error:' in output.err and 'Traceback' not in output.err
    assert 'PASS' not in output.out


@pytest.mark.parametrize('command',COMMANDS)
@pytest.mark.parametrize('text',['[','[[0]]','[[3]]','[[NaN]]','[[Infinity]]'])
def test_other_bad_json_fails_cleanly(command,text,capsys):
    with pytest.raises(SystemExit) as caught:cli.main(argv(command,text))
    assert caught.value.code==2
    assert 'Traceback' not in capsys.readouterr().err


@pytest.mark.parametrize('command',COMMANDS)
@pytest.mark.parametrize('text,count',[('[]',4),('[[]]',0),('[[1,2]]',3)])
def test_valid_cli_inputs_keep_exact_semantics(command,text,count,capsys):
    cli.main(argv(command,text));result=json.loads(capsys.readouterr().out)
    assert result['status']=='PASS_EXACT_COUNT' and result['count']==count
    assert result['source_qualified'] is False


@pytest.mark.parametrize('command',COMMANDS)
def test_dimacs_errors_are_clean(command,tmp_path,capsys):
    path=tmp_path/'invalid.cnf';path.write_text('p cnf 2 1\nbogus 0\n')
    args=argv(command,'[]');index=args.index('--clauses-json');args[index:index+2]=['--dimacs',str(path)]
    with pytest.raises(SystemExit) as caught:cli.main(args)
    assert caught.value.code==2
    assert 'Traceback' not in capsys.readouterr().err


def test_scaled_cli_requires_explicit_finite_schedule(capsys):
    with pytest.raises(SystemExit) as caught:cli.main(['count-scaled','--n','1','--clauses-json','[[1]]'])
    assert caught.value.code==2
    assert '--active-depth' in capsys.readouterr().err


def exact(formula):
    return sum(all(any(bits[abs(lit)-1] if lit>0 else not bits[abs(lit)-1] for lit in clause) for clause in formula.clauses)
               for bits in itertools.product((False,True),repeat=formula.n))


@pytest.mark.parametrize('formula',[Formula(0,()),Formula(1,((),)),Formula(1,((1,),)),Formula(2,((-1,),)),
    Formula(2,((1,2),)),Formula(2,((1,-2),)),Formula(2,((1,1,2),(1,2))),Formula(5,((1,2),)),Formula(2,((1,-1),))])
def test_shared_encoding_count_matches_original_variable_oracle(formula,monkeypatch):
    def forbidden(*args,**kwargs):raise RuntimeError('silent CNF direct-count fallback')
    monkeypatch.setattr(cnf,'direct_count',forbidden)
    result=count_scaled_cnf(formula,experiment=EXPERIMENT,limits=Limits(max_work=100000000,max_seconds=120))
    assert result['status']=='PASS_EXACT_COUNT' and result['count']==exact(formula)
    for key in ('source_qualified','complexity_proven','executable_refinement_proven'):assert result[key] is False
    if result['route']=='EXPERIMENTAL_SCALED_CNF':
        assert result['precision']==formula.n+1
        assert result['extension_degree']==4*(result['finite_parameters']['s']-1).bit_length()
        assert result['inner_route']=='EXPERIMENTAL_CERTIFIED_RECURSION'
        assert result['budget_policy']=='SHARED_ENCODING_AND_CONTRACTION'
        assert result['ledger']['calls']>1 and result['ledger']['maximum_depth']==1


def test_two_active_levels_shared_encoder_and_unused_factor():
    formula=Formula(2,((1,),));events=[]
    result=count_scaled_cnf(formula,experiment=replace(EXPERIMENT,active_depth=2),limits=Limits(max_work=200000000,max_seconds=120),event_sink=events.append)
    assert result['status']=='PASS_EXACT_COUNT' and result['count']==2
    assert result['precision']==3 and result['unused_variables']==1 and result['encoded_wires']==2
    assert result['ledger']['maximum_depth']==2
    assert events[0]['kind']=='encoding' and events[0]['unused_variables']==1
    assert any(event['kind']=='active' and event['depth']==1 for event in events)
    assert all('zero_certificate' in event for event in events if event['kind']=='point')


def test_shared_budget_is_not_reset_or_doubled():
    budget=Budget(Limits(max_work=1000,max_seconds=120));budget.tick(990)
    result=count_scaled_cnf(Formula(2,((1,2),)),experiment=EXPERIMENT,budget=budget)
    assert result['status']=='INCONCLUSIVE_RESOURCE_LIMIT' and 'count' not in result and 'result' not in result
    assert result['ledger']['work_units']==budget.work>990


def test_noncompleted_or_unexpected_tensor_routes_never_become_counts(monkeypatch):
    for status in ('INCONCLUSIVE_RESOURCE_LIMIT','PASS_EXPERIMENTAL_CERTIFIED_LEAF','PASS_EXPERIMENTAL_UNKNOWN'):
        receipt={'status':status,'source_qualified':False}
        monkeypatch.setattr(experimental,'contract_scaled',lambda *args,**kwargs:receipt)
        assert count_scaled_cnf(Formula(1,((1,),)),experiment=EXPERIMENT) is receipt


def test_default_unpruned_policy_description_is_preserved():
    default=ScaledExperiment()
    assert default.description()['full_weighted_mode_domain'] is True
    assert EXPERIMENT.description()['full_weighted_mode_domain'] is False
    with pytest.raises(TypeError):ScaledExperiment(certified_support=1)
    with pytest.raises(TypeError):count_scaled_cnf(Formula(1,((1,),)),experiment=None)


@pytest.fixture(scope='module')
def replay_module():
    import importlib.util
    import sys
    from pathlib import Path
    scripts=Path(__file__).resolve().parents[1]/'scripts'
    sys.path.insert(0,str(scripts))
    spec=importlib.util.spec_from_file_location('scaled_cnf_validator',scripts/'validate_manuscript_scaled_cnf.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


@pytest.fixture(scope='module')
def certificate(replay_module):return replay_module.produce(2,[[-1]],active_depth=1)


def test_independent_replay_rejects_all_producer_dependencies(replay_module,certificate,monkeypatch):
    from veritas.research.manuscript import children,executor,model,packing,recovery,certified_modes,cauchy
    def forbidden(*args,**kwargs):raise RuntimeError('producer was called by independent replay')
    for module,names in ((cnf,('encode','count','direct_count')),(experimental,('count_scaled_cnf','contract_scaled')),
        (executor,('_contract','contract')),(children,('child_network','point_contraction')),
        (model,('direct',)),(packing,('construct',)),(recovery,('recover',)),(replay_module,('produce','count_scaled_cnf'))):
        for name in names:
            if hasattr(module,name):monkeypatch.setattr(module,name,forbidden)
    monkeypatch.setattr(certified_modes.DegreeCertifiedDomain,'__init__',forbidden)
    monkeypatch.setattr(cauchy.Kernel,'value',forbidden)
    result=replay_module.replay(certificate)
    assert result['status']=='PASS_INDEPENDENT_SHARED_SCALED_CNF_REPLAY' and result['count']==2
    assert result['calls']==57 and result['points']==14 and result['maximum_depth']==1


@pytest.mark.parametrize('n,clauses',[(0,[]),(2,[[]]),(3,[[1,-1]]),(3,[[1,1],[1]]),(9,[[-1]])])
def test_general_precision_and_normalization_replay(replay_module,n,clauses):
    result=replay_module.replay(replay_module.produce(n,clauses,active_depth=1))
    assert result['count']==exact(Formula(n,tuple(map(tuple,clauses))))
    assert result['precision']==n+1
    if n==9:assert result['extension_degree']==16


@pytest.mark.parametrize('fault',[
 'count','precision','unused','field','flags','configuration','ledger','trailing','truncated',
 'literal_sign','creation_precision','endpoint','normalized','wire_cap','original_bool',
 'leaf','point','recovered','padding','labels','variance','support','capacity','formal_size',
 'node_precision','unknown_fields','work_allowance'])
def test_shared_certificate_tampering_fails_closed(replay_module,certificate,fault):
    from copy import deepcopy
    c=deepcopy(certificate);r=c['report'];events=c['events'];encoding=events[0]
    active=next(e for e in events if e['kind']=='active');point=next(e for e in events if e['kind']=='point')
    if fault=='count':r['count']+=1
    elif fault=='precision':r['precision']-=1
    elif fault=='unused':encoding['unused_variables']=0
    elif fault=='field':active['defining_polynomial']=256
    elif fault=='flags':r['source_qualified']=True
    elif fault=='configuration':c['configuration']['full_weighted_mode_domain']=True
    elif fault=='ledger':r['ledger']['calls']+=1
    elif fault=='trailing':events.append(deepcopy(events[-1]))
    elif fault=='truncated':events.pop()
    elif fault=='literal_sign':encoding['vertices'][0]['tensor']['positive'][0]=True
    elif fault=='creation_precision':encoding['vertices'][0]['tensor']['creation_precision']+=1
    elif fault=='endpoint':encoding['vertices'][1]['ports'][0]=encoding['vertices'][0]['ports'][0]
    elif fault=='normalized':encoding['clauses'][0]=[1]
    elif fault=='wire_cap':encoding['wires']=9
    elif fault=='original_bool':c['formula']['clauses'][0][0]=True
    elif fault in ('leaf','point','recovered'):
        event=next(e for e in events if e['kind']==fault);value=[list(row) for row in event['result']];value[0][0]^=1;event['result']=value
    elif fault=='padding':active['padded_height']+=2
    elif fault=='labels':active['labels'][0]['word']=(1,)
    elif fault=='variance':active['variance_scaled']+=1
    elif fault=='support':point['zero_certificate']['eligible_modes']=[]
    elif fault=='capacity':point['zero_certificate']['target_capacities'][0][2]+=1
    elif fault=='formal_size':point['zero_certificate']['formal_mode_count']+=1
    elif fault=='node_precision':point['precision']-=1
    elif fault=='unknown_fields':point['trusted']=True
    elif fault=='work_allowance':c['limits']['max_work']=1
    with pytest.raises(replay_module.ReplayError):replay_module.replay(c)


def test_independent_replay_resource_and_incomplete_refusals(replay_module,certificate):
    from copy import deepcopy
    with pytest.raises(replay_module.ReplayError,match='RESOURCE_LIMIT'):replay_module.replay(certificate,max_seconds=1e-30)
    c=deepcopy(certificate);c['report']['status']='INCONCLUSIVE_RESOURCE_LIMIT';c['report'].pop('count')
    with pytest.raises(replay_module.ReplayError,match='did not complete'):replay_module.replay(c)


def test_encoding_checker_handles_repeated_variable_tree(replay_module):
    from veritas.research.manuscript.model import ClauseTensor
    formula=Formula(2,((1,2),(1,-2))).normalize(Budget());encoded=cnf.encode(formula,Budget())
    vertices=[]
    for v in encoded.network.vertices:
        tensor=dict(kind='clause',positive=list(v.tensor.positive),creation_precision=encoded.precision) if type(v.tensor) is ClauseTensor else dict(kind='equality',arity=v.tensor.arity,creation_precision=encoded.precision)
        vertices.append(dict(side=v.side,identity=v.identity,ports=list(v.ports),tensor=tensor))
    event=dict(kind='encoding',n=2,clauses=[list(c) for c in formula.clauses],wires=encoded.network.wires,
               unused_variables=encoded.unused,precision=encoded.precision,vertices=vertices)
    graph,unused=replay_module.verify_encoding(dict(n=2,clauses=[list(c) for c in formula.clauses]),event)
    assert graph['wires']==8 and unused==0


def test_scalar_cnf_through_jet_ring_and_unpruned_failure():
    result=count_scaled_cnf(Formula(1,((1,),)),experiment=EXPERIMENT,ell=2,limits=Limits(max_work=100000000,max_seconds=120))
    assert result['status']=='PASS_EXACT_COUNT' and result['count']==1 and result['ell']==2
    refused=count_scaled_cnf(Formula(1,((1,),)),experiment=ScaledExperiment(),limits=Limits(max_work=1000))
    assert refused['status']=='INCONCLUSIVE_RESOURCE_LIMIT' and 'count' not in refused
