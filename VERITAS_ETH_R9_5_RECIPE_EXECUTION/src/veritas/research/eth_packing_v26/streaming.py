"""Streaming D.3 conditional-expectation construction.

This module implements the labeling step described in ``lem:tensor-packets``
without retaining an O(M**2) edge-pair table.  It assigns one complete
``[r]^a`` label to each side-specific vertex, in a canonical order, by testing
all labels and recomputing the exact conditional expectation from the edge
list.  The resulting computation is polynomial but can be very expensive; all
work is bounded and resource exhaustion raises ``PackingBudgetExceeded``.

The JSON certificate is a finite-instance execution record.  Its checker is
in ``streaming_check.py`` and uses exact ``Fraction`` probabilities rather
than this module's integer exponent-count formula.  Neither module proves the
universal lemma or the manuscript's outer recursion/complexity claims.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from types import MappingProxyType

from .constructor import d3_preconditions
from .cpp_backend import (
    CPP_BATCH_ALGORITHM_VERSION,
    INT64_MAX,
    CPP_BATCH_WORK_METRIC_VERSION,
    CppBackendUnavailable,
    NATIVE_BACKEND_NAMES,
    PYTHON_ALGORITHM_VERSION,
    UINT64_MAX,
    candidate_score_cpp,
    check_batch_limits,
    resolve_score_backend,
    vertex_scores_ctypes,
    vertex_scores_pybind,
)
from .expectation import PackingBudgetExceeded, max_side_degree, validate_edges
from .implicit import ImplicitPacking


STREAMING_CERT_SCHEMA = "VERITAS_ETH_D3_STREAMING_CERT_V3"
STREAMING_BATCH_CERT_SCHEMA = "VERITAS_ETH_D3_STREAMING_CERT_V4"
MAX_STREAMING_LABEL_DIMENSION = 64


class D3PreconditionsNotMet(ValueError):
    """The pinned active-call inequalities do not hold for this instance."""


@dataclass(frozen=True)
class StreamingPackingBuild:
    packing: ImplicitPacking
    certificate: dict
    work_units: int
    estimated_work_units: int
    backend_fallback_reason: str | None = None


class _Work:
    def __init__(self, limit):
        if limit is not None and (type(limit) is not int or limit < 0):
            raise ValueError("max_work must be a nonnegative integer or None")
        self.limit = limit
        self.used = 0

    def tick(self, amount=1):
        self.used += amount
        if self.limit is not None and self.used > self.limit:
            raise PackingBudgetExceeded("streaming conditional-expectation work budget exceeded")


def _ordered_vertices(edges):
    # Side tags deliberately keep row and column IDs distinct, even if their
    # integer spellings happen to be equal.
    rows = sorted({u for u, _ in edges})
    cols = sorted({v for _, v in edges})
    return tuple([("R", v) for v in rows] + [("C", v) for v in cols])


def _candidate_score(edges, partial, *, r, a, D, vertex, label, work):
    """Return D times the conditional E[sum_gamma X_gamma^2].

    For each unordered edge pair, compute its equality probability by counting
    still-random side-coordinate comparisons.  This is intentionally a direct
    streaming calculation: no pair records or endpoint update table survive
    between candidates.
    """
    def value(side, ident, coordinate):
        if (side, ident) == vertex:
            return label[coordinate]
        return partial.get((side, ident, coordinate))

    m = len(edges)
    total = m * D
    for i, (u, v) in enumerate(edges):
        for w, z in edges[:i]:
            work.tick()
            unknown = 0
            possible = True
            for d in range(a):
                for side, left, right in (("R", u, w), ("C", v, z)):
                    if left == right:
                        continue
                    x = value(side, left, d)
                    y = value(side, right, d)
                    work.tick()
                    if x is not None and y is not None:
                        if x != y:
                            possible = False
                            break
                    else:
                        unknown += 1
                if not possible:
                    break
            if possible:
                total += 2 * (D // (r ** unknown))
    return total


def estimated_streaming_work(edges, *, r, a):
    """Conservative pair-coordinate work bound for the direct implementation."""
    edges = validate_edges(edges)
    if (type(r) is not int or r < 2 or type(a) is not int or
            not 1 <= a <= MAX_STREAMING_LABEL_DIMENSION):
        raise ValueError("invalid radix or label dimension")
    variables = len(_ordered_vertices(edges))
    candidates = r ** a
    pair_count = len(edges) * (len(edges) - 1) // 2
    # One pair visit plus at most two comparisons per coordinate, plus one
    # candidate bookkeeping unit.  This is an executable-work estimate, not
    # bit complexity or a timing guarantee.
    score_cost = 1 + pair_count * (1 + 2 * a)
    # Include the unconditional initial-score pass as well.
    return (variables * candidates + 1) * score_cost


def estimated_batch_streaming_work(edges, *, r, a):
    """Conservative bound for the versioned native batch work metric.

    Each vertex step classifies every unordered pair once, evaluates all pairs
    once for the parent score, evaluates candidate-dependent pairs for each
    label, and charges candidate bookkeeping. A pair score charges at most one
    visit and two comparisons per coordinate. Allocation and bit work are not
    included.
    """
    edges = validate_edges(edges)
    if (type(r) is not int or r < 2 or type(a) is not int or
            not 1 <= a <= MAX_STREAMING_LABEL_DIMENSION):
        raise ValueError("invalid radix or label dimension")
    vertices = len(_ordered_vertices(edges))
    candidates = r ** a
    pairs = len(edges) * (len(edges) - 1) // 2
    score_cost = 1 + 2 * a
    per_vertex = pairs + (candidates + 1) * pairs * score_cost + candidates
    return pairs * score_cost + vertices * per_vertex


def _pybind_tables(edges, partial, r, a):
    """Flat assignment tables for the pybind11 entry point."""
    from .cpp_backend import _flat_inputs
    rows, columns, row_values, column_values, _side, _id = _flat_inputs(
        edges, partial, r, a, ("", -1))
    return rows, row_values, columns, column_values


def _side_code(vertex):
    return {"": 2, "R": 0, "C": 1}[vertex[0]]


def _native_vertex_scores(name, handle, edges, partial, *, r, a, vertex, max_work):
    if name == "cpp-pybind":
        return vertex_scores_pybind(edges, partial, r=r, a=a, vertex=vertex,
                                    max_work=max_work, module=handle)
    return vertex_scores_ctypes(edges, partial, r=r, a=a, vertex=vertex,
                                max_work=max_work, handle=handle)


def construct_streaming_d3_packing(
    edges, *, r=64, a=1, max_work=30_000_000,
    max_candidate_evaluations=1_000_000, require_paper_conditions=False,
    score_backend="python",
):
    """Build a sparse implicit packet packing and a replayable certificate.

    ``require_paper_conditions=True`` checks the three packing inequalities
    using the graph's actual maximum degree and requires radix 64. It does
    not check the manuscript's size, global degree bound, or depth schedule.
    Set it false for bounded finite
    mechanism experiments.  Resource limits fail before construction when
    the conservative estimate exceeds the selected budget.
    """
    edges = validate_edges(edges)
    if type(r) is not int or not 2 <= r <= 64 or type(a) is not int or a < 1:
        raise ValueError("unsupported radix or label dimension")
    if a > MAX_STREAMING_LABEL_DIMENSION:
        raise PackingBudgetExceeded("streaming label dimension exceeds the explicit cap")
    if type(require_paper_conditions) is not bool:
        raise ValueError("require_paper_conditions must be Boolean")
    if score_backend not in ("python", "cpp", "auto"):
        raise ValueError("score_backend must be one of: python, cpp, auto")
    if max_work is not None and (type(max_work) is not int or max_work < 0):
        raise ValueError("max_work must be a nonnegative integer or None")
    if require_paper_conditions and r != 64:
        raise ValueError("the pinned manuscript uses radix 64")
    if type(max_candidate_evaluations) is not int or max_candidate_evaluations < 0:
        raise ValueError("max_candidate_evaluations must be nonnegative")

    m = len(edges)
    delta = max_side_degree(edges)
    conditions = d3_preconditions(m, r, a, delta)
    eligible = all(conditions[k] for k in (
        "M_ge_2_D_squared_delta", "M_ge_LD", "2L_le_delta"))
    if require_paper_conditions and not eligible:
        raise D3PreconditionsNotMet(
            "INCONCLUSIVE_D3_PRECONDITIONS: eq:tensor-packing-conditions fail")

    candidate_count = r ** a
    variable_order = _ordered_vertices(edges)
    total_candidate_evaluations = len(variable_order) * candidate_count
    if total_candidate_evaluations > max_candidate_evaluations:
        raise PackingBudgetExceeded(
            "streaming label candidate count exceeds resource budget")
    selected_backend, backend_handle = resolve_score_backend(score_backend)
    # The native ABI transports vertex ids as int64.  `auto` means "native when
    # usable", so fall back to the reference for wider ids and record why; an
    # explicit `cpp` request still fails closed.
    backend_fallback = None
    if selected_backend in NATIVE_BACKEND_NAMES and any(
            max(u, v) > INT64_MAX for u, v in edges):
        if score_backend == "cpp":
            raise ValueError(
                "C++ scorer vertex IDs must fit a nonnegative int64; "
                "use score_backend='python' or 'auto'")
        backend_fallback = "vertex_id_exceeds_int64"
        selected_backend, backend_handle = "python", None
    if selected_backend in NATIVE_BACKEND_NAMES:
        estimate = estimated_batch_streaming_work(edges, r=r, a=a)
        check_batch_limits(edges, radix=r, dimension=a,
                           total_work_bound=estimate)
    else:
        estimate = estimated_streaming_work(edges, r=r, a=a)
    if max_work is not None and estimate > max_work:
        raise PackingBudgetExceeded(
            f"streaming work estimate {estimate} exceeds {max_work}")
    work = _Work(max_work)

    D = r ** (2 * a)
    partial = {}

    def score_candidate(vertex, label):
        if selected_backend == "python":
            return _candidate_score(edges, partial, r=r, a=a, D=D,
                                     vertex=vertex, label=label, work=work)
        remaining = None if work.limit is None else work.limit - work.used
        if selected_backend == "cpp-pybind":
            symbols = list(label) if len(label) else [0] * a
            text, charged = backend_handle.candidate_score(
                r, a, [edge[0] for edge in edges], [edge[1] for edge in edges],
                *_pybind_tables(edges, partial, r, a), _side_code(vertex),
                vertex[1], symbols,
                UINT64_MAX if remaining is None else min(remaining, UINT64_MAX))
            score = int(text)
        else:
            score, charged = candidate_score_cpp(
                edges, partial, r=r, a=a, D=D, vertex=vertex, label=label,
                max_work=remaining, function=backend_handle[1])
        work.tick(charged)
        return score

    initial = score_candidate(("", -1), ())
    previous = initial
    steps = []
    for side, vertex_id in variable_order:
        best = None
        score_sum = 0
        if selected_backend in NATIVE_BACKEND_NAMES:
            remaining = None if work.limit is None else max(0, work.limit - work.used)
            scores, _parent, charged = _native_vertex_scores(
                selected_backend, backend_handle, edges, partial, r=r, a=a,
                vertex=(side, vertex_id), max_work=remaining)
            work.tick(charged)
            if _parent != previous:
                raise AssertionError("native parent score differs from the prior exact expectation")
            for label, score in zip(product(range(r), repeat=a), scores):
                score_sum += score
                candidate = (score, label)
                if best is None or candidate < best:
                    best = candidate
        else:
            for label in product(range(r), repeat=a):
                work.tick()
                score = score_candidate((side, vertex_id), label)
                score_sum += score
                candidate = (score, label)
                if best is None or candidate < best:
                    best = candidate
        if best is None:
            raise AssertionError("nonempty label alphabet produced no candidate")
        # Averaging over all complete vertex labels must recover the previous
        # conditional expectation.  Check this identity during construction.
        if score_sum != previous * candidate_count:
            raise AssertionError("candidate conditional expectations do not average to the parent")
        score, label = best
        if score > previous:
            raise AssertionError("conditional expectation increased")
        for coordinate, symbol in enumerate(label):
            partial[(side, vertex_id, coordinate)] = symbol
        steps.append({"side": side, "vertex": vertex_id,
                      "label": list(label), "expected_square_scaled": score})
        previous = score

    rows = {v: tuple(partial[("R", v, d)] for d in range(a))
            for side, v in variable_order if side == "R"}
    cols = {v: tuple(partial[("C", v, d)] for d in range(a))
            for side, v in variable_order if side == "C"}
    classes = {}
    for edge_id, (u, v) in enumerate(edges):
        classes.setdefault((rows[u], cols[v]), []).append(edge_id)
    classes = {key: tuple(ids) for key, ids in classes.items()}
    L = 1 << a
    maximum = max((len(ids) for ids in classes.values()), default=0)
    H = ((maximum + L - 1) // L) * L
    packing = ImplicitPacking(
        edges, r, a, H, MappingProxyType(rows), MappingProxyType(cols),
        MappingProxyType(classes), initial, previous,
        (),
    )

    is_native = selected_backend in NATIVE_BACKEND_NAMES
    certificate = {
        "schema": STREAMING_BATCH_CERT_SCHEMA if is_native else STREAMING_CERT_SCHEMA,
        "algorithm_version": (
            CPP_BATCH_ALGORITHM_VERSION if is_native
            else PYTHON_ALGORITHM_VERSION),
        "score_backend_requested": score_backend,
        "score_backend": selected_backend,
        "claim": "FINITE_STREAMING_D3_CONDITIONAL_EXPECTATION_EXECUTION",
        "paper_labels": ["lem:tensor-packets", "eq:tensor-packing-conditions"],
        "r": r, "a": a, "L": L, "D": D, "M": m, "delta": delta,
        "H_pad": H, "edges": [list(edge) for edge in edges],
        "row_labels": {str(k): list(v) for k, v in sorted(rows.items())},
        "column_labels": {str(k): list(v) for k, v in sorted(cols.items())},
        "steps": steps,
        "initial_expected_square_scaled": initial,
        "final_square_scaled": previous,
        "preconditions": conditions,
        "paper_preconditions_required": require_paper_conditions,
        "eligible_at_this_instance": eligible,
        "fixed_manuscript_radix": r == 64,
        # No s, depth, or source Delta is supplied, so active-call eligibility
        # cannot be inferred even when the local packing inequalities hold.
        "paper_active_call_eligible": False,
        "policy": ({"max_work": max_work,
                    "max_candidate_evaluations": max_candidate_evaluations,
                    "work_metric_version": CPP_BATCH_WORK_METRIC_VERSION}
                   if is_native else
                   {"max_work": max_work,
                    "max_candidate_evaluations": max_candidate_evaluations}),
        "work_units": work.used,
        "estimated_work_units": estimate,
        "resource_ledger": {
            "work_unit_definition": (
                "batch pair classification, exact pair-score visits, coordinate comparisons, and candidate bookkeeping"
                if is_native else
                "edge-pair visits, coordinate comparisons, and candidate bookkeeping"),
            "peak_memory_measured": False,
            "bit_complexity_complete": False,
            "time_bound_claimed": False,
            **({"work_metric_version": CPP_BATCH_WORK_METRIC_VERSION} if is_native else {}),
        },
    }
    return StreamingPackingBuild(packing, certificate, work.used, estimate,
                                 backend_fallback)


def construct_active_call_streaming_packing(
    edges, *, a, max_work=30_000_000,
    max_candidate_evaluations=1_000_000,
    score_backend="python",
):
    """Check fixed-radix packing-lemma inequalities for one finite graph.

    Numeric hypotheses are evaluated before the labeler is invoked. A result
    object is returned only after the separate rational checker validates the
    complete finite trace and packet/load claims. This proves only the
    certificate instance; it does not turn the Python routine into a universal
    proof of ``lem:tensor-packets``. The API does not receive the source
    schedule, so a successful replay is not an eligible active-call proof.
    """
    edges = validate_edges(edges)
    if type(a) is not int or a < 1:
        raise ValueError("invalid label dimension")
    if a > MAX_STREAMING_LABEL_DIMENSION:
        return {
            "status": "INCONCLUSIVE_RESOURCE_LIMIT",
            "reason": "streaming label dimension exceeds the explicit cap",
            "preconditions": None,
            "packing": None,
            "certificate": None,
            "universal_packing_lemma_proven": False,
        }
    m = len(edges)
    delta = max_side_degree(edges)
    conditions = d3_preconditions(m, 64, a, delta)
    if not all(conditions[k] for k in (
            "M_ge_2_D_squared_delta", "M_ge_LD", "2L_le_delta")):
        return {
            "status": "INCONCLUSIVE_D3_PRECONDITIONS",
            "preconditions": conditions,
            "packing": None,
            "certificate": None,
            "universal_packing_lemma_proven": False,
        }
    try:
        built = construct_streaming_d3_packing(
            edges, r=64, a=a, max_work=max_work,
            max_candidate_evaluations=max_candidate_evaluations,
            require_paper_conditions=True, score_backend=score_backend)
    except CppBackendUnavailable as exc:
        return {
            "status": "INCONCLUSIVE_CPP_BACKEND_UNAVAILABLE",
            "preconditions": conditions,
            "reason": str(exc),
            "packing": None,
            "certificate": None,
            "universal_packing_lemma_proven": False,
        }
    except PackingBudgetExceeded as exc:
        return {
            "status": "INCONCLUSIVE_RESOURCE_LIMIT",
            "preconditions": conditions,
            "reason": str(exc),
            "packing": None,
            "certificate": None,
            "universal_packing_lemma_proven": False,
        }
    from .streaming_check import verify_streaming_d3_certificate
    checked = verify_streaming_d3_certificate(
        built.certificate,
        max_work=max_work,
        max_candidate_evaluations=max_candidate_evaluations)
    if (checked.get("valid") is not True or
            any(checked.get(key) is not True for key in (
                "numeric_active_call_inequalities", "initial_variance_bound",
                "packet_count_bound", "port_load_bound"))):
        return {
            "status": "INCONCLUSIVE_CERTIFICATE_REPLAY",
            "preconditions": conditions,
            "verification": checked,
            "packing": None,
            "certificate": None,
            "universal_packing_lemma_proven": False,
        }
    return {
        "status": "FINITE_PACKING_LEMMA_INSTANCE_REPLAYED",
        "preconditions": conditions,
        "verification": checked,
        "packing": built.packing,
        "certificate": built.certificate,
        "universal_packing_lemma_proven": False,
    }

