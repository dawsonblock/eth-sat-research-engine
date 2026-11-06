"""Two separated regimes, and a proof that the source-active one is unreachable.

The contradiction
-----------------

The pinned schedule sets, with ``lambda = ceil(log2(s))``:

* ``e = 4 * lambda`` extension degree,
* ``base = floor(lambda / 131072)``,
* and an active call needs ``base >= 1``, i.e. ``lambda >= 131072``.

Every admissible :class:`~.source_state.SourceContext` must satisfy

* ``e <= limits.max_extension_degree`` (whose supported ceiling is 4096), and
* ``s.bit_length() <= limits.max_size_bits`` (whose supported ceiling is 65536).

The first gives ``lambda <= max_extension_degree // 4``.  With the shipped
default of 64 that is ``lambda <= 16``; with the largest value the class will
accept it is ``lambda <= 1024``.  Both are far below 131072, so
``base == 0`` for every admitted context and
``schedule_preflight`` can never return ``ACTIVE_NUMERIC_PRECONDITIONS_MET``
for a non-leaf node.  The second wall is independent: ``s = 2**131071`` has
``bit_length == 131072 > 65536``.

This is a *parameter contradiction in the current representation*, not a proof
that the manuscript's theorem is false.  Raising the constants would not fix
it either: ``s = 2**131071`` has ~39,000 decimal digits and ``e = 524284``, so
no materialized graph, ring or description of that size is executable here.
The honest conclusion is that the source-active regime is
**not implemented**, and the two regimes must be named separately.

The regimes
-----------

``EXPERIMENTAL_SCALED_FINITE``
    The bounded finite fixtures that actually run.  Every parameter is a
    caller-supplied scaled stand-in; nothing here instantiates the manuscript's
    numbers.

``SOURCE_THEOREM_PARAMETERIZED``
    The manuscript's parameter regime.  This release can *describe* it
    symbolically and refuse to execute it.  It must not report a value.

``source_active_status`` returns the regime plus
``INCONCLUSIVE_SOURCE_ACTIVE_PATH_NOT_IMPLEMENTED``; theorem mode stays off.
"""
from __future__ import annotations

from dataclasses import dataclass

from .source_state import SourceContext, SourceLimits

EXPERIMENTAL_SCALED_FINITE = "EXPERIMENTAL_SCALED_FINITE"
SOURCE_THEOREM_PARAMETERIZED = "SOURCE_THEOREM_PARAMETERIZED"
SOURCE_ACTIVE_STATUS = "INCONCLUSIVE_SOURCE_ACTIVE_PATH_NOT_IMPLEMENTED"
THEOREM_STATUS = "INCONCLUSIVE_THEOREM_PATH_NOT_IMPLEMENTED"

#: The manuscript's ``epsilon = 2**-17`` reciprocal enters the schedule as the
#: denominator of ``base``.  Recorded here as one named constant so no caller
#: re-derives it from a literal.
SCHEDULE_DENOMINATOR = 1 << 17
EXTENSION_DEGREE_PER_LAMBDA = 4


def lambda_of(size_parameter):
    """``ceil(log2(s))`` for ``s >= 2``, without constructing anything large."""
    if type(size_parameter) is not int or size_parameter < 2:
        raise ValueError("size parameter must be an integer >= 2")
    return (size_parameter - 1).bit_length()


def minimum_active_lambda():
    return SCHEDULE_DENOMINATOR


def maximum_admissible_lambda(limits=None):
    """Largest ``lambda`` any admitted :class:`SourceContext` can carry."""
    limits = limits or SourceLimits()
    if type(limits) is not SourceLimits:
        raise TypeError("SourceLimits required")
    by_degree = limits.max_extension_degree // EXTENSION_DEGREE_PER_LAMBDA
    by_bits = limits.max_size_bits
    return min(by_degree, by_bits)


