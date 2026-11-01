"""v3.4 independently replayable D.3 -> D.4.4 *structural* child topology.

This does NOT construct the paper's recursive child tensors or prove their
M/8 wire bound. It certifies the prerequisite real port distribution from an
independently checked D.3 packet schedule and, optionally, the exact endpoints
of checked finite geometric modes. A potential shrink of *real half-ports*
is explicitly distinguished from total child-network size (which includes
packet tensors and auxiliary mode connections).
"""
from __future__ import annotations
from collections import Counter
from copy import deepcopy
from veritas.research.eth_packing_v26.checker import verify_d3_packing
from veritas.research.eth_modes_v31.jet_tiles import check_jet_tile_modes, _v2

SCHEMA = 'VERITAS_ETH_STRUCTURAL_CHILD_TOPOLOGY_V34'
CLAIM = 'FINITE_D3_PORT_AND_MODE_INCIDENCE_LEDGER_ONLY'
SCOPE = {
    'd3_real_port_distribution_recomputed': True,
    'finite_mode_endpoint_incidence_checked': True,
    'exact_packet_slot_coverage_checked': True,
    'manuscript_recursive_child_tensors': False,
    'manuscript_m_over_8_child_wire_theorem': False,
    'subexponential_runtime_proven': False,
}


def _build(d3, mode_certificate, coordinate):
    result = verify_d3_packing(d3, check_trace=True)
    if result.get('valid') is not True:
        raise ValueError('D.3 packet certificate did not independently verify: '+str(result.get('reason')))
    r, a, M = d3['r'], d3['a'], d3['M']
    if type(coordinate) is not int or not 0 <= coordinate < a:
        raise ValueError('coordinate must be an integer in [0,a)')
    if M < 1:
        raise ValueError('requires at least one real edge')
    if mode_certificate is not None:
        checked = check_jet_tile_modes(mode_certificate)
        if checked.get('valid') is not True:
            raise ValueError('finite geometric-mode certificate did not verify: '+str(checked.get('reason')))
        if mode_certificate['d3_certificate'] != d3:
            raise ValueError('mode certificate is for a different D.3 packing')
        if _v2(mode_certificate['node']) != coordinate:
            raise ValueError('coordinate disagrees with mode node valuation')
    row = [[] for _ in range(r)]
    col = [[] for _ in range(r)]
    edge_to_groups = []
    for eid, (u,v) in enumerate(d3['edges']):
        row_group=d3['row_labels'][str(u)][coordinate]
        col_group=d3['column_labels'][str(v)][coordinate]
        row[row_group].append(eid)
        col[col_group].append(eid)
        edge_to_groups.append([row_group,col_group])
    packet_ledger=[]
    coverage=Counter()
    for pid, packet in enumerate(d3['packets']):
        real=[]
        for slot,eid in enumerate(packet['slots']):
            if eid is not None:
                coverage[eid]+=1
                real.append({'slot':slot,'edge':eid,
                    'row_group':edge_to_groups[eid][0],
                    'column_group':edge_to_groups[eid][1]})
        packet_ledger.append({'packet_id':pid,'real_slots':real,
                              'padding_slots':len(packet['slots'])-len(real)})
    if sorted(coverage.items()) != [(i,1) for i in range(M)]:
        raise ArithmeticError('real slot coverage mismatch')
    endpoints=[[] for _ in range(r)]
    mode_ledger=[]
    if mode_certificate is not None:
        for mid, mode in enumerate(mode_certificate['modes']):
            src=mode['source_group'];dst=mode['target_group'];w=mode['weight']
            if any(type(v) is not int for v in (src,dst,w)) or not (0<=src<r and 0<=dst<r and src!=dst and 1<=w<mode_certificate['precision']):
                raise ValueError('invalid mode endpoint or weight')
            endpoints[src].append(mid);endpoints[dst].append(mid)
            mode_ledger.append({'mode_id':mid,'source_group':src,
                'target_group':dst,'weight':w,'packet':mode['packet'],
                'tile_residue':mode['tile_residue'],
                'geometric_exponent':mode['exponent']})
    groups=[]
    for group in range(r):
        original_half_ports=len(row[group])+len(col[group])
        groups.append({'group':group,
            'row_edges':row[group], 'column_edges':col[group],
            'real_half_ports':original_half_ports,
            'incident_mode_ids':endpoints[group],
            'incident_mode_count':len(endpoints[group]),
            # This is a bound on ORIGINAL half-ports ONLY. Not total child wires.
            'original_half_ports_below_m_over_8':8*original_half_ports < M})
    max_row=max(map(len,row));max_col=max(map(len,col))
    half_bound=max_row*r<=3*M and max_col*r<=3*M
    if half_bound!=result['symbol_port_bound']:
        raise ArithmeticError('structural port bound disagrees with D.3 checker')
    finite_packing_bounds=result['finite_bounds_satisfied']
    source_assumptions=result['d6_numeric_preconditions_satisfied']
    return {
        'coordinate':coordinate,'radix':r,'original_wires':M,
        'groups':groups,'packet_real_slot_ledger':packet_ledger,
        'edge_to_groups':edge_to_groups,'mode_ledger':mode_ledger,
        'summary':{
            'max_real_row_ports':max_row,'max_real_column_ports':max_col,
            'max_original_half_ports':max(g['real_half_ports'] for g in groups),
            'total_original_half_ports':sum(g['real_half_ports'] for g in groups),
            'real_edge_coverage_exact':True,
            'finite_symbol_port_bound':half_bound,
            'finite_packet_bound':result['packing_count_bound'],
            'all_finite_packing_bounds':finite_packing_bounds,
            'manuscript_d6_numeric_preconditions':source_assumptions,
            'fixed_radix_64':r==64,
            'potential_original_half_port_shrink': all(g['original_half_ports_below_m_over_8'] for g in groups),
            'manuscript_parameter_gate':bool(r==64 and source_assumptions and finite_packing_bounds and result['potential_bound']),
            'actual_recursive_child_wires_verified':False,
            'm_over_8_child_wire_theorem_proven':False,
        }}


def construct_topology_certificate(d3, *, mode_certificate=None, coordinate=0):
    ledger=_build(d3,mode_certificate,coordinate)
    return {'schema':SCHEMA,'claim':CLAIM,'scope':deepcopy(SCOPE),
        'd3_certificate':deepcopy(d3),
        'mode_certificate':deepcopy(mode_certificate),
        **ledger}


def check_topology_certificate(cert):
    try:
        if not isinstance(cert,dict) or cert.get('schema')!=SCHEMA or cert.get('claim')!=CLAIM or cert.get('scope')!=SCOPE:
            raise ValueError('unsupported topology claim or schema')
        recomputed=construct_topology_certificate(cert['d3_certificate'],
            mode_certificate=cert['mode_certificate'],coordinate=cert['coordinate'])
        if cert!=recomputed:
            raise ValueError('topology ledger differs from independent reconstruction')
        return {'valid':True,'status':'FINITE_STRUCTURAL_CHILD_TOPOLOGY_CHECKED',
            'manuscript_m_over_8_child_wire_theorem':False,
            'subexponential_runtime_proven':False,
            'original_half_port_counts_checked':True,
            'mode_incidence_checked':cert['mode_certificate'] is not None}
    except (ValueError,KeyError,TypeError,IndexError,OverflowError,
            ArithmeticError,RuntimeError,ZeroDivisionError) as exc:
        return {'valid':False,'status':'INVALID_V34_TOPOLOGY_CERTIFICATE',
            'reason':str(exc)}
