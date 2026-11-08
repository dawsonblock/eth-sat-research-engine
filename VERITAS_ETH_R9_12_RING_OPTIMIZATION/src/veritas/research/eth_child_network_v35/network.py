"""v3.5 explicit finite child factor scopes, independent replay and budget gates.

Constructs a concrete finite *mode-bond child* network from v3.4's checked
D.3 topology and v3.3's exact group tensors. Counts every owned half-edge
bit and cross-group mode index, and refuses budgets exceeding resource caps.

These scopes are NOT the manuscript D.4.4 child packet-tensor wire counts.
No statement about subexponential complexity or M/8 for the manuscript.
"""
from __future__ import annotations
from copy import deepcopy
from collections import Counter
from veritas.research.eth_child_topology_v34.pipeline import (
    construct_integrated_certificate, check_integrated_certificate)
from veritas.research.eth_child_topology_v34.topology import construct_topology_certificate
from veritas.research.eth_modes_v31.jet_tiles import _v2
from veritas.research.eth_recursion_v30.implicit_children import (
    _deserialize_net, make_bipartite_edges)

SCHEMA='VERITAS_ETH_EXPLICIT_FINITE_CHILD_SCOPES_V35'
CLAIM='FINITE_MODE_BOND_CHILD_FACTOR_SCOPES_WITH_RESOURCE_GATES_ONLY'
SCOPE={
  'all_original_owned_halfbits_counted':True,
  'all_finite_geometric_mode_bonds_counted':True,
  'every_factor_original_port_scope_checked':True,
  'finite_child_scope_budget_enforced':True,
  'independent_source_replay_and_exact_contraction':True,
  'manuscript_D44_packet_tensors':False,
  'manuscript_M_over_8_full_child_bound':False,
  'subexponential_time_proven':False,
}
class ChildScopeBudgetExceeded(RuntimeError):pass


def _model(integrated,max_child_scope):
    if type(max_child_scope) is not int or not 1<=max_child_scope<=256:
        raise ValueError('max_child_scope must be an integer in 1..256')
    topo=integrated['topology_certificate']; rec=integrated['recursive_certificate']
    net=_deserialize_net(rec['network']); M=net.edges
    if make_bipartite_edges(net)!=topo['d3_certificate']['edges']:
        raise ValueError('network and packing endpoints differ')
    bygroup={g['group']:g for g in topo['groups']}
    old={c['group']:c for c in rec['child_descriptions']}
    if len(old)!=len(rec['child_descriptions']):
        raise ValueError('duplicate child group')
    factors=[]
    for f in net.factors:
        try:role,vertex=f.label.split(':',1)
        except ValueError as exc:raise ValueError('factor missing vertex label') from exc
        if role in ('row','clause'):
            group=topo['d3_certificate']['row_labels'].get(vertex,[0]*topo['d3_certificate']['a'])[topo['coordinate']]
            scope=list(f.ports)
        elif role in ('col','variable'):
            group=topo['d3_certificate']['column_labels'].get(vertex,[0]*topo['d3_certificate']['a'])[topo['coordinate']]
            scope=[M+v for v in f.ports]
        else:raise ValueError('unexpected original factor role')
        if any(not 0<=v<2*M for v in scope):raise ValueError('factor out of range')
        if any(v not in set(bygroup[group]['row_edges']+[M+j for j in bygroup[group]['column_edges']]) for v in scope):
            raise ValueError('original factor crosses purported group boundary')
        factors.append({'label':f.label,'group':group,'owned_halfbits':scope,
                        'arity':len(scope),'table_entries':len(f.table)})
    result=[];all_owned=[];all_modes=[];max_scope=0
    for group,source in sorted(bygroup.items()):
        owned=sorted(source['row_edges']+[M+v for v in source['column_edges']])
        modes=sorted(source['incident_mode_ids'])
        child=old.get(group)
        if child is None:
            if owned or modes:raise ValueError('nonempty group has no exact child tensor')
            entry_count=0
        else:
            if sorted(child['owned_halfbits'])!=owned or sorted(child['mode_indices'])!=modes:
                raise ValueError('finite child differs from exact group tensor')
            entry_count=len(child['entries'])
        scope_size=len(owned)+len(modes)
        if scope_size>max_child_scope:
            raise ChildScopeBudgetExceeded(f'finite group {group} has scope {scope_size} > {max_child_scope}')
        max_scope=max(max_scope,scope_size)
        all_owned.extend(owned);all_modes.extend(modes)
        result.append({'group':group,'owned_halfbit_indices':owned,
                       'mode_bond_indices':modes,
                       'finite_scope_indices':[['bit',v] for v in owned]+[['mode',v] for v in modes],
                       'owned_original_halfbit_count':len(owned),
                       'incident_mode_bond_count':len(modes),
                       'finite_child_scope_size':scope_size,
                       'exact_sparse_group_tensor_entries':entry_count,
                       'original_factor_labels':[f['label'] for f in factors if f['group']==group],
                       'scope_below_m_over_8_observed':8*scope_size<M})
    if sorted(all_owned)!=list(range(2*M)):
        raise ValueError('original halfbits are missing or multiply owned')
    mode_counts=Counter(all_modes)
    if mode_counts!=Counter({j:2 for j in range(len(topo['mode_ledger']))}):
        raise ValueError('each mode bond must have precisely two group incidences')
    for j,mode in enumerate(topo['mode_ledger']):
        if j not in result[mode['source_group']]['mode_bond_indices'] or j not in result[mode['target_group']]['mode_bond_indices']:
            raise ValueError('source/target mode endpoints do not agree with group scopes')
    return {'original_wire_count':M,'finite_group_count':len(result),
        'original_vertex_factors':factors,'children':result,
        'mode_bonds':[{'index':j,'source':m['source_group'],'target':m['target_group'],
                       'weight':m['weight']} for j,m in enumerate(topo['mode_ledger'])],
        'summary':{'original_halfbit_count':len(all_owned),
                   'total_finite_mode_bond_incidences':len(all_modes),
                   'mode_bond_count':len(mode_counts),
                   'max_finite_child_scope_size':max_scope,
                   'max_child_scope_budget':max_child_scope,
                   'all_finite_scopes_below_m_over_8_observed':all(8*c['finite_child_scope_size']<M for c in result),
                   'manuscript_D44_child_wire_bound_verified':False,
                   'subexponential_runtime_proven':False}}


