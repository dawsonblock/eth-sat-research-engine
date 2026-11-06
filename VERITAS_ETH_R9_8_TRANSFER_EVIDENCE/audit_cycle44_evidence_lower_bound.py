"""Independent integer-polynomial lower bound for current transfer certificates.

Scope: the 44-edge connected cycle fixture, 64 first-fit groups, L=2,
creation p=128 and point p_t=2944, complete 133-point binary residue
order at each of t=-1,+1, and the CURRENT schema serializing every child
recipe in every local binary state. This is not a lower bound for a
deduplicated schema, a different ring, or an altered evidence policy.
"""
from hashlib import sha256
import json
from pathlib import Path

E, M, GROUPS, PRECISION, POINTS = 8, 44, 64, 2944, 133
CAP = 100_000_000

def gf2_remainder(poly, divisor):
    while poly and poly.bit_length() >= divisor.bit_length():
        poly ^= divisor << (poly.bit_length() - divisor.bit_length())
    return poly

def independently_irreducible(poly):
    if poly.bit_length() != E + 1 or not (poly & 1):
        return False
    for degree in range(1, E // 2 + 1):
        for low in range(1 << degree):
            if gf2_remainder(poly, (1 << degree) | low) == 0:
                return False
    return True

def add(*vectors):
    return [sum(values) for values in zip(*vectors)]

def scale(n, vector):
    return [n * value for value in vector]

def multiply(a, b, f):
    terms = [0] * (2 * E - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            terms[i + j] += x * y
    for k in range(len(terms) - 1, E - 1, -1):
        value = terms[k]
        for j in range(E):
            if (f >> j) & 1:
                terms[k - E + j] -= value
    return terms[:E]

def counts(f):
    total_by_node, max_abs = {}, 0
    for node in (-1, 1):
        count = 0
        for z in range(POINTS):
            v = [(z >> i) & 1 for i in range(E)]
            v2, v3 = multiply(v, v, f), None
            v3 = multiply(v2, v, f)
            # Exact integer identities before reduction modulo 2^p_t.
            w = add(scale(4 if node == -1 else -12, v),
                    scale(8 if node == -1 else -40, v2), scale(-32, v3))
            count += sum(x < 0 for x in w)
            max_abs = max(max_abs, *(abs(x) for x in w))
        total_by_node[str(node)] = count
    assert max_abs < 2**(PRECISION-4)
    return total_by_node, max_abs

# Independent projection of the fixed first-fit layout: all vertices have
# degree two and capacity floor(3*44/64)=2, so vertex i on either side is
# assigned to group i. Each original edge has distinct row/column owners.
assert 3*M//GROUPS == 2
row_owner, column_owner = {}, {}
for i in range(M // 2):
    for edge in (2*i, 2*i+1):
        assert edge not in row_owner
        row_owner[edge] = i
    for edge in (2*i+1, 2*((i+1) % (M//2))):
        assert edge not in column_owner
        column_owner[edge] = i
assert set(row_owner) == set(column_owner) == set(range(M))
incident = [0] * GROUPS
for edge in range(M):
    a,b = row_owner[edge],column_owner[edge]
    if a != b:
        incident[a] += 1
        incident[b] += 1
assert sorted(x for x in incident if x) == [2] * 22
local = sum(row_owner[e] == column_owner[e] for e in range(M))
cross = M - local
# Each mode appears in its target packet; each local edge appears in one
# local packet. Every active group has two incident mode bits and four
# serialized local states. Both packet recipes contain the same W value.
coefficient_copies_per_nonzero_point = sum(
    1 << incident[row_owner[edge]] for edge in range(M)
)
assert (local,cross,coefficient_copies_per_nonzero_point) == (22,22,176)
assert PRECISION % 4 == 0
hex_digits = PRECISION // 4
polynomials = [f for f in range(1 << E, 1 << (E + 1)) if independently_irreducible(f)]
assert len(polynomials) == 30 and min(polynomials) == 0x11b
results=[]
for f in polynomials:
    nodes,max_abs=counts(f)
    negative=sum(nodes.values())
    results.append({'polynomial_hex':hex(f),'negative_by_node':nodes,
                    'negative_coordinates':negative,'max_abs_integer_coordinate':max_abs,
                    'raw_hex_character_lower_bound':negative*coefficient_copies_per_nonzero_point*hex_digits})
results.sort(key=lambda row:(row['negative_coordinates'],row['polynomial_hex']))
first=next(row for row in results if row['polynomial_hex']=='0x11b')
assert first['negative_by_node']=={'-1':529,'1':520}
assert first['raw_hex_character_lower_bound']==135_883_264
assert results[0]['negative_coordinates']==851
assert results[0]['raw_hex_character_lower_bound']==110_235_136 > CAP
record={'schema':'VERITAS_R98_TRANSFER_CYCLE44_RAW_HEX_LOWER_BOUND_V1',
        'scope':'CURRENT_FULL_GRID_CHILD_SERIALIZATION_ONLY',
        'method':'INDEPENDENT_INTEGER_POLYNOMIAL_REDUCTION_AND_GF2_TRIAL_DIVISION',
        'fixture_edges':M,'groups':GROUPS,'local_packets':local,'cross_packets':cross,
        'states_per_active_group':4,'W_copies_per_nonzero_point':coefficient_copies_per_nonzero_point,
        'point_precision':PRECISION,'points_per_node':POINTS,'hex_digits_per_negative':hex_digits,
        'irreducible_polynomials_checked':len(polynomials),'first_irreducible':first,
        'minimum_over_degree8_polynomials':results[0],'all_degree8_results':results,
        'hard_uncompressed_byte_cap':CAP,'conclusion':'EXCEEDS_CAP_FOR_EVERY_DEGREE_8_BINARY_COEFFICIENT_IRREDUCIBLE',
        'exclusions':['does not rule out other extension degrees','does not rule out a deduplicated certificate schema',
                      'does not rule out a changed resource policy','not a source-regime complexity proof'],
        'script_sha256':sha256(Path(__file__).read_bytes()).hexdigest()}
out=Path(__file__).with_name('cycle44-evidence-lower-bound.json')
assert not out.exists(),'refuse to overwrite existing evidence'
out.write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':'PASS_INDEPENDENT_RAW_EVIDENCE_LOWER_BOUND',
                  'first_f_lower_bound':first['raw_hex_character_lower_bound'],
                  'best_degree8_lower_bound':results[0]['raw_hex_character_lower_bound'],
                  'output':str(out)}))
