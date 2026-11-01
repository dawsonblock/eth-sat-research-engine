"""Reproducible performance diagnostic, not an ETH-runtime benchmark."""
import json,random,time,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from veritas.research.eth_packing_v26 import construct_d3_packing,verify_d3_packing
rng=random.Random(2626)
cases=[]
for m in (8,16,32,64,128):
    width=max(2,m//4)
    edges=[(rng.randrange(width),rng.randrange(width)) for _ in range(m)]
    t0=time.perf_counter()
    cert=construct_d3_packing(edges,r=2,a=1,max_work=6_000_000)
    t1=time.perf_counter()
    check=verify_d3_packing(cert)
    t2=time.perf_counter()
    assert check['valid']
    cases.append({'M':m,'r':2,'a':1,'packets':len(cert['packets']),
                  'H_pad':cert['H_pad'],'preconditions':check['d6_numeric_preconditions_satisfied'],
                  'finite_bounds':check['finite_bounds_satisfied'],
                  'construct_sec':round(t1-t0,6),'verify_sec':round(t2-t1,6)})
print(json.dumps({'seed':2626,'method':'finite D3 conditional expectation, Python',
      'note':'single process timing; not a proof of general speedup','cases':cases},indent=2))
