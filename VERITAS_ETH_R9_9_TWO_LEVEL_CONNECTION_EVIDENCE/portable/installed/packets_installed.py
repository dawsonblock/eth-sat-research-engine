"""External finite R9.9 component evidence, not source qualification."""
import argparse
import json
from pathlib import Path
from veritas.research.tapered_v4.provenance import source_binding
from dataclasses import replace

from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.eth_recursive_contraction_v39.described_network import describe_integer_network
from veritas.research.tensor import Factor, TensorNetwork
from veritas.research.parent_child_r98.model import (Budget, Policy, PacketLayout, ModeSet, ExponentTuple,
                                                    Refusal, canonical, from_described)
from veritas.research.parent_child_r98.constructor import construct_children
from veritas.research.parent_child_r98.engine import leaf
from veritas.research.parent_child_r98.packing import construct_layout, audit_layout
from veritas.research.parent_child_r98.shrinking_oracle import parent_point
from veritas.research.parent_child_r99 import (build_packet_modes, verify_packet_modes,
    evaluate_packet_point, verify_packet_term, contract_packet_recursion)
from veritas.research.parent_child_r99.recovery import make_packet_plan, packet_points, recover_packet_grid


def fixture(cross=True, u=1, degree=4):
    net = TensorNetwork(2, tuple(Factor((e,), values, side+str(e))
                                for e in range(2) for side, values in (("row:",(1,3)),("col:",(2,5)))))
    p = from_described(describe_integer_network(net, creation_precision=5,
                                               defining_polynomial=first_irreducible(degree)), root_s=16, precision=5)
    l = construct_layout(p, a=2, u=u, budget=Budget())
    src = l.source
    src['row_labels'] = {'0':[0,0], '1':[0,0]}
    src['column_labels'] = {'0':[int(cross),0], '1':[int(cross),0]}
    src['H_pad'] = 4
    src['packets'] = [{'symbol_pairs':[[0,int(cross)],[0,0]], 'index':0, 'occupied_slots':[[0,0],[2,1]]}]
    l = PacketLayout(p.content_digest, 2, u, canonical(src))
    audit_layout(p,l)
    return p,l



def run():
    p,l=fixture(u=2); b=Budget()
    m=build_packet_modes(p,l,1,(1 << 40,0,0,0),budget=b)
    verification=verify_packet_modes(p,l,m,budget=b)
    betas=[]
    for exponent in (0,1,2):
        values=[0]*len(m.certificate['modes']);values[0]=exponent
        beta=ExponentTuple(m.content_digest,tuple(values))
        children=construct_children(p,l,m,beta,budget=b,_admitted=True)
        ar=JetRing(ExtensionRing(m.certificate['precision'],p.defining_polynomial),1)
        value=ar.one
        for child in children:value=ar.mul(value,leaf(child.as_parent(p),b))
        checked=verify_packet_term(p,l,m,beta,children,value,budget=b)
        assert checked['status']=='PASS_FINITE_GENERAL_PACKET_COEFFICIENT',checked
        betas.append({'exponent':exponent,'value':value,'status':checked['status']})
    assert betas[2]['value']!=ar.zero
    p2,l2=fixture(cross=False,u=2);plan=make_packet_plan(p2,l2,budget=b);rows=[]
    for t,z,precision in packet_points(p2,l2,plan,budget=b):
        modes=build_packet_modes(p2,l2,t,z,budget=b)
        value=evaluate_packet_point(p2,l2,modes,budget=b)
        assert value==parent_point(p2,l2,modes,budget=b)
        rows.append([t,list(z),precision,list(value[0])])
    result,cert=recover_packet_grid(p2,l2,rows,budget=b)
    assert result==((1,0,0,0),)
    return {'status':'PASS_BOUNDED_GENERAL_PACKET_COMPONENTS',
            'implementation_source_sha256':source_binding()['digest'],
            'source_qualified':False,'two_active_shrinking_levels':'NOT_ESTABLISHED',
            'crossing_parent_digest':p.content_digest,'crossing_mode_count':len(m.certificate['modes']),
            'complete_weighted_tuple_count':m.certificate['mode_tuple_count'],
            'crossing_complete_point':'NOT_EVALUATED_TUPLE_BUDGET',
            'fixed_coefficients':betas,'mode_verification':verification,
            'multivaluation_recovery':{'point_count':len(rows),'valuations':sorted({n.valuation for n in plan.nodes}),
                                      'crossing_modes':0,'result':result,
                                      'certificate':json.loads(cert.payload)},
            'ledger':b.report()}

print(json.dumps(run()))
