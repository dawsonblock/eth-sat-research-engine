"""End-to-end exact modular #SAT via grouped Cauchy child tensors and Hermite.

Implements a bounded, reproducible *research reference* connecting v1.2's
independent modules:
  1. Construct a degree bound for the paper D.4.3 Cauchy-deformed network.
  2. Select nonzero interpolation nodes and calculate exact confluent
     Hermite weights, including sufficient 2-adic guard precision.
  3. Evaluate a jet at every node by weighted grouped rank-one modes and
     recursively contracted explicit boundary tensors.
  4. Reconstruct F(0) modulo 2^p. With p >= n+1 this uniquely determines
     the integer number of satisfying assignments.
  5. Optionally compare every jet with an independent direct half-wire
     enumeration AND the final count against the original CNF oracle.

This is NOT the manuscript's special D.4.4 weighted mode-packing recursion,
its amortized complexity bound, nor its D.5 tapered Hermite schedule.
The worst-case complexity is exponential. Returned transcripts are replayable
and cross-checkable, NOT stand-alone succinct mathematical proofs.
"""
from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from hashlib import sha256
import json

from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf, brute_contract
from veritas.research.hermite_ring import hermite_plan, reconstruct_mod
from veritas.research.weighted_children import recursive_weighted_jet, ChildTensorLimit
from veritas.research.cauchy_deformation import shifted_cauchy_jet_mod


class RecoveryBudgetExceeded(Exception):
    """The entire run must fail closed; no partial residue is authoritative."""


@dataclass(frozen=True)
class WeightedRecoveryResult:
    residue: int
    exact_count: int | None
    n_variables: int
    edges: int
    degree_bound: int
    packet_size: int
    group_span: int
    target_bits: int
    data_bits: int
    guard_bits: int
    nodes: tuple[int, ...]
    multiplicity: int
    hermite_weights: tuple[str, ...]
    node_jets: tuple[tuple[int, ...], ...]
    independent_jet_checked: bool
    independent_count_checked: bool
    total_recursion_calls: int
    total_work_assignments: int
    total_rank_one_modes: int
    total_pruned_modes: int
    transcript_sha256: str
    method: str = 'BOUNDED_WEIGHTED_CHILD_JETS_EXACT_HERMITE'


def recovery_payload(result: WeightedRecoveryResult) -> dict:
    """Public serializable evidence ledger; the hash is about identity, not proof."""
    return dict(result.__dict__)


