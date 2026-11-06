"""Independent evidence lower bounds for the first irreducible fields e=8..12."""
from hashlib import sha256
from pathlib import Path
import json

def rem(a,b):
    while a and a.bit_length()>=b.bit_length(): a ^= b << (a.bit_length()-b.bit_length())
    return a
def irreducible(f,e):
    return all(rem(f,(1<<d)|v)!=0 for d in range(1,e//2+1) for v in range(1<<d))
def first(e):
    return next(f for f in range((1<<e)+1,1<<(e+1),2) if irreducible(f,e))
def negative_count(e,f):
    def mul(a,b):
        c=[0]*(2*e-1)
        for i,x in enumerate(a):
            for j,y in enumerate(b): c[i+j]+=x*y
        for k in range(len(c)-1,e-1,-1):
            for j in range(e):
                if (f>>j)&1: c[k-e+j]-=c[k]
        return c[:e]
    counts={}
    for t in (-1,1):
        n=0
        for z in range(133):
            a=[(z>>i)&1 for i in range(e)]; a2=mul(a,a); a3=mul(a2,a)
            w=[(4 if t==-1 else -12)*x+(8 if t==-1 else -40)*y-32*z for x,y,z in zip(a,a2,a3)]
            assert all(abs(v)<2**2940 for v in w)
            n+=sum(v<0 for v in w)
        counts[str(t)]=n
    return counts
results=[]
for e in range(8,13):
    f=first(e);counts=negative_count(e,f);lower=sum(counts.values())*176*736
    assert lower>100_000_000
    results.append({"degree":e,"first_irreducible_hex":hex(f),"negative_by_node":counts,"raw_hex_character_lower_bound":lower})
out=Path(__file__).with_name("cycle44-first-fields-lower-bound.json")
assert not out.exists()
out.write_text(json.dumps({"schema":"VERITAS_R98_CYCLE44_FIRST_FIELDS_EVIDENCE_LOWER_BOUND_V1","scope":"first irreducible field at each supported degree 8..12, current child-serialization schema only","results":results,"script_sha256":sha256(Path(__file__).read_bytes()).hexdigest(),"excludes":"other irreducibles at degrees 9..12, deduplication, and changed policy"},indent=2)+"\n")
print(json.dumps({"status":"PASS", "output":str(out), "degrees":len(results)}))
