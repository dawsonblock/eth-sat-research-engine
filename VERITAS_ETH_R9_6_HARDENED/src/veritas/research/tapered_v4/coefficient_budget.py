"""One deterministic coefficient-admission counter for every recipe shape.

Budget contract (stated once, enforced everywhere)
--------------------------------------------------

``EntryLimits.max_coefficients`` bounds the number of **normalized stored
coefficients at creation precision**: every integer coordinate that the
canonical recipe payload stores and that the evaluator may consult.  Concretely,
for a recipe over the creation ring ``(Z/2^p)[U]/(f)`` with ``e = deg f`` and
``ell`` jet coordinates:

============================  ===========================================
representation                admitted coordinates
============================  ===========================================
``dense``                     2**arity * ell * e
``clause``                    arity (literal-polarity scalars)
``equality``                  0
``packet`` local matrix       len(rows) * len(cols) * ell * e
``packet`` target coefficients sum over retained targets of
                              len(rows) * ell * e
``packet`` source coefficients sum over retained sources of len(cols)
============================  ===========================================

The same counter is shared by :func:`compile_entry`,
:func:`make_reference`, the described-network bridge, the source-leaf
executor and the independent oracle.  Two properties follow and are tested:

* a payload is refused **before** any ring arithmetic runs, and
* a refusal carries **no** accepted numerical result.

Source-mode scalar coefficients are *syntactic* coordinates: they are stored
one integer per (source, column) pair.  The previous implementation validated
their range but never counted them, so four source scalars were admitted under
``max_coefficients=1``.  They now count, and so do clause polarities.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .source_state import SourceAdmissionError

COUNTER_STATUS = "INCONCLUSIVE_RESOURCE_LIMIT"
REASON = "coefficient admission cap exceeded"


def nonnegative_int(value, label):
    """Strict nonnegative integer check that rejects booleans and floats."""
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a nonnegative integer")
    return value


@dataclass
class CoefficientAdmission:
    """Cumulative, shape-aware coefficient counter."""
    maximum: int
    total: int = 0
    by_kind: dict = field(default_factory=dict)

    def __post_init__(self):
        if type(self.maximum) is not int or self.maximum < 1:
            raise ValueError("coefficient maximum must be a positive integer")
        self.by_kind = {}

    def admit(self, count, kind):
        """Admit ``count`` coordinates of one representation, or refuse.

        The whole request is refused atomically: a partial admission never
        leaves an under-counted ledger behind.
        """
        nonnegative_int(count, "coefficient count")
        if type(kind) is not str or not kind:
            raise ValueError("coefficient kind must be a nonempty name")
        if count == 0:
            return self.total
        projected = self.total + count
        if projected > self.maximum:
            raise SourceAdmissionError(
                COUNTER_STATUS,
                f"{REASON}: {kind} needs {count}, ledger "
                f"{self.total}/{self.maximum}")
        self.total = projected
        self.by_kind[kind] = self.by_kind.get(kind, 0) + count
        return projected

    def remaining(self):
        return self.maximum - self.total

    def snapshot(self):
        return {"maximum": self.maximum, "total": self.total,
                "by_kind": dict(sorted(self.by_kind.items())),
                "contract": "normalized_stored_coefficients_at_creation_precision"}


def jet_coordinates(jet_length, extension_degree):
    """Coordinates stored by one creation-ring jet."""
    nonnegative_int(jet_length, "jet length")
    nonnegative_int(extension_degree, "extension degree")
    return jet_length * extension_degree


def packet_coordinate_counts(rows, cols, local, targets, sources, jet_length,
                             extension_degree):
    """Exact stored-coordinate census for one packet payload.

    ``rows``/``cols``/``local``/``targets``/``sources`` must already be
    shape-validated by the caller; this routine only counts.
    """
    per_jet = jet_coordinates(jet_length, extension_degree)
    census = {
        "packet_local_matrix": len(rows) * len(cols) * per_jet,
        "packet_target_coefficients": sum(
            len(values) * per_jet for _, values in targets),
        "packet_source_coefficients": sum(
            len(values) for _, values in sources),
    }
    return census