def _transcript_digest(details: dict) -> str:
    raw = json.dumps(details, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
    return sha256(raw).hexdigest()


def recover_weighted_count(
    cnf: CNF, *, packet_size: int = 2, group_span: int = 1,
    precision_bits: int | None = None, max_edges: int = 6,
    max_boundary_vars: int = 12, max_table_entries: int = 4096,
    max_work_assignments: int = 250_000, timeout_s: float = 15.0,
    cross_check: bool = True,
) -> WeightedRecoveryResult:
    """Perform multi-node, guard-bit-safe, exact modular Hermite recovery.

    ``precision_bits=None`` selects n+1 bits: the residue *is* exact #SAT,
    because 0 <= #F <= 2**n. If the user requests fewer bits, the result
    is only a residue. All limits are validated before computation.

    Node computations share ONE global wall-clock and work-assignment budget;
    the independent checks consume the same wall-clock budget.
    """
    if type(packet_size) is not int or packet_size not in (1, 2):
        raise ValueError('packet_size must be 1 or 2 for bounded reconstruction')
    if type(group_span) is not int or not 1 <= group_span <= packet_size:
        raise ValueError('invalid group_span')
    if precision_bits is not None and (type(precision_bits) is not int or not 1 <= precision_bits <= 64):
        raise ValueError('precision_bits must be 1..64 or omitted')
    if type(max_edges) is not int or not 0 <= max_edges <= 6:
        raise ValueError('max_edges must be 0..6')
    if type(max_boundary_vars) is not int or not 0 <= max_boundary_vars <= 16:
        raise ValueError('invalid child boundary budget')
    if type(max_table_entries) is not int or not 1 <= max_table_entries <= 65536:
        raise ValueError('invalid child tensor entry budget')
    if type(max_work_assignments) is not int or not 1 <= max_work_assignments <= 2_000_000:
        raise ValueError('invalid global work budget')
    if type(timeout_s) not in (int, float) or not 0 < timeout_s <= 30:
        raise ValueError('timeout_s must be in (0,30]')
    if type(cross_check) is not bool:
        raise ValueError('cross_check must be a bool')
    deadline = monotonic() + timeout_s

    net = from_cnf(cnf, max_degree=8)
    if net.edges > max_edges:
        raise ValueError('weighted Hermite research wire budget exceeded')
    target_bits = cnf.n + 1 if precision_bits is None else precision_bits
    if not 1 <= target_bits <= 64:
        raise ValueError('target exact-count precision must be <=64 bits')
    degree = net.edges * (2*packet_size - 1)
    nodes = tuple(t for t in range(-packet_size, packet_size) if t != 0)
    multiplicity = (degree + len(nodes)) // len(nodes)
    if multiplicity > 20:
        raise ValueError('required local jet order exceeds the certified reference limit')
    plan = hermite_plan([(t, multiplicity) for t in nodes],
                        alpha=2*packet_size, degree_bound=degree)
    data_bits = target_bits + plan.guard_bits
    if data_bits > 128:
        raise ValueError('required Hermite guard precision exceeds child tensor limit')

    def remaining() -> float:
        left = deadline - monotonic()
        if left <= 0:
            raise RecoveryBudgetExceeded('global recovery deadline exceeded')
        return left

    jets: list[tuple[int, ...]] = []
    work = calls = all_modes = pruned = 0
    for node in nodes:
        left_work = max_work_assignments - work
        if left_work < 1:
            raise RecoveryBudgetExceeded('global child tensor work budget exceeded')
        try:
            jet, modes, stats = recursive_weighted_jet(
                net, packet_size=packet_size, node=node,
                group_span=group_span, precision_bits=data_bits,
                jet_order=multiplicity, max_edges=max_edges,
                max_boundary_vars=max_boundary_vars,
                max_table_entries=max_table_entries,
                max_work_assignments=left_work, timeout_s=remaining(),
            )
        except ChildTensorLimit as exc:
            raise RecoveryBudgetExceeded(str(exc)) from exc
        jets.append(jet)
        work += stats.work_assignments
        calls += stats.recursion_calls
        all_modes += stats.raw_rank_one_modes
        pruned += stats.dropped_rank_one_modes
        if cross_check:
            independent, _ = shifted_cauchy_jet_mod(
                net, packet_size=packet_size, node=node,
                precision_bits=data_bits, jet_order=multiplicity,
                max_edges=max_edges, timeout_s=remaining(),
            )
            if jet != independent:
                raise AssertionError(f'independent shifted Cauchy jet mismatch at node {node}')

    recovered = reconstruct_mod(plan, jets, precision_bits=target_bits,
                                data_precision_bits=data_bits)
    exact = recovered if target_bits >= cnf.n+1 else None
    if cross_check:
        independent_count = brute_contract(net, max_edges=max_edges, timeout_s=remaining())
        if recovered != independent_count % (1 << target_bits):
            raise AssertionError('Hermite recovered residue disagrees with original tensor contraction')
        if exact is not None and exact != independent_count:
            raise AssertionError('Hermite recovered exact count differs from original tensor contraction')

    transcript = {
        'cnf_sha256': cnf.digest(), 'packet_size':packet_size, 'group_span':group_span,
        'degree_bound':degree, 'nodes':nodes, 'multiplicity':multiplicity,
        'hermite_weights': tuple(str(w) for w in plan.weights),
        'jet_residues': jets, 'target_bits':target_bits, 'data_bits':data_bits,
        'recovered_residue':recovered,
    }
    return WeightedRecoveryResult(
        residue=recovered, exact_count=exact, n_variables=cnf.n,
        edges=net.edges, degree_bound=degree, packet_size=packet_size,
        group_span=group_span, target_bits=target_bits, data_bits=data_bits,
        guard_bits=plan.guard_bits, nodes=nodes, multiplicity=multiplicity,
        hermite_weights=tuple(str(w) for w in plan.weights),
        node_jets=tuple(jets), independent_jet_checked=cross_check,
        independent_count_checked=cross_check, total_recursion_calls=calls,
        total_work_assignments=work, total_rank_one_modes=all_modes,
        total_pruned_modes=pruned, transcript_sha256=_transcript_digest(transcript),
    )


def verify_recovery_transcript(cnf: CNF, record: WeightedRecoveryResult, *,
                               replay_jets: bool = False, timeout_s: float = 15.0) -> bool:
    """Revalidate Hermite arithmetic, transcript identity, optionally all jets.

    Algebraic checking validates the interpolation ledger, NOT the supplied
    jets' truth. With ``replay_jets=True``, an independent full half-wire
    evaluator recomputes them and verifies the original count.
    """
    try:
        if record.n_variables != cnf.n:
            return False
        net=from_cnf(cnf,max_degree=8)
        if net.edges!=record.edges:
            return False
        d=record.edges*(2*record.packet_size-1)
        if d!=record.degree_bound:
            return False
        nodes=tuple(t for t in range(-record.packet_size,record.packet_size) if t!=0)
        m=(d+len(nodes))//len(nodes)
        if nodes!=record.nodes or record.multiplicity!=m:
            return False
        plan=hermite_plan([(t,m) for t in nodes],alpha=2*record.packet_size,degree_bound=d)
        if record.guard_bits!=plan.guard_bits or record.data_bits!=record.target_bits+plan.guard_bits:
            return False
        if tuple(map(str,plan.weights)) != record.hermite_weights:
            return False
        if record.exact_count != (record.residue if record.target_bits>=cnf.n+1 else None):
            return False
        result=reconstruct_mod(plan,record.node_jets,precision_bits=record.target_bits,
                               data_precision_bits=record.data_bits)
        if result!=record.residue:
            return False
        transcript={'cnf_sha256':cnf.digest(), 'packet_size':record.packet_size,
                    'group_span':record.group_span,'degree_bound':d,'nodes':nodes,
                    'multiplicity':m,'hermite_weights':record.hermite_weights,
                    'jet_residues':record.node_jets,'target_bits':record.target_bits,
                    'data_bits':record.data_bits,'recovered_residue':record.residue}
        if _transcript_digest(transcript)!=record.transcript_sha256:
            return False
        if replay_jets:
            deadline=monotonic()+timeout_s
            for t,jet in zip(nodes,record.node_jets):
                remaining=deadline-monotonic()
                if remaining<=0:return False
                independent,_=shifted_cauchy_jet_mod(net,packet_size=record.packet_size,
                    node=t,precision_bits=record.data_bits,jet_order=m,
                    max_edges=6,timeout_s=remaining)
                if independent!=jet:
                    return False
            remaining=deadline-monotonic()
            if remaining<=0:return False
            raw=brute_contract(net,max_edges=6,timeout_s=remaining)
            if result!=raw%(1<<record.target_bits):
                return False
        return True
    except (ValueError, AssertionError, TypeError, KeyError, OverflowError, TimeoutError):
        return False
