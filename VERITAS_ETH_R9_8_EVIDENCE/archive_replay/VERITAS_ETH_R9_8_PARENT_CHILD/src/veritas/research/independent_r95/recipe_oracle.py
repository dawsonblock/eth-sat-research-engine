"""Independent entry/leaf oracle: integer polynomial reduction and elimination.

Does not import production recipes, ring arithmetic, child builders or the leaf
summation. Shared inputs are the documented wire schema and SourceNode data.
It is deliberately bounded and never supplies the production answer.
"""
import json
from itertools import product


class ReferenceLimit(ValueError): pass


class ReferenceArithmetic:
    def __init__(self,p,f,length,max_work):
        if type(p) is not int or not 1<=p<=1024 or type(f) is not int or not 1<=f.bit_length()-1<=64 or not 1<=length<=64:
            raise ValueError('unsupported reference ring')
        self.p=p;self.f=f;self.e=f.bit_length()-1;self.length=length;self.q=2**p
        self.maximum=max_work;self.used=0
        self.zero=tuple(tuple(0 for _ in range(self.e)) for _ in range(length))
        self.one=tuple(tuple(int(i==0 and j==0) for i in range(self.e)) for j in range(length))
    def tick(self,n=1):
        self.used+=n
        if self.used>self.maximum:raise ReferenceLimit('independent reference budget exhausted')
    def scalar(self,n):return ((n%self.q,)+(0,)*(self.e-1),)+self.zero[1:]
    def add(self,x,y):
        self.tick(self.e*self.length)
        return tuple(tuple((x[j][i]+y[j][i])%self.q for i in range(self.e)) for j in range(self.length))
    def neg(self,x):return tuple(tuple(-v%self.q for v in row) for row in x)
    def mul(self,x,y):
        terms={}
        for v in range(self.length):
            for w in range(self.length-v):
                for i in range(self.e):
                    for j in range(self.e):
                        self.tick()
                        key=(v+w,i+j);terms[key]=terms.get(key,0)+x[v][i]*y[w][j]
        # Integer polynomial long reduction, with no production ring primitive.
        for v in range(self.length):
            for k in range(2*self.e-2,self.e-1,-1):
                coefficient=terms.pop((v,k),0)
                for i in range(self.e):
                    if (self.f//2**i)%2:
                        key=(v,k-self.e+i);terms[key]=terms.get(key,0)-coefficient
        return tuple(tuple(terms.get((j,i),0)%self.q for i in range(self.e)) for j in range(self.length))
    def power(self,x,n):
        z=self.one
        for _ in range(n):z=self.mul(z,x)
        return z


def _entry(ref,bits,ar):
    ar.tick(len(ref.description)+1)
    p=json.loads(ref.description)
    if p.get('schema')!='VERITAS_SOURCE_ENTRY_V1':raise ValueError('unsupported reference schema')
    if (p['arity'],p['creation_precision'],p['polynomial'],p['jet_length'])!=(ref.arity,ref.creation_precision,ref.defining_polynomial,ref.jet_length):
        raise ValueError('reference metadata mismatch')
    if type(bits) is not tuple or len(bits)!=ref.arity or any(type(b) is not int or b not in (0,1) for b in bits):raise ValueError('invalid Boolean index')
    # Arithmetic at pc; the caller may subsequently multiply these unchanged
    # coordinate representatives at a larger precision.
    local=ReferenceArithmetic(ref.creation_precision,ref.defining_polynomial,ref.jet_length,ar.maximum-ar.used)
    kind,data=p['kind'],p['data']
    asjet=lambda x:tuple(tuple(row) for row in x)
    if kind=='dense':
        idx=sum(b*2**i for i,b in enumerate(reversed(bits)));result=asjet(data[idx])
    elif kind=='clause':result=local.scalar(int(any(bits[j]==data[j] for j in range(len(bits)))))
    elif kind=='equality':result=local.scalar(int(len(set(bits))==1))
    elif kind=='packet':
        rows,cols,coefficients,targets,sources=data
        if len(targets)>8 or len(rows)>8:raise ReferenceLimit('reference polynomial dimension cap')
        dim=len(targets);zero=(0,)*dim;poly={zero:local.one}
        # Materialize the full unpruned formal mode polynomial, unlike the
        # production selection stream. Requested coefficient is extracted last.
        for i,pos in enumerate(rows):
            c=local.zero
            for col,value in zip(cols,coefficients[i]):
                if bits[col]:c=local.add(c,asjet(value))
            if not bits[pos]:c=local.add(local.one,local.neg(c))
            factor={zero:c}
            for j,(_,values) in enumerate(targets):
                exponent=tuple(int(k==j) for k in range(dim));v=asjet(values[i])
                factor[exponent]=v if bits[pos] else local.neg(v)
            newer={}
            for left,x in poly.items():
                for right,y in factor.items():
                    z=tuple(a+b for a,b in zip(left,right));value=local.mul(x,y)
                    newer[z]=local.add(newer.get(z,local.zero),value)
            poly=newer
            if len(poly)>10000:raise ReferenceLimit('reference polynomial cap')
        result=poly.get(tuple(t[0] for t in targets),local.zero)
        for beta,values in sources:
            if not 0<=beta<=4096:raise ReferenceLimit('reference exponent cap')
            value=local.scalar(sum(bits[pos]*c for pos,c in zip(cols,values)))
            result=local.mul(result,local.power(value,beta))
    else:raise ValueError('unsupported reference kind')
    ar.tick(local.used)
    return result


def evaluate_reference(ref,bits,*,precision,max_work=2_000_000):
    if precision<ref.creation_precision:raise ValueError('decreased reference precision')
    ar=ReferenceArithmetic(precision,ref.defining_polynomial,ref.jet_length,max_work)
    return _entry(ref,bits,ar)


def contract_reference(node,*,max_edges=8,max_work=2_000_000):
    if node.edge_count>max_edges or max_edges>8 or len(node.vertices)>128:raise ReferenceLimit('reference graph cap')
    ar=ReferenceArithmetic(node.precision,node.context.defining_polynomial,node.context.jet_length,max_work)
    return contract_reference_factors(node.edge_count, [(v.ports, v.tensor) for v in node.vertices], ar)


def contract_reference_factors(edge_count, vertices, ar):
    """Contract supplied entry references with independent polynomial and bucket arithmetic."""
    if type(edge_count) is not int or not 0 <= edge_count <= 8 or len(vertices)>128:
        raise ReferenceLimit('reference graph cap')
    factors=[]
    for ports, ref in vertices:
        table={bits:_entry(ref,bits,ar) for bits in product((0,1),repeat=len(ports))}
        factors.append((ports,table))
    # Eliminate one edge at a time. This does not enumerate all parent-edge
    # assignments or call the production leaf executor.
    for edge in range(edge_count):
        incident=[f for f in factors if edge in f[0]]
        factors=[f for f in factors if edge not in f[0]]
        remaining=tuple(sorted(set().union(*(set(ports) for ports,_ in incident))-{edge}))
        table={}
        for bits in product((0,1),repeat=len(remaining)):
            values=dict(zip(remaining,bits));total=ar.zero
            for bit in (0,1):
                values[edge]=bit;term=ar.one
                for ports,entries in incident:term=ar.mul(term,entries[tuple(values[p] for p in ports)])
                total=ar.add(total,term)
            table[bits]=total
        factors.append((remaining,table))
    result=ar.one
    for ports,entries in factors:
        if ports:raise ValueError('uneliminated edge')
        result=ar.mul(result,entries[()])
    return result
