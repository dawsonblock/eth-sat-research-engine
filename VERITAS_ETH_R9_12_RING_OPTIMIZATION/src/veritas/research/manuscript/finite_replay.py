"""Independent oracle replay for the documented one-wire integration fixture.

No production tensor constructors, entry evaluators, packing, modes, traversal,
interpolation or Hermite implementation are imported. Kernel coefficients come
from rational polynomial multiplication; extension arithmetic uses the older,
separately implemented ExtensionRing. This checks every emitted point and the
final exhaustive integer answer, not a universal proof or a recursive certificate
for arbitrary networks. Structural counters are consistency checks, not proof.
"""
from fractions import Fraction
from math import comb, factorial
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing


class ReplayError(ValueError):
    pass


def _require(condition,message):
    if not condition:raise ReplayError(message)


def _multiply(left,right,ell):
    return [sum(left[j]*right[k-j] for j in range(k+1)) for k in range(ell)]


def _canonical(value,p,ell,e):
    _require(isinstance(value,(tuple,list)) and len(value)==ell,'bad jet shape')
    _require(all(isinstance(row,(tuple,list)) and len(row)==e and
                 all(type(c) is int and 0<=c<2**p for c in row) for row in value),
             'noncanonical extension result')
    return tuple(tuple(row) for row in value)


