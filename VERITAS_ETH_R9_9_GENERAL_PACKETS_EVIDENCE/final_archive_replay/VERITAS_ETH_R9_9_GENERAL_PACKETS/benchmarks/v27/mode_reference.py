"""Finite D.4.4 mode-validation costs; no claimed scaling beyond tested inputs."""
import json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from veritas.research.eth_packing_v26 import construct_d3_packing
from veritas.research.eth_modes_v27 import construct_tile_modes,verify_tile_modes
cases=[
 [[0,0],[1,1],[0,1],[1,0]],
 [[1,3],[2,2],[3,2],[0,3],[3,2],[1,1],[3,1],[2,2],[3,2],[0,2],[1,1],[3,3]],
]
results=[]
for edges in cases:
 a=1 if len(edges)==4 else 2
 start=time.perf_counter();d3=construct_d3_packing(edges,r=2,a=a)
 packed=time.perf_counter();cert=construct_tile_modes(d3,node=1,zeta=1,precision=5)
 built=time.perf_counter();res=verify_tile_modes(cert)
 checked=time.perf_counter()
 if not res['valid']:raise AssertionError(res)
 results.append({'wires':len(edges),'packets':len(d3['packets']),
 'modes':len(cert['modes']),'weighted_tuples':cert['mode_tuple_count'],
 'd3_seconds':round(packed-start,6),'mode_seconds':round(built-packed,6),
 'check_seconds':round(checked-built,6)})
print(json.dumps(results,indent=2))
