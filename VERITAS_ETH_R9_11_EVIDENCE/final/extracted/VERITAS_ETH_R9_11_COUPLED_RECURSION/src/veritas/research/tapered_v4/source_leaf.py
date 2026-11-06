"""Source-prescribed leaf summation over validated immutable entry recipes.

No direct summation is used when M exceeds the source leaf threshold. Active
calls and theorem mode remain explicitly inconclusive.
"""
from dataclasses import dataclass
from itertools import product

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from .source_state import SourceNode, SourceAdmissionError, inspect_source_node
from .source_recipes import EntryLimits, EntryBudget, compile_entry, evaluate_compiled, Arithmetic


@dataclass(frozen=True)
class SourceLeafPolicy:
    entry_limits: EntryLimits = EntryLimits()
    max_edges: int = 12
    max_vertices: int = 4096
    verify_independent: bool = False
    oracle_max_edges: int = 8
    oracle_max_work: int = 2_000_000

    def __post_init__(self):
        if type(self.entry_limits) is not EntryLimits: raise TypeError('EntryLimits required')
        for name,low,high in (('max_edges',0,16),('max_vertices',0,10000),
                              ('oracle_max_edges',0,8),('oracle_max_work',1,20_000_000)):
            x=getattr(self,name)
            if type(x) is not int or not low<=x<=high:raise ValueError('invalid '+name)
        if type(self.verify_independent) is not bool: raise ValueError('Boolean oracle policy required')


def contract_source_leaf(node: SourceNode,policy=SourceLeafPolicy(),*,mode='source_leaf'):
    if type(node) is not SourceNode or type(policy) is not SourceLeafPolicy:
        raise TypeError('source node and leaf policy required')
    if mode=='theorem':
        return {'status':'INCONCLUSIVE_THEOREM_PATH_NOT_IMPLEMENTED','theorem_mode_enabled':False}
    if mode!='source_leaf': raise ValueError('unsupported execution mode')
    budget=EntryBudget(policy.entry_limits)
    try:
        admission=inspect_source_node(node)
        if node.edge_count>node.context.leaf_threshold:
            raise SourceAdmissionError('INCONCLUSIVE_SOURCE_ACTIVE_PATH_NOT_IMPLEMENTED',
                                       'nonleaf node requires the unimplemented active source executor')
        if node.edge_count>policy.max_edges or len(node.vertices)>policy.max_vertices:
            raise SourceAdmissionError('INCONCLUSIVE_RESOURCE_LIMIT','leaf dimensions exceed policy')
        if (node.precision>policy.entry_limits.max_precision_bits or
            node.context.jet_length>policy.entry_limits.max_jet_length or
            node.context.extension_degree>policy.entry_limits.max_extension_degree):
            raise SourceAdmissionError('INCONCLUSIVE_RESOURCE_LIMIT','leaf arithmetic exceeds supported limits')
        if policy.verify_independent and node.edge_count>policy.oracle_max_edges:
            raise SourceAdmissionError('INCONCLUSIVE_ORACLE_COVERAGE','requested full oracle exceeds its edge cap')
        # Validate every description, even if another vertex happens to be zero.
        compiled=tuple(compile_entry(v.tensor,budget) for v in node.vertices)
        if node.depth==0:
            for entry in compiled:
                if entry.kind=='packet' or (entry.kind=='dense' and any(
                    any(c[1:]) for value in entry.data for c in value)):
                    raise SourceAdmissionError('INCONCLUSIVE_ROOT_COEFFICIENT_DOMAIN',
                                               'original source tensors must be certified in the base V-ring')
        ring=JetRing(ExtensionRing(node.precision,node.context.defining_polynomial),node.context.jet_length)
        ar=Arithmetic(ring,budget);total=ring.zero
        for bits in product((0,1),repeat=node.edge_count):
            budget.tick(1,'edge_assignments');term=ring.one
            for vertex,entry in zip(node.vertices,compiled):
                value=evaluate_compiled(entry,tuple(bits[e] for e in vertex.ports),node.precision,budget)
                term=ar.mul(term,value)
            total=ar.add(total,term)
        verified=False
        if policy.verify_independent:
            from veritas.research.independent_r95.recipe_oracle import contract_reference,ReferenceLimit
            try:
                check=contract_reference(node,max_edges=policy.oracle_max_edges,max_work=policy.oracle_max_work)
            except ReferenceLimit as exc:
                raise SourceAdmissionError('INCONCLUSIVE_ORACLE_RESOURCE_LIMIT',str(exc)) from exc
            if check!=total:raise SourceAdmissionError('INCONCLUSIVE_INVARIANT_FAILURE','independent leaf contraction differs')
            budget.tick(0)  # Include oracle elapsed time in the cooperative deadline.
            verified=True
        return {'status':'EXACT_SOURCE_LEAF_MODULAR_CONTRACTION','result':total,
                'precision':node.precision,'s':node.context.size_parameter,'M':node.edge_count,
                'leaf_threshold':node.context.leaf_threshold,'ledger':budget.ledger(),
                'independent_variable_elimination_checked':verified,
                'recipe_hashes':tuple(v.tensor.description_sha256 for v in node.vertices),
                'theorem_mode_enabled':False,'entry_cost_theorem_proven':False,
                'active_recursion_implemented':False,'executable_refinement_proven':False}
    except SourceAdmissionError as exc:
        return {'status':exc.status,'reason':str(exc),'ledger':budget.ledger(),'theorem_mode_enabled':False}
    except (MemoryError,RecursionError):
        return {'status':'INCONCLUSIVE_RESOURCE_LIMIT','reason':'leaf resources exhausted','theorem_mode_enabled':False}
    except (ValueError,TypeError,ArithmeticError) as exc:
        return {'status':'INCONCLUSIVE_INVALID_RECIPE','reason':str(exc),'ledger':budget.ledger(),'theorem_mode_enabled':False}
