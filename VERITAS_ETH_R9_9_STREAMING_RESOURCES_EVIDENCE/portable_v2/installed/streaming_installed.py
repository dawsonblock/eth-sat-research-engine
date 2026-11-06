from veritas.research.tensor import TensorNetwork, Factor
from veritas.research.eth_recursive_contraction_v39.described_network import describe_integer_network
from veritas.research.parent_child_r98.model import from_described, Budget
from veritas.research.parent_child_r98.packing import construct_layout
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.parent_child_r99.resources import prepare_scalar_field
from veritas.research.parent_child_r99.stream_engine import contract_streaming
from veritas.research.parent_child_r99.stream_verify import verify_streaming
from veritas.research.parent_child_r99.stream_recovery import StreamRecovery
from veritas.research.parent_child_r99.recovery import packet_points
net = TensorNetwork(2, tuple(Factor((i,), values, side+str(i)) for i in range(2)
                            for side,values in (('row:',(1,3)),('col:',(2,5)))))
p = from_described(describe_integer_network(net, creation_precision=5,
                    defining_polynomial=first_irreducible(4)), root_s=16, precision=5)
assert prepare_scalar_field(p,727).defining_polynomial.bit_length()-1 == 10
l = construct_layout(p,a=2,u=2,budget=Budget())
b=Budget(); r=StreamRecovery(p,l,budget=b); v=StreamRecovery(p,l,budget=b,independent=True)
for t,z,bits in packet_points(p,l,r.plan,budget=b):
    ar=ExtensionRing(bits,p.defining_polynomial)
    point=ar.add(ar.elem([t]),ar.mul(ar.elem([8]),z))
    value=ar.add(ar.elem([5]),ar.add(ar.mul(ar.elem([3]),point),ar.mul(ar.elem([2]),ar.mul(point,point))))
    r.add(t,z,bits,value);v.add(t,z,bits,value)
assert r.finish()==v.finish()==((5,0,0,0),)
events=[];report=contract_streaming(p,evidence_sink=events.append)
assert report['status']=='PASS_FINITE_STREAMED_TAPERED_RECURSION' and not report['source_tapered_functional_used']
assert verify_streaming(p,iter(events),report)['status']=='PASS_INDEPENDENT_STREAMED_RECURSION'
print('PASS_INSTALLED_STREAMING_RESOURCES')
