from pathlib import Path
import json,collections,hashlib
base=Path(__file__).resolve().parent
source=json.loads((base/'environment.json').read_text())['checker_source_sha256']

def read(path):return json.loads(path.read_text())

def summarize(folder):
 r=read(folder/'report.json');ledger=r['ledger'];counts=collections.Counter();sizes=collections.Counter()
 stream=folder/'events.jsonl'
 if stream.exists():
  with stream.open('rb') as f:
   for line in f:
    event=json.loads(line);counts[event['kind']]+=1;sizes[event['kind']]+=len(line)
 data={'status':r['status'],'reason':r.get('reason'),'resource_failure':r.get('resource_failure'),
       'ledger':ledger,'event_counts':dict(counts),'event_bytes_by_kind':dict(sizes),
       'written_stream_bytes':sum(sizes.values()),'result_returned':'result' in r,
       'active_calls_by_depth':r.get('active_calls_by_depth'), 'cache':r.get('cache')}
 if r['status'].startswith('PASS_'):
  assert r['implementation_source_sha256']==source
  checked=read(folder/'verification.json');reference=read(folder/'reference.json')
  assert checked['status']=='PASS_INDEPENDENT_NUMERICAL_REPLAY'
  assert r['result']==checked['result']==reference['result']
  data['independent_replay']=checked['status'];data['reference_matches']=True
 else:
  assert 'result' not in r
 if (folder/'plan.json').exists():
  plan=read(folder/'plan.json');assert plan['implementation_source_sha256']==source
  data.update({k:plan[k] for k in ['root_expected_samples','root_nonconstant_rows','structurally_connected','constant_row_padding','driver_sha256']})
 return data

folders=['coupled_core','coupled_core_100mb','coupled_one_level','coupled_one_level_no_cache','fully_nonconstant_cycle']
folders += [f'sweep_shifted/b{b}' for b in [1,2,4,8,16,32,242]]
records={name:summarize(base/name) for name in folders}
# Independent runs, same deterministic input. Compare charged work, not wall-speed claims.
a=read(base/'coupled_one_level/report.json');b=read(base/'coupled_one_level_no_cache/report.json')
assert a['parent_digest']==b['parent_digest'] and a['result']==b['result']
assert b['cache']['hits']==0
result={'source_sha256':source,'measurement_scope':'FINITE_SHARED_HOST_POLICY_WORK_NOT_BIT_OPERATIONS',
        'experiments':records,'cache_ablation':{'same_exact_result':True,
        'cache_enabled_work_units':a['ledger']['work_units'],'cache_disabled_work_units':b['ledger']['work_units'],
        'cache_enabled_computations':a['ledger']['actual_calls'],'cache_disabled_computations':b['ledger']['actual_calls']}}
(base/'experiment_summary.json').write_text(json.dumps(result,indent=2))
print('Wrote finite experiment summary; no universal or performance qualification')
