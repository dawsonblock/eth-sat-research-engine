"""Bounded, content-bound entry semantics for the source-state interface.

Packet evaluation implements subsec:tensor-children by extracting one exact
target-mode coefficient from the product of affine row factors.  Entries are
computed modulo their creation precision BEFORE their coordinate
representatives are lifted.  No active recursive driver is enabled.

R9.6 changes, all behaviour-preserving except where a defect is repaired:

* one shared :class:`~.coefficient_budget.CoefficientAdmission` counter covers
  dense tables, packet local matrices, target coefficients, source scalars and
  clause polarities, and it refuses before any ring arithmetic;
* packet coefficient extraction no longer walks ``product(*row_choices)``; it
  uses an exact first-order product rule or a bounded truncated polynomial DP
  (:mod:`.packet_coefficients`), with a deliberately naive reference retained
  for differential testing;
* the constructor pre-scan bounds structure by the *admissible* payload size
  rather than by a multiple of the coefficient cap, so a small cap no longer
  rejects a payload that would have fitted.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from time import monotonic

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from .coefficient_budget import (
    CoefficientAdmission, jet_coordinates, packet_coordinate_counts)
from .packet_coefficients import algorithm_for, row_factors, target_coefficient
from .source_state import SourceTensorReference, SourceAdmissionError

SCHEMA = "VERITAS_SOURCE_ENTRY_V1"
KINDS = ("dense", "equality", "clause", "packet")


@dataclass(frozen=True)
class EntryLimits:
    max_arity: int = 16
    max_coefficients: int = 65536
    max_description_bytes: int = 2_000_000
    max_modes: int = 128
    max_exponent: int = 4096
    max_extension_degree: int = 64
    max_precision_bits: int = 1024
    max_jet_length: int = 64
    max_work: int = 5_000_000
    max_seconds: float = 30.0

    def __post_init__(self):
        caps=(16,1_000_000,16_000_000,1024,65536,64,1024,64,100_000_000)
        for name,cap in zip(tuple(self.__dataclass_fields__)[:-1],caps):
            v=getattr(self,name)
            if type(v) is not int or not 1 <= v <= cap:
                raise ValueError(f"invalid {name}")
        if type(self.max_seconds) not in (int,float) or not 0 < self.max_seconds <= 60:
            raise ValueError("invalid entry time cap")


class EntryBudget:
    """Cooperative work/time ledger with an attached coefficient counter."""

    def __init__(self, limits: EntryLimits):
        if type(limits) is not EntryLimits: raise TypeError("EntryLimits required")
        self.limits=limits;self.used=0;self.started=monotonic();self.counters={}
        self.coefficients=CoefficientAdmission(limits.max_coefficients)
        self.notes={}

    def tick(self,n=1,kind="control"):
        if type(n) is not int or n < 0: raise ValueError("nonnegative work charge required")
        self.used+=n;self.counters[kind]=self.counters.get(kind,0)+n
        if self.used>self.limits.max_work or monotonic()-self.started>self.limits.max_seconds:
            raise SourceAdmissionError("INCONCLUSIVE_RESOURCE_LIMIT","entry work/time budget exhausted")

    def admit_coefficients(self,count,kind):
        return self.coefficients.admit(count,kind)

    def note(self,key,value):
        if type(key) is not str or not key: raise ValueError("note key required")
        self.notes[key]=value

    def ledger(self):
        return {"work_units":self.used,"counters":dict(self.counters),
                "coefficients":self.coefficients.snapshot(),
                "notes":dict(sorted(self.notes.items())),
                "elapsed_seconds":monotonic()-self.started,"complete_bit_work":False,
                "hard_memory_limit_enforced":False,
                "limitations":["Integer bit costs, JSON allocations, irreducibility tests and peak memory are not measured.",
                               "Independent oracle work is separately capped and excluded from work_units.",
                               "Deadline checks are cooperative; description dimensions are separately capped.",
                               "Coefficient admission counts stored coordinates, not the bit width of their arithmetic."]}


@dataclass(frozen=True)
class CompiledEntry:
    reference: SourceTensorReference
    kind: str
    data: tuple


def _keys(d,expected):
    if type(d) is not dict or set(d)!=set(expected): raise ValueError("unexpected recipe fields")


def _int(x,low,high,label):
    if type(x) is not int or not low<=x<=high: raise ValueError(f"invalid {label}")


def _tuple_tree(value):
    if type(value) is list: return tuple(_tuple_tree(x) for x in value)
    if type(value) is int: return value
    raise ValueError("recipe payload must be an integer/list tree")


def _canonical(payload):
    return json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode("ascii")


def _no_duplicates(pairs):
    d={}
    for k,v in pairs:
        if k in d: raise ValueError("duplicate recipe field")
        d[k]=v
    return d


def compile_entry(ref: SourceTensorReference, budget: EntryBudget) -> CompiledEntry:
    if type(ref) is not SourceTensorReference: raise TypeError("SourceTensorReference required")
    lim=budget.limits
    if (ref.arity>lim.max_arity or len(ref.description)>lim.max_description_bytes or
        ref.creation_precision>lim.max_precision_bits or ref.jet_length>lim.max_jet_length or
        ref.defining_polynomial.bit_length()-1>lim.max_extension_degree):
        raise SourceAdmissionError("INCONCLUSIVE_RESOURCE_LIMIT","entry dimensions exceed cap")
    if ref.recipe_kind not in tuple(SCHEMA+":"+k for k in KINDS):
        raise SourceAdmissionError("INCONCLUSIVE_UNSUPPORTED_RECIPE","unknown entry semantics")
    budget.tick(len(ref.description),"description_bytes")
    def parse_int(s):
        if len(s)>400: raise ValueError("oversized recipe integer")
        return int(s)
    try:
        p=json.loads(ref.description,object_pairs_hook=_no_duplicates,parse_int=parse_int,
                     parse_float=lambda s: (_ for _ in ()).throw(ValueError("floating coefficient")))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("invalid recipe encoding") from exc
    _keys(p,("schema","kind","arity","creation_precision","polynomial","jet_length","data"))
    if (p['schema']!=SCHEMA or p['kind'] not in KINDS or ref.recipe_kind!=SCHEMA+":"+p['kind'] or
        any(type(p[k]) is not int for k in ('arity','creation_precision','polynomial','jet_length')) or
        (p['arity'],p['creation_precision'],p['polynomial'],p['jet_length'])!=
        (ref.arity,ref.creation_precision,ref.defining_polynomial,ref.jet_length) or _canonical(p)!=ref.description):
        raise ValueError("recipe metadata/canonical encoding mismatch")
    ring=JetRing(ExtensionRing(ref.creation_precision,ref.defining_polynomial),ref.jet_length)
    per_jet=jet_coordinates(ring.length,ring.base.e)
    def check_jet(v):
        if type(v) is not list or len(v)!=ring.length or any(type(c) is not list or len(c)!=ring.base.e for c in v):
            raise ValueError("coefficient dimensions differ from creation ring")
        for c in v:
            for x in c: _int(x,0,ring.base.modulus-1,"canonical coefficient")
    def jet(v,kind):
        check_jet(v)
        budget.tick(per_jet,"coefficient_checks")
    data=p['data'];kind=p['kind']
    if type(data) is not list: raise ValueError("list payload required")
    if kind=='dense':
        if len(data)!=(1<<ref.arity): raise ValueError("dense table must cover every Boolean index")
        # Admit the whole table atomically before touching any entry.
        budget.admit_coefficients(len(data)*per_jet,"dense_entries")
        for v in data: jet(v,"dense_entries")
    elif kind=='equality':
        if data or ref.arity<1: raise ValueError("equality requires positive arity and no payload")
    elif kind=='clause':
        if len(data)!=ref.arity: raise ValueError("clause signs must cover ports")
        budget.admit_coefficients(len(data),"clause_polarities")
        for sign in data: _int(sign,0,1,"literal polarity")
    else:
        if len(data)!=5: raise ValueError("packet payload has five fields")
        rows,cols,local,targets,sources=data
        if any(type(x) is not list for x in data): raise ValueError("packet fields must be lists")
        for x in rows+cols: _int(x,0,ref.arity-1,"packet port")
        if len(rows)+len(cols)!=ref.arity or sorted(rows+cols)!=list(range(ref.arity)):
            raise ValueError("packet rows/columns must partition its ports")
        if len(local)!=len(rows): raise ValueError("local rows incomplete")
        # Admit the whole local matrix before validating any coefficient.
        budget.admit_coefficients(len(rows)*len(cols)*per_jet,"packet_local_matrix")
        for row in local:
            if type(row) is not list or len(row)!=len(cols): raise ValueError("local columns incomplete")
            for c in row: jet(c,"packet_local_matrix")
        if len(targets)+len(sources)>lim.max_modes: raise SourceAdmissionError("INCONCLUSIVE_RESOURCE_LIMIT","mode cap")
        for group,size,is_target in ((targets,len(rows),True),(sources,len(cols),False)):
            for mode in group:
                if type(mode) is not list or len(mode)!=2: raise ValueError("malformed packet mode")
                beta,values=mode;_int(beta,0,lim.max_exponent,"mode exponent")
                if type(values) is not list or len(values)!=size: raise ValueError("mode support incomplete")
                if is_target:
                    budget.admit_coefficients(len(values)*per_jet,"packet_target_coefficients")
                    for c in values:jet(c,"packet_target_coefficients")
                else:
                    budget.admit_coefficients(len(values),"packet_source_coefficients")
                    for c in values:_int(c,0,ring.base.modulus-1,"source coefficient")
        budget.note("packet_coordinate_census",
                    packet_coordinate_counts(rows,cols,local,targets,sources,
                                             ring.length,ring.base.e))
    return CompiledEntry(ref,kind,_tuple_tree(data))


def _admissible_payload_nodes(limits):
    """Structural node budget derived from what can actually be admitted.

    A valid payload stores at most ``max_coefficients`` coefficient integers
    plus small metadata (ports, mode exponents, polarity flags).  Each
    coefficient integer sits inside a handful of nested containers, so the
    total node count is bounded by ``4 * max_coefficients`` plus slack for the
    metadata.  This replaces a flat ``4 * max_coefficients`` item cap that
    rejected every realistic payload when the coefficient cap was small.
    """
    metadata = 8 * (limits.max_arity + limits.max_modes) + 64
    return 4 * limits.max_coefficients + metadata


def make_reference(*,kind,arity,creation_precision,defining_polynomial,jet_length,data,limits=EntryLimits()):
    """Validate and bind a caller-supplied concrete recipe; not a mode certificate."""
    if type(limits) is not EntryLimits: raise TypeError('EntryLimits required')
    _int(arity,0,limits.max_arity,'constructor arity')
    _int(creation_precision,1,limits.max_precision_bits,'creation precision')
    _int(jet_length,1,limits.max_jet_length,'jet length')
    if type(defining_polynomial) is not int or not 1 <= defining_polynomial.bit_length()-1 <= limits.max_extension_degree:
        raise ValueError('constructor extension degree exceeds limit')
    if type(kind) is not str or kind not in KINDS: raise ValueError('unsupported constructor kind')
    p={'schema':SCHEMA,'kind':kind,'arity':arity,'creation_precision':creation_precision,
       'polynomial':defining_polynomial,'jet_length':jet_length,'data':data}
    # Bound caller-provided trees before JSON serialization (tuples are
    # accepted by the constructor and become canonical JSON arrays).
    node_cap = _admissible_payload_nodes(limits)
    stack=[(data,0)];items=0
    while stack:
        value,depth=stack.pop();items+=1
        if items>node_cap or depth>8:
            raise SourceAdmissionError("INCONCLUSIVE_RESOURCE_LIMIT","constructor tree cap")
        if type(value) in (tuple,list):
            if len(value)>node_cap:
                raise SourceAdmissionError("INCONCLUSIVE_RESOURCE_LIMIT","constructor array cap")
            stack.extend((child,depth+1) for child in value)
        elif type(value) is not int or value.bit_length()>limits.max_precision_bits+1:
            raise ValueError("invalid or oversized constructor coefficient")
    raw=_canonical(p)
    ref=SourceTensorReference(arity,creation_precision,defining_polynomial,jet_length,SCHEMA+":"+kind,raw)
    compile_entry(ref,EntryBudget(limits))
    return ref


class Arithmetic:
    def __init__(self,ring,budget):self.ring=ring;self.budget=budget
    def add(self,x,y):
        self.budget.tick(self.ring.length*self.ring.base.e,"coordinate_additions")
        return self.ring.add(x,y)
    def neg(self,x):
        self.budget.tick(self.ring.length*self.ring.base.e,"coordinate_negations")
        return self.ring.neg(x)
    def mul(self,x,y):
        self.budget.tick(self.ring.length*(self.ring.length+1)//2*self.ring.base.e**2,"coefficient_multiplications")
        return self.ring.mul(x,y)
    def power(self,x,n):
        z=self.ring.one
        while n:
            if n&1:z=self.mul(z,x)
            n>>=1
            if n:x=self.mul(x,x)
        return z


def evaluate_compiled(entry: CompiledEntry,bits,precision,budget: EntryBudget):
    """Evaluate at pc, then retain the same integer representatives at p>=pc."""
    ref=entry.reference
    _int(precision,ref.creation_precision,budget.limits.max_precision_bits,"evaluation precision")
    if type(bits) is not tuple or len(bits)!=ref.arity or any(type(b) is not int or b not in (0,1) for b in bits):
        raise ValueError("Boolean index has wrong shape/type")
    budget.tick(1+len(bits),"entry_evaluations")
    ring=JetRing(ExtensionRing(ref.creation_precision,ref.defining_polynomial),ref.jet_length)
    ar=Arithmetic(ring,budget);data=entry.data
    if entry.kind=='dense':
        index=0
        for bit in bits:index=2*index+bit
        result=data[index]
    elif entry.kind=='equality':result=ring.one if all(b==bits[0] for b in bits) else ring.zero
    elif entry.kind=='clause':result=ring.one if any(b==s for b,s in zip(bits,data)) else ring.zero
    elif entry.kind=='packet':
        rows,cols,local,targets,sources=data
        selected=[(beta,coeffs) for beta,coeffs in targets if beta]
        desired=tuple(beta for beta,_ in selected)
        if sum(desired)>len(rows):
            result=ring.zero
        else:
            factors=row_factors(rows,cols,local,targets,bits,ring,ar,budget,selected=selected)
            algorithm=algorithm_for(desired)
            budget.note("coefficient_algorithm",algorithm)
            result=target_coefficient(factors,desired,ring,ar,budget,algorithm=algorithm)
        for beta,coeffs in sources:
            source=ring.zero
            for pos,c in zip(cols,coeffs):
                if bits[pos]:source=ar.add(source,ring.elem([[c]]))
            result=ar.mul(result,ar.power(source,beta))
    else: raise SourceAdmissionError("INCONCLUSIVE_UNSUPPORTED_RECIPE","compiled entry kind is unknown")
    # Result is canonical at pc. Do not recompute its formula at precision.
    return result


def evaluate_source_entry(ref,bits,*,precision,limits=EntryLimits()):
    budget=EntryBudget(limits)
    compiled=compile_entry(ref,budget)
    result=evaluate_compiled(compiled,bits,precision,budget)
    return {'schema':'VERITAS_SOURCE_ENTRY_RESULT_V1',
            'status':'EXACT_CREATION_PRECISION_ENTRY','result':result,
            'creation_precision':ref.creation_precision,'evaluation_precision':precision,
            'recipe_sha256':sha256(ref.description).hexdigest(),'ledger':budget.ledger(),
            'theorem_qualified':False}
