"""Explicit execution choices. Selecting source semantics never qualifies code."""
from dataclasses import asdict, dataclass
from enum import Enum

from veritas.research.parent_child_r98.model import Semantics, canonical, digest


class ScheduleKind(str, Enum):
    FINITE = 'FINITE_SCALED_EXPERIMENT'
    SOURCE = 'PINNED_SOURCE_SCHEDULE'


class TupleStrategy(str, Enum):
    COMPLETE = 'complete_weighted'
    SUPPORT = 'certified_support'


class RecoveryKind(str, Enum):
    TAPERED = 'FULL_TAPERED_HERMITE'
    DEGREE = 'CERTIFIED_ROW_DEGREE_TAYLOR'


class LeafKind(str, Enum):
    FOUR_EDGES = 'FINITE_FOUR_EDGES'
    SOURCE = 'SOURCE_H'


@dataclass(frozen=True)
class ExecutionSpec:
    schedule_kind: ScheduleKind = ScheduleKind.FINITE
    schedule: tuple = ((1, 1),)
    tuples: TupleStrategy = TupleStrategy.COMPLETE
    recovery: RecoveryKind = RecoveryKind.TAPERED
    leaves: LeafKind = LeafKind.FOUR_EDGES
    groups: int = 64
    max_points: int = 256

    def __post_init__(self):
        for name, kind in (('schedule_kind', ScheduleKind), ('tuples', TupleStrategy),
                           ('recovery', RecoveryKind), ('leaves', LeafKind)):
            if type(getattr(self, name)) is not kind:
                raise TypeError('typed execution option required: ' + name)
        if type(self.groups) is not int or self.groups != 64:
            raise ValueError('general packet executor uses 64 groups; configurable singleton experiments are separate')
        if type(self.max_points) is not int or not 1 <= self.max_points <= 4096:
            raise ValueError('point cap must be 1..4096')
        if self.schedule_kind is ScheduleKind.SOURCE:
            if (self.schedule != () or self.leaves is not LeafKind.SOURCE or
                    self.tuples is not TupleStrategy.COMPLETE or self.recovery is not RecoveryKind.TAPERED):
                raise ValueError('source parameters must be derived; finite shortcuts cannot enter source execution')
        else:
            if (type(self.schedule) is not tuple or not 1 <= len(self.schedule) <= 16 or
                any(type(pair) is not tuple or len(pair) != 2 or
                    any(type(x) is not int for x in pair) or not 1 <= pair[1] <= pair[0] <= 3
                    for pair in self.schedule)):
                raise ValueError('immutable finite schedule required')
            if self.leaves is not LeafKind.FOUR_EDGES:
                raise ValueError('finite executor requires four-edge leaves')
            if self.recovery is RecoveryKind.DEGREE and self.tuples is not TupleStrategy.SUPPORT:
                raise ValueError('current degree executor requires independently certified support')

    def record(self):
        return asdict(self)

    @property
    def content_digest(self):
        return digest(canonical(self.record()))


def execute(parent, spec, *, policy, layout_factory=None, evidence_sink=None):
    """Route explicitly; source admission is never redirected to finite code.

    Existing entry points retain their defaults. The full tapered engine does
    its structural preflight before constructing interpolation weights.
    """
    if type(spec) is not ExecutionSpec:
        raise TypeError('ExecutionSpec required')
    if spec.schedule_kind is ScheduleKind.SOURCE:
        # The existing source entry point has a different context contract.
        # Do not fabricate that context, or advertise this selector as its proof.
        report = {'status': 'INCONCLUSIVE_SOURCE_REFINEMENT',
                  'reason': 'source execution requires the existing qualified context boundary',
                  'source_qualified': False, 'theorem_mode_enabled': False}
    elif parent.semantics is not Semantics.FINITE_SCALED_EXPERIMENT:
        report = {'status': 'INCONCLUSIVE_SOURCE_REFINEMENT',
                  'reason': 'finite execution requires finite parent semantics', 'source_qualified': False}
    elif spec.recovery is RecoveryKind.TAPERED:
        if evidence_sink is not None:
            if spec.tuples is not TupleStrategy.SUPPORT:
                raise ValueError('streamed executor requires explicit certified_support strategy')
            from .stream_engine import contract_streaming
            report = contract_streaming(parent, schedule=spec.schedule, layout_factory=layout_factory,
                policy=policy, max_points=spec.max_points, evidence_sink=evidence_sink)
            report['execution_spec'] = spec.record()
            report['execution_spec_digest'] = spec.content_digest
            return report
        from .engine import contract_packet_recursion
        report = contract_packet_recursion(parent, schedule=spec.schedule, layout_factory=layout_factory,
            policy=policy, max_points=spec.max_points, point_strategy=spec.tuples.value)
    else:
        from .degree_engine import contract_supported_recursion
        report = contract_supported_recursion(parent, schedule=spec.schedule, layout_factory=layout_factory,
            policy=policy, max_points=spec.max_points, evidence_sink=evidence_sink)
    report['execution_spec'] = spec.record()
    report['execution_spec_digest'] = spec.content_digest
    return report
