"""v3.4 verified finite packing->mode-bond->recursive-contraction bridge.

This composes existing *finite exact* implementations and checks their edge,
mode, and owned-half-bit indexing agrees. It does not implement the special
D.4.4 shrinking child packet tensors or their complexity proof.
"""
from __future__ import annotations
from veritas.research.eth_modes_v31.jet_tiles import check_jet_tile_modes,_v2
from veritas.research.eth_recursion_v30.implicit_children import make_bipartite_edges
from veritas.research.eth_recursive_bonds_v33.recursive import (
    construct_recursive_certificate,check_recursive_certificate)
from .topology import construct_topology_certificate,check_topology_certificate

SCHEMA='VERITAS_ETH_STRUCTURAL_FINITE_CONTRACTION_V34'
CLAIM='STRUCTURE_BOUND_FINITE_EXACT_CONTRACTION_ONLY'
SCOPE={'d3_port_and_mode_bridge_checked':True,
       'v33_finite_recursive_bond_contraction_checked':True,
       'manuscript_recursive_packet_tensors':False,
       'm_over_8_child_wire_bound_proven':False,
       'subexponential_runtime_proven':False}


def _verify_link(topology,recursive):
    if topology['mode_certificate']!=recursive['mode_certificate']:
        raise ValueError('mode certificate changed between topology and contraction')
    if topology['d3_certificate']['edges']!=recursive['mode_certificate']['d3_certificate']['edges']:
        raise ValueError('D.3 edge mismatch')
    M=topology['original_wires']
    actual={c['group']:c for c in recursive['child_descriptions']}
    if len(actual)!=len(recursive['child_descriptions']):
        raise ValueError('duplicate group child')
    for g in topology['groups']:
        child=actual.get(g['group'])
        expected=set(g['row_edges'])|{M+k for k in g['column_edges']}
        if child is None:
            if expected or g['incident_mode_ids']:
                raise ValueError('missing group tensor for nonempty group')
            continue
        if set(child['owned_halfbits'])!=expected or len(child['owned_halfbits'])!=len(expected):
            raise ValueError('group tensor half-bits disagree with D.3 labels')
        if sorted(child['mode_indices'])!=sorted(g['incident_mode_ids']):
            raise ValueError('group mode bonds disagree with checked geometric modes')
    if set(actual) - {g['group'] for g in topology['groups']}:
        raise ValueError('unexpected symbol-group tensor')
    return {'port_index_bridge':True,'mode_bond_bridge':True,
            'group_tensors_checked':len(actual),
            'actual_recursive_child_wires_verified':False}


def construct_integrated_certificate(net, mode_certificate, *,max_work=150000,
                                     max_entries=3000,max_cache=10000,max_depth=64,timeout_s=10):
    if check_jet_tile_modes(mode_certificate).get('valid') is not True:
        raise ValueError('unverified geometric-mode certificate')
    d3=mode_certificate['d3_certificate']
    if make_bipartite_edges(net)!=d3['edges']:
        raise ValueError('network differs from D.3 packing')
    topology=construct_topology_certificate(d3,mode_certificate=mode_certificate,
                                           coordinate=_v2(mode_certificate['node']))
    recursive=construct_recursive_certificate(net,mode_certificate,max_work=max_work,
        max_entries=max_entries,max_cache=max_cache,max_depth=max_depth,timeout_s=timeout_s)
    link=_verify_link(topology,recursive)
    return {'schema':SCHEMA,'claim':CLAIM,'scope':dict(SCOPE),
            'topology_certificate':topology,'recursive_certificate':recursive,
            'structural_link':link,'result':recursive['result']}


def check_integrated_certificate(cert, *,max_work=150000,max_entries=3000,
                                 max_cache=10000,max_depth=64,timeout_s=10):
    try:
        if not isinstance(cert,dict) or cert.get('schema')!=SCHEMA or cert.get('claim')!=CLAIM or cert.get('scope')!=SCOPE:
            raise ValueError('invalid composite claim/scope/schema')
        if not check_topology_certificate(cert['topology_certificate']).get('valid'):
            raise ValueError('invalid topology certificate')
        if not check_recursive_certificate(cert['recursive_certificate'],max_work=max_work,
             max_entries=max_entries,max_cache=max_cache,max_depth=max_depth,timeout_s=timeout_s).get('valid'):
            raise ValueError('invalid exact recursive certificate')
        link=_verify_link(cert['topology_certificate'],cert['recursive_certificate'])
        if link!=cert['structural_link'] or cert['result']!=cert['recursive_certificate']['result']:
            raise ValueError('composite result/link changed')
        return {'valid':True,'status':'STRUCTURE_BOUND_FINITE_EXACT_CONTRACTION_VERIFIED',
            'manuscript_m_over_8_child_wire_bound_proven':False,
            'subexponential_runtime_proven':False}
    except (ValueError,KeyError,TypeError,IndexError,OverflowError,
            ArithmeticError,RuntimeError,ZeroDivisionError) as exc:
        return {'valid':False,'status':'INVALID_V34_INTEGRATED_CERTIFICATE',
                'reason':str(exc)}
