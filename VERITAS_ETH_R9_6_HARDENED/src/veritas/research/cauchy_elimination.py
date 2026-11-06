"""Exact, bounded Cauchy-jet contraction via polynomial factor elimination.

The original CNF network has M wires. Its polynomial deformation produces a
factor graph on 2M binary half-wire variables X and Y:

 F(t+2L*z) = sum_{X,Y} A(Y) B(X)
                 product_i [Y_i ? z_i(X) : (1-z_i(X))],
 z_i(X) = sum_{j in the same packet} W_ij(t+2L*z) X_j.

This implementation contracts the factor graph using polynomial bucket
elimination over R=(Z/2^p Z)[z]/(z^K). Unlike the 4**M oracle, intermediate
states are built only as needed, subject to exact table-size/time caps. The
algorithm is still exponential in treewidth, NOT the paper's subexponential
weighted-mode recursive contraction. All calculations are exact modulo R.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from time import monotonic

from veritas.research.tensor import TensorNetwork
from veritas.research.cauchy_deformation import shifted_integral_kernel
from veritas.research.hermite_ring import modular_fraction
from veritas.research.packet_schedule import plan_packets, relabel_network, PacketSchedule
from veritas.research.optimal_packets import optimize_packets_exact, PacketPlanningLimit
from veritas.research.scalable_packets import optimize_packets_scalable
from veritas.research.matching_packets import optimize_packets_matching


class EliminationLimit(Exception):
    """Bounded computation is inconclusive, never a partial result."""


@dataclass(frozen=True)
class JetFactor:
    ports: tuple[int, ...]
    values: tuple[tuple[int, ...], ...]


@dataclass
class JetEliminationStats:
    eliminated_variables: int = 0
    peak_factor_entries: int = 0
    peak_active_entries: int = 0
    maximum_width: int = 0
    polynomial_products: int = 0
    polynomial_sums: int = 0
    input_factors: int = 0
    elimination_order: tuple[int, ...] = ()
    packet_schedule: PacketSchedule | None = None
    # The requested coefficient jet describes F(t+2L*z), not F(0) except t=0.


def _poly_mul(a: tuple[int, ...], b: tuple[int, ...], mask: int, k: int) -> tuple[int, ...]:
    out = [0] * k
    for i, x in enumerate(a):
        if x:
            for j, y in enumerate(b[:k-i]):
                if y:
                    out[i+j] = (out[i+j] + x*y) & mask
    return tuple(out)


def _entry(factor: JetFactor, assignment: int) -> tuple[int, ...]:
    index = sum(1 << i for i, port in enumerate(factor.ports) if assignment & (1 << port))
    return factor.values[index]


def _estimate_width(factors: list[JetFactor], var: int) -> tuple[int, int, int]:
    bucket = [f for f in factors if var in f.ports]
    neighbors = set().union(*(set(f.ports) for f in bucket)) - {var}
    # Prefer fewer fill-in edges when widths tie.
    already = {tuple(sorted((x, y))) for f in factors for x in f.ports for y in f.ports if x < y}
    ordered = sorted(neighbors)
    missing = sum((ordered[i], ordered[j]) not in already
                  for i in range(len(ordered)) for j in range(i+1, len(ordered)))
    return len(neighbors), missing, var


def _make_factors(network: TensorNetwork, *, packet_size: int, node: int,
                  bits: int, order: int) -> list[JetFactor]:
    M = network.edges
    mask = (1 << bits) - 1
    zero = (0,) * order
    one = (1,) + (0,) * (order - 1)
    factors = []
    for f in network.factors:
        if f.label.startswith('clause:'):
            ports = f.ports
        elif f.label.startswith('variable:'):
            ports = tuple(M+e for e in f.ports)
        else:
            raise ValueError('supports CNF bipartite factors only')
        factors.append(JetFactor(ports, tuple((v & mask,)+zero[1:] for v in f.table)))
    W = shifted_integral_kernel(packet_size, node, max_order=order)
    Wm = tuple(tuple(tuple(modular_fraction(c, bits) for c in W[i][j])
                      for j in range(packet_size)) for i in range(packet_size))
    for i in range(M):
        beg = i // packet_size * packet_size
        cols = tuple(range(beg, min(M, beg+packet_size)))
        ports = (i,) + tuple(M+j for j in cols)
        if len(ports) > 11:
            raise EliminationLimit('kernel factor exceeds degree budget')
        values = []
        for selection in range(1 << len(ports)):
            ybit = selection & 1
            polynomial = [0] * order
            for pos,j in enumerate(cols):
                if selection & (1 << (pos+1)):
                    w = Wm[i%packet_size][j%packet_size]
                    for k in range(len(w)):
                        polynomial[k] = (polynomial[k]+w[k]) & mask
            if not ybit:
                polynomial = [(1-polynomial[0]) & mask] + [(-v) & mask for v in polynomial[1:]]
            values.append(tuple(polynomial))
        factors.append(JetFactor(ports, tuple(values)))
    return factors


def eliminate_cauchy_jet(network: TensorNetwork, *, packet_size: int=2,
                         node: int=0, precision_bits: int=12, jet_order: int=5,
                         optimize_packets: bool=False, max_table_entries: int=1<<13,
                         max_total_entries: int=1<<16, timeout_s: float=10.0,
                         elimination_order: str='min_fill',
                         packet_optimizer: str='legacy') -> tuple[tuple[int, ...], JetEliminationStats]:
    if type(packet_size) is not int or packet_size not in (1,2,4,8):
        raise ValueError('packet size must be 1,2,4,8')
    if type(node) is not int or not -packet_size <= node < packet_size:
        raise ValueError('node outside kernel interpolation grid')
    if type(precision_bits) is not int or not 1<=precision_bits<=128:
        raise ValueError('precision_bits must be 1..128')
    if type(jet_order) is not int or not 1<=jet_order<=24:
        raise ValueError('jet_order must be 1..24')
    if network.edges > 12:
        raise ValueError('bounded polynomial-elimination solver supports <=12 wires')
    if type(max_table_entries) is not int or not 2<=max_table_entries<=1<<18:
        raise ValueError('max_table_entries must be 2..262144')
    if type(max_total_entries) is not int or not max_table_entries<=max_total_entries<=1<<20:
        raise ValueError('invalid global table budget')
    if type(timeout_s) not in (int, float) or not 0 < timeout_s<=30:
        raise ValueError('timeout_s must be in (0,30]')
    if elimination_order not in ('min_fill','natural'):
        raise ValueError('unsupported elimination order')
    if packet_optimizer not in ('legacy','exact_dp','scalable','matching'):
        raise ValueError('packet_optimizer must be legacy, exact_dp, scalable or matching')
    total_deadline=monotonic()+timeout_s
    schedule = None
    if optimize_packets:
        try:
            if packet_optimizer == 'matching':
                if packet_size!=2:raise ValueError('matching requires packet_size=2')
                schedule,_=optimize_packets_matching(network,max_wires=128)
            elif packet_optimizer == 'exact_dp':
                schedule,_ = optimize_packets_exact(network,packet_size=packet_size,timeout_s=min(timeout_s/4,2))
            elif packet_optimizer == 'scalable':
                schedule,_ = optimize_packets_scalable(network, packet_size=packet_size,
                                                      timeout_s=min(timeout_s/4,2), max_evaluations=5000)
            else:
                schedule = plan_packets(network,packet_size=packet_size,timeout_s=min(timeout_s/4,2))
        except PacketPlanningLimit as exc:
            raise EliminationLimit(str(exc)) from exc
    if schedule is not None:
        network = relabel_network(network,schedule.wire_order)
    M = network.edges
    deadline = total_deadline
    if monotonic()>deadline:
        raise EliminationLimit('packet optimization exhausted the total time budget')
    stats = JetEliminationStats(packet_schedule=schedule)
    mask = (1 << precision_bits)-1
    zero = (0,)*jet_order
    one = (1,)+(0,)*(jet_order-1)
    factors = _make_factors(network,packet_size=packet_size,node=node,bits=precision_bits,order=jet_order)
    stats.input_factors = len(factors)
    stats.peak_factor_entries = max((len(f.values) for f in factors),default=0)
    stats.peak_active_entries = sum(len(f.values) for f in factors)
    if stats.peak_factor_entries>max_table_entries or stats.peak_active_entries>max_total_entries:
        raise EliminationLimit('initial polynomial factor table budget exhausted')
    path = []
    remaining = list(range(2*M))
    while remaining:
        if monotonic() > deadline:
            raise EliminationLimit('polynomial elimination deadline exceeded')
        var = min(remaining,key=lambda v:_estimate_width(factors,v)) if elimination_order=='min_fill' else remaining[0]
        bucket = [f for f in factors if var in f.ports]
        neighbors = tuple(sorted(set().union(*(set(f.ports) for f in bucket))-{var}))
        entries = 1 << len(neighbors)
        if entries > max_table_entries:
            raise EliminationLimit(f'intermediate table exceeds cap at variable {var}')
        stats.maximum_width = max(stats.maximum_width,len(neighbors))
        out=[]
        for assignment in range(entries):
            if (assignment & 127) == 0 and monotonic() > deadline:
                raise EliminationLimit('polynomial elimination deadline exceeded')
            base = sum((1 << v) for j,v in enumerate(neighbors) if assignment & (1 << j))
            acc = [0] * jet_order
            for bit in (0,1):
                full = base | ((1 << var) if bit else 0)
                val = one
                for factor in bucket:
                    val = _poly_mul(val,_entry(factor,full),mask,jet_order)
                    stats.polynomial_products += 1
                for k, x in enumerate(val):
                    acc[k] = (acc[k]+x)&mask
                stats.polynomial_sums += 1
            out.append(tuple(acc))
        factors = [f for f in factors if var not in f.ports]
        factors.append(JetFactor(neighbors,tuple(out)))
        active = sum(len(f.values) for f in factors)
        if active>max_total_entries:
            raise EliminationLimit('global polynomial table budget exhausted')
        stats.peak_active_entries=max(stats.peak_active_entries,active)
        stats.peak_factor_entries=max(stats.peak_factor_entries,entries)
        stats.eliminated_variables += 1
        path.append(var)
        remaining.remove(var)
    value = one
    for factor in factors:
        if factor.ports:
            raise AssertionError('uneliminated variable remains')
        value = _poly_mul(value,factor.values[0],mask,jet_order)
        stats.polynomial_products += 1
    stats.elimination_order=tuple(path)
    return value,stats