def replay(certificate):
    """Bounded, explicitly scoped verification; malformed input never passes."""
    _require(isinstance(certificate,dict),'certificate object required')
    _require(certificate.get('schema')=='VERITAS_SCALED_ONE_WIRE_V1','unsupported replay scope')
    fixture=certificate['fixture'];report=certificate['report'];events=certificate['events']
    _require(type(fixture['precision']) is int and fixture['precision']==2 and
             type(fixture['ell']) is int and fixture['ell'] in (1,2),'unsupported fixture ring')
    p=2;ell=fixture['ell'];e=4;f=19
    left,right=fixture['row'],fixture['column']
    _require(all(isinstance(table,(tuple,list)) and len(table)==2 and
                 all(isinstance(row,(tuple,list)) and len(row)==ell and
                     all(type(c) is int and 0<=c<4 for c in row) for row in table)
                 for table in (left,right)),'invalid canonical input tables')
    _require(report['status']=='PASS_EXPERIMENTAL_SCALED_RECURSION' and
             report['route']=='EXPERIMENTAL_SCALED_RECURSION','not completed scaled recursion')
    for key in ('source_qualified','executable_refinement_proven','complexity_proven'):
        _require(report.get(key) is False,'unauthorized qualification')
    expected_parameters=dict(s=2,C=1,lambda_value=1,extension_degree=4,
                             leaf_threshold=2,degree_limit=2)
    _require(report.get('parameters')==expected_parameters and
             all(type(value) is int for value in report['parameters'].values()),
             'schedule parameter metadata mismatch')
    expected_scaling=dict(a=1,u=1,radix=2,active_depth=1,column_label_shift=1,
        precision_policy='EXACT_HERMITE_FUNCTIONAL_DENOMINATOR_LOSS',
        stopping_rule='EXPLICIT_DEPTH_NOT_SOURCE_LEAF_THRESHOLD',
        full_padded_inventory=True,full_weighted_mode_domain=True,
        manuscript_packing_bounds_enforced=False,shrinking_children_certified=False)
    _require(report['experimental_scaling']==expected_scaling,'scaling metadata mismatch')
    _require(len(events)==10,'incomplete or extra root transcript')
    active=events[0]
    _require(active['kind']=='active' and active['depth']==0 and active['wires']==1 and
             active['precision']==2 and active['a']==active['u']==1 and active['radix']==2 and
             active['defining_polynomial']==19 and active['experiment_scaled'] is True,
             'active call metadata mismatch')
    expected_packets=[dict(pattern=[[0,0]],index=0,slots=[]),
                      dict(pattern=[[0,1]],index=0,slots=[[0,0]]),
                      dict(pattern=[[0,1]],index=1,slots=[]),
                      dict(pattern=[[1,1]],index=0,slots=[])]
    import json
    _require(json.loads(json.dumps(active['packets']))==expected_packets and
             active['padded_packets']==4,'full padded packet inventory mismatch')

    # Independent F(T)=A0(B0+B1)+(A1-A0)B1 W_00(T).
    # W_00(T) = product(T-r, r=-2,-1,1)/(-2), with W_00(0)=1.
    coefficients=[Fraction(1)]
    for root in (-2,-1,1):
        nxt=[Fraction(0)]*(len(coefficients)+1)
        for j,c in enumerate(coefficients):nxt[j]-=root*c;nxt[j+1]+=c
        coefficients=nxt
    coefficients=[c/(-factorial(2)*factorial(1)) for c in coefficients]
    base=_multiply(left[0],[a+b for a,b in zip(right[0],right[1])],ell)
    factor=_multiply([a-b for a,b in zip(left[1],left[0])],right[1],ell)
    # Two nodes +/-1, multiplicity 3. The independent functional at zero
    # has weights (1/2, +/-5/64, 1/128), so p+7=9 is sufficient.
    expected_points=[(t,index) for t in (-1,1) for index in range(4)]
    for event,(t,index) in zip(events[1:9],expected_points):
        _require(event['kind']=='point' and event['depth']==0 and event['wires']==1 and
                 event['t']==t and event['precision']==9 and event['multiplicity']==3,
                 'point metadata or completeness mismatch')
        z=tuple((index>>j)&1 for j in range(e))
        _require(tuple(event['zeta'])==z,'point ordering or coordinate mismatch')
        ring=ExtensionRing(9,f)
        shifted=[sum(c*comb(j,k)*t**(j-k)*4**k
                     for j,c in enumerate(coefficients) if j>=k)
                 for k in range(4)]
        kernel=ring.zero
        for value in reversed(shifted):
            _require(value.denominator&1,'nonintegral local kernel')
            scalar=value.numerator*pow(value.denominator,-1,512)%512
            kernel=ring.add(ring.mul(kernel,z),ring.elem([scalar]))
        expected=tuple(ring.add(ring.elem([a]),ring.mul(ring.elem([b]),kernel))
                       for a,b in zip(base,factor))
        _require(_canonical(event['result'],9,ell,e)==expected,'independent point value mismatch')
    integer=[0]*ell
    for bit in (0,1):
        integer=[a+b for a,b in zip(integer,_multiply(left[bit],right[bit],ell))]
    expected=tuple((value%4,0,0,0) for value in integer)
    _require(_canonical(report['result'],p,ell,e)==expected,'exhaustive root mismatch')
    last=events[-1]
    _require(last['kind']=='recovered' and last['depth']==0 and last['wires']==1 and
             _canonical(last['result'],p,ell,e)==expected,'recovered event mismatch')
    # Count full beta set independently via a generating function, not the
    # producer's lexicographic odometer. Four channels exist at every weight.
    counts=[1]+[0]*8
    for weight in range(1,9):
        for _ in range(4):
            for n in range(weight,9):counts[n]+=counts[n-weight]
    tuples=sum(counts)*8;leaves=tuples*2
    ledger=report['ledger']
    _require(ledger['exponent_tuples']==tuples and ledger['interpolation_points']==8 and
             ledger['calls']==leaves+1 and ledger['maximum_depth']==1,
             'recursive execution counters mismatch')
    _require(certificate['leaf_summary']=={'count':leaves,'depths':[1],'wire_counts':[1]},
             'child traversal summary mismatch')
    return dict(status='PASS_FINITE_SCALED_REPLAY',independent_integer_jet=integer,
                modular_jet=[x%4 for x in integer],checked_points=8,
                checked_formal_tuple_count=tuples,child_calls=leaves,
                source_qualified=False,executable_refinement_proven=False,complexity_proven=False,
                scope='ONE_WIRE_ONE_ACTIVE_LEVEL; point values and root independently recomputed')
