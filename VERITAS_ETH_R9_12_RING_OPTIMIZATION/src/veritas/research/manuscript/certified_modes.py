"""Explicit finite support pruning with exact, creation-point-local reuse.

This is not used by the source executor. A retained exponent vector still has
its original full padded-domain shape and weighted valuation constraint.
Excluded vectors have an identically zero source factor or exceed the degree
of a product of affine target-row factors. No nonzero modes are combined.
"""
from collections import defaultdict
from itertools import product

from veritas.research.eth_packing_v26.packet_bijection import encode_class_offset
from .cauchy import Kernel
from .modes import Domain
from .parameters import natural


class SupportCertificateError(ValueError):
    pass


def validate_layout(network, layout, point, budget):
    """Check complete canonical packet addressing for the supplied labels.

    This establishes layout validity, not optimality of its label construction.
    """
    natural(layout.a, 'label width', 1)
    natural(layout.r, 'radix', 2)
    natural(layout.padded_height, 'padded height', 1)
    natural(point.precision, 'point precision', 1)
    natural(point.ell, 'jet length', 1)
    if type(point.zeta) is not tuple:
        raise SupportCertificateError('immutable interpolation coordinates required')
    budget.bits(layout.a + 1, 'packet width')
    if point.L != layout.L or not 0 <= point.coordinate < layout.a:
        raise SupportCertificateError('point and layout geometry differ')
    H = layout.padded_height
    if H % layout.L:
        raise SupportCertificateError('padding must be a positive multiple of L')
    for side in ('row', 'column'):
        labels = layout.labels(side)
        if any(type(key) is not int or key < 0 for key in labels) or set(labels) != {v.identity for v in network.vertices if v.side == side}:
            raise SupportCertificateError('label coverage mismatch')
        for word in labels.values():
            if (type(word) is not tuple or len(word) != layout.a or
                    any(type(c) is not int or not 0 <= c < layout.r for c in word)):
                raise SupportCertificateError('invalid label word')
    buckets = defaultdict(list)
    for edge, (row, col) in enumerate(network.edges()):
        budget.tick()
        buckets[layout.rows[row], layout.columns[col]].append(edge)
    expected_height = layout.L * ((max(map(len, buckets.values()), default=0) + layout.L - 1) // layout.L)
    if H != expected_height:
        raise SupportCertificateError('noncanonical padded height')
    budget.bits(2 * layout.a * layout.r.bit_length() + H.bit_length(), 'padded inventory size')
    class_count = layout.r ** (2 * layout.a)
    expected_variance = class_count * sum(len(edges) ** 2 for edges in buckets.values()) - network.wires ** 2
    if type(layout.variance_scaled) is not int or layout.variance_scaled != expected_variance:
        raise SupportCertificateError('class variance mismatch')
    expected_count = class_count * H // layout.L
    budget.items(expected_count, 'complete padded inventory validation')
    if len(layout.packets) != expected_count:
        raise SupportCertificateError('incomplete padded inventory')
    occupied = defaultdict(list)
    for (row, col), edges in buckets.items():
        for offset, edge in enumerate(edges):
            budget.tick()
            address = encode_class_offset(row, col, offset, radix=layout.r,
                                          width=layout.a, padded_height=H)
            occupied[address.pattern, address.packet].append((address.slot, edge))
    pairs = tuple((lo, hi) for lo in range(layout.r) for hi in range(lo, layout.r))
    cursor = 0
    for pattern in product(pairs, repeat=layout.a):
        for index in range(H >> sum(lo == hi for lo, hi in pattern)):
            budget.tick()
            packet = layout.packets[cursor]
            expected = tuple(sorted(occupied.get((pattern, index), ())))
            if (type(packet.pattern) is not tuple or
                    any(type(pair) is not tuple or any(type(c) is not int for c in pair) for pair in packet.pattern) or
                    packet.pattern != pattern or type(packet.index) is not int or
                    packet.index != index or packet.slots != expected or
                    any(type(slot) is not int or type(edge) is not int for slot, edge in packet.slots)):
                raise SupportCertificateError('packet address or slot mismatch')
            cursor += 1


class _PointKernel(Kernel):
    """Bounded immutable scalar caches, never shared across creation points."""
    def __init__(self, point, ring):
        super().__init__(point, ring)
        self._values = {}
        self._modes = {}

    def _reserve(self):
        self.ring.budget.items((len(self._values) + len(self._modes) + 1) * self.ring.e,
                               'point kernel cache coefficients')

    def value(self, x, y):
        self.ring.budget.tick()
        key = x, y
        if key not in self._values:
            self._reserve()
            self._values[key] = super().value(x, y)
        return self._values[key]

    def mode_coefficient(self, x, y0, b):
        self.ring.budget.tick()
        key = x, y0, b
        if key not in self._modes:
            self._reserve()
            self._modes[key] = super().mode_coefficient(x, y0, b)
        return self._modes[key]


class DegreeCertifiedDomain(Domain):
    """A general structural zero certificate, explicitly experimental.

    A positive mode needs an occupied source column in its residue tile.
    For b>0 it also needs a nonzero geometric index j in that tile. For each
    packet and target group, total selected powers cannot exceed its row count.
    These necessary conditions may retain further zero coefficients.
    """
    def __init__(self, network, layout, point, budget, *, cache_kernel=True):
        if type(cache_kernel) is not bool:
            raise TypeError('cache_kernel must be a Boolean')
        validate_layout(network, layout, point, budget)
        super().__init__(layout, point, budget)
        self.cache_kernel = cache_kernel
        self._kernel = None
        self._last_beta = None
        self._positive_modes = {}
        eligible = []
        capacities = {}
        for index in range(self.size):
            budget.tick()
            mode = self.mode(index)
            packet = layout.packets[mode.packet]
            pair = packet.pattern[point.coordinate]
            rows = [slot for slot, _ in packet.slots
                    if pair[(slot >> point.coordinate) & 1] == mode.target]
            columns = [slot for slot, _ in packet.slots
                       if pair[1 - ((slot >> point.coordinate) & 1)] == mode.source
                       and slot % self.B == mode.tile]
            key = mode.packet, mode.target
            if rows and columns and (mode.exponent == 0 or any(slot // self.B for slot in columns)):
                eligible.append((index, mode.weight, key))
                capacities[key] = len(rows)
        self.eligible = tuple(eligible)
        self.capacities = capacities
        budget.items(len(eligible) * 3 + len(capacities) * 3, 'support certificate')

    def packet_kernel(self, ring):
        if ((ring.p, ring.f, ring.ell) != (self.point.precision, self.point.f, self.point.ell)
                or ring.budget is not self.budget):
            raise SupportCertificateError('kernel creation-point context mismatch')
        if not self.cache_kernel:
            return Kernel(self.point, ring)
        if self._kernel is None:
            self._kernel = _PointKernel(self.point, ring)
        return self._kernel

    def packet_modes(self, pid, beta, budget=None):
        # Cache the exact sparse contents of any supplied full beta, including
        # unsupported vectors used by fault tests. Do not silently drop entries
        # merely because they were not emitted by this domain's iterator.
        meter = self.budget if budget is None else budget
        if self._last_beta is not beta:
            if type(beta) is not tuple or len(beta) != self.size:
                raise ValueError('full immutable exponent vector required')
            meter.tick(self.size)
            positive = defaultdict(list)
            for index, power in enumerate(beta):
                if type(power) is not int or power < 0:
                    raise ValueError('invalid exponent')
                if power:
                    mode = self.mode(index)
                    positive[mode.packet].append((mode, power))
            meter.items(sum(map(len, positive.values())) * 2, 'nonzero exponent cache')
            self._positive_modes = {key: tuple(values) for key, values in positive.items()}
            self._last_beta = beta
        for pair in self._positive_modes.get(pid, ()):
            meter.tick()
            yield pair

    def tuples(self):
        beta = [0] * self.size
        used = 0
        degrees = dict.fromkeys(self.capacities, 0)
        while True:
            self.budget.tick()
            self.budget.tuples += 1
            yield tuple(beta)
            for index, weight, key in reversed(self.eligible):
                self.budget.tick()
                if (used + weight < self.point.precision and
                        degrees[key] < self.capacities[key]):
                    beta[index] += 1
                    used += weight
                    degrees[key] += 1
                    break
                used -= beta[index] * weight
                degrees[key] -= beta[index]
                beta[index] = 0
            else:
                return

    def certificate(self):
        return dict(schema='PACKET_SOURCE_AND_TARGET_DEGREE_ZERO_V1',
                    eligible_modes=[index for index, _, _ in self.eligible],
                    target_capacities=[[packet, group, count] for (packet, group), count in sorted(self.capacities.items())],
                    formal_channels_per_weight=self.per_weight,
                    formal_mode_count=self.size,
                    families=['EMPTY_SOURCE_TILE', 'POSITIVE_EXPONENT_WITH_ONLY_J_ZERO',
                              'TOTAL_POWER_EXCEEDS_TARGET_ROW_COUNT'])
