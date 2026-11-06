"""Complete finite crossing point, not full parent recovery or source recursion."""
import sys,json,time
from pathlib import Path
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_recursive_contraction_v39.described_network import describe_integer_network
from veritas.research.tensor import TensorNetwork,Factor
from veritas.research.parent_child_r98.model import *
from veritas.research.parent_child_r98.packing import construct_layout,audit_layout
from veritas.research.parent_child_r98.shrinking_oracle import parent_point
from veritas.research.parent_child_r99 import build_packet_modes,verify_packet_modes,evaluate_packet_point
from veritas.research.tapered_v4.provenance import source_binding
net=TensorNetwork(3,tuple(Factor((e,),v,s+str(e)) for e in range(3) for s,v in [('row:',(1,3)),('col:',(2,5))]))
import argparse
parser=argparse.ArgumentParser(description='Complete bounded general packet point; approximately 715200 child calls')
parser.add_argument('--output',required=True,type=Path)
args=parser.parse_args(); output=args.output.resolve(); root=Path(__file__).resolve().parents[1]
if output==root or root in output.parents:parser.error('evidence must be outside source tree')
if output.exists():parser.error('refusing to overwrite evidence')
p=from_described(describe_integer_network(net,creation_precision=5,defining_polynomial=first_irreducible(4)),root_s=16,precision=5)
policy=Policy(max_edges=8,max_tuples=100000,max_calls=1000000,max_work=1000000000,max_seconds=1200)
b=Budget(policy);l=construct_layout(p,a=3,u=3,budget=b);src=l.source
src['row_labels']={'0':[0,0,0],'1':[0,0,0],'2':[2,2,2]}
src['column_labels']={'0':[0,0,1],'1':[0,0,1],'2':[2,2,2]};src['H_pad']=8
src['packets']=[{'symbol_pairs':[[0,0],[0,0],[0,1]],'index':0,'occupied_slots':[[0,0],[2,1]]}, {'symbol_pairs':[[2,2],[2,2],[2,2]],'index':0,'occupied_slots':[[0,2]]}]
l=PacketLayout(p.content_digest,3,3,canonical(src));packing=audit_layout(p,l)
m=build_packet_modes(p,l,4,(1,0,0,0),budget=b)
print('inventory',len(m.certificate['modes']),m.certificate['mode_tuple_count'],flush=True)
start_binding=source_binding()['digest']
try:
 value=evaluate_packet_point(p,l,m,budget=b)
 oracle=parent_point(p,l,m,budget=b)
 assert value==oracle
 assert source_binding()['digest']==start_binding
 report={'status':'PASS_FINITE_GENERAL_MULTISLOT_COMPLETE_POINT','result':value,'full_weighted_tuples':m.certificate['mode_tuple_count'],'modes':m.certificate,'packing':packing,'parent_digest':p.content_digest,'source':start_binding,'source_qualified':False,'shrinking_transition':False,'active_shrinking_recursive_levels':0,'ledger':b.report()}
except (ValueError,RuntimeError,ArithmeticError) as exc:
 report={'status':getattr(exc,'status','INCONCLUSIVE'),'reason':str(exc),'ledger':b.report(),'source_qualified':False}
output.parent.mkdir(parents=True,exist_ok=True)
output.write_text(json.dumps(report,indent=2)+'\n')
print(report['status'],report['ledger'],flush=True)
