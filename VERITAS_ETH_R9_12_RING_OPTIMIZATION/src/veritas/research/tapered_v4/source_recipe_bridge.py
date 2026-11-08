"""Explicit bridge from existing finite descriptions to the entry wire format.

This compiles entry semantics only. It does not certify the generating mode
set, packing, tuple enumeration, child identity or the recursion schedule.
"""
from itertools import product

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.eth_recursive_contraction_v39.described_network import (
    CreatedDenseTensor,CreatedPacketTensor,DescribedNetwork)
from .source_recipes import EntryLimits,make_reference
from .source_state import SourceContext,SourceNode,SourceVertex,SourceAdmissionError


def source_reference_from_created(tensor,*,limits=EntryLimits()):
    if type(limits) is not EntryLimits:raise TypeError('EntryLimits required')
    if type(tensor) not in (CreatedDenseTensor,CreatedPacketTensor):
        raise TypeError('supported immutable created tensor required')
    if tensor.arity>limits.max_arity:
        raise SourceAdmissionError('INCONCLUSIVE_RESOURCE_LIMIT','bridge arity cap')
    if type(tensor) is CreatedDenseTensor:
        first=tensor.entries[0]
        coefficient_count=len(tensor.entries)*len(first.coefficients)*(first.defining_polynomial.bit_length()-1)
        if coefficient_count>limits.max_coefficients:
            raise SourceAdmissionError('INCONCLUSIVE_RESOURCE_LIMIT','bridge coefficient cap')
        return make_reference(kind='dense',arity=tensor.arity,
            creation_precision=first.creation_precision,defining_polynomial=first.defining_polynomial,
            jet_length=len(first.coefficients),data=[tensor.entries[sum(b << i for i,b in enumerate(bits))].coefficients
                  for bits in product((0,1),repeat=tensor.arity)],limits=limits)
    if type(tensor) is not CreatedPacketTensor:raise TypeError('supported immutable created tensor required')
    recipe=tensor.recipe
    if (len(recipe.target_modes)+len(recipe.source_modes)>limits.max_modes or
        tensor.creation_precision>limits.max_precision_bits or tensor.jet_length>limits.max_jet_length or
        tensor.defining_polynomial.bit_length()-1>limits.max_extension_degree):
        raise SourceAdmissionError('INCONCLUSIVE_RESOURCE_LIMIT','bridge ring/mode cap')
    # Check existing sparse data before allocating canonical dense coordinates.
    coefficients=0
    for _,terms in recipe.rows:
        for _,jet in terms:
            for row in jet:
                coefficients+=len(row)
                if coefficients>limits.max_coefficients or any(c.bit_length()>limits.max_precision_bits+1 for c in row):
                    raise SourceAdmissionError('INCONCLUSIVE_RESOURCE_LIMIT','bridge coefficient cap')
    for modes,target in ((recipe.target_modes,True),(recipe.source_modes,False)):
        for _,beta,terms in modes:
            if beta>limits.max_exponent:
                raise SourceAdmissionError('INCONCLUSIVE_RESOURCE_LIMIT','bridge exponent cap')
            for _,value in terms:
                rows=value if target else ((value,),)
                for row in rows:
                    coefficients+=len(row)
                    if coefficients>limits.max_coefficients or any(c.bit_length()>limits.max_precision_bits+1 for c in row):
                        raise SourceAdmissionError('INCONCLUSIVE_RESOURCE_LIMIT','bridge coefficient cap')
    ring=JetRing(ExtensionRing(tensor.creation_precision,tensor.defining_polynomial),tensor.jet_length)
    rows=[i for i,(kind,_) in enumerate(recipe.variables) if kind=='Y']
    cols=[i for i,(kind,_) in enumerate(recipe.variables) if kind=='X']
    rowids=[recipe.variables[i][1] for i in rows];colids=[recipe.variables[i][1] for i in cols]
    byrow={rid:dict(terms) for rid,terms in recipe.rows}
    local=[[ring.elem(byrow[rid].get(cid,())) for cid in colids] for rid in rowids]
    targets=[];sources=[]
    for _,beta,values in recipe.target_modes:
        mapping=dict(values)
        targets.append([beta,[ring.elem(mapping.get(rid,())) for rid in rowids]])
    for _,beta,values in recipe.source_modes:
        mapping=dict(values)
        sources.append([beta,[mapping.get(cid,0)%ring.base.modulus for cid in colids]])
    return make_reference(kind='packet',arity=len(recipe.ports),creation_precision=tensor.creation_precision,
        defining_polynomial=tensor.defining_polynomial,jet_length=tensor.jet_length,
        data=[rows,cols,local,targets,sources],limits=limits)


def source_node_from_described(network,context,*,depth,precision,limits=EntryLimits()):
    if type(network) is not DescribedNetwork or type(context) is not SourceContext:
        raise TypeError('described network and source context required')
    vertices=[];next_id={'row':0,'column':0}
    for v in network.vertices:
        ident=next_id[v.side];next_id[v.side]+=1
        vertices.append(SourceVertex(v.side,ident,v.ports,source_reference_from_created(v.tensor,limits=limits)))
    return SourceNode(context,network.edges,tuple(vertices),depth,precision)
