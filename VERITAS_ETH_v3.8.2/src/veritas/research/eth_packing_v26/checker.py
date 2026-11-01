"""Independent D.3 certificate checker. No trust in reported scores or labels.

Reconstructs directed-class loads, validates uniform padding and *every* edge,
and checks the stated numerical inequalities with exact integers. For trace
validation it also recomputes the conditional expectation from scratch using a
separate equality-event formula.
"""
from __future__ import annotations
from collections import Counter
from itertools import product


def _failure(reason):
    return {'valid':False,'d6_numeric_preconditions_satisfied':False,
            'finite_bounds_satisfied':False,'status':'INVALID_CERTIFICATE','reason':reason}


def _expected_score(edges,partial,r,a,_budget=None):
    D=r**(2*a)
    score=D*len(edges)
    for i,(u,v) in enumerate(edges):
        for j in range(i):
            if _budget is not None: _budget.tick()
            w,z=edges[j]
            k=0;okay=True
            for d in range(a):
                for side,l,rgt in (('R',u,w),('C',v,z)):
                    if l==rgt:continue
                    x=partial.get((side,l,d));y=partial.get((side,rgt,d))
                    if x is not None and y is not None and x!=y:
                        okay=False;break
                    if x is None or y is None:k+=1
                if not okay:break
            if okay:score+=2*(D//(r**k))
    return score


def verify_d3_packing(cert,*,check_trace=True,max_trace_work=12_000_000,_budget=None):
    try:
        if _budget is not None: _budget.tick()
        if not isinstance(cert,dict) or cert.get('schema')!='VERITAS_ETH_D3_CERT_V1':
            raise ValueError('incorrect certificate schema')
        r,a,L,D,M,H,delta=(cert[x] for x in ('r','a','L','D','M','H_pad','delta'))
        if any(type(x) is not int for x in (r,a,L,D,M,H,delta)) or not(2<=r<=64 and 1<=a<=5 and L==1<<a and D==r**(2*a) and 0<=M<=4000 and H>=0 and H%L==0):
            raise ValueError('invalid packet parameters')
        if D>4096 or D*H//L>10000 or (M*M*a)>max_trace_work:
            raise ValueError('certificate exceeds verification resource budget')
        edges=cert['edges']
        if not isinstance(edges,list) or len(edges)!=M or any(not isinstance(x,list) or len(x)!=2 or any(type(v) is not int or v<0 for v in x) for x in edges):
            raise ValueError('invalid edges')
        row_ids={str(x[0]) for x in edges};col_ids={str(x[1]) for x in edges}
        row=cert['row_labels']; col=cert['column_labels']
        if not isinstance(row,dict) or not isinstance(col,dict) or set(row)!=row_ids or set(col)!=col_ids:
            raise ValueError('row/column vertex labeling mismatch')
        for labels in (row,col):
            for values in labels.values():
                if not isinstance(values,list) or len(values)!=a or any(type(v) is not int or not 0<=v<r for v in values):
                    raise ValueError('invalid label vector')
        actual_degree=max([0]+list(Counter(u for u,_ in edges).values())+list(Counter(v for _,v in edges).values()))
        if delta!=actual_degree:raise ValueError('incorrect maximum degree')
        directed=Counter((tuple(row[str(u)]),tuple(col[str(v)])) for u,v in edges)
        maxload=max(directed.values(),default=0)
        rounded=((maxload+L-1)//L)*L
        if H!=rounded:raise ValueError('nonminimal or incorrect uniform class padding')
        # Every directed class must have H slots, including classes with no real edges.
        if len(cert['packets'])!=D*H//L:raise ValueError('incorrect padded packet count')
        capacities=Counter(); seen=Counter()
        for packet in cert['packets']:
            if _budget is not None: _budget.tick()
            if not isinstance(packet,dict) or set(packet)!={'symbol_pairs','slots'}:
                raise ValueError('malformed packet')
            pairs=packet['symbol_pairs'];slots=packet['slots']
            if not isinstance(pairs,list) or len(pairs)!=a or not isinstance(slots,list) or len(slots)!=L:
                raise ValueError('incorrect packet dimensions')
            for pair in pairs:
                if not isinstance(pair,list) or len(pair)!=2 or any(type(z) is not int for z in pair) or not 0<=pair[0]<=pair[1]<r:
                    raise ValueError('invalid unordered symbol pair')
            for slot,eid in enumerate(slots):
                if _budget is not None: _budget.tick()
                expected_row=tuple(p[(slot>>d)&1] for d,p in enumerate(pairs))
                expected_col=tuple(p[1-((slot>>d)&1)] for d,p in enumerate(pairs))
                capacities[(expected_row,expected_col)]+=1
                if eid is None:continue
                if type(eid) is not int or not 0<=eid<M:raise ValueError('invalid wire ID')
                seen[eid]+=1
                u,v=edges[eid]
                if tuple(row[str(u)])!=expected_row or tuple(col[str(v)])!=expected_col:
                    raise ValueError('slot orientation does not match wire labels')
        if any(seen[i]!=1 for i in range(M)):
            raise ValueError('duplicated/missing wire')
        # Unused/padded classes must also occur H times. Count *all* r**2a classes.
        for rv in product(range(r),repeat=a):
            for cv in product(range(r),repeat=a):
                if _budget is not None: _budget.tick()
                if capacities[(rv,cv)]!=H:raise ValueError('directed-class padding is not uniform')
        sqsum=sum(v*v for v in directed.values())
        final_scaled=D*sqsum
        if cert['final_square_scaled']!=final_scaled:raise ValueError('false final potential')
        phi_scaled=final_scaled-M*M
        degree_bound=(phi_scaled<=2*M*delta*D)
        loads=[]
        for d in range(a):
            for sym in range(r):
                loads.extend((sum(row[str(u)][d]==sym for u,_ in edges),
                              sum(col[str(v)][d]==sym for _,v in edges)))
        max_port_load=max(loads,default=0)
        pcount=len(cert['packets'])
        packet_bound=pcount*L<=3*M
        port_bound=max_port_load*r<=3*M
        assumptions={'M_ge_2_D_squared_delta':M>=2*D*D*delta,
                     'M_ge_LD':M>=L*D,'2L_le_delta':2*L<=delta,
                     'D':D,'L':L,'delta':delta}
        if cert['hypotheses']!=assumptions:raise ValueError('false D.6 preconditions')
        initial=_expected_score(edges,{},r,a,_budget)
        if cert['initial_expected_square_scaled']!=initial:raise ValueError('incorrect initial expectation')
        nonincreasing=final_scaled<=initial
        trace=cert.get('conditional_expectation_steps')
        if check_trace:
            if not isinstance(trace,list) or len(trace)!=a*(len(row_ids)+len(col_ids)):
                # Explicit expression avoids cross-side vertex-ID merging.
                raise ValueError('wrong conditional-expectation trace length')
            if (len(trace)*max(1,M*M)*a)>max_trace_work:
                raise ValueError('certificate exceeds trace checking budget')
            partial={};last=initial
            required={('R',int(x),d) for x in row_ids for d in range(a)}|{('C',int(x),d) for x in col_ids for d in range(a)}
            for step in trace:
                if _budget is not None: _budget.tick()
                if not isinstance(step,dict) or set(step)!={'side','vertex','coordinate','symbol','expected_square_scaled'}:
                    raise ValueError('malformed trace step')
                side,v,d,s,claim=(step[x] for x in ('side','vertex','coordinate','symbol','expected_square_scaled'))
                key=(side,v,d)
                if key not in required or key in partial or type(s) is not int or not 0<=s<r or type(claim) is not int:
                    raise ValueError('invalid trace assignment')
                partial[key]=s
                exact=_expected_score(edges,partial,r,a,_budget)
                if exact!=claim or exact>last:raise ValueError('invalid conditional-expectation step')
                last=exact
            if set(partial)!=required or last!=final_scaled:
                raise ValueError('incomplete or incorrect trace')
            for v,lab in row.items():
                for d,x in enumerate(lab):
                    if partial[('R',int(v),d)]!=x:raise ValueError('trace row-label mismatch')
            for v,lab in col.items():
                for d,x in enumerate(lab):
                    if partial[('C',int(v),d)]!=x:raise ValueError('trace column-label mismatch')
        if not nonincreasing:raise ValueError('final potential exceeds unconditional expectation')
        bounds=packet_bound and port_bound
        eligible=all(assumptions[k] for k in ('M_ge_2_D_squared_delta','M_ge_LD','2L_le_delta'))
        # These are finite *per-instance* checks; not an asymptotic proof.
        return {'valid':True,'d6_numeric_preconditions_satisfied':eligible,
                'finite_bounds_satisfied':bounds,'packing_count_bound':packet_bound,
                'symbol_port_bound':port_bound,'potential_bound':degree_bound,
                'conditional_expectation_nonincreasing':nonincreasing,
                'packet_count':pcount,'H_pad':H,'directed_classes':D,
                'manuscript_fixed_radix':r==64,
                'max_port_load':max_port_load,'phi_scaled':phi_scaled,
                'status':'D3_FINITE_BOUNDS_CERTIFIED' if bounds and eligible and degree_bound else
                         'FINITE_PACKET_VALID_NOT_ALL_THEOREM_PRECONDITIONS'}
    except (ValueError,KeyError,TypeError,IndexError,OverflowError) as exc:
        return _failure(str(exc))
