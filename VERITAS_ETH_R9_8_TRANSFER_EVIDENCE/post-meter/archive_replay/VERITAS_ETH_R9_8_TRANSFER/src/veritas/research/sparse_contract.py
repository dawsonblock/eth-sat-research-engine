"""Experimental exact sparse hash-join variable elimination.

Stores only nonzero factor rows; useful for equality-heavy networks. Unlike
indexed_contract it may be slower than dense elimination. Never approximate
counts and never declare a runtime advantage without benchmarks.
"""
from __future__ import annotations
from dataclasses import dataclass
from time import monotonic
from veritas.research.contraction_planner import FactorModel, ContractionPlan, ContractLimit, ExactStats

@dataclass
class SparseFactor:
    ports: tuple[int,...]
    values: dict[int,int]


def sparse_contract_order(model: FactorModel, plan: ContractionPlan, *, modulus:int|None=None,
                          max_table_entries:int=65536, max_work_assignments:int=2_000_000,
                          deadline:float|None=None)->tuple[int,ExactStats]:
    if type(max_table_entries) is not int or not 1<=max_table_entries<=1<<20:
        raise ValueError('invalid sparse entry limit')
    if type(max_work_assignments) is not int or not 1<=max_work_assignments<=20_000_000:
        raise ValueError('invalid sparse work limit')
    if modulus is not None and (type(modulus) is not int or not 2<=modulus<=2**256):
        raise ValueError('invalid modulus')
    if len(plan.order)!=len(model.variables) or set(plan.order)!=set(model.variables):
        raise ValueError('invalid elimination plan')
    start=monotonic(); deadline=deadline if deadline is not None else start+15
    factors=[]; work=0;lookups=0;peak=0
    for f in model.factors:
        if len(f.table)>max_table_entries:
            raise ContractLimit('initial dense input factor exceeds budget')
        # Explicit branch avoids mod operation and supports negative coefficients.
        values={i:vv for i,v in enumerate(f.table)
                if (vv:=(v%modulus if modulus is not None else v))!=0}
        factors.append(SparseFactor(f.ports,values))
        peak=max(peak,len(values))
    def guard():
        if monotonic()>deadline:raise ContractLimit('sparse contraction deadline exceeded')
    def join(left:SparseFactor,right:SparseFactor)->SparseFactor:
        nonlocal work,lookups,peak
        ports=tuple(sorted(set(left.ports)|set(right.ports)))
        where={v:i for i,v in enumerate(ports)}
        pos_l={v:i for i,v in enumerate(left.ports)}
        pos_r={v:i for i,v in enumerate(right.ports)}
        overlap=tuple(sorted(set(left.ports)&set(right.ports)))
        def k(mask:int, pos:dict[int,int])->int:
            return sum(((mask>>pos[v])&1)<<j for j,v in enumerate(overlap))
        right_rows={}
        for mask,value in right.values.items():
            right_rows.setdefault(k(mask,pos_r),[]).append((mask,value))
        lshift=tuple(1<<where[v] for v in left.ports)
        rshift=tuple(1<<where[v] for v in right.ports)
        output={}
        counter=0
        for lm,lv in left.values.items():
            lmap=sum(bit for j,bit in enumerate(lshift) if lm&(1<<j))
            for rm,rv in right_rows.get(k(lm,pos_l),()):
                counter+=1
                if counter & 255==0:guard()
                if work>=max_work_assignments:
                    raise ContractLimit('sparse join work budget exceeded')
                work+=1;lookups+=2
                rmap=sum(bit for j,bit in enumerate(rshift) if rm&(1<<j))
                outmask=lmap|rmap
                value=lv*rv
                if modulus is not None:value%=modulus
                combined=output.get(outmask,0)+value
                if modulus is not None:combined%=modulus
                if combined:output[outmask]=combined
                else:output.pop(outmask,None)
                if len(output)>max_table_entries:
                    raise ContractLimit('sparse factor exceeds nonzero-entry budget')
        peak=max(peak,len(output))
        return SparseFactor(ports,output)
    for vertex in plan.order:
        guard()
        touched=[f for f in factors if vertex in f.ports]
        factors=[f for f in factors if vertex not in f.ports]
        if not touched:
            factors.append(SparseFactor((),{0:2%modulus if modulus else 2}))
            continue
        touched.sort(key=lambda f:(len(f.values),len(f.ports)))
        acc=touched[0]
        for nxt in touched[1:]:
            acc=join(acc,nxt)
            if not acc.values:break
        # Sum out this vertex; the remaining rows are exact counts.
        bit=1<<acc.ports.index(vertex)
        output={}
        for i,(mask,value) in enumerate(acc.values.items()):
            if (i & 255)==0:guard()
            if work>=max_work_assignments:raise ContractLimit('sparse sum work budget exceeded')
            work+=1
            lower=mask&(bit-1)
            upper=(mask>>(acc.ports.index(vertex)+1))<<(acc.ports.index(vertex))
            reduced=lower|upper
            combined=output.get(reduced,0)+value
            if modulus is not None:combined%=modulus
            if combined:output[reduced]=combined
            else:output.pop(reduced,None)
            if len(output)>max_table_entries:
                raise ContractLimit('sparse sum exceeds nonzero-entry budget')
        peak=max(peak,len(output))
        factors.append(SparseFactor(tuple(v for v in acc.ports if v!=vertex),output))
    result=1
    for f in factors:
        if f.ports:raise AssertionError('uneliminated sparse factor')
        result*=f.values.get(0,0)
        if modulus is not None:result%=modulus
    return result,ExactStats(peak,work,lookups,len(plan.order),monotonic()-start,
                             method='EXACT_SPARSE_HASH_JOIN_NONZERO_ENTRIES')