def active_parameter_contradiction(limits=None):
    """Executable derivation that no admitted context reaches the active path."""
    limits = limits or SourceLimits()
    maximum = maximum_admissible_lambda(limits)
    required = minimum_active_lambda()
    by_degree = limits.max_extension_degree // EXTENSION_DEGREE_PER_LAMBDA
    return {
        "schema": "VERITAS_SOURCE_ACTIVE_UNREACHABILITY_V1",
        "reachable": maximum >= required,
        "derivation": [
            "lambda = ceil(log2(s))",
            "e = 4 * lambda and e <= max_extension_degree",
            f"max_extension_degree = {limits.max_extension_degree} "
            f"-> lambda <= {by_degree}",
            "s.bit_length() <= max_size_bits",
            f"max_size_bits = {limits.max_size_bits} -> lambda <= {limits.max_size_bits}",
            f"base = floor(lambda / {SCHEDULE_DENOMINATOR})",
            f"an active call needs base >= 1 -> lambda >= {required}",
            f"max admissible lambda = {maximum} < {required}",
            "therefore base == 0 for every admitted context and the active "
            "numeric preconditions can never be met",
        ],
        "maximum_admissible_lambda": maximum,
        "required_lambda": required,
        "shortfall_bits": required - maximum,
        "schedule_denominator": SCHEDULE_DENOMINATOR,
        "status": ("UNREACHABLE_IN_CURRENT_REPRESENTATION" if maximum < required
                   else "NOT_RULED_OUT_BY_THIS_BOUND"),
        "this_is_a_parameter_contradiction_not_a_theorem": True,
        "source_active_implemented": False,
        "theorem_mode_enabled": False,
    }


@dataclass(frozen=True)
class SymbolicSourceSize:
    """``s = 2**lambda`` described by its exponent, never constructed.

    A scalable stand-in for the manuscript parameters: every quantity the
    schedule needs is a function of ``lambda`` alone, so no graph, ring or
    description of astronomical size is ever allocated.  This is a
    *representation* proposal; nothing here claims the derived bounds hold.
    """
    lambda_value: int

    def __post_init__(self):
        if type(self.lambda_value) is not int or self.lambda_value < 1:
            raise ValueError("lambda must be a positive integer")

    @property
    def size_parameter_exponent(self):
        return self.lambda_value

    @property
    def extension_degree(self):
        return EXTENSION_DEGREE_PER_LAMBDA * self.lambda_value

    @property
    def schedule_base(self):
        return self.lambda_value // SCHEDULE_DENOMINATOR

    @property
    def leaf_threshold_exponent_bound(self):
        # H = ceil(s / floor(sqrt(lambda))) <= s, recorded as an exponent.
        return self.lambda_value

    def refinement_obligations(self):
        return {
            "representation": "s = 2**lambda; never materialized",
            "obligations": [
                "prove parent-to-child derivation is a function of lambda only",
                "prove the width bound at every depth without enumerating modes",
                "prove the shrinking bound as an exponent inequality",
                "connect the symbolic statement to the executed finite code",
            ],
            "discharged": False,
            "theorem_mode_enabled": False,
        }

    def describe(self):
        return {
            "schema": "VERITAS_SYMBOLIC_SOURCE_SIZE_V1",
            "lambda": self.lambda_value,
            "size_parameter_decimal_digits": int(self.lambda_value * 0.30103) + 1,
            "extension_degree": self.extension_degree,
            "schedule_base": self.schedule_base,
            "active": self.schedule_base >= 1,
            "materialized": False,
        }


def source_active_status(context, *, mode="source_leaf"):
    """Regime label and refusal for one context.  Never returns a value."""
    if type(context) is not SourceContext:
        raise TypeError("SourceContext required")
    contradiction = active_parameter_contradiction(context.limits)
    if mode == "theorem":
        return {"regime": SOURCE_THEOREM_PARAMETERIZED,
                "status": THEOREM_STATUS, "theorem_mode_enabled": False,
                "reason": "no source-active executor and no compiled refinement",
                "unreachability": contradiction}
    return {
        "regime": (EXPERIMENTAL_SCALED_FINITE if contradiction["reachable"]
                   else SOURCE_THEOREM_PARAMETERIZED),
        "status": SOURCE_ACTIVE_STATUS,
        "theorem_mode_enabled": False,
        "reason": ("the admitted context cannot satisfy the active schedule; "
                   "bounded finite fixtures are the only executable regime"),
        "lambda": context.lambda_value,
        "extension_degree": context.extension_degree,
        "unreachability": contradiction,
    }


def assert_no_false_active_claim(context):
    """Raise if a context would let a caller claim an active/theorem run."""
    status = source_active_status(context)
    if status["theorem_mode_enabled"]:
        raise AssertionError("theorem mode must stay disabled")
    if status["regime"] == SOURCE_THEOREM_PARAMETERIZED:
        return status
    raise AssertionError(
        "this context unexpectedly reaches the active regime; the hardening "
        "claims in R9.6 assume it cannot")
