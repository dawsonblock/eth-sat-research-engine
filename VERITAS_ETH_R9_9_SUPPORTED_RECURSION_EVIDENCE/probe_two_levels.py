from veritas.research.tensor import TensorNetwork, Factor
from veritas.research.eth_recursive_contraction_v39.described_network import describe_integer_network
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.parent_child_r98.model import from_described, Policy, PacketLayout, canonical
from veritas.research.parent_child_r98.shrinking_layout import construct_vertex_shrinking_layout
from veritas.research.parent_child_r99.degree_engine import contract_supported_recursion
from pathlib import Path
M=484
net=TensorNetwork(M,tuple(Factor((e,),((1,3) if side=='row:' else (2,5)) if e==0 else (1,1),side+str(e)) for e in range(M) for side in ('row:','col:')))
from veritas.research.parent_child_r98.shrinking_cli import load_input
import json
inp=Path(__file__).parent/'two_level_matching484.json'
inp.write_text(json.dumps({'root_s':512,'precision':512,'extension_degree':4,'edges':M,'vertices':[{'side':side,'ports':[e],'table':((1,3) if side=='row' else (2,5)) if e==0 else (1,1)} for e in range(M) for side in ('row','column')]}))
p=load_input(inp)
def factory(call,a,u,budget):
 l=construct_vertex_shrinking_layout(call,budget=budget)
 if call.depth: return l
 s=l.source
 s['column_labels']['0'],s['column_labels']['22']=s['column_labels']['22'],s['column_labels']['0']
 counts={};packets=[]
 for e,(r,c) in enumerate(s['edges']):
  x,y=s['row_labels'][str(r)][0],s['column_labels'][str(c)][0];pair=(min(x,y),max(x,y));index=counts.get(pair,0);counts[pair]=index+1
  packets.append({'symbol_pairs':[list(pair)],'index':index,'occupied_slots':[[int(x>y),e]]})
 s['packets']=sorted(packets,key=lambda q:(q['symbol_pairs'],q['index']))
 return PacketLayout(call.content_digest,1,1,canonical(s),'balanced_vertices')
pol=Policy(max_edges=1024,max_precision=65536,max_work=1000000000,max_calls=2000000,max_seconds=3600,max_depth=4,max_certificate_bytes=100000000)
root=Path(__file__).parent
with (root/'probe_two_levels.events').open('wb') as out:
 r=contract_supported_recursion(p,layout_factory=factory,policy=pol,evidence_sink=lambda raw:out.write(raw+b'\n'))
print(r,flush=True)
if 'result' in r: assert r['result']==((17*2**483,0,0,0),)
(root/'probe_two_levels.json').write_bytes(canonical(r))
