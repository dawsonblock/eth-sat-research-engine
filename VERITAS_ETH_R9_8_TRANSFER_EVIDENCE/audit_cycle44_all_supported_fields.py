"""Exhaustive independent lower bound for the currently supported fields.

For the 44-edge/64-group connected fixture, the current residue grid picks
integer bit-vector lifts 0..132 at each of t=-1,+1. Every active group has two
incident modes; target/local singleton recipes repeat W in four child states,
for 176 copies per nonzero point. This examines e=8..12 and every monic
irreducible binary polynomial of each degree using independent trial division.
It bounds only raw hex bodies in the CURRENT serialized-child schema; it says
nothing about other grids, larger e, deduplication or different resource policy.
"""
from hashlib import sha256
import json
from pathlib import Path

P, POINTS, W_COPIES, CAP = 2944, 133, 176, 100_000_000
EXPECTED = {8:30, 9:56, 10:99, 11:186, 12:335}

def rem(a,b):
    while a and a.bit_length() >= b.bit_length():
        a ^= b << (a.bit_length() - b.bit_length())
    return a

def irreducible(f,e):
    if f.bit_length() != e+1 or not f & 1:
        return False
    return all(rem(f,(1 << d) | low) != 0
               for d in range(1,e//2+1) for low in range(1 << d))

def counts(e,f):
    def multiply(a,b):
        values=[0]*(2*e-1)
        for i,x in enumerate(a):
            for j,y in enumerate(b):
                values[i+j] += x*y
        for k in range(len(values)-1,e-1,-1):
            coeff=values[k]
            for j in range(e):
                if (f >> j) & 1:
                    values[k-e+j] -= coeff
        return values[:e]
    nodes={}; max_abs=0
    for t in (-1,1):
        negative=0
        for z in range(POINTS):
            vector=[(z >> i) & 1 for i in range(e)]
            square=multiply(vector,vector); cube=multiply(square,vector)
            coefficients=[(4 if t==-1 else -12)*a + (8 if t==-1 else -40)*b -32*c
                          for a,b,c in zip(vector,square,cube)]
            negative += sum(x < 0 for x in coefficients)
            max_abs=max(max_abs,*(abs(x) for x in coefficients))
        nodes[str(t)]=negative
    assert max_abs < 2**(P-4)
    return nodes,max_abs

results=[]
for e in range(8,13):
    fields=[]
    for f in range(1 << e,1 << (e+1)):
        if irreducible(f,e):
            nodes,max_abs=counts(e,f)
            negative=sum(nodes.values())
            fields.append({'f':hex(f),'negative_coordinates_by_node':nodes,
                           'max_abs_integer_coordinate':max_abs,
                           'hex_character_lower_bound':negative*W_COPIES*(P//4)})
    assert len(fields)==EXPECTED[e]
    minimum=min(fields,key=lambda row:(row['hex_character_lower_bound'],row['f']))
    assert minimum['hex_character_lower_bound']>CAP
    results.append({'degree':e,'fields_checked':len(fields),'minimum':minimum,'fields':fields})
record={'schema':'VERITAS_R98_CYCLE44_ALL_SUPPORTED_FIELDS_LOWER_BOUND_V1',
        'method':'INDEPENDENT_GF2_TRIAL_DIVISION_AND_INTEGER_POLYNOMIAL_REDUCTION',
        'scope':'CURRENT_SERIALIZED_CHILD_SCHEMA_AND_FIRST_133_BINARY_RESIDUE_LIFTS',
        'precision':P,'nodes':[-1,1],'points_per_node':POINTS,'W_copies_per_nonzero_point':W_COPIES,
        'hard_uncompressed_byte_cap':CAP,'results':results,
        'exclusions':['other interpolation grids','extension degree >12','deduplicated certificate schema','changed resource policy','source-regime complexity'],
        'script_sha256':sha256(Path(__file__).read_bytes()).hexdigest()}
out=Path(__file__).with_name('cycle44-all-supported-fields-lower-bound.json')
assert not out.exists(),'refuse overwrite'
out.write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':'PASS','fields_checked':sum(r['fields_checked'] for r in results),
                  'minima':[(r['degree'],r['minimum']['f'],r['minimum']['hex_character_lower_bound']) for r in results],
                  'output':str(out)}))
