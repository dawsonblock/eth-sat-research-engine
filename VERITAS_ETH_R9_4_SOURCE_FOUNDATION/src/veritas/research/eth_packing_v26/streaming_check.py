"""Independent exact replay for streaming D.3 labeling certificates.

This module intentionally does not import the production labeler, its score
formula, the packet constructor, or its precondition helper.  It recomputes
each conditional expectation as a sum of ``Fraction`` collision
probabilities, enumerates all complete labels of each next vertex, and checks
the canonical minimizer.  The only shared representation convention is that
an edge is a pair ``(row_vertex_id, column_vertex_id)`` and sides are distinct.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from fractions import Fraction
from itertools import product


SCHEMA = "VERITAS_ETH_D3_STREAMING_CERT_V3"
NATIVE_BATCH_SCHEMA = "VERITAS_ETH_D3_STREAMING_CERT_V4"
PREVIOUS_SCHEMA = "VERITAS_ETH_D3_STREAMING_CERT_V2"
LEGACY_SCHEMA = "VERITAS_ETH_D3_STREAMING_CERT_V1"
BACKEND_ALGORITHMS = {
    "python": "d3-streaming-python-direct-v1",
    "cpp": "d3-streaming-cpp-direct-v1",
}
NATIVE_BATCH_ALGORITHMS = {
    "cpp-pybind": "d3-cpp20-direct-v1+batch-v1",
    "cpp-ctypes": "d3-cpp20-direct-v1+batch-v1",
}
NATIVE_BATCH_WORK_METRIC = "d3-batch-pair-score-work-v1"


def _vertices(edge_list):
    left = sorted({edge[0] for edge in edge_list})
    right = sorted({edge[1] for edge in edge_list})
    return [("R", x) for x in left] + [("C", x) for x in right]


def _reference_score(edge_list, fixed, radix, dimension, trial_vertex,
                     trial_label, tick):
    """Scaled expected squared class load via rational event probabilities."""
    def assignment(side, vertex, coordinate):
        if (side, vertex) == trial_vertex:
            return trial_label[coordinate]
        return fixed.get((side, vertex, coordinate))

    expected_square = Fraction(len(edge_list), 1)
    for i in range(len(edge_list)):
        row_i, col_i = edge_list[i]
        for j in range(i):
            tick(1)
            row_j, col_j = edge_list[j]
            chance = Fraction(1, 1)
            for coordinate in range(dimension):
                for side, x, y in (("R", row_i, row_j),
                                   ("C", col_i, col_j)):
                    if x == y:
                        continue
                    sx = assignment(side, x, coordinate)
                    sy = assignment(side, y, coordinate)
                    tick(1)
                    if sx is not None and sy is not None:
                        if sx != sy:
                            chance = Fraction(0, 1)
                            break
                    else:
                        chance /= radix
                if chance == 0:
                    break
            expected_square += 2 * chance
    scaled = expected_square * (radix ** (2 * dimension))
    if scaled.denominator != 1:
        raise ValueError("reference scaled expectation is not integral")
    return scaled.numerator


def _packing_layout(edge_list, row_labels, col_labels, radix, dimension,
                    packet_width, padded_height):
    """Check class padding and reconstruct unique implicit packet addresses."""
    grouped = defaultdict(list)
    for eid, (u, v) in enumerate(edge_list):
        grouped[(tuple(row_labels[u]), tuple(col_labels[v]))].append(eid)
    max_class = max((len(ids) for ids in grouped.values()), default=0)
    expected_height = ((max_class + packet_width - 1) // packet_width) * packet_width
    if padded_height != expected_height:
        raise ValueError("uniform padded class height mismatch")

    addresses = set()
    for (row, col), ids in grouped.items():
        unordered = tuple((min(x, y), max(x, y)) for x, y in zip(row, col))
        equal_coordinates = [d for d, (x, y) in enumerate(unordered) if x == y]
        for position, eid in enumerate(ids):
            packet_index, copy = divmod(position, 1 << len(equal_coordinates))
            orientation = sum((int(row[d] > col[d]) << d)
                              for d in range(dimension))
            copy_bits = sum(((copy >> bit) & 1) << d
                            for bit, d in enumerate(equal_coordinates))
            slot = orientation | copy_bits
            address = (unordered, packet_index, slot)
            if address in addresses:
                raise ValueError("two wires occupy the same packet slot")
            addresses.add(address)
            if not 0 <= slot < packet_width or eid < 0:
                raise ValueError("invalid packet slot assignment")
    if len(addresses) != len(edge_list):
        raise ValueError("packet embedding omits a wire")
    return grouped


def _pair_score_work(edge_i, edge_j, fixed, dimension, current, candidate,
                     tick):
    """Independently count the pair/coordinate visits in one candidate scan.

    This is used only to replay the native V4 work metric.  It does not call
    either production scorer and does not determine the score; the score is
    recomputed separately with rational probabilities in ``_reference_score``.
    """
    row_i, col_i = edge_i
    row_j, col_j = edge_j
    used = 1  # unordered pair visit
    tick(1)
    for coordinate in range(dimension):
        for side, left, right in (("R", row_i, row_j), ("C", col_i, col_j)):
            if left == right:
                continue
            used += 1
            tick(1)
            x = candidate[coordinate] if (side, left) == current else fixed.get(
                (side, left, coordinate))
            y = candidate[coordinate] if (side, right) == current else fixed.get(
                (side, right, coordinate))
            if x is not None and y is not None and x != y:
                return used
    return used


def _parent_pair_work(edge_i, edge_j, fixed, dimension, current, tick):
    """Count the native parent-score scan, including mismatch short circuits."""
    row_i, col_i = edge_i
    row_j, col_j = edge_j
    used = 1
    tick(1)
    for coordinate in range(dimension):
        for side, left, right in (("R", row_i, row_j), ("C", col_i, col_j)):
            if left == right:
                continue
            used += 1
            tick(1)
            if (side, left) == current or (side, right) == current:
                continue
            x = fixed.get((side, left, coordinate))
            y = fixed.get((side, right, coordinate))
            if x is not None and y is not None and x != y:
                return used
    return used


def _independent_batch_work(edge_list, vertices, steps, radix, dimension,
                            candidate_count, tick):
    """Recompute V4's native work units with a separate Python implementation.

    Work units are pair classifications, exact pair-score visits, coordinate
    comparisons, and candidate bookkeeping.  The calculation intentionally
    shares only the edge/assignment representation, not the C++ scoring code.
    """
    if candidate_count != radix ** dimension:
        raise ValueError("native candidate count does not match radix and dimension")
    fixed = {}
    pairs = [(edge_list[i], edge_list[j])
             for i in range(len(edge_list)) for j in range(i)]
    total = 0
    for edge_i, edge_j in pairs:
        total += _pair_score_work(edge_i, edge_j, fixed, dimension,
                                  ("", -1), (), tick)

    if len(vertices) != len(steps):
        raise ValueError("native work replay trace length mismatch")
    for current, step in zip(vertices, steps):
        incident = []
        independent = []
        for edge_i, edge_j in pairs:
            total += 1
            tick(1)  # pair classification
            if ((current[0] == "R" and
                 (edge_i[0] == current[1] or edge_j[0] == current[1])) or
                (current[0] == "C" and
                 (edge_i[1] == current[1] or edge_j[1] == current[1]))):
                incident.append((edge_i, edge_j))
            else:
                independent.append((edge_i, edge_j))
        for edge_i, edge_j in independent:
            total += _pair_score_work(edge_i, edge_j, fixed, dimension,
                                      ("", -1), (), tick)
        for edge_i, edge_j in incident:
            total += _parent_pair_work(edge_i, edge_j, fixed, dimension,
                                       current, tick)
        for label in product(range(radix), repeat=dimension):
            total += 1  # candidate bookkeeping
            tick(1)
            for edge_i, edge_j in incident:
                total += _pair_score_work(edge_i, edge_j, fixed, dimension,
                                          current, label, tick)
        chosen = step.get("label")
        if (not isinstance(chosen, list) or len(chosen) != dimension or
                any(type(symbol) is not int or not 0 <= symbol < radix
                    for symbol in chosen)):
            raise ValueError("invalid label in native work replay trace")
        for coordinate, symbol in enumerate(chosen):
            fixed[(current[0], current[1], coordinate)] = symbol
    return total


def verify_streaming_d3_certificate(certificate, *, max_work=30_000_000,
                                    max_candidate_evaluations=1_000_000):
    """Return a fail-closed finite-instance replay result.

    ``valid=True`` means the exact labeling trace and implicit packet layout
    replay for this finite input. It is not a proof of the universal packing
    lemma, its asymptotic algorithm, or any recursive theorem claim.
    """
    if max_work is not None and (type(max_work) is not int or max_work < 0):
        return {"valid": False, "status": "INVALID_CHECKER_POLICY",
                "reason": "max_work must be a nonnegative integer or None"}
    if (type(max_candidate_evaluations) is not int or
            max_candidate_evaluations < 0):
        return {"valid": False, "status": "INVALID_CHECKER_POLICY",
                "reason": "max_candidate_evaluations must be nonnegative"}
    work = 0

    def tick(amount=1):
        nonlocal work
        work += amount
        if max_work is not None and work > max_work:
            raise RuntimeError("independent checker work budget exceeded")

    try:
        if not isinstance(certificate, dict) or certificate.get("schema") not in (
                NATIVE_BATCH_SCHEMA, SCHEMA, PREVIOUS_SCHEMA, LEGACY_SCHEMA):
            raise ValueError("incorrect streaming certificate schema")
        schema = certificate["schema"]
        required = {
            "schema", "claim", "paper_labels", "r", "a", "L", "D", "M",
            "delta", "H_pad", "edges", "row_labels", "column_labels",
            "steps", "initial_expected_square_scaled", "final_square_scaled",
            "preconditions", "paper_preconditions_required",
            "eligible_at_this_instance", "fixed_manuscript_radix",
            "paper_active_call_eligible", "policy", "work_units",
            "estimated_work_units", "resource_ledger",
        }
        if schema in (SCHEMA, NATIVE_BATCH_SCHEMA):
            required |= {"algorithm_version", "score_backend_requested", "score_backend"}
            selected = certificate["score_backend"]
            requested = certificate["score_backend_requested"]
            if requested not in ("python", "cpp", "auto"):
                raise ValueError("invalid requested backend declaration")
            if schema == NATIVE_BATCH_SCHEMA:
                if (selected not in NATIVE_BATCH_ALGORITHMS or
                        certificate["algorithm_version"] != NATIVE_BATCH_ALGORITHMS.get(selected) or
                        requested == "python"):
                    raise ValueError("invalid V4 native backend or algorithm version")
            elif (selected not in BACKEND_ALGORITHMS or
                    certificate["algorithm_version"] != BACKEND_ALGORITHMS.get(selected) or
                    (requested == "python" and selected != "python") or
                    (requested == "cpp" and selected != "cpp")):
                raise ValueError("invalid backend or algorithm-version declaration")
        else:
            selected = "python"
        if set(certificate) != required:
            raise ValueError("certificate has missing or unexpected fields")
        if certificate["claim"] != "FINITE_STREAMING_D3_CONDITIONAL_EXPECTATION_EXECUTION":
            raise ValueError("incorrect certificate claim")
        if certificate["paper_labels"] != ["lem:tensor-packets", "eq:tensor-packing-conditions"]:
            raise ValueError("paper contract labels differ")

        radix, dim = certificate["r"], certificate["a"]
        if (type(radix) is not int or not 2 <= radix <= 64 or
                type(dim) is not int or not 1 <= dim <= 64):
            raise ValueError("invalid label dimensions")
        for key in ("L", "D", "M", "delta", "H_pad",
                    "initial_expected_square_scaled", "final_square_scaled",
                    "work_units", "estimated_work_units"):
            if type(certificate[key]) is not int or certificate[key] < 0:
                raise ValueError(f"{key} must be a nonnegative integer")
        if (type(certificate["paper_preconditions_required"]) is not bool or
                type(certificate["eligible_at_this_instance"]) is not bool or
                type(certificate["fixed_manuscript_radix"]) is not bool or
                type(certificate["paper_active_call_eligible"]) is not bool):
            raise ValueError("precondition flags must be Boolean")
        width = 1 << dim
        classes_count = radix ** (2 * dim)
        edge_raw = certificate["edges"]
        if not isinstance(edge_raw, list):
            raise ValueError("edges must be a list")
        edges = []
        for edge in edge_raw:
            if (not isinstance(edge, list) or len(edge) != 2 or
                    any(type(v) is not int or v < 0 for v in edge)):
                raise ValueError("invalid edge")
            edges.append((edge[0], edge[1]))
        m = len(edges)
        if schema == NATIVE_BATCH_SCHEMA and (m > 100_000 or
                len({u for u, _ in edges}) > 10_000 or
                len({v for _, v in edges}) > 10_000 or
                m * (m - 1) // 2 > 1_000_000):
            raise RuntimeError("V4 native certificate exceeds independent replay caps")
        delta = max([0] + list(Counter(u for u, _ in edges).values()) +
                    list(Counter(v for _, v in edges).values()))
        if (certificate["r"] != radix or certificate["L"] != width or
                certificate["D"] != classes_count or certificate["M"] != m or
                certificate["delta"] != delta):
            raise ValueError("incorrect derived packing parameters")

        q = radix ** dim
        vertices = _vertices(edges)
        if len(vertices) * q > max_candidate_evaluations:
            raise RuntimeError("independent candidate enumeration budget exceeded")
        pair_count = m * (m - 1) // 2
        # The two algorithms retain distinct, versioned work metrics.  V3 is
        # preserved byte-for-byte; V4 accounts for the batch pair partition,
        # shared pair scores, parent score and candidate-dependent scans.
        if schema == NATIVE_BATCH_SCHEMA:
            estimated = (pair_count * (1 + 2 * dim) +
                         len(vertices) * (pair_count +
                         (q + 1) * pair_count * (1 + 2 * dim) + q))
        else:
            estimated = (len(vertices) * q + 1) * (1 + pair_count * (1 + 2 * dim))
        if certificate["estimated_work_units"] != estimated:
            raise ValueError("work estimate mismatch")
        policy = certificate["policy"]
        expected_policy_keys = ({"max_work", "max_candidate_evaluations",
                                 "work_metric_version"}
                                if schema == NATIVE_BATCH_SCHEMA else
                                {"max_work", "max_candidate_evaluations"})
        if (not isinstance(policy, dict) or
                set(policy) != expected_policy_keys or
                type(policy["max_candidate_evaluations"]) is not int or
                policy["max_candidate_evaluations"] < 0 or
                policy["max_candidate_evaluations"] < len(vertices) * q):
            raise ValueError("invalid construction policy")
        if (schema == NATIVE_BATCH_SCHEMA and
                policy["work_metric_version"] != NATIVE_BATCH_WORK_METRIC):
            raise ValueError("unknown V4 work metric")
        if (policy["max_work"] is not None and
                (type(policy["max_work"]) is not int or policy["max_work"] < 0)):
            raise ValueError("invalid construction work cap")
        if (policy["max_work"] is not None and estimated > policy["max_work"]):
            raise ValueError("construction policy could not admit its declared work estimate")
        if (policy["max_candidate_evaluations"] < len(vertices) * q):
            raise ValueError("construction policy excludes its candidate evaluations")
        fixed = {}
        initial = _reference_score(edges, fixed, radix, dim, ("", -1), (), tick)
        if certificate["initial_expected_square_scaled"] != initial:
            raise ValueError("incorrect unconditional expectation")
        if not isinstance(certificate["steps"], list) or len(certificate["steps"]) != len(vertices):
            raise ValueError("incorrect conditional-expectation trace length")
        previous = initial
        labels = {}
        for expected_vertex, step in zip(vertices, certificate["steps"]):
            if not isinstance(step, dict) or set(step) != {
                    "side", "vertex", "label", "expected_square_scaled"}:
                raise ValueError("malformed trace step")
            side, vertex = expected_vertex
            if step["side"] != side or step["vertex"] != vertex:
                raise ValueError("noncanonical vertex order")
            if (type(step["vertex"]) is not int or
                    type(step["expected_square_scaled"]) is not int or
                    step["expected_square_scaled"] < 0):
                raise ValueError("trace scores and vertex IDs must be exact integers")
            label = step["label"]
            if (not isinstance(label, list) or len(label) != dim or
                    any(type(x) is not int or not 0 <= x < radix for x in label)):
                raise ValueError("invalid chosen vertex label")
            best = None
            score_sum = 0
            for trial in product(range(radix), repeat=dim):
                tick(1)
                score = _reference_score(edges, fixed, radix, dim,
                                         (side, vertex), trial, tick)
                score_sum += score
                candidate = (score, trial)
                if best is None or candidate < best:
                    best = candidate
            if score_sum != previous * q:
                raise ValueError("candidate expectations fail the averaging identity")
            if best != (step["expected_square_scaled"], tuple(label)):
                raise ValueError("chosen label is not the canonical exact minimizer")
            if best[0] > previous:
                raise ValueError("conditional expectation increased")
            labels[(side, vertex)] = tuple(label)
            for d, symbol in enumerate(label):
                fixed[(side, vertex, d)] = symbol
            previous = best[0]
        if certificate["final_square_scaled"] != previous:
            raise ValueError("incorrect final conditional expectation")

        row_expected = sorted({u for u, _ in edges})
        col_expected = sorted({v for _, v in edges})
        raw_rows = certificate["row_labels"]
        raw_cols = certificate["column_labels"]
        if not isinstance(raw_rows, dict) or not isinstance(raw_cols, dict):
            raise ValueError("label maps must be objects")
        if set(raw_rows) != {str(v) for v in row_expected} or set(raw_cols) != {str(v) for v in col_expected}:
            raise ValueError("label map vertex sets differ from the network")
        rows = {v: labels[("R", v)] for v in row_expected}
        cols = {v: labels[("C", v)] for v in col_expected}
        if ({str(k): list(v) for k, v in sorted(rows.items())} != raw_rows or
                {str(k): list(v) for k, v in sorted(cols.items())} != raw_cols):
            raise ValueError("label maps differ from verified trace")

        grouped = _packing_layout(edges, rows, cols, radix, dim, width,
                                  certificate["H_pad"])
        actual_final = classes_count * sum(len(ids) ** 2 for ids in grouped.values())
        if actual_final != previous:
            raise ValueError("final class loads disagree with conditional expectation")
        if certificate["H_pad"] * classes_count > 3 * m:
            packet_bound = False
        else:
            packet_bound = True

        side_loads = Counter()
        for u, v in edges:
            for d in range(dim):
                side_loads[("R", d, rows[u][d])] += 1
                side_loads[("C", d, cols[v][d])] += 1
        max_port = max(side_loads.values(), default=0)
        port_bound = radix * max_port <= 3 * m
        initial_variance = initial - m * m
        variance_bound = initial_variance <= 2 * m * delta * classes_count
        if previous > initial:
            raise ValueError("final potential exceeds unconditional expectation")

        conditions = {
            "M_ge_2_D_squared_delta": m >= 2 * classes_count ** 2 * delta,
            "M_ge_LD": m >= width * classes_count,
            "2L_le_delta": 2 * width <= delta,
            "D": classes_count, "L": width, "delta": delta,
        }
        declared_conditions = certificate["preconditions"]
        if (not isinstance(declared_conditions, dict) or
                set(declared_conditions) != set(conditions) or
                any(type(declared_conditions[key]) is not bool for key in (
                    "M_ge_2_D_squared_delta", "M_ge_LD", "2L_le_delta")) or
                any(type(declared_conditions[key]) is not int for key in (
                    "D", "L", "delta"))):
            raise ValueError("numeric precondition flags must be Boolean")
        if declared_conditions != conditions:
            raise ValueError("numeric preconditions mismatch")
        eligible = all(conditions[key] for key in (
            "M_ge_2_D_squared_delta", "M_ge_LD", "2L_le_delta"))
        if certificate["eligible_at_this_instance"] is not eligible:
            raise ValueError("eligibility claim mismatch")
        # V1 used an unsound active-call label for this weaker local check.
        # Replay its historical field exactly, but never repeat that claim.
        legacy = schema == LEGACY_SCHEMA
        recorded_paper_eligible = radix == 64 and eligible if legacy else False
        if certificate["fixed_manuscript_radix"] is not (radix == 64):
            raise ValueError("fixed manuscript radix claim mismatch")
        if certificate["paper_active_call_eligible"] is not recorded_paper_eligible:
            raise ValueError("paper active-call eligibility claim mismatch")
        if certificate["paper_preconditions_required"]:
            if radix != 64 or not eligible:
                raise ValueError("active-call certificate lacks paper hypotheses")

        ledger = certificate["resource_ledger"]
        expected_ledger = {
            "work_unit_definition": (
                "batch pair classification, exact pair-score visits, coordinate comparisons, and candidate bookkeeping"
                if schema == NATIVE_BATCH_SCHEMA else
                "edge-pair visits, coordinate comparisons, and candidate bookkeeping"),
            "peak_memory_measured": False,
            "bit_complexity_complete": False,
            "time_bound_claimed": False,
        }
        if schema == NATIVE_BATCH_SCHEMA:
            expected_ledger["work_metric_version"] = NATIVE_BATCH_WORK_METRIC
        if ledger != expected_ledger:
            raise ValueError("resource-ledger limitations were altered")
        if schema == NATIVE_BATCH_SCHEMA:
            native_work = _independent_batch_work(
                edges, vertices, certificate["steps"], radix, dim, q, tick)
            if certificate["work_units"] != native_work:
                raise ValueError("native batch work-unit ledger mismatch")
            if policy["max_work"] is not None and native_work > policy["max_work"]:
                raise ValueError("native work exceeds the declared construction cap")
        else:
            native_work = None
            if certificate["work_units"] != work:
                raise ValueError("construction work-unit ledger mismatch")
        if max_work is not None and work > max_work:
            raise RuntimeError("independent checker work budget exceeded")
        if len(vertices) * q > max_candidate_evaluations:
            raise RuntimeError("independent candidate enumeration budget exceeded")

        return {
            "valid": True,
            "execution_backend": selected,
            "backend_independently_replayed": True,
            "status": ("FINITE_FIXED_RADIX_LEMMA_INSTANCE_CHECKED"
                       if radix == 64 and eligible and packet_bound and port_bound
                       else "FINITE_GENERIC_RADIX_D3_REPLAYED"),
            "edge_count": m,
            "vertices_labeled": len(vertices),
            "conditional_expectation_steps": len(vertices),
            "independent_candidate_evaluations": len(vertices) * q,
            "independent_work_units": work,
            "independently_recomputed_construction_work_units": (
                native_work if schema == NATIVE_BATCH_SCHEMA else work),
            "work_metric_version": (
                NATIVE_BATCH_WORK_METRIC if schema == NATIVE_BATCH_SCHEMA else
                "d3-direct-pair-score-work-v1"),
            "initial_variance_bound": variance_bound,
            "packet_count_bound": packet_bound,
            "port_load_bound": port_bound,
            "max_side_symbol_load": max_port,
            "numeric_active_call_inequalities": eligible,
            "paper_active_call_eligible": False,
            "source_schedule_checked": False,
            "legacy_active_call_claim_discarded": legacy,
            "universal_packing_lemma_proven": False,
            "theorem_recursion_qualified": False,
        }
    except RuntimeError as exc:
        return {"valid": False, "status": "INCONCLUSIVE_RESOURCE_LIMIT", "reason": str(exc)}
    except (ValueError, KeyError, TypeError, IndexError, OverflowError) as exc:
        return {"valid": False, "status": "INVALID_CERTIFICATE", "reason": str(exc)}