def construct_child_network_certificate(net,mode_certificate,*,max_child_scope=64,
    max_work=150000,max_entries=3000,max_cache=10000,max_depth=64,timeout_s=10):
    # Cheap finite structural preflight runs before expensive exact group tables.
    if type(max_child_scope) is not int or not 1<=max_child_scope<=256:
        raise ValueError('max_child_scope must be an integer in 1..256')
    topology=construct_topology_certificate(mode_certificate['d3_certificate'],
        mode_certificate=mode_certificate,coordinate=_v2(mode_certificate['node']))
    for g in topology['groups']:
        forecast=g['real_half_ports']+g['incident_mode_count']
        if forecast>max_child_scope:
            raise ChildScopeBudgetExceeded(f'finite group {g["group"]} preflight scope {forecast} > {max_child_scope}')
    integrated=construct_integrated_certificate(net,mode_certificate,max_work=max_work,
        max_entries=max_entries,max_cache=max_cache,max_depth=max_depth,timeout_s=timeout_s)
    model=_model(integrated,max_child_scope)
    return {'schema':SCHEMA,'claim':CLAIM,'scope':deepcopy(SCOPE),
        'max_child_scope':max_child_scope,'integrated_certificate':integrated,
        'model':model,'result':deepcopy(integrated['result'])}


def check_child_network_certificate(cert,*,max_work=150000,max_entries=3000,
        max_cache=10000,max_depth=64,timeout_s=10):
    try:
        if not isinstance(cert,dict) or cert.get('schema')!=SCHEMA or cert.get('claim')!=CLAIM or cert.get('scope')!=SCOPE:
            raise ValueError('invalid schema, scope or mathematical claim')
        valid=check_integrated_certificate(cert['integrated_certificate'],
            max_work=max_work,max_entries=max_entries,max_cache=max_cache,
            max_depth=max_depth,timeout_s=timeout_s)
        if valid.get('valid') is not True:
            raise ValueError('underlying independent exact contraction replay failed: '+str(valid.get('reason')))
        expect=_model(cert['integrated_certificate'],cert['max_child_scope'])
        if expect!=cert['model'] or cert['result']!=cert['integrated_certificate']['result']:
            raise ValueError('child graph model or result differs from source replay')
        return {'valid':True,'status':'FINITE_CHILD_SCOPE_AND_EXACT_CONTRACTION_REPLAYED',
            'manuscript_D44_packet_tensors':False,'manuscript_M_over_8_wire_theorem':False,
            'subexponential_runtime_proven':False}
    except (TypeError,ValueError,KeyError,IndexError,ArithmeticError,
            RuntimeError,OverflowError,TimeoutError,ZeroDivisionError) as exc:
        return {'valid':False,'status':'INVALID_V35_CHILD_CERTIFICATE','reason':str(exc)}
