"""R9.6 regression tests: the source-active schedule is unreachable.

The shipped ``SourceLimits`` cap the extension degree at 64 by default (4096 is
the largest value the class accepts) and the size parameter at 65536 bits.  The
schedule needs ``lambda = ceil(log2(s)) >= 131072`` before ``base`` is nonzero,
and ``lambda = e/4``.  So no admitted ``SourceContext`` can ever reach
``ACTIVE_NUMERIC_PRECONDITIONS_MET``.

These tests pin the derivation, pin the two separated regime labels, and pin
that neither regime can set a theorem flag.
"""
import pytest

from veritas.research.appendix_d_schedule import schedule_preflight
from veritas.research.tapered_v4.source_regime import (
    EXPERIMENTAL_SCALED_FINITE, SCHEDULE_DENOMINATOR, SOURCE_ACTIVE_STATUS,
    SOURCE_THEOREM_PARAMETERIZED, SymbolicSourceSize,
    active_parameter_contradiction, assert_no_false_active_claim,
    lambda_of, maximum_admissible_lambda, minimum_active_lambda,
    source_active_status)
from veritas.research.tapered_v4.source_state import (
    SourceContext, SourceLimits)


def test_default_limits_cannot_reach_the_active_regime():
    contradiction = active_parameter_contradiction()
    assert contradiction["reachable"] is False
    assert contradiction["status"] == "UNREACHABLE_IN_CURRENT_REPRESENTATION"
    assert contradiction["maximum_admissible_lambda"] == 16
    assert contradiction["required_lambda"] == SCHEDULE_DENOMINATOR == 131072
    assert contradiction["shortfall_bits"] == 131072 - 16


def test_the_largest_supported_limits_still_cannot_reach_it():
    widest = SourceLimits(max_extension_degree=4096, max_size_bits=65536)
    contradiction = active_parameter_contradiction(widest)
    assert contradiction["maximum_admissible_lambda"] == 1024
    assert contradiction["reachable"] is False
    assert contradiction["required_lambda"] == 131072


def test_the_two_walls_are_independent():
    """Even with an unbounded degree the bit cap alone blocks the regime."""
    degree_only = SourceLimits(max_extension_degree=4096, max_size_bits=65536)
    assert degree_only.max_extension_degree // 4 == 1024
    assert degree_only.max_size_bits == 65536 < SCHEDULE_DENOMINATOR
    # lambda = 131072 would need an extension degree of 524288.
    assert 4 * SCHEDULE_DENOMINATOR == 524288


def test_every_admissible_context_gets_base_zero():
    for degree in (4, 64, 256, 1024, 4096):
        limits = SourceLimits(max_extension_degree=degree, max_size_bits=65536)
        widest_lambda = maximum_admissible_lambda(limits)
        assert widest_lambda // SCHEDULE_DENOMINATOR == 0
        assert widest_lambda < minimum_active_lambda()


def test_schedule_preflight_never_reports_active_for_admitted_parameters():
    """A direct check against the production preflight, not the derivation."""
    for lambda_value in (1, 2, 4, 16, 256, 1024):
        s = 1 << lambda_value
        result = schedule_preflight(s, edges=1 << 20, degree=1, depth=0,
                                    size_constant=1, max_size_bits=65536)
        assert result["status"] != "ACTIVE_NUMERIC_PRECONDITIONS_MET", lambda_value


def test_lambda_of_matches_the_definition():
    assert lambda_of(2) == 1
    assert lambda_of(3) == 2
    assert lambda_of(4) == 2
    assert lambda_of(2 ** 131071) == 131071
    with pytest.raises(ValueError):
        lambda_of(1)


def test_symbolic_size_never_materializes_the_parameter():
    symbolic = SymbolicSourceSize(131072)
    described = symbolic.describe()
    assert described["materialized"] is False
    assert described["extension_degree"] == 524288
    assert described["schedule_base"] == 1
    assert described["size_parameter_decimal_digits"] > 39000
    assert symbolic.refinement_obligations()["discharged"] is False


def test_regimes_are_labelled_separately():
    context = SourceContext(2, 1, 1, 1, 1, 1, 19)
    status = source_active_status(context)
    assert status["regime"] == SOURCE_THEOREM_PARAMETERIZED
    assert status["status"] == SOURCE_ACTIVE_STATUS
    assert status["theorem_mode_enabled"] is False
    theorem = source_active_status(context, mode="theorem")
    assert theorem["regime"] == SOURCE_THEOREM_PARAMETERIZED
    assert theorem["theorem_mode_enabled"] is False


def test_no_admitted_context_can_claim_an_active_run():
    for size_parameter, polynomial in ((2, 19), (4, 19), (64, 19), (65536, 19)):
        try:
            context = SourceContext(size_parameter, 1, 1, 1, 1, 1, polynomial)
        except ValueError:
            continue
        status = assert_no_false_active_claim(context)
        assert status["regime"] == SOURCE_THEOREM_PARAMETERIZED
        assert status["theorem_mode_enabled"] is False


def test_the_experimental_label_is_used_only_when_the_bound_is_met():
    """A hypothetical context that *could* be active must not be mislabelled."""
    assert EXPERIMENTAL_SCALED_FINITE != SOURCE_THEOREM_PARAMETERIZED
    contradiction = active_parameter_contradiction()
    assert contradiction["source_active_implemented"] is False
