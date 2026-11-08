"""Seeded finite D.3 differential structural verification, not theorem proof."""
import json,random,sys,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from veritas.research.eth_packing_v26 import construct_d3_packing,verify_d3_packing
from veritas.research.eth_packing_v26.expectation import expected_sq_load_scaled

rng=random.Random(2606)
results={'seed':2606,'cases':0,'trace_checked':0,'mutated_certificates_rejected':0,'theorem_numeric_cases':0,
         'claim':'SEEDED_FINITE_TESTS_NOT_AN_ASYMPTOTIC_PROOF'}
for i in range(150):
    a=rng.choice([1,2]);r=2
    row=rng.randint(1,7);col=rng.randint(1,7)
    m=rng.randint(0,22)
    edges=[(rng.randrange(row),rng.randrange(col)) for _ in range(m)]
    cert=construct_d3_packing(edges,r=r,a=a,max_work=3_000_000)
    check=verify_d3_packing(cert)
    assert check['valid'] and check['conditional_expectation_nonincreasing'],check
    assert check['packet_count']*cert['L']==cert['D']*cert['H_pad']
    results['cases']+=1;results['trace_checked']+=len(cert['conditional_expectation_steps'])
    if check['d6_numeric_preconditions_satisfied']:results['theorem_numeric_cases']+=1
    if cert['packets']:
        bad=copy.deepcopy(cert)
        bad['packets'][0]['slots'].append(None)
        assert not verify_d3_packing(bad)['valid']
        results['mutated_certificates_rejected']+=1
# Guarantee D.6 fixture with degree 4, r=2,a=1,D=4,M=128.
edges=[(u,(u+t)%32) for u in range(32) for t in range(4)]
verified=construct_d3_packing(edges,r=2,a=1,max_work=5_000_000,
                              require_theorem_preconditions=True)
r=verify_d3_packing(verified)
assert r['valid'] and r['d6_numeric_preconditions_satisfied'] and r['finite_bounds_satisfied']
results['theorem_numeric_cases']+=1
results['full_d3_example']={'M':len(edges),'delta':verified['delta'],
   'packet_count':len(verified['packets']),'H_pad':verified['H_pad'],'status':r['status']}
output=Path(__file__).resolve().parents[1]/'validation'/'v26_d3_validation.json'
output.parent.mkdir(exist_ok=True)
output.write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
