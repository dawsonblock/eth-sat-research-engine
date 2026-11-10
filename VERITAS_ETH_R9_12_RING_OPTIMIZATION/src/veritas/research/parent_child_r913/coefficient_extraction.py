"""Structure-aware exact coefficient extraction (research prototype).

**Problem B:** recover A_β (and source column powers) for one exponent β at fixed
Boolean bits — what ``evaluate_compiled`` must preserve — without always building
the full exponent support.

**Problem A** (truncated aggregate) lives in ``truncated_weighted_resummation``.

Provides reference expansion, separator elimination on row factor graphs, and
cost telemetry. No general polynomial-time claim; permanent barriers apply.

No ETH theorem or subexponential bound is claimed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping, Sequence, Tuple

from veritas.research.parent_child_r912.elimination import (
    EliminationBudget,
    plan_order,
    verify_order,
)
from veritas.research.parent_child_r913.algebraic_resummation import (
    Exponent,
    RowFactor,
    expand_packet_polynomial,
)
from veritas.research.parent_child_r913.dependency_analyzer import (
    mode_factor_graph_from_modes,
)
from veritas.research.tapered_v4.source_recipes import CompiledEntry

from .research_spec import PacketQuantityKind


@dataclass(frozen=True)
class ExtractionStateEstimate:
    """Symbolic separator cost sketch (not a treewidth certificate)."""

    target_beta: Exponent
    mode_count: int
    factor_rows: int
    elimination_width: int
    max_table_entries: int
    predicted_work: int
    boolean_separator_states: int
    exponent_tracking_multiplier: int
    qualification: str = "heuristic_mode_elimination_width_sketch"


@dataclass(frozen=True)
class SeparatorExtractionStats:
    elimination_width: int
    max_monomial_table: int
    peak_monomial_table: int
    variable_eliminations: int
    join_count: int
    work_ticks: int
    fits_plan: bool


@dataclass(frozen=True)
class SeparatorExtractionResult:
    value: object
    stats: SeparatorExtractionStats
    order: Tuple[int, ...]
    qualification: str = "exact_separator_elimination_bounded_factors"


ExponentKey = Tuple[int, ...]


@dataclass
class _FactorPoly:
    variables: Tuple[int, ...]
    terms: Dict[ExponentKey, object]


def _tick(ar, n: int = 1) -> None:
    budget = getattr(ar, "budget", None)
    if budget is not None:
        budget.tick(n)


def _row_factors_to_polys(
    factors: Sequence[RowFactor],
    ar,
) -> Tuple[List[_FactorPoly], List[object]]:
    """Row scopes plus constant-only scalars to multiply at the end."""
    polys: List[_FactorPoly] = []
    scalars: List[object] = []
    zero = ar.ring.zero
    for factor in factors:
        variables = tuple(
            j for j, coeff in enumerate(factor.mode_coefficients) if coeff != zero
        )
        if not variables:
            scalars.append(factor.constant)
            continue
        terms: Dict[ExponentKey, object] = {tuple(0 for _ in variables): factor.constant}
        for index, mode in enumerate(variables):
            exp = tuple(1 if k == index else 0 for k in range(len(variables)))
            terms[exp] = factor.mode_coefficients[mode]
        polys.append(_FactorPoly(variables, terms))
    return polys, scalars


def _multiply_polys(
    left: _FactorPoly,
    right: _FactorPoly,
    target_beta: Exponent,
    ar,
) -> _FactorPoly:
    union = tuple(sorted(set(left.variables) | set(right.variables)))
    pos = {v: i for i, v in enumerate(union)}
    lpos = {v: i for i, v in enumerate(left.variables)}
    rpos = {v: i for i, v in enumerate(right.variables)}
    zero = ar.ring.zero
    merged: Dict[ExponentKey, object] = {}
    _tick(ar, len(left.terms) * len(right.terms))
    for lexp, lcoef in left.terms.items():
        for rexp, rcoef in right.terms.items():
            acc = [0] * len(union)
            for variable, index in lpos.items():
                acc[pos[variable]] += lexp[index]
            for variable, index in rpos.items():
                acc[pos[variable]] += rexp[index]
            if any(acc[pos[v]] > target_beta[v] for v in union):
                continue
            key = tuple(acc)
            merged[key] = ar.add(merged.get(key, zero), ar.mul(lcoef, rcoef))
    return _FactorPoly(union, merged)


def _multiply_many(
    polys: Sequence[_FactorPoly],
    target_beta: Exponent,
    ar,
) -> _FactorPoly:
    if not polys:
        raise ValueError("empty polynomial join")
    current = polys[0]
    for nxt in polys[1:]:
        current = _multiply_polys(current, nxt, target_beta, ar)
    return current


def _eliminate_at_variable(
    poly: _FactorPoly,
    variable: int,
    target_beta: Exponent,
    ar,
) -> _FactorPoly:
    if variable not in poly.variables:
        if target_beta[variable] != 0:
            return _FactorPoly((), {})
        return poly
    vi = poly.variables.index(variable)
    need = target_beta[variable]
    frontier = tuple(v for v in poly.variables if v != variable)
    zero = ar.ring.zero
    out: Dict[ExponentKey, object] = {}
    _tick(ar, len(poly.terms))
    for exp, coef in poly.terms.items():
        if exp[vi] != need:
            continue
        key = tuple(exp[i] for i, v in enumerate(poly.variables) if v != variable)
        out[key] = ar.add(out.get(key, zero), coef)
    return _FactorPoly(frontier, out)


def _scopes_from_polys(polys: Sequence[_FactorPoly]) -> Tuple[Tuple[int, ...], ...]:
    return tuple(poly.variables for poly in polys)


def target_coefficient_by_expansion(
    factors: Sequence[RowFactor],
    target_beta: Exponent,
    ar,
    *,
    max_monomials: int = 50_000,
):
    """Reference problem-B value: coefficient at ``target_beta`` from full expansion."""
    poly = expand_packet_polynomial(
        factors, ar, max_monomials=max_monomials, mode_count=len(target_beta)
    )
    return poly.get(target_beta, ar.ring.zero)


def target_coefficient_by_separator_elimination(
    factors: Sequence[RowFactor],
    target_beta: Exponent,
    ar,
    *,
    budget: EliminationBudget | None = None,
    heuristic: str = "min_fill",
) -> SeparatorExtractionResult:
    """Exact A_β via variable elimination on the row factor graph (problem B)."""
    if not factors:
        raise ValueError("at least one row factor required")
    mode_count = len(factors[0].mode_coefficients)
    if len(target_beta) != mode_count:
        raise ValueError("target_beta length mismatch")
    if any(b < 0 for b in target_beta):
        raise ValueError("negative exponent in target_beta")
    budget = EliminationBudget() if budget is None else budget
    polys, scalars = _row_factors_to_polys(factors, ar)
    variables = sorted({v for poly in polys for v in poly.variables})
    zero = ar.ring.zero
    active = set(variables)
    for mode_index, need in enumerate(target_beta):
        if need <= 0:
            continue
        if mode_index not in active:
            stats = SeparatorExtractionStats(
                0, 1, 1, 0, 0, 0, True
            )
            return SeparatorExtractionResult(zero, stats, tuple())
        rows_touching = sum(1 for poly in polys if mode_index in poly.variables)
        if need > rows_touching:
            stats = SeparatorExtractionStats(
                0, 1, 1, 0, 0, 0, True
            )
            return SeparatorExtractionResult(zero, stats, tuple())
    if not variables:
        one = ar.ring.one
        total = one
        for scalar in scalars:
            total = ar.mul(total, scalar)
        stats = SeparatorExtractionStats(
            elimination_width=0,
            max_monomial_table=1,
            peak_monomial_table=1,
            variable_eliminations=0,
            join_count=0,
            work_ticks=0,
            fits_plan=True,
        )
        return SeparatorExtractionResult(total, stats, tuple())

    scopes = _scopes_from_polys(polys)
    order = plan_order(scopes, tuple(variables), heuristic)
    plan = verify_order(scopes, tuple(variables), order, budget)

    peak = max((len(p.terms) for p in polys), default=1)
    largest = peak
    joins = 0
    work = 0

    for variable in order:
        joined = [p for p in polys if variable in p.variables]
        if not joined:
            if target_beta[variable] != 0:
                zero = ar.ring.zero
                stats = SeparatorExtractionStats(
                    elimination_width=int(plan["width"]),
                    max_monomial_table=largest,
                    peak_monomial_table=peak,
                    variable_eliminations=len(order),
                    join_count=joins,
                    work_ticks=work,
                    fits_plan=bool(plan["fits"]),
                )
                return SeparatorExtractionResult(zero, stats, order)
            continue
        joins += 1
        combined = _multiply_many(joined, target_beta, ar)
        if not combined.terms:
            zero = ar.ring.zero
            stats = SeparatorExtractionStats(
                elimination_width=int(plan["width"]),
                max_monomial_table=largest,
                peak_monomial_table=peak,
                variable_eliminations=len(order),
                join_count=joins,
                work_ticks=work,
                fits_plan=bool(plan["fits"]),
            )
            return SeparatorExtractionResult(zero, stats, order)
        work += len(combined.terms)
        peak = max(peak, len(combined.terms))
        largest = max(largest, len(combined.terms))
        projected = _eliminate_at_variable(combined, variable, target_beta, ar)
        if not projected.terms:
            zero = ar.ring.zero
            stats = SeparatorExtractionStats(
                elimination_width=int(plan["width"]),
                max_monomial_table=largest,
                peak_monomial_table=peak,
                variable_eliminations=len(order),
                join_count=joins,
                work_ticks=work,
                fits_plan=bool(plan["fits"]),
            )
            return SeparatorExtractionResult(zero, stats, order)
        polys = [p for p in polys if variable not in p.variables] + [projected]
        peak = max(peak, len(projected.terms))

    zero = ar.ring.zero
    one = ar.ring.one
    total = one
    for poly in polys:
        if poly.variables:
            return SeparatorExtractionResult(
                zero,
                SeparatorExtractionStats(
                    elimination_width=int(plan["width"]),
                    max_monomial_table=largest,
                    peak_monomial_table=peak,
                    variable_eliminations=len(order),
                    join_count=joins,
                    work_ticks=work,
                    fits_plan=bool(plan["fits"]),
                ),
                order,
            )
        if not poly.terms:
            return SeparatorExtractionResult(
                zero,
                SeparatorExtractionStats(
                    elimination_width=int(plan["width"]),
                    max_monomial_table=largest,
                    peak_monomial_table=peak,
                    variable_eliminations=len(order),
                    join_count=joins,
                    work_ticks=work,
                    fits_plan=bool(plan["fits"]),
                ),
                order,
            )
        for coef in poly.terms.values():
            total = ar.mul(total, coef)
    for scalar in scalars:
        total = ar.mul(total, scalar)

    stats = SeparatorExtractionStats(
        elimination_width=int(plan["width"]),
        max_monomial_table=largest,
        peak_monomial_table=peak,
        variable_eliminations=len(order),
        join_count=joins,
        work_ticks=work,
        fits_plan=bool(plan["fits"]),
    )
    return SeparatorExtractionResult(total, stats, order)


def target_coefficient_with_sources(
    compiled: CompiledEntry,
    bits: Tuple[int, ...],
    factors: Sequence[RowFactor],
    target_beta: Exponent,
    ar,
    *,
    budget: EliminationBudget | None = None,
) -> SeparatorExtractionResult:
    """Row factor separator coefficient times source-column powers (production shape)."""
    extracted = target_coefficient_by_separator_elimination(
        factors, target_beta, ar, budget=budget
    )
    if extracted.value == ar.ring.zero:
        return extracted
    _rows, cols, _local, _targets, sources = compiled.data
    coeff = extracted.value
    for beta, col_coeffs in sources:
        if not beta:
            continue
        source = ar.ring.zero
        for pos, scalar in zip(cols, col_coeffs):
            if bits[pos]:
                source = ar.add(source, ar.ring.elem([[scalar]]))
        coeff = ar.mul(coeff, ar.power(source, beta))
    return SeparatorExtractionResult(coeff, extracted.stats, extracted.order)


def target_coefficient_by_separator_elimination_int(
    constants: Sequence[int],
    coefficients: Sequence[Sequence[int]],
    target_beta: Exponent,
    modulus: int,
) -> Tuple[int, SeparatorExtractionStats]:
    """Integer separator extractor for randomized and large-instance checks."""
    zero, one = 0, 1 % modulus

    def add(a, b):
        return (a + b) % modulus

    def mul(a, b):
        return (a * b) % modulus

    int_ring = type("Ring", (), {"zero": zero, "one": one})()

    class _AR:
        budget = None
        ring = int_ring

        @staticmethod
        def add(a, b):
            return add(a, b)

        @staticmethod
        def mul(a, b):
            return mul(a, b)

    ar = _AR()
    mode_count = len(target_beta)
    factors = tuple(
        RowFactor(
            constants[r] % modulus,
            tuple(int(coefficients[r][j]) % modulus for j in range(mode_count)),
        )
        for r in range(len(constants))
    )
    result = target_coefficient_by_separator_elimination(factors, target_beta, ar)
    return result.value, result.stats


def estimate_extraction_state(
    modes: Sequence[dict],
    target_beta: Exponent,
    *,
    row_certificate: dict | None = None,
    budget: EliminationBudget | None = None,
    heuristic: str = "min_fill",
) -> ExtractionStateEstimate:
    """Upper-bound style estimate for separator DP on mode factor graph."""
    budget = EliminationBudget() if budget is None else budget
    graph = mode_factor_graph_from_modes(modes, row_certificate=row_certificate)
    order = plan_order(graph.scopes, graph.variables, heuristic)
    certificate = verify_order(graph.scopes, graph.variables, order, budget)
    max_exp = max(target_beta) if target_beta else 0
    exp_multiplier = max_exp + 1 if max_exp > 1 else 1
    bool_states = certificate["max_table_entries"]
    return ExtractionStateEstimate(
        target_beta=target_beta,
        mode_count=len(modes),
        factor_rows=len(graph.scopes),
        elimination_width=int(certificate["width"]),
        max_table_entries=int(certificate["max_table_entries"]),
        predicted_work=int(certificate["predicted_work"]),
        boolean_separator_states=bool_states,
        exponent_tracking_multiplier=exp_multiplier,
    )


def extraction_report(
    compiled: CompiledEntry,
    factors: Sequence[RowFactor],
    target_beta: Exponent,
    modes: Sequence[dict],
    ar,
    *,
    row_certificate: dict | None = None,
    budget: EliminationBudget | None = None,
    skip_expansion_reference: bool = False,
) -> Dict[str, object]:
    """Compare quantity kinds for one packet (bounded diagnostics)."""
    estimate = estimate_extraction_state(
        modes, target_beta, row_certificate=row_certificate, budget=budget
    )
    extracted = target_coefficient_by_separator_elimination(
        factors, target_beta, ar, budget=budget or EliminationBudget()
    )
    agrees = None
    if not skip_expansion_reference and len(target_beta) <= 18:
        reference = target_coefficient_by_expansion(
            factors,
            target_beta,
            ar,
            max_monomials=min(50_000, 1 << min(20, len(target_beta) + 4)),
        )
        agrees = extracted.value == reference
    return {
        "schema": "VERITAS_R913_COEFFICIENT_EXTRACTION_DIAG_V1",
        "quantity_kinds": [k.value for k in PacketQuantityKind],
        "target_beta": list(target_beta),
        "target_kind": PacketQuantityKind.TARGET_COEFFICIENT.value,
        "aggregate_kind": PacketQuantityKind.TRUNCATED_WEIGHTED_AGGREGATE.value,
        "separator_agrees_with_expansion": agrees,
        "state_estimate": {
            "elimination_width": estimate.elimination_width,
            "max_table_entries": estimate.max_table_entries,
            "boolean_separator_states": estimate.boolean_separator_states,
            "exponent_tracking_multiplier": estimate.exponent_tracking_multiplier,
            "effective_state_upper_bound": (
                estimate.boolean_separator_states * estimate.exponent_tracking_multiplier
            ),
            "predicted_work": estimate.predicted_work,
            "qualification": estimate.qualification,
        },
        "measured_separator": {
            "elimination_width": extracted.stats.elimination_width,
            "max_monomial_table": extracted.stats.max_monomial_table,
            "peak_monomial_table": extracted.stats.peak_monomial_table,
            "join_count": extracted.stats.join_count,
            "work_ticks": extracted.stats.work_ticks,
            "fits_plan": extracted.stats.fits_plan,
        },
        "row_count": len(factors),
        "mode_count": len(modes),
        "source_qualified": False,
        "subexponential_bound_evidence": False,
        "separator_extractor_implemented": True,
    }
