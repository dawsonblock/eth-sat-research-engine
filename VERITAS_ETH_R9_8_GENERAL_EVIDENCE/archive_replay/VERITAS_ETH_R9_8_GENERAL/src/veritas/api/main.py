"""Local-first FastAPI interface. Browser requests do not execute arbitrary code."""
from __future__ import annotations
from pathlib import Path
import re
import time
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from veritas.audit.store import AuditStore, digest
from veritas.core.cnf import CNF
from veritas.core.logic import parse, encode, entailment_query, Expr
from veritas.solvers.reference import solve, exhaustive_count
from veritas.solvers.certificates import make_unsat_certificate, check_unsat_certificate
from veritas.solvers.projected import projected_count, MAX_PROJECTED
from veritas.solvers.count_certificates import make_count_certificate, check_count_certificate, MAX_NODES as COUNT_PROOF_NODES
from veritas.solvers.count_dag import make_dag_count_certificate, check_dag_count_certificate, MAX_NODES as DAG_PROOF_NODES
from veritas.solvers.weighted_dag import make_weighted_dag_certificate, check_weighted_dag_certificate, parse_weights, weight_digest, MAX_VARS as WEIGHTED_MAX_VARS
from veritas.solvers.conditional import exact_conditional
from veritas.solvers.marginals import exact_marginals, check_marginal_certificate
from veritas.solvers.ganak import exact_count, CounterUnavailable
from veritas.research.tensor import from_cnf, brute_contract, eliminate
from veritas.research.violation_polynomial import eliminate_violation_polynomial, exact_violation_histogram, evaluate_polynomial, recover_zero_from_positive_nodes
from veritas.research.wire_deformation import deform_polynomial, independent_defect_histogram, check_deformation_invariants
from veritas.research.cauchy_deformation import (exact_cauchy_deformation, verify_cauchy_small,
    shifted_cauchy_jet_mod, coefficient_valuations)
from veritas.research.cauchy_modes import cauchy_modes_at_node
from veritas.research.hermite_ring import hermite_plan, reconstruct_mod
from veritas.research.grouped_cauchy import grouped_cauchy_jet_mod
from veritas.research.recursive_separator import recursive_contract, separator_plan, ResourceLimit
from veritas.research.packet_schedule import plan_packets, relabel_network
from veritas.research.optimal_packets import optimize_packets_exact, PacketPlanningLimit
from veritas.research.scalable_packets import optimize_packets_scalable
from veritas.research.matching_packets import optimize_packets_matching, MatchingDependencyMissing
from veritas.research.matching_checker import verify_matching_evidence
from veritas.research.bounded_partition import optimize_packets_bounded
from veritas.research.bounded_partition_checker import verify_bounded_partition
from veritas.research.packet_bound_checker import check_packet_search_evidence
from veritas.research.cauchy_elimination import eliminate_cauchy_jet, EliminationLimit
from veritas.research.weighted_children import recursive_weighted_jet, ChildTensorLimit
from veritas.research.weighted_recovery import recover_weighted_count, RecoveryBudgetExceeded, recovery_payload
from veritas.research.bounded_degree import bounded_degree_from_cnf, describe_network
from veritas.research.minfill_contract import minfill_contract, ContractionBudgetExceeded
from veritas.research.adaptive_contract import adaptive_count
from veritas.research.contraction_planner import ContractLimit

from veritas import __version__

app = FastAPI(title="VERITAS-ETH", version=__version__, description="Auditable exact Boolean reasoning and bounded ETH-inspired research")
app.state.audit = None


def audits() -> AuditStore:
    if app.state.audit is None:
        app.state.audit = AuditStore()
    return app.state.audit


class CNFRequest(BaseModel):
    n: int = Field(ge=0, le=512)
    clauses: list[list[int]] = Field(max_length=20_000)
    timeout_s: float = Field(default=4.0, gt=0, le=30)
    max_nodes: int = Field(default=150_000, ge=1, le=2_000_000)


class VerifyRequest(CNFRequest):
    request_unsat_certificate: bool = False


class CertifyRequest(CNFRequest):
    max_certificate_bytes: int = Field(default=1_000_000, ge=256, le=4_000_000)


class CertificateCheckRequest(CNFRequest):
    certificate: dict


class ProjectedCountRequest(CNFRequest):
    projected: list[int] = Field(max_length=MAX_PROJECTED)
    cross_check: bool = True


class CertifiedCountRequest(CNFRequest):
    max_certificate_bytes: int = Field(default=1_000_000, ge=256, le=4_000_000)


class CountCertificateCheckRequest(CNFRequest):
    certificate: dict


class WeightedCertifiedCountRequest(CertifiedCountRequest):
    weights: dict[str, list[str]] = Field(default_factory=dict, max_length=WEIGHTED_MAX_VARS)


class WeightedCountCertificateCheckRequest(WeightedCertifiedCountRequest):
    certificate: dict


class MarginalCheckRequest(WeightedCertifiedCountRequest):
    certificate: dict


class ConditionalRequest(WeightedCertifiedCountRequest):
    query_clauses: list[list[int]] = Field(max_length=10_000)


class SpectrumRequest(CNFRequest):
    precision_bits: int | None = Field(default=None, ge=1, le=64)
    max_table_entries: int = Field(default=1 << 13, ge=1, le=1 << 16)
    cross_check: bool = True



class WireDeformationRequest(CNFRequest):
    precision_bits: int | None = Field(default=None, ge=1, le=64)
    max_edges: int = Field(default=10, ge=0, le=12)
    max_table_entries: int = Field(default=1 << 13, ge=1, le=1 << 16)
    cross_check: bool = True

class CauchyRequest(CNFRequest):
    packet_size: int = Field(default=2, ge=1, le=8)
    max_edges: int = Field(default=5, ge=0, le=6)
    cross_check: bool = True
    node: int = Field(default=0, ge=-8, le=7)
    precision_bits: int = Field(default=8, ge=1, le=64)
    jet_order: int = Field(default=4, ge=1, le=24)


class CauchyModesRequest(CNFRequest):
    packet_size: int = Field(default=2, ge=1, le=8)
    node: int = Field(default=1, ge=-8, le=7)
    precision_bits: int = Field(default=12, ge=1, le=128)
    jet_order: int = Field(default=6, ge=1, le=24)
    max_edges: int = Field(default=5, ge=0, le=6)
    cross_check: bool = True


class CauchyHermiteRequest(CNFRequest):
    packet_size: int = Field(default=2, ge=1, le=2)
    max_edges: int = Field(default=4, ge=0, le=4)
    precision_bits: int = Field(default=8, ge=1, le=32)
    cross_check: bool = True


class SeparatorContractRequest(CNFRequest):
    max_cut_edges: int = Field(default=10, ge=0, le=16)
    max_leaf_edges: int = Field(default=16, ge=0, le=22)
    max_calls: int = Field(default=150_000, ge=1, le=500_000)
    leaf_factors: int = Field(default=3, ge=1, le=9)
    precision_bits: int | None = Field(default=None, ge=1, le=128)
    cross_check: bool = True


class GroupedCauchyRequest(CNFRequest):
    packet_size: int = Field(default=2, ge=1, le=8)
    node: int = Field(default=1, ge=-8, le=7)
    jet_order: int = Field(default=5, ge=1, le=20)
    group_span: int = Field(default=1, ge=1, le=8)
    precision_bits: int = Field(default=10, ge=1, le=128)
    cross_check: bool = True


class PacketScheduleRequest(CNFRequest):
    packet_size: int = Field(default=2, ge=1, le=8)
    optimizer: str = Field(default="legacy", pattern="^(legacy|exact_dp|scalable|matching|bounded)$")
    max_evaluations: int = Field(default=25000, ge=1, le=1000000)
    restarts: int = Field(default=5, ge=0, le=64)
    seed: int = Field(default=190026, ge=0, le=4294967295)
    max_permutations: int = Field(default=40320, ge=1, le=40320)
    max_states: int = Field(default=150000, ge=1, le=1000000)
    max_blocks: int = Field(default=1000000, ge=1, le=5000000)
    cross_check: bool = True


class CauchyEliminationRequest(CNFRequest):
    packet_size: int = Field(default=2, ge=1, le=8)
    node: int = Field(default=0, ge=-8, le=7)
    precision_bits: int = Field(default=12, ge=1, le=128)
    jet_order: int = Field(default=5, ge=1, le=24)
    optimize_packets: bool = False
    packet_optimizer: str = Field(default="legacy", pattern="^(legacy|exact_dp|scalable|matching)$")
    max_table_entries: int = Field(default=1 << 13, ge=2, le=1 << 18)
    max_total_entries: int = Field(default=1 << 16, ge=2, le=1 << 20)
    elimination_order: str = 'min_fill'
    cross_check: bool = True


class WeightedChildrenRequest(CNFRequest):
    packet_size: int = Field(default=2, ge=1, le=8)
    node: int = Field(default=1, ge=-8, le=7)
    group_span: int = Field(default=1, ge=1, le=8)
    precision_bits: int = Field(default=12, ge=1, le=128)
    jet_order: int = Field(default=5, ge=1, le=20)
    max_edges: int = Field(default=6, ge=0, le=8)
    max_boundary_vars: int = Field(default=12, ge=0, le=16)
    max_table_entries: int = Field(default=4096, ge=1, le=65536)
    max_work_assignments: int = Field(default=250_000, ge=1, le=2_000_000)
    cross_check: bool = True


class WeightedRecoveryRequest(CNFRequest):
    packet_size: int = Field(default=2, ge=1, le=2)
    group_span: int = Field(default=1, ge=1, le=2)
    precision_bits: int | None = Field(default=None, ge=1, le=64)
    max_edges: int = Field(default=6, ge=0, le=6)
    max_boundary_vars: int = Field(default=12, ge=0, le=16)
    max_table_entries: int = Field(default=4096, ge=1, le=65536)
    max_work_assignments: int = Field(default=250000, ge=1, le=2000000)
    cross_check: bool = True


class CountRequest(CNFRequest):
    backend: str = "reference"
    cross_check: bool = True


class FormalizeRequest(BaseModel):
    expression: str = Field(min_length=1, max_length=5_000)


class EntailmentRequest(BaseModel):
    request_unsat_certificate: bool = False
    premises: list[str] = Field(max_length=60)
    conclusion: str = Field(min_length=1, max_length=5_000)
    timeout_s: float = Field(default=4.0, gt=0, le=30)
    max_nodes: int = Field(default=150_000, ge=1, le=2_000_000)


class EquivalenceRequest(BaseModel):
    left: str = Field(min_length=1, max_length=5_000)
    right: str = Field(min_length=1, max_length=5_000)
    request_unsat_certificate: bool = False
    timeout_s: float = Field(default=4.0, gt=0, le=30)
    max_nodes: int = Field(default=150_000, ge=1, le=2_000_000)


class ContractRequest(CNFRequest):
    method: str = "eliminate"
    max_table_entries: int = Field(default=1 << 16, ge=1, le=1 << 18)


def checked_cnf(request: CNFRequest) -> CNF:
    try:
        return CNF.from_lists(request.n, request.clauses)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


def record(op: str, problem: dict, result: dict) -> dict:
    payload = {"operation": op, "input_sha256": digest(problem), "result": result,
               "schema_version": "v1.7", "algorithm_tag": "bounded-reference-or-experimental"}
    try:
        token = audits().add(payload)
    except Exception as exc:
        # Fail closed: do not publish a supposedly audited verdict when persistence fails.
        raise HTTPException(503, f"audit persistence unavailable: {type(exc).__name__}") from exc
    return {**result, "input_sha256": payload["input_sha256"], "audit_sha256": token}


@app.get("/health")
def health():
    good, n = audits().verify_chain()
    return {"service": "VERITAS-ETH", "version": "2.4.0", "audit_chain_valid": good, "audit_records": n}


@app.get("/", response_class=HTMLResponse)
def home():
    return (Path(__file__).resolve().parents[1] / "web" / "index.html").read_text(encoding="utf-8")


@app.post("/v1/formalize")
def formalize(request: FormalizeRequest):
    try:
        expr = parse(request.expression)
        cnf, mapping = encode(expr)
    except (ValueError, RecursionError) as exc:
        raise HTTPException(422, f"formal expression required; no natural-language model is installed: {exc}") from exc
    return record("formalize", request.model_dump(), {
        "status": "COMPILED_REVIEW_REQUIRED", "cnf": cnf.as_dict(),
        "primary_variables": mapping, "encoding": "definitional_tseitin_unique_extension",
        "notice": "This parser understands propositional syntax, NOT natural language. Verify the semantics before using this result.",
    })


@app.post("/v1/verify")
def verify(request: VerifyRequest):
    cnf = checked_cnf(request)
    search = solve(cnf, timeout_s=request.timeout_s, max_nodes=request.max_nodes)
    verified = search.status == "SAT" and cnf.evaluate(search.model)
    if search.status == "SAT" and not verified:
        raise HTTPException(500, "solver returned an invalid model")
    certificate = None
    certificate_nodes = None
    if search.status == "UNSAT" and request.request_unsat_certificate:
        attempt = make_unsat_certificate(cnf, timeout_s=request.timeout_s,
                                         max_nodes=min(request.max_nodes, 100_000))
        if attempt.status == "SAT":
            raise HTTPException(500, "independent proof generator contradicts UNSAT solver")
        if attempt.status == "UNSAT":
            valid, reason, certificate_nodes = check_unsat_certificate(cnf, attempt.certificate)
            if not valid:
                raise HTTPException(500, f"generated UNSAT certificate rejected: {reason}")
            certificate = attempt.certificate
    result = {
        "status": search.status,
        "evidence_level": "WITNESS_CHECKED" if verified else "PROOF_CHECKED" if certificate is not None else "SOLVER_ONLY" if search.status == "UNSAT" else "NONE",
        "model": {str(k): v for k, v in search.model.items()} if search.model else None,
        "solver_id": "bounded_dpll_reference_v1", "cnf_sha256": cnf.digest(),
        "nodes": search.nodes, "wall_time_ms": round(search.seconds*1000, 3),
        "reason": search.reason,
        "certificate": certificate, "certificate_checker_nodes": certificate_nodes,
        "warning": "UNSAT remains solver-only unless a complete independent refutation tree is returned and checked." if search.status == "UNSAT" and certificate is None else None,
    }
    return record("verify", cnf.as_dict(), result)


@app.post("/v1/counterexample")
def counterexample(request: EntailmentRequest):
    try:
        cnf, mapping, premises, target = entailment_query(request.premises, request.conclusion)
    except (ValueError, RecursionError) as exc:
        raise HTTPException(422, str(exc)) from exc
    search = solve(cnf, timeout_s=request.timeout_s, max_nodes=request.max_nodes)
    example = None
    if search.status == "SAT":
        if not cnf.evaluate(search.model):
            raise HTTPException(500, "invalid encoded SAT witness")
        example = {name: search.model[idx] for name, idx in mapping.items()}
        if not all(p.eval(example) for p in premises) or target.eval(example):
            raise HTTPException(500, "invalid counterexample to stated entailment")
    status = "NOT_ENTAILED" if search.status == "SAT" else "ENTAILED" if search.status == "UNSAT" else "UNKNOWN"
    certificate = None
    if status == "ENTAILED" and request.request_unsat_certificate:
        attempt = make_unsat_certificate(cnf, timeout_s=request.timeout_s,
                                         max_nodes=min(request.max_nodes, 100_000))
        if attempt.status == "SAT":
            raise HTTPException(500, "entailment solver disagrees with independent proof search")
        if attempt.status == "UNSAT":
            valid, _, _ = check_unsat_certificate(cnf, attempt.certificate)
            if not valid:
                raise HTTPException(500, "entailment certificate rejected")
            certificate = attempt.certificate
    result = {
        "status": status,
        "evidence_level": "WITNESS_CHECKED" if example is not None else "PROOF_CHECKED" if certificate is not None else "SOLVER_ONLY" if status == "ENTAILED" else "NONE",
        "counterexample": example,
        "certificate": certificate,
        "primary_variables": mapping,
        "cnf_sha256": cnf.digest(),
        "nodes": search.nodes,
        "wall_time_ms": round(search.seconds*1000, 3),
        "reason": search.reason,
        "notice": "Entailment is only about the submitted formal propositions; it does not establish natural-language truth. Inconsistent premises entail every conclusion.",
    }
    return record("counterexample", request.model_dump(), result)


@app.post("/v1/count")
def count(request: CountRequest):
    cnf = checked_cnf(request)
    started = time.monotonic()
    if request.backend == "reference":
        search = solve(cnf, count=True, timeout_s=request.timeout_s, max_nodes=request.max_nodes)
        found = search.count
        status = search.status
        reason = search.reason
        nodes = search.nodes
    elif request.backend == "ganak":
        try:
            found = exact_count(cnf, seconds=request.timeout_s)
            status, reason, nodes = "COUNT", None, None
        except CounterUnavailable as exc:
            found, status, reason, nodes = None, "UNKNOWN", str(exc), None
    else:
        raise HTTPException(422, "backend must be 'reference' or 'ganak'")
    cross_checked = False
    if status == "COUNT":
        if not (0 <= found <= 1 << cnf.n):
            raise HTTPException(500, "invalid count returned")
        if request.cross_check and cnf.n <= 12:
            oracle = exhaustive_count(cnf, max_vars=12)
            if found != oracle:
                raise HTTPException(500, "COUNT MISMATCH: production result rejected")
            cross_checked = True
    result = {
        "status": status,
        "evidence_level": "CROSS_CHECKED" if cross_checked else "EXACT_ALGORITHM" if status == "COUNT" else "NONE",
        "count": str(found) if found is not None else None,
        "count_semantics": "all_declared_variables_unweighted",
        "solver_id": "bounded_dpll_reference_v1" if request.backend == "reference" else "ganak_nonprobabilistic",
        "cnf_sha256": cnf.digest(), "nodes": nodes,
        "wall_time_ms": round((time.monotonic()-started)*1000, 3),
        "reason": reason,
        "notice": "Exact arithmetic is not the same as an independently proof-checked counting certificate.",
    }
    return record("count", cnf.as_dict(), result)






@app.post("/v1/equivalent")
def equivalent(request: EquivalenceRequest):
    """Check whether two syntactic propositional expressions are equivalent.

    The checked counterexample is evaluated on both ORIGINAL expressions, not
    merely the Tseitin clauses. UNSAT can optionally be proof-checked.
    """
    try:
        left = parse(request.left)
        right = parse(request.right)
        # Exclusive-or: models exist precisely where the expressions disagree.
        mismatch = Expr("or", (
            Expr("and", (left, Expr("not", (right,)))),
            Expr("and", (Expr("not", (left,)), right)),
        ))
        cnf, mapping = encode(mismatch)
    except (ValueError, RecursionError) as exc:
        raise HTTPException(422,str(exc)) from exc
    result = solve(cnf,timeout_s=request.timeout_s,max_nodes=request.max_nodes)
    valuation = None
    if result.status == "SAT":
        if not cnf.evaluate(result.model):
            raise HTTPException(500,"invalid equivalence witness")
        valuation = {name:result.model[idx] for name,idx in mapping.items()}
        if left.eval(valuation) == right.eval(valuation):
            raise HTTPException(500,"encoded mismatch is not a true counterexample")
    certificate = None
    if result.status == "UNSAT" and request.request_unsat_certificate:
        built = make_unsat_certificate(cnf, timeout_s=request.timeout_s,
                                       max_nodes=min(request.max_nodes, 100_000))
        if built.status == "SAT":
            raise HTTPException(500,"equivalence proof disagrees with solver")
        if built.status == "UNSAT":
            valid, _, _ = check_unsat_certificate(cnf, built.certificate)
            if not valid:
                raise HTTPException(500,"equivalence certificate rejected")
            certificate = built.certificate
    return record("equivalent", request.model_dump(), {
        "status": "EQUIVALENT" if result.status == "UNSAT" else "NOT_EQUIVALENT" if result.status == "SAT" else "UNKNOWN",
        "evidence_level": "WITNESS_CHECKED" if valuation is not None else "PROOF_CHECKED" if certificate is not None else "SOLVER_ONLY" if result.status == "UNSAT" else "NONE",
        "counterexample": valuation,
        "left_value": left.eval(valuation) if valuation is not None else None,
        "right_value": right.eval(valuation) if valuation is not None else None,
        "certificate": certificate, "cnf_sha256": cnf.digest(),
        "reason":result.reason,
        "notice":"Equivalence is over explicit propositional syntax, not natural-language interpretation."
    })


@app.post("/v1/certify/unsat")
def certify_unsat(request: CertifyRequest):
    cnf = checked_cnf(request)
    built = make_unsat_certificate(cnf, timeout_s=request.timeout_s,
                                   max_nodes=min(100_000,request.max_nodes),
                                   max_bytes=request.max_certificate_bytes)
    if built.status == "UNSAT":
        valid, detail, nodes = check_unsat_certificate(cnf, built.certificate,
                                                       max_bytes=request.max_certificate_bytes)
        if not valid:
            raise HTTPException(500, f"independent UNSAT certificate check failed: {detail}")
        evidence = "PROOF_CHECKED"
    elif built.status == "SAT":
        if not cnf.evaluate(built.model):
            raise HTTPException(500, "invalid witness from certificate search")
        nodes, evidence = None, "WITNESS_CHECKED"
    else:
        nodes, evidence = None, "NONE"
    return record("certify_unsat", cnf.as_dict(), {
        "status": built.status, "evidence_level": evidence,
        "certificate_format": "veritas-dpll-refutation-v1" if built.certificate else None,
        "certificate": built.certificate,
        "model": {str(k): v for k,v in built.model.items()} if built.model else None,
        "generator_nodes": built.nodes, "checker_nodes": nodes,
        "cnf_sha256": cnf.digest(), "reason": built.reason,
        "notice": "Bounded full refutation trees, not DRAT/LRAT; proof checking is sound but may be exponentially costly.",
    })


@app.post("/v1/certificates/check")
def check_certificate(request: CertificateCheckRequest):
    cnf = checked_cnf(request)
    valid, reason, nodes = check_unsat_certificate(cnf, request.certificate)
    return record("check_certificate", cnf.as_dict(), {
        "status": "VALID" if valid else "REJECTED",
        "evidence_level": "PROOF_CHECKED" if valid else "NONE",
        "checker_nodes": nodes, "reason": reason,
        "certificate_sha256": digest(request.certificate), "cnf_sha256": cnf.digest(),
    })


@app.post("/v1/count/projected")
def count_projected(request: ProjectedCountRequest):
    cnf = checked_cnf(request)
    try:
        result = projected_count(cnf, request.projected,
                                 timeout_s=request.timeout_s, max_nodes=request.max_nodes)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    cross_checked = False
    if result.status == "COUNT" and request.cross_check and cnf.n <= 10:
        from itertools import product
        solutions = set()
        for bits in product((False,True),repeat=cnf.n):
            model = {i+1: bit for i,bit in enumerate(bits)}
            if cnf.evaluate(model):
                solutions.add(tuple(model[v] for v in request.projected))
        if len(solutions) != result.count:
            raise HTTPException(500,"PROJECTED COUNT MISMATCH")
        cross_checked = True
    return record("projected_count", {**cnf.as_dict(), "projected": sorted(request.projected)}, {
        "status": result.status,
        "evidence_level": "CROSS_CHECKED" if cross_checked else "EXACT_ALGORITHM" if result.status == "COUNT" else "NONE",
        "count": str(result.count) if result.count is not None else None,
        "count_semantics": "distinct_projected_valuations_with_existential_extension",
        "projected": sorted(request.projected), "solver_calls": result.solver_calls,
        "nodes": result.nodes, "reason": result.reason, "cnf_sha256": cnf.digest(),
        "notice": "Exact via witness-blocking enumeration, NOT the ETH algorithm or a succinct counting certificate.",
    })


@app.post("/v1/research/contract")
def contract(request: ContractRequest):
    cnf = checked_cnf(request)
    if cnf.n > 24 or sum(map(len, cnf.clauses)) > 25:
        raise HTTPException(422, "research endpoint limited to 24 variables and 25 occurrences")
    try:
        network = from_cnf(cnf, max_degree=15)
        if request.method == "edge_enum":
            result_count = brute_contract(network, max_edges=19, timeout_s=request.timeout_s)
        elif request.method == "eliminate":
            result_count = eliminate(network, max_table_entries=request.max_table_entries, timeout_s=request.timeout_s)
        else:
            raise HTTPException(422, "method must be edge_enum or eliminate")
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except TimeoutError:
        return record("tensor_contract", cnf.as_dict(), {
            "status": "UNKNOWN", "evidence_level": "NONE", "count": None,
            "reason": "tensor contraction time budget exceeded",
            "warning": "No answer was inferred from a partial contraction.",
        })
    oracle_verified = False
    if cnf.n <= 12:
        oracle = exhaustive_count(cnf, max_vars=12)
        if oracle != result_count:
            raise HTTPException(500, "tensor/count oracle mismatch")
        oracle_verified = True
    return record("tensor_contract", cnf.as_dict(), {
        "status": "COUNT", "evidence_level": "RESEARCH_CROSS_CHECKED" if oracle_verified else "RESEARCH_ONLY",
        "count": str(result_count), "count_semantics": "all_declared_variables_unweighted",
        "edges": network.edges, "factors": len(network.factors),
        "algorithm": f"generic_tensor_{request.method}",
        "warning": "NOT the paper's subexponential ETH algorithm; this is a conventional tensor-contraction baseline.",
    })




@app.post("/v1/certify/count")
def certify_count(request: CertifiedCountRequest):
    cnf = checked_cnf(request)
    attempt = make_count_certificate(
        cnf, timeout_s=request.timeout_s, max_nodes=min(request.max_nodes, COUNT_PROOF_NODES),
        max_bytes=request.max_certificate_bytes)
    checked_nodes = None
    if attempt.status == "COUNT":
        valid, why, independent_count, checked_nodes = check_count_certificate(
            cnf, attempt.certificate, max_bytes=request.max_certificate_bytes)
        if not valid or independent_count != attempt.count:
            raise HTTPException(500, f"independent count checker rejected generated tree: {why}")
    return record("certify_count", cnf.as_dict(), {
        "status": attempt.status,
        "evidence_level": "COUNT_PROOF_CHECKED" if attempt.status == "COUNT" else "NONE",
        "count": str(attempt.count) if attempt.count is not None else None,
        "certificate_format": "veritas-shannon-count-tree-v1" if attempt.certificate else None,
        "certificate": attempt.certificate,
        "generator_nodes": attempt.nodes, "checker_nodes": checked_nodes,
        "cnf_sha256": cnf.digest(), "reason": attempt.reason,
        "warning": "Fully checked exact counting via bounded exhaustive Shannon tree; exponential worst-case, not ETH algorithm.",
    })


@app.post("/v1/certify/count-dag")
def certify_count_dag(request: CertifiedCountRequest):
    cnf = checked_cnf(request)
    attempt = make_dag_count_certificate(
        cnf, timeout_s=request.timeout_s, max_nodes=min(request.max_nodes, DAG_PROOF_NODES),
        max_bytes=request.max_certificate_bytes)
    checked_nodes = None
    if attempt.status == 'COUNT':
        valid, why, independently_counted, checked_nodes = check_dag_count_certificate(
            cnf, attempt.certificate, max_bytes=request.max_certificate_bytes)
        if not valid or independently_counted != attempt.count:
            raise HTTPException(500, f'independent DAG checker rejected generated count: {why}')
    return record('certify_count_dag', cnf.as_dict(), {
        'status': attempt.status,
        'evidence_level': 'COUNT_PROOF_CHECKED' if attempt.status == 'COUNT' else 'NONE',
        'count': str(attempt.count) if attempt.count is not None else None,
        'certificate_format': 'veritas-component-count-dag-v1' if attempt.certificate else None,
        'certificate': attempt.certificate,
        'generator_nodes': attempt.nodes, 'cache_hits': attempt.cache_hits,
        'checker_nodes': checked_nodes, 'cnf_sha256': cnf.digest(), 'reason': attempt.reason,
        'warning': 'Independently checked component-DAG #SAT; exponential worst case, not paper ETH algorithm.',
    })


@app.post("/v1/certificates/check-count-dag")
def check_count_dag_proof(request: CountCertificateCheckRequest):
    cnf = checked_cnf(request)
    valid, reason, count_value, checked_nodes = check_dag_count_certificate(cnf, request.certificate)
    return record('check_count_dag_proof', cnf.as_dict(), {
        'status': 'VALID' if valid else 'REJECTED',
        'evidence_level': 'COUNT_PROOF_CHECKED' if valid else 'NONE',
        'count': str(count_value) if count_value is not None else None,
        'checker_nodes': checked_nodes, 'reason': reason,
        'certificate_sha256': digest(request.certificate), 'cnf_sha256': cnf.digest(),
    })


@app.post('/v1/probability/marginals')
def all_exact_posterior_marginals(request: WeightedCertifiedCountRequest):
    cnf = checked_cnf(request)
    try:
        outcome = exact_marginals(cnf, request.weights, timeout_s=request.timeout_s,
                                  max_nodes=min(request.max_nodes, DAG_PROOF_NODES),
                                  max_bytes=request.max_certificate_bytes)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return record('exact_posterior_marginals', {'cnf': cnf.as_dict(), 'weights': request.weights}, {
        'status': outcome.status,
        'evidence_level': 'WEIGHTED_DAG_AND_MARGINAL_REPLAY_CHECKED' if outcome.certificate else 'NONE',
        'evidence_weight': outcome.evidence_weight, 'marginals': outcome.marginals,
        'certificate': outcome.certificate, 'nodes': outcome.nodes, 'reason': outcome.reason,
        'warning': 'Independent Bernoulli priors and Boolean evidence only; not causal inference, '
                   'not manuscript ETH recursion; exponential worst case.',
    })


@app.post('/v1/certificates/check-marginals')
def check_exact_posterior_marginals(request: MarginalCheckRequest):
    cnf = checked_cnf(request)
    try:
        valid, reason, status, marginals, nodes = check_marginal_certificate(
            cnf, request.weights, request.certificate, timeout_s=request.timeout_s)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return record('check_posterior_marginals', {'cnf': cnf.as_dict(), 'weights': request.weights}, {
        'status': 'VALID' if valid else 'REJECTED', 'reason': reason,
        'evidence_level': 'WEIGHTED_DAG_AND_MARGINAL_REPLAY_CHECKED' if valid else 'NONE',
        'posterior_status': status if valid else None,
        'marginals': marginals, 'nodes': nodes,
        'certificate_sha256': digest(request.certificate),
    })


@app.post('/v1/probability/conditional')
def exact_conditional_probability(request: ConditionalRequest):
    evidence = checked_cnf(request)
    try:
        query = CNF.from_lists(request.n, request.query_clauses)
        outcome = exact_conditional(evidence, query, request.weights,
                   timeout_s=request.timeout_s, max_nodes=min(request.max_nodes, DAG_PROOF_NODES),
                   max_bytes=request.max_certificate_bytes)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return record('exact_conditional_probability', {'evidence': evidence.as_dict(),
                   'query': query.as_dict(), 'weights': request.weights}, {
        'status': outcome.status,
        'evidence_level': 'WEIGHTED_COUNT_PROOF_CHECKED' if outcome.status in ('PROBABILITY','UNDEFINED') else 'NONE',
        'probability': outcome.probability, 'joint_weight': outcome.numerator,
        'evidence_weight': outcome.denominator,
        'evidence_certificate': outcome.evidence_certificate,
        'joint_certificate': outcome.joint_certificate,
        'reason': outcome.reason,
        'warning': 'Exact independent-Bernoulli prior conditioning; not causal inference or the ETH algorithm.',
    })


@app.post('/v1/certify/weighted-count-dag')
def certify_weighted_count_dag(request: WeightedCertifiedCountRequest):
    cnf = checked_cnf(request)
    try:
        weights = parse_weights(cnf.n, request.weights)
        result = make_weighted_dag_certificate(
            cnf, request.weights, timeout_s=request.timeout_s,
            max_nodes=min(request.max_nodes, DAG_PROOF_NODES),
            max_bytes=request.max_certificate_bytes)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    checked_nodes = None
    if result.status == 'WEIGHTED_COUNT':
        valid, reason, value, checked_nodes = check_weighted_dag_certificate(
            cnf, request.weights, result.certificate, max_bytes=request.max_certificate_bytes)
        if not valid or value != result.count:
            raise HTTPException(500, f'weighted counting checker rejected generated certificate: {reason}')
    return record('certify_weighted_count_dag', {'cnf': cnf.as_dict(), 'weights': request.weights}, {
        'status': result.status, 'evidence_level':
        'WEIGHTED_COUNT_PROOF_CHECKED' if result.status == 'WEIGHTED_COUNT' else 'NONE',
        'count': result.count, 'normalized_distribution': result.normalized,
        'certificate_format': 'veritas-rational-weighted-component-dag-v1' if result.certificate else None,
        'certificate': result.certificate, 'generator_nodes': result.nodes,
        'checker_nodes': checked_nodes, 'cache_hits': result.cache_hits,
        'weights_sha256': weight_digest(weights), 'cnf_sha256': cnf.digest(), 'reason': result.reason,
        'warning': ('If all false/true weights sum to one, the count is an exact probability '
                    'under independent Bernoulli priors. Otherwise it is an exact weighted sum. '
                    'Exponential worst-case; not the ETH algorithm.'),
    })


@app.post('/v1/certificates/check-weighted-count-dag')
def check_weighted_count_dag(request: WeightedCountCertificateCheckRequest):
    cnf = checked_cnf(request)
    try:
        weights = parse_weights(cnf.n, request.weights)
        valid, reason, count, checked_nodes = check_weighted_dag_certificate(
            cnf, request.weights, request.certificate, max_bytes=request.max_certificate_bytes)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return record('check_weighted_count_dag', {'cnf': cnf.as_dict(), 'weights': request.weights}, {
        'status': 'VALID' if valid else 'REJECTED',
        'evidence_level': 'WEIGHTED_COUNT_PROOF_CHECKED' if valid else 'NONE',
        'count': count, 'checker_nodes': checked_nodes, 'reason': reason,
        'weights_sha256': weight_digest(weights), 'cnf_sha256': cnf.digest(),
        'certificate_sha256': digest(request.certificate),
    })


@app.post("/v1/certificates/check-count")
def check_count_proof(request: CountCertificateCheckRequest):
    cnf = checked_cnf(request)
    valid, reason, count_value, checked_nodes = check_count_certificate(cnf, request.certificate)
    return record("check_count_proof", cnf.as_dict(), {
        "status": "VALID" if valid else "REJECTED",
        "evidence_level": "COUNT_PROOF_CHECKED" if valid else "NONE",
        "count": str(count_value) if count_value is not None else None,
        "checker_nodes": checked_nodes, "reason": reason,
        "certificate_sha256": digest(request.certificate),
        "cnf_sha256": cnf.digest(),
    })


@app.post("/v1/research/violation-spectrum")
def violation_spectrum(request: SpectrumRequest):
    cnf = checked_cnf(request)
    if cnf.n > 32 or len(cnf.clauses) > 12 or sum(map(len, cnf.clauses)) > 24:
        raise HTTPException(422, "violation-spectrum research endpoint limited to 32 variables, 12 clauses and 24 occurrences")
    try:
        coefficients, stats = eliminate_violation_polynomial(
            cnf, precision_bits=request.precision_bits, timeout_s=request.timeout_s,
            max_table_entries=request.max_table_entries)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except TimeoutError:
        return record("violation_spectrum", request.model_dump(), {
            "status": "UNKNOWN", "evidence_level": "NONE", "coefficients": None,
            "reason": "research contraction time budget exceeded"})
    independent = False
    if cnf.n <= 12 and request.cross_check:
        oracle = exact_violation_histogram(cnf, max_vars=12)
        expect = [v % (1 << request.precision_bits) for v in oracle] if request.precision_bits is not None else oracle
        if coefficients != expect:
            raise HTTPException(500, "polynomial tensor result differs from independent assignment oracle")
        independent = True
    exact = request.precision_bits is None or request.precision_bits > cnf.n
    if exact and sum(coefficients) != 1 << cnf.n:
        raise HTTPException(500, "violation generating polynomial normalization failed")
    min_violations = next((i for i, c in enumerate(coefficients) if c), None) if exact else None
    nonzero_node_values = [evaluate_polynomial(coefficients,x,request.precision_bits)
                           for x in range(1,len(cnf.clauses)+2)]
    interpolated_at_zero = recover_zero_from_positive_nodes(nonzero_node_values,request.precision_bits)
    if interpolated_at_zero != coefficients[0]:
        raise HTTPException(500, "exact integer finite-difference reconstruction failed")
    result = {
        "status": "POLYNOMIAL", "evidence_level": "RESEARCH_CROSS_CHECKED" if independent else "RESEARCH_ONLY",
        "coefficients": [str(c) for c in coefficients],
        "meaning": "coefficient[k] counts declared-variable assignments that violate exactly k clauses",
        "precision_bits": request.precision_bits,
        "coefficient_semantics": "exact_integer" if exact else "residue_mod_2_power",
        "satisfying_assignments": str(coefficients[0]) if exact else None,
        "min_violated_clauses": min_violations,
        "max_satisfied_clauses": len(cnf.clauses) - min_violations if min_violations is not None else None,
        "H_at_1": str(evaluate_polynomial(coefficients,1,request.precision_bits)),
        "H_at_0_via_nonzero_integer_interpolation": str(interpolated_at_zero),
        "terms_provably_zero_mod_2_power": stats.v2_zero_pairs_elided,
        "polynomial_multiplication_pairs": stats.multiplication_pairs,
        "table_entries_evaluated": stats.table_entries_evaluated,
        "max_intermediate_arity": stats.max_intermediate_arity,
        "cnf_sha256": cnf.digest(),
        "warning": "Generic polynomial-semiring elimination, NOT Cauchy deformation or ETH subexponential contraction. Modular residues cannot recover counts unless precision exceeds n.",
    }
    return record("violation_spectrum", {**cnf.as_dict(), "precision_bits": request.precision_bits}, result)



@app.post("/v1/research/wire-deformation")
def wire_deformation(request: WireDeformationRequest):
    """Exact *toy* split-wire deformation; does not implement Cauchy construction."""
    cnf = checked_cnf(request)
    if cnf.n > 40 or len(cnf.clauses) > 18 or sum(map(len,cnf.clauses)) > 12:
        raise HTTPException(422, "wire-deformation restricted to 40 variables, 18 clauses and 12 occurrences")
    try:
        network = from_cnf(cnf, max_degree=14)
        coefficients, stats = deform_polynomial(
            network, precision_bits=request.precision_bits, max_edges=request.max_edges,
            max_table_entries=request.max_table_entries, timeout_s=request.timeout_s)
        nodes = check_deformation_invariants(network,coefficients,precision_bits=request.precision_bits)
        if request.cross_check and network.edges <= 7:
            independent = independent_defect_histogram(network, max_edges=7,timeout_s=request.timeout_s)
            if request.precision_bits is not None:
                independent = [v % (1 << request.precision_bits) for v in independent]
            if coefficients != independent:
                raise HTTPException(500, "independent split-wire enumeration disagrees with contraction")
            evidence = "RESEARCH_CROSS_CHECKED"
        else:
            evidence = "RESEARCH_INVARIANTS_CHECKED"
        if request.cross_check and cnf.n <= 12:
            oracle = exhaustive_count(cnf, max_vars=12)
            expected = oracle if request.precision_bits is None else oracle % (1 << request.precision_bits)
            if coefficients[0] != expected:
                raise HTTPException(500, "original CNF count disagrees with deformation constant term")
            evidence = "RESEARCH_CROSS_CHECKED"
        nonzero_values = [evaluate_polynomial(coefficients,t,request.precision_bits)
                          for t in range(1,len(coefficients)+1)]
        recovered = recover_zero_from_positive_nodes(nonzero_values,request.precision_bits)
        if recovered != coefficients[0]:
            raise HTTPException(500, "deformation interpolation invariant failed")
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except TimeoutError:
        return record("wire_deformation",request.model_dump(), {
            "status":"UNKNOWN", "evidence_level":"NONE", "reason":"research time budget exceeded",
            "coefficients":None})
    exact_at_zero = request.precision_bits is None or request.precision_bits > cnf.n
    return record("wire_deformation",request.model_dump(), {
        "status":"POLYNOMIAL", "evidence_level":evidence,
        "method":"TOY_SPLIT_WIRE_DEFORMATION_GENERIC_ELIMINATION",
        "degree_bound":network.edges, "half_edges":2*network.edges,
        "coefficients":[str(v) for v in coefficients],
        "coefficient_semantics":"exact_integer" if request.precision_bits is None else "residue_mod_2_power",
        "precision_bits":request.precision_bits,
        "original_satisfying_assignments":str(coefficients[0]) if exact_at_zero else None,
        "original_count_residue":str(coefficients[0]),
        "interpolated_constant_term":str(recovered),
        "independent_rank_one_checks":nodes,
        "table_entries_evaluated":stats.table_entries_evaluated,
        "max_intermediate_arity":stats.max_intermediate_arity,
        "provably_zero_products_mod_2_power":stats.provably_zero_products_mod_2_power,
        "cnf_sha256":cnf.digest(),
        "warning":"Ordinary degree-E split-wire polynomial, not the Cauchy deformation, ETH mode pruning, or subexponential contraction. Independent testing covers bounded instances only.",
    })

@app.post("/v1/research/cauchy-deformation")
def cauchy_deformation(request: CauchyRequest):
    """Actual manuscript local W_xy Cauchy kernel, tiny exhaustive reference only."""
    cnf = checked_cnf(request)
    if cnf.n > 24 or len(cnf.clauses) > 14 or sum(map(len, cnf.clauses)) > 6:
        raise HTTPException(422, "Cauchy reference limited to 24 variables, 14 clauses, 6 occurrences")
    if request.packet_size not in (1, 2, 4, 8):
        raise HTTPException(422, "packet_size must be one of 1, 2, 4, 8")
    if request.packet_size == 8 and sum(map(len,cnf.clauses)) > 3:
        raise HTTPException(422, "packet_size 8 limited to 3 wires")
    if request.node not in range(-request.packet_size,request.packet_size):
        raise HTTPException(422, "Cauchy node outside packet grid")
    started = time.monotonic()
    def remaining() -> float:
        duration = request.timeout_s - (time.monotonic() - started)
        if duration <= 0:
            raise TimeoutError('Cauchy request time budget exhausted')
        return duration
    try:
        network=from_cnf(cnf,max_degree=6)
        coefficients, stats=exact_cauchy_deformation(network,packet_size=request.packet_size,
                                    max_edges=request.max_edges,timeout_s=remaining())
        verified = verify_cauchy_small(network,coefficients,request.packet_size,
                           timeout_s=remaining()) if request.cross_check else None
        jet, jet_stats=shifted_cauchy_jet_mod(network,packet_size=request.packet_size,
                                node=request.node,precision_bits=request.precision_bits,
                                jet_order=request.jet_order,max_edges=request.max_edges,
                                timeout_s=remaining())
        if request.cross_check:
            from veritas.research.cauchy_deformation import _polynomial_shift
            from fractions import Fraction
            shifted = _polynomial_shift(coefficients,request.node,2*request.packet_size,request.jet_order)
            modulus=1 << request.precision_bits
            oracle=[]
            for a in shifted:
                v=Fraction(a)
                if v.denominator % 2 == 0:
                    raise HTTPException(500, "shifted F has a nonunit 2-adic denominator")
                oracle.append((v.numerator*pow(v.denominator,-1,modulus))%modulus)
            oracle += [0]*(request.jet_order-len(oracle))
            if tuple(oracle)!=jet:
                raise HTTPException(500, "independent shifted polynomial jet mismatch")
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
    except TimeoutError:
        return record('cauchy_deformation',request.model_dump(), {
            'status':'UNKNOWN','evidence_level':'NONE',
            'reason':'exhaustive research time budget exceeded'})
    return record('cauchy_deformation',request.model_dump(), {
        'status':'POLYNOMIAL',
        'evidence_level':'RESEARCH_CROSS_CHECKED' if request.cross_check else 'RESEARCH_ONLY',
        'method':'MANUSCRIPT_D4_3_CAUCHY_KERNEL_EXHAUSTIVE_REFERENCE',
        'paper_formulae':['76','77'],
        'packet_size':request.packet_size, 'original_wires':network.edges,
        'degree_bound':network.edges*(2*request.packet_size-1),
        'rational_coefficients':[str(c) for c in coefficients],
        'original_satisfying_assignments':str(coefficients[0]),
        'grid_invariants':verified,
        'shifted_jet':{'node':request.node,'alpha':2*request.packet_size,
                       'precision_bits':request.precision_bits,'order':request.jet_order,
                       'coefficients_mod_2_power':[str(v) for v in jet],
                       'valuations':[v if v is not None else 'ZERO_MOD_PRECISION'
                                      for v in coefficient_valuations(jet,request.precision_bits)]},
        'enumerated_pairs':stats.evaluated_pairs,
        'max_polynomial_degree':stats.max_polynomial_degree,
        'cnf_sha256':cnf.digest(),
        'warning': 'This reproduces formulas (76)-(77) only for a tiny CNF network. '
                   'It uses exhaustive 4**M pair enumeration and does NOT implement packet '
                   'collision packing, mode truncation, recursive child networks, '
                   'original D.5 recovery schedule, or a subexponential algorithm.'})




@app.post("/v1/research/cauchy-modes")
def cauchy_modes(request: CauchyModesRequest):
    """Certified *toy* cross-mode expansion, independently compared with full local jets."""
    cnf=checked_cnf(request)
    if request.packet_size not in (1,2,4,8) or request.node not in range(-request.packet_size,request.packet_size):
        raise HTTPException(422,'invalid Cauchy grid or node')
    if cnf.n>24 or len(cnf.clauses)>14 or sum(map(len,cnf.clauses))>6:
        raise HTTPException(422,'Cauchy modes limited to 24 variables, 14 clauses, six wires')
    try:
        network=from_cnf(cnf,max_degree=6)
        result,modes,stats=cauchy_modes_at_node(network,packet_size=request.packet_size,
                 node=request.node,precision_bits=request.precision_bits,jet_order=request.jet_order,
                 max_edges=request.max_edges,timeout_s=request.timeout_s)
        if request.cross_check:
            expected,_=shifted_cauchy_jet_mod(network,packet_size=request.packet_size,
                 node=request.node,precision_bits=request.precision_bits,jet_order=request.jet_order,
                 max_edges=request.max_edges,timeout_s=request.timeout_s)
            if result!=expected:
                raise HTTPException(500,'independent direct local Cauchy jet disagrees with mode expansion')
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
    except TimeoutError:
        return record('cauchy_modes',request.model_dump(),{'status':'UNKNOWN','evidence_level':'NONE',
                      'reason':'bounded Cauchy mode expansion timed out'})
    return record('cauchy_modes',request.model_dump(),{
        'status':'JET_RESIDUES','evidence_level':'RESEARCH_CROSS_CHECKED' if request.cross_check else 'RESEARCH_ONLY',
        'method':'SMALL_NODE_MATCHING_VALUATION_CERTIFIED_MODE_EXPANSION',
        'node':request.node,'packet_size':request.packet_size,
        'precision_bits':request.precision_bits,'jet_order':request.jet_order,
        'jet_coefficients_mod_2_power':list(map(str,result)),
        'cross_modes':[{'row':m.row,'column':m.column,'source_group':m.source_group,
                        'target_group':m.target_group,'min_valuation':m.min_valuation,
                        'min_z_degree':m.min_z_degree} for m in modes],
        'stats':vars(stats),'cnf_sha256':cnf.digest(),
        'warning':'Reference expansion with certified precision pruning. NOT the manuscript D.4.4 grouped low-rank modes or recursive ETH contraction.'})


@app.post("/v1/research/separator-contract")
def separator_contract(request: SeparatorContractRequest):
    """Conventional exact recursive contraction, NOT the paper's ETH recursion."""
    cnf=checked_cnf(request)
    occurrences=sum(map(len, cnf.clauses))
    if cnf.n+len(cnf.clauses)>18 or occurrences>30:
        raise HTTPException(422,'bounded prototype requires <=18 factor vertices and <=30 occurrences')
    if request.cross_check and occurrences>16:
        raise HTTPException(422,'independent edge enumeration requires <=16 occurrences; disable cross_check explicitly')
    try:
        net=from_cnf(cnf,max_degree=14)
        count,stats=recursive_contract(net,modulus=(1<<request.precision_bits) if request.precision_bits else None,
                  leaf_factors=request.leaf_factors,max_cut_edges=request.max_cut_edges,
                  max_leaf_edges=request.max_leaf_edges,max_calls=request.max_calls,timeout_s=request.timeout_s)
        oracle=None
        if request.cross_check:
            oracle=brute_contract(net,max_edges=16,modulus=(1<<request.precision_bits) if request.precision_bits else None,
                                  timeout_s=request.timeout_s)
            if count!=oracle:
                raise HTTPException(500,'recursive separator result disagreed with independent enumeration')
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
    except (ResourceLimit,TimeoutError) as exc:
        return record('separator_contract',request.model_dump(),{'status':'UNKNOWN','evidence_level':'NONE',
                       'reason':str(exc)})
    return record('separator_contract',request.model_dump(),{
        'status':'COUNT_RESIDUE' if request.precision_bits else 'EXACT_COUNT',
        'evidence_level':'RESEARCH_CROSS_CHECKED' if oracle is not None else 'RESEARCH_ONLY',
        'method':'BALANCED_FACTOR_SEPARATOR_RECURSION', 'count':str(count),
        'precision_bits':request.precision_bits,'independent_oracle':str(oracle) if oracle is not None else None,
        'stats':vars(stats),'cnf_sha256':cnf.digest(),
        'warning':'Conventional bounded separator contraction, exponential worst-case. NOT the ETH manuscript recursion.'})


@app.post("/v1/research/grouped-cauchy")
def grouped_cauchy(request: GroupedCauchyRequest):
    """Exact grouped coefficient-matrix rank factoring, small reference only."""
    cnf=checked_cnf(request)
    occurrences=sum(map(len,cnf.clauses))
    if occurrences>6 or cnf.n>18 or len(cnf.clauses)>12:
        raise HTTPException(422,'grouped Cauchy research limited to six wires')
    try:
        net=from_cnf(cnf,max_degree=6)
        jet,modes,summary=grouped_cauchy_jet_mod(net,packet_size=request.packet_size,
             node=request.node,group_span=request.group_span,precision_bits=request.precision_bits,
             jet_order=request.jet_order,timeout_s=request.timeout_s)
        oracle=None
        if request.cross_check:
            oracle,_=shifted_cauchy_jet_mod(net,packet_size=request.packet_size,node=request.node,
             precision_bits=request.precision_bits,jet_order=request.jet_order,max_edges=6,timeout_s=request.timeout_s)
            if jet!=oracle:
                raise HTTPException(500,'grouped coefficient modes disagreed with independent Cauchy jet')
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
    except TimeoutError:
        return record('grouped_cauchy',request.model_dump(),{'status':'UNKNOWN','evidence_level':'NONE',
                      'reason':'grouped reference timed out'})
    return record('grouped_cauchy',request.model_dump(),{
        'status':'JET_RESIDUES','evidence_level':'RESEARCH_CROSS_CHECKED' if oracle is not None else 'RESEARCH_ONLY',
        'method':'EXACT_RATIONAL_GROUPED_COEFFICIENT_RANK_MODES',
        'jet_coefficients_mod_2_power':list(map(str,jet)),'precision_bits':request.precision_bits,
        'group_summary':vars(summary),
        'modes':[{'row_group':m.row_group,'column_group':m.column_group,'coefficient_degree':m.coefficient_degree,
                  'u':list(map(str,m.u)),'v':list(map(str,m.v))} for m in modes],
        'independent_jet':list(map(str,oracle)) if oracle is not None else None,
        'cnf_sha256':cnf.digest(),
        'warning':'Exact small-instance grouped rank modes, not the paper D.4.4 weighted mode bound or full recursion.'})


@app.post("/v1/research/cauchy-hermite")
def cauchy_hermite(request: CauchyHermiteRequest):
    """Reconstruct F(0) from shifted local 2-adic jets with guard bits."""
    cnf=checked_cnf(request)
    if cnf.n>24 or len(cnf.clauses)>14 or sum(map(len,cnf.clauses))>4:
        raise HTTPException(422,'finite-ring Hermite reference limited to four wires')
    if request.packet_size not in (1,2):
        raise HTTPException(422,'packet_size must be 1 or 2 for bounded reconstruction')
    started=time.monotonic()
    def remaining():
        left=request.timeout_s-(time.monotonic()-started)
        if left<=0: raise TimeoutError('Hermite research budget elapsed')
        return left
    try:
        network=from_cnf(cnf,max_degree=6)
        degree=network.edges*(2*request.packet_size-1)
        nodes=[t for t in range(-request.packet_size,request.packet_size) if t!=0]
        multiplicity=(degree+len(nodes))//len(nodes)
        plan=hermite_plan([(t,multiplicity) for t in nodes],
                          alpha=2*request.packet_size,degree_bound=degree)
        bits=request.precision_bits+plan.guard_bits
        if bits>256 or multiplicity>24:
            raise ValueError('required guard precision exceeds implementation budget')
        jets=[]
        for t in nodes:
            local,_=shifted_cauchy_jet_mod(network,packet_size=request.packet_size,
                   node=t,precision_bits=bits,jet_order=multiplicity,
                   max_edges=request.max_edges,timeout_s=remaining())
            jets.append(local)
        recovered=reconstruct_mod(plan,jets,precision_bits=request.precision_bits,
                                  data_precision_bits=bits)
        check=None
        if request.cross_check:
            from veritas.research.tensor import brute_contract
            check=brute_contract(network,max_edges=request.max_edges,timeout_s=remaining())
            if recovered != check % (1<<request.precision_bits):
                raise HTTPException(500,'Hermite recovered residue disagrees with independent original contraction')
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
    except TimeoutError:
        return record('cauchy_hermite',request.model_dump(),{'status':'UNKNOWN','evidence_level':'NONE',
                       'reason':'Hermite calculation timed out'})
    return record('cauchy_hermite',request.model_dump(),{
        'status':'COUNT_RESIDUE','evidence_level':'RESEARCH_CROSS_CHECKED' if request.cross_check else 'RESEARCH_ONLY',
        'method':'EXACT_BOUNDED_MODULAR_HERMITE_WITH_GUARD_BITS',
        'recovered_constant_mod_2_power':str(recovered),'target_precision_bits':request.precision_bits,
        'input_precision_bits':bits,'guard_bits':plan.guard_bits,'degree_bound':degree,
        'nodes':nodes,'multiplicity_per_node':multiplicity,
        'exact_linear_recovery_weights':list(map(str,plan.weights)),
        'independently_contracted_original_count':str(check) if check is not None else None,
        'cnf_sha256':cnf.digest(),
        'warning':'Precision-checked bounded interpolation only. NOT the manuscript full D.5 schedule or subexponential recursion.'})

@app.post("/v1/research/packet-schedule")
def packet_schedule(request: PacketScheduleRequest):
    cnf = checked_cnf(request)
    occurrences = sum(map(len, cnf.clauses))
    max_occurrences = 24 if request.optimizer == 'bounded' else (128 if request.optimizer in ('scalable','matching') else 16)
    max_n = 24 if request.optimizer == 'bounded' else (128 if request.optimizer in ('scalable','matching') else 24)
    max_clauses = 24 if request.optimizer == 'bounded' else (128 if request.optimizer in ('scalable','matching') else 16)
    if occurrences > max_occurrences or cnf.n > max_n or len(cnf.clauses) > max_clauses:
        raise HTTPException(422, f'{request.optimizer} packet optimizer allows <={max_occurrences} wires, '
                                f'{max_n} variables, {max_clauses} clauses')
    if request.cross_check and occurrences > 12:
        raise HTTPException(422, 'independent count cross-check requires <=12 wires; set cross_check=false')
    try:
        net = from_cnf(cnf, max_degree=12 if request.optimizer in ('scalable','matching','bounded') else 16)
        evidence = None
        bounded_proof = None
        bound_replay = None
        matching_proof = None
        partition_proof = None
        partition_replay = None
        if request.optimizer == 'bounded':
            plan,partition_proof=optimize_packets_bounded(net,packet_size=request.packet_size,
                timeout_s=request.timeout_s,max_states=request.max_states,max_blocks=request.max_blocks)
            valid,partition_replay=verify_bounded_partition(net,plan,partition_proof)
            if not valid:raise HTTPException(500,'bounded partition evidence failed: '+partition_replay)
        elif request.optimizer == 'matching':
            if request.packet_size != 2:
                raise HTTPException(422,'matching optimizer requires packet_size=2')
            plan, matching_proof = optimize_packets_matching(net,max_wires=128)
            matching_valid, matching_replay = verify_matching_evidence(net,plan,matching_proof)
            if not matching_valid: raise HTTPException(500,'matching evidence replay failed: '+matching_replay)
        elif request.optimizer == 'exact_dp':
            plan,evidence = optimize_packets_exact(net, packet_size=request.packet_size,
                                                    timeout_s=request.timeout_s)
        elif request.optimizer == 'scalable':
            plan,bounded_proof = optimize_packets_scalable(net, packet_size=request.packet_size,
                      timeout_s=request.timeout_s, max_evaluations=request.max_evaluations,
                      restarts=request.restarts, seed=request.seed)
            valid,bound_replay = check_packet_search_evidence(net, plan, bounded_proof)
            if not valid:
                raise HTTPException(500, 'packet lower-bound evidence failed independent verification')
        else:
            plan = plan_packets(net, packet_size=request.packet_size,
                                max_permutations=request.max_permutations,
                                timeout_s=request.timeout_s)
        cross_check = None
        if request.cross_check:
            reordered = relabel_network(net, plan.wire_order)
            original = brute_contract(net, max_edges=12, timeout_s=request.timeout_s)
            changed = eliminate(reordered, max_table_entries=1<<15, timeout_s=request.timeout_s)
            if original != changed:
                raise HTTPException(500, 'edge permutation changed original tensor contraction')
            cross_check = str(original)
    except (ValueError,MatchingDependencyMissing) as exc:
        raise HTTPException(422,str(exc)) from exc
    except (TimeoutError, PacketPlanningLimit):
        return record('packet_schedule',request.model_dump(),{'status':'UNKNOWN','evidence_level':'NONE',
                      'reason':'bounded packet search exceeded resource budget'})
    return record('packet_schedule',request.model_dump(),{
        'status':'SCHEDULE',
        'evidence_level':('FINITE_PARTITION_INDEPENDENT_DP' if partition_proof.independent_oracle_checked else
             'FINITE_PARTITION_SEARCH_INTERNAL' if partition_proof.finished_search else 'FINITE_PARTITION_BOUND_CHECKED') if partition_proof else
             'FINITE_MATCHING_CROSSCHECKED' if matching_proof and matching_proof.oracle_checked else
             'FINITE_MATCHING_ALGORITHM_ONLY' if matching_proof else
             'FINITE_SURROGATE_OPTIMUM_LOWER_BOUND_CHECKED'
             if bounded_proof and bounded_proof.exact_optimum_certified else
             'RESEARCH_CROSS_CHECKED' if cross_check is not None else 'RESEARCH_ONLY',
        'method':'BOUNDED_PACKET_BRANCH_AND_BOUND' if partition_proof else 'EXACT_MINIMUM_WEIGHT_MATCHING' if matching_proof else
                 'SCALABLE_LOWER_BOUND_PACKET_SEARCH' if bounded_proof else 'BOUNDED_FACTOR_INCIDENCE_COLLISION_OPTIMIZER',
        'wire_order':list(plan.wire_order), 'stats':vars(plan),
        'finite_optimum_evidence':vars(evidence) if evidence is not None else None,
        'scalable_lower_bound_evidence':vars(bounded_proof) if bounded_proof is not None else None,
        'matching_evidence':vars(matching_proof) if matching_proof is not None else None,
        'bounded_partition_evidence':vars(partition_proof) if partition_proof is not None else None,
        'bounded_partition_replay':partition_replay,
        'matching_independent_replay':matching_replay if matching_proof is not None else None,
        'independent_lower_bound_check':bound_replay,
        'original_count_check':cross_check,'cnf_sha256':cnf.digest(),
        'warning':'Optimizes a finite incidence-collision proxy. Not the manuscript D.3 packing theorem or its asymptotic bound.'})


@app.post("/v1/research/cauchy-eliminate")
def cauchy_eliminate(request: CauchyEliminationRequest):
    cnf=checked_cnf(request)
    occurrences=sum(map(len,cnf.clauses))
    if occurrences>12 or cnf.n>24 or len(cnf.clauses)>18:
        raise HTTPException(422,'bounded Cauchy polynomial elimination allows <=12 wires, 24 variables and 18 clauses')
    if request.cross_check and occurrences>6:
        raise HTTPException(422,'independent half-wire oracle requires <=6 wires; set cross_check=false')
    if request.max_total_entries < request.max_table_entries:
        raise HTTPException(422,'max_total_entries must be >= max_table_entries')
    try:
        net=from_cnf(cnf,max_degree=12)
        result,stats=eliminate_cauchy_jet(net,packet_size=request.packet_size,
                node=request.node,precision_bits=request.precision_bits,jet_order=request.jet_order,
                optimize_packets=request.optimize_packets,packet_optimizer=request.packet_optimizer,
                max_table_entries=request.max_table_entries,
                max_total_entries=request.max_total_entries,timeout_s=request.timeout_s,
                elimination_order=request.elimination_order)
        oracle=None
        if request.cross_check:
            checked_net=relabel_network(net,stats.packet_schedule.wire_order) if stats.packet_schedule else net
            oracle,_=shifted_cauchy_jet_mod(checked_net,packet_size=request.packet_size,
                         node=request.node,precision_bits=request.precision_bits,
                         jet_order=request.jet_order,max_edges=6,timeout_s=request.timeout_s)
            if result!=oracle:
                raise HTTPException(500,'independent exhaustive Cauchy jet disagreed with polynomial bucket elimination')
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
    except (EliminationLimit, TimeoutError) as exc:
        return record('cauchy_eliminate',request.model_dump(),{'status':'UNKNOWN','evidence_level':'NONE',
                     'reason':str(exc)})
    from dataclasses import asdict
    return record('cauchy_eliminate',request.model_dump(),{
        'status':'JET_RESIDUES','evidence_level':'RESEARCH_CROSS_CHECKED' if oracle is not None else 'RESEARCH_ONLY',
        'method':'EXACT_POLYNOMIAL_FACTOR_ELIMINATION_OVER_MODULAR_JET_RING',
        'jet_coefficients_mod_2_power':list(map(str,result)),
        'independent_jet':list(map(str,oracle)) if oracle is not None else None,
        'precision_bits':request.precision_bits,'jet_order':request.jet_order,
        'stats':asdict(stats),'cnf_sha256':cnf.digest(),
        'warning':'Treewidth-dependent exact elimination, exponential worst case. Not the manuscript weighted-mode subexponential contraction.'})


@app.post("/v1/research/weighted-children")
def weighted_children(request: WeightedChildrenRequest):
    cnf=checked_cnf(request)
    occurrences=sum(map(len,cnf.clauses))
    if occurrences>request.max_edges or cnf.n>24 or len(cnf.clauses)>18:
        raise HTTPException(422,'weighted child-tensor research endpoint exceeds wire/formula budget')
    if request.cross_check and occurrences>6:
        raise HTTPException(422,'independent exhaustive half-wire oracle requires <=6 wires; set cross_check=false')
    try:
        net=from_cnf(cnf,max_degree=8)
        jet,modes,stats=recursive_weighted_jet(net,packet_size=request.packet_size,node=request.node,
                    group_span=request.group_span,precision_bits=request.precision_bits,
                    jet_order=request.jet_order,max_edges=request.max_edges,
                    max_boundary_vars=request.max_boundary_vars,
                    max_table_entries=request.max_table_entries,
                    max_work_assignments=request.max_work_assignments,timeout_s=request.timeout_s)
        oracle=None
        if request.cross_check:
            oracle,_=shifted_cauchy_jet_mod(net,packet_size=request.packet_size,node=request.node,
                     precision_bits=request.precision_bits,jet_order=request.jet_order,
                     max_edges=6,timeout_s=request.timeout_s)
            if jet!=oracle:
                raise HTTPException(500,'weighted recursive tensor disagreed with independent half-wire oracle')
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
    except (ChildTensorLimit,TimeoutError) as exc:
        return record('weighted_children',request.model_dump(),{
            'status':'UNKNOWN','evidence_level':'NONE','reason':str(exc),
            'warning':'No partial result was accepted.'})
    from dataclasses import asdict
    return record('weighted_children',request.model_dump(),{
        'status':'JET_RESIDUES','evidence_level':'RESEARCH_CROSS_CHECKED' if oracle is not None else 'RESEARCH_ONLY',
        'method':'RATIONAL_RANK_ONE_MODES_AND_BOUNDARY_CHILD_TENSORS',
        'jet_coefficients_mod_2_power':list(map(str,jet)),
        'independent_jet':list(map(str,oracle)) if oracle is not None else None,
        'precision_bits':request.precision_bits,'jet_order':request.jet_order,
        'stats':asdict(stats),'cnf_sha256':cnf.digest(),
        'warning':'Exact bounded rank-one mode reconstruction and conventional boundary recursion; exponential worst-case. NOT the manuscript D.4.4 mode-packing or subexponential recurrence.'})


@app.post("/v1/research/weighted-recovery")
def weighted_recovery(request: WeightedRecoveryRequest):
    """End-to-end guarded nonzero-node Hermite recovery from weighted child jets."""
    cnf=checked_cnf(request)
    if cnf.n>24 or len(cnf.clauses)>18:
        raise HTTPException(422, 'bounded weighted recovery supports <=24 variables and 18 clauses')
    try:
        result=recover_weighted_count(cnf, packet_size=request.packet_size,
            group_span=request.group_span, precision_bits=request.precision_bits,
            max_edges=request.max_edges,max_boundary_vars=request.max_boundary_vars,
            max_table_entries=request.max_table_entries,
            max_work_assignments=request.max_work_assignments,
            timeout_s=request.timeout_s,cross_check=request.cross_check)
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
    except (RecoveryBudgetExceeded,TimeoutError) as exc:
        return record('weighted_recovery',request.model_dump(),{
            'status':'UNKNOWN', 'evidence_level':'NONE', 'reason':str(exc),
            'warning':'No partial interpolation residue or count was accepted.'})
    payload=recovery_payload(result)
    # Avoid emitting false assertions of independently proved source jets.
    payload.update(status='EXACT_COUNT' if result.exact_count is not None else 'COUNT_RESIDUE',
        evidence_level='RESEARCH_CROSS_CHECKED' if request.cross_check else 'RESEARCH_ONLY',
        residue=str(result.residue),
        exact_count=str(result.exact_count) if result.exact_count is not None else None,
        warning='Bounded end-to-end rational mode/Hermite reference. Exponential complexity; not D.4.4/D.5 paper algorithm or a succinct proof.')
    return record('weighted_recovery',request.model_dump(),payload)


class BoundedDegreeRequest(CNFRequest):
    max_clause_width: int = Field(default=8,ge=0,le=12)
    max_wires: int = Field(default=5000,ge=0,le=50000)
    max_factors: int = Field(default=5000,ge=0,le=50000)
    contract: bool = False
    modulus_bits: int | None = Field(default=None,ge=2,le=64)
    max_table_entries: int = Field(default=65536,ge=1,le=1048576)
    max_work_assignments: int = Field(default=2000000,ge=1,le=20000000)


@app.post("/v1/research/bounded-degree-tensor")
def bounded_degree_tensor(request: BoundedDegreeRequest):
    cnf = CNF.from_lists(request.n,request.clauses)
    try:
        net, stats = bounded_degree_from_cnf(cnf,
            max_clause_width=request.max_clause_width,
            max_wires=request.max_wires,max_factors=request.max_factors)
        from dataclasses import asdict
        data = {'status':'STRUCTURALLY_PARISMONIOUS_TENSOR',
                'evidence_level':'MATHEMATICAL_CONSTRUCTION_NOT_KERNEL_PROOF',
                'input_sha256':cnf.digest(), 'stats':asdict(stats),
                'warning':'Constant-degree COPY gadget. NOT manuscript D.4.4/ETH speedup.'}
        data['independent_count_checked'] = False
        if request.contract:
            if net.edges > 512 or len(net.factors)>1200:
                raise ValueError('bounded contract permits <=512 wires and <=1200 factors; use structural-only mode')
            count, cstats = minfill_contract(net,
                modulus=(1<<request.modulus_bits) if request.modulus_bits is not None else None,
                max_table_entries=request.max_table_entries,
                max_work_assignments=request.max_work_assignments,
                timeout_s=request.timeout_s)
            if cnf.n <= 10 and len(cnf.clauses) <= 128 and sum(map(len, cnf.clauses)) <= 400:
                from veritas.solvers.reference import exhaustive_count
                reference=exhaustive_count(cnf,max_vars=10)
                if request.modulus_bits is not None:
                    reference%=1<<request.modulus_bits
                if count!=reference:
                    raise AssertionError('independent #SAT oracle disagrees with gadget contraction')
                data['independent_count_checked']=True
            data.update(status='EXACT_COUNT' if request.modulus_bits is None else 'COUNT_RESIDUE',
                        evidence_level='EXACT_ALGORITHM_NOT_PROOF_CERTIFICATE',
                        count=str(count), contract_stats=asdict(cstats))
        return record('bounded_degree_tensor',request.model_dump(),data)
    except (ValueError,ContractionBudgetExceeded) as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@app.get("/v1/paper/audit")
def paper_audit():
    return {
        "manuscript": "OpenAI: The Exponential Time Hypothesis is False (October 2026)",
        "formalization_scope_url": "https://github.com/openai/math/blob/main/lean/docs/378.md",
        "claims": [
            {"claim": "weaker Lean runtime", "statement": "2^O(n(loglog n)^2/sqrt(log n)) with polynomial factors", "implementation": "NOT_REPRODUCED_HERE"},
            {"claim": "sharper manuscript runtime", "statement": "2^O(n loglog n/sqrt(log n)) with polynomial factors", "implementation": "NOT_REPRODUCED_HERE"},
            {"claim": "Boolean indicator arithmetic", "implementation": "TOY_IDENTITY_TESTS"},
            {"claim": "2-adic modular arithmetic", "implementation": "TOY_IDENTITY_TESTS"},
            {"claim": "Boolean Mobius and Hermite interpolation", "implementation": "SMALL_EXACT_REFERENCE"},
            {"claim": "general tensor-network contraction", "implementation": "GENERIC_BASELINE_ONLY"},
            {"claim": "independently checked bounded UNSAT refutations", "implementation": "DPLL_TREE_CERTIFICATES_NOT_LRAT"},
            {"claim": "existential projected model counting", "implementation": "BOUNDED_BLOCKING_ENUMERATION"},
            {"claim": "counting proof certificates", "implementation": "EXACT_BOUNDED_SHANNON_TREE_INDEPENDENT_CHECKER"},
            {"claim": "violation count generating polynomial", "implementation": "EXACT_POLYNOMIAL_SEMIRING_TENSOR_ELIMINATION"},
            {"claim": "2-adic coefficient arithmetic", "implementation": "EXACT_RESIDUE_RING_TRUNCATION_NOT_ETH_MODE_PRUNING"},
            {"claim": "toy split-wire deformation with independent factorization nodes", "implementation": "EXACT_GENERIC_ELIMINATION_NO_SPEEDUP"},
            {"claim": "D.4.3 local Cauchy kernel and equation (77)", "implementation": "EXACT_TINY_EXHAUSTIVE_REFERENCE_NO_SPEEDUP"},
            {"claim": "2-adically integral shifted local Cauchy coordinates", "implementation": "EXACT_ODD_DENOMINATOR_RESIDUE_JETS_TOY"},
            {"claim": "node-matching cross-group mode expansion", "implementation": "SMALL_EXACT_VALUATION_CERTIFIED_REFERENCE_NOT_D4_4"},
            {"claim": "finite ring Hermite reconstruction with guard-bit tracking", "implementation": "EXACT_BOUNDED_RECONSTRUCTION_NOT_FULL_D5"},
            {"claim": "v1.0 exact grouped rational Cauchy rank modes", "implementation": "BOUNDED_COEFFICIENTWISE_RANK_FACTORIZATION_NOT_D4_4"},
            {"claim": "v1.0 balanced separator recursion", "implementation": "GENERIC_EXACT_EXHAUSTIVE_CUT_ENUMERATION_NOT_ETH"},
            {"claim": "v1.1 deterministic finite packet collision optimization", "implementation": "BOUNDED_INCIDENCE_COLLISION_HEURISTIC_NOT_MANUSCRIPT_D3"},
            {"claim": "v1.1 exact Cauchy polynomial-factor elimination", "implementation": "EXACT_BOUNDED_JET_CONTRACTION_TREEWIDTH_EXPONENTIAL"},
            {"claim": "v1.2 exact weighted low-rank mode pruning and boundary child tensors", "implementation": "BOUNDED_EXACT_RECONSTRUCTION_AND_GENERIC_BOUNDARY_RECURSION_NOT_D4_4"},
            {"claim": "v1.3 multi-node guarded Hermite count via weighted child jets", "implementation": "BOUNDED_END_TO_END_EXACT_COUNT_RESEARCH_ORACLE_CHECKED_NOT_D4_4"},
            {"claim": "v1.4 parsimonious constant-degree CNF tensor conversion", "implementation": "EXACT_COPY3_CHAIN_BIJECTION_AND_MIN_NEIGHBOR_EXACT_CONTRACTION_NOT_D4_4"},
            {"claim": "v1.5 adaptive exact CNF/COPY3 planner, valid elimination decomposition and separator DP", "implementation": "EXACT_TREEWIDTH_DEPENDENT_BACKEND_NOT_MANUSCRIPT_D4_4"},
            {"claim": "v1.6 fast indexed factor execution, sparse exact hash join and quick planner fallback", "implementation": "EXACT_BOUNDED_TREEWIDTH_ALGORITHMS_NOT_MANUSCRIPT_D4_4"},
            {"claim": "v1.7 exact subset-DP optimal dense-work order for <=12 original CNF variables", "implementation": "GLOBAL_OPTIMUM_OF_DENSE_WORK_PROXY_WITH_INDEPENDENT_GRAPH_FILL_REPLAY_NOT_D4_4"},
            {"claim": "Cauchy deformation: original D.4.4 packet collision packing and subexponential recursive contraction", "implementation": "NOT_IMPLEMENTED"},
        ],
        "status": "INCOMPLETE_PAPER_REPRODUCTION",
        "note": "Compilation of upstream Lean and its axioms has not been performed by this build.",
    }


class OptimalOrderRequest(CNFRequest):
    objective: str = Field(default='work', pattern='^(work|width)$')


@app.post('/v1/research/optimal-order')
def optimal_order_report(request: OptimalOrderRequest):
    """Finite-graph optimality of a declared proxy, NOT theoretical ETH proof."""
    from dataclasses import asdict
    from time import monotonic
    from veritas.research.contraction_planner import original_cnf_model, elimination_order
    from veritas.research.optimal_order import optimize_small_model, replay_order
    cnf=checked_cnf(request)
    start=monotonic()
    try:
        model=original_cnf_model(cnf)
        deadline=start+request.timeout_s
        plan,evidence=optimize_small_model(model,objective=request.objective,deadline=deadline)
        quick=elimination_order(model,'min_degree',deadline=deadline)
        # Replay uses independently coded graph-fill, not the subset DP.
        replay_cost,replay_width=replay_order(model,plan.order)
        if (replay_cost,replay_width)!=(plan.estimated_assignments,plan.induced_width):
            raise AssertionError('optimizer/replay mismatch')
    except (ValueError,ContractLimit) as exc:
        return record('optimal_order_report',request.model_dump(),
                      {'status':'UNKNOWN','reason':str(exc),
                       'evidence_level':'NONE','count':None})
    result={'status':'FINITE_GRAPH_OPTIMAL_ORDER','objective':request.objective,
            'plan':asdict(plan),'optimality':asdict(evidence),
            'baseline_min_degree':asdict(quick),
            'model_sha256':cnf.digest(),'count':None,
            'replay_verified':True,
            'evidence_level':'EXACT_SUBSET_DP_PLUS_INDEPENDENT_FILL_REPLAY',
            'elapsed_seconds':monotonic()-start,
            'warning':'The work proxy and induced width are NOT guarantees of elapsed time; '
                      'this is not the manuscript D.3/D.4.4 subexponential recursion.'}
    return record('optimal_order_report',request.model_dump(),result)


class AdaptiveContractRequest(CNFRequest):
    portfolio_mode: str = Field(default='auto', pattern='^(auto|thorough|optimal_small)$')
    execution_mode: str = Field(default='indexed', pattern='^(indexed|legacy|sparse)$')
    precision_bits: int | None = Field(default=None, ge=1, le=128)
    include_copy3: bool = True
    enable_separators: bool = True
    max_separator: int = Field(default=2, ge=0, le=3)
    max_slices: int = Field(default=3, ge=0, le=8)
    max_table_entries: int = Field(default=65536, ge=1, le=1048576)
    max_work_assignments: int = Field(default=2000000, ge=1, le=20000000)
    max_wires: int = Field(default=1800, ge=1, le=2500)
    max_factors: int = Field(default=2500, ge=1, le=5000)
    cross_check: bool = True


@app.post('/v1/research/adaptive-contract')
def adaptive_contract(request: AdaptiveContractRequest):
    cnf=checked_cnf(request)
    try:
        result=adaptive_count(cnf, precision_bits=request.precision_bits,
            include_copy3=request.include_copy3,
            enable_separators=request.enable_separators,
            max_separator=request.max_separator,
            max_slices=request.max_slices,
            max_table_entries=request.max_table_entries,
            max_work_assignments=request.max_work_assignments,
            max_wires=request.max_wires,max_factors=request.max_factors,
            timeout_s=request.timeout_s,
            portfolio_mode=request.portfolio_mode,execution_mode=request.execution_mode)
    except (ValueError,ContractLimit) as exc:
        return record('adaptive_contract', request.model_dump(),
            {'status':'UNKNOWN','evidence_level':'NONE','reason':str(exc),
             'warning':'Limits exceeded. No count returned and no partial answer accepted.'})
    independent=False
    if request.cross_check and cnf.n<=10 and len(cnf.clauses)<=128:
        expected=exhaustive_count(cnf)
        if request.precision_bits is not None:
            expected%=1<<request.precision_bits
        if int(result['count'])!=expected:
            raise HTTPException(500,'independent exhaustive counting mismatch')
        independent=True
    result['independent_count_checked']=independent
    result['evidence_level']='REFERENCE_CROSS_CHECKED' if independent else 'EXACT_ALGORITHM_NOT_INDEPENDENTLY_CHECKED'
    return record('adaptive_contract',request.model_dump(),result)


@app.get("/v1/audits/{record_sha256}")
def read_audit(record_sha256: str):
    if not re.fullmatch(r"[a-f0-9]{64}", record_sha256):
        raise HTTPException(422, "expected 64 lowercase hex characters")
    audit = audits().get(record_sha256)
    if audit is None:
        raise HTTPException(404, "audit not found")
    chain_ok, _ = audits().verify_chain()
    return {**audit, "entire_local_chain_valid": chain_ok}


def serve():
    import uvicorn
    uvicorn.run("veritas.api.main:app", host="127.0.0.1", port=8080, reload=False)


# v2.5 research endpoints: isolated from authoritative proof and count responses.
from veritas.research.eth_packing.parameters import manuscript_parameters, scaled_parameters
from veritas.research.eth_packing.packing import construct_packing
from veritas.research.eth_packing.checker import check_packing
from veritas.research.eth_packing.cauchy import verify_cauchy_matrix
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing

class ETHParametersRequest(BaseModel):
    s: int = Field(ge=1)
    depth: int = Field(default=0, ge=0, le=1000)
    mode: str = Field(default="MANUSCRIPT_EXACT", pattern="^(MANUSCRIPT_EXACT|EXPERIMENTAL_SCALED)$")
    a: int = Field(default=2, ge=1, le=5)
    r: int = Field(default=4, ge=2, le=64)

class ETHPackingRequest(BaseModel):
    edges: list[list[int]] = Field(max_length=512)
    a: int = Field(default=2, ge=1, le=5)
    r: int = Field(default=4, ge=2, le=64)
    enforce_bounds: bool = False

class ETHCheckRequest(BaseModel):
    certificate: dict
    require_bounds: bool = False

class ETHRingRequest(BaseModel):
    degree: int = Field(default=4, ge=1, le=16)
    precision: int = Field(default=8, ge=1, le=128)
    coefficients: list[int] = Field(default_factory=lambda:[1,1],max_length=16)

@app.post("/v1/research/eth/parameters")
def eth_parameters_v25(request: ETHParametersRequest):
    try:
        p = (manuscript_parameters(request.s,request.depth) if request.mode=="MANUSCRIPT_EXACT"
             else scaled_parameters(request.s,request.a,request.r,request.depth))
        return p.to_dict()
    except (ValueError, OverflowError) as exc:
        raise HTTPException(status_code=422,detail=str(exc))

@app.post("/v1/research/eth/packing")
def eth_packing_v25(request: ETHPackingRequest):
    try:
        return construct_packing(request.edges,r=request.r,a=request.a,
                                 enforce_bounds=request.enforce_bounds,max_edges=512)
    except (ValueError,TypeError,KeyError) as exc:
        raise HTTPException(status_code=422,detail=str(exc))

@app.post("/v1/research/eth/packing/check")
def eth_packing_check_v25(request: ETHCheckRequest):
    return check_packing(request.certificate,require_bounds=request.require_bounds)

@app.post("/v1/research/eth/ring")
def eth_ring_v25(request: ETHRingRequest):
    try:
        f = first_irreducible(request.degree)
        ring = ExtensionRing(request.precision,f)
        elem = ring.elem(request.coefficients)
        return {'degree':ring.e,'precision':ring.p,'irreducible_binary':bin(f),
                'element':elem,'is_unit':ring.is_unit(elem),
                'valuation':ring.valuation(elem),
                'inverse':ring.inverse(elem) if ring.is_unit(elem) else None,
                'status':'EXACT_RING_REFERENCE'}
    except (ValueError,ZeroDivisionError) as exc:
        raise HTTPException(status_code=422,detail=str(exc))

@app.get("/v1/research/eth/status")
def eth_status_v25():
    return {'version':'2.5.0','experimental':True,'subexponential_solver':False,
            'implemented':['manuscript parameter formulas and eligibility flags',
                'scaled finite packet arrangement with independent invariant checks',
                'endpoint-load conditional expectation',
                'exact 2-adic unramified extension arithmetic and truncated jets',
                'bounded exact Cauchy polynomial identity'],
            'not_implemented':['complete D.3 packet packing conditional-expectation theorem',
                'manuscript-specified full coefficient-ring interpolation',
                'D.4.4 weighted mode bound and specialized subexponential recursion']}


# v2.6 — exact finite Appendix D.3 conditional expectation and padding.
# This route is isolated from authoritative #SAT endpoints.
from veritas.research.eth_packing_v26 import construct_d3_packing, verify_d3_packing

class D3PackingRequestV26(BaseModel):
    edges: list[list[int]] = Field(max_length=512)
    r: int = Field(default=2,ge=2,le=64)
    a: int = Field(default=1,ge=1,le=5)
    max_work: int = Field(default=3_000_000,ge=1,le=5_000_000)
    max_packets: int = Field(default=5000,ge=1,le=10000)
    require_theorem_preconditions: bool = False

class D3CertificateCheckRequestV26(BaseModel):
    certificate: dict
    check_trace: bool = True

@app.post('/v1/research/eth/d3/construct')
def d3_construct_v26(request:D3PackingRequestV26):
    try:
        return construct_d3_packing(request.edges,r=request.r,a=request.a,
           max_work=request.max_work,max_packets=request.max_packets,
           require_theorem_preconditions=request.require_theorem_preconditions)
    except (ValueError,TypeError,OverflowError) as exc:
        raise HTTPException(status_code=422,detail=str(exc))

@app.post('/v1/research/eth/d3/check')
def d3_check_v26(request:D3CertificateCheckRequestV26):
    return verify_d3_packing(request.certificate,check_trace=request.check_trace)

@app.get('/v1/research/eth/d3/status')
def d3_status_v26():
    return {'version':'2.6.0','implementation':'FINITE_D3_CONDITIONAL_EXPECTATION_AND_UNIFORM_PADDING',
      'properties':['separate row and column vertex labels',
                    'exact directed-pair collision potential',
                    'monotone derandomization transcript',
                    'common H padding of every directed class',
                    'D.6 finite numerical predicate checks',
                    'independent per-wire orientation and class-capacity checker'],
      'limitations':['bounded-scale constructor','no original asymptotic runtime claim',
                     'no D.4.4 mode enumeration/recursive ETH solver']}

# v2.7 — finite scalar Appendix D.4.4 column-tile geometric modes.
# This is *not* the extension-ring Taylor-jet / recursive child-tensor theorem.
from veritas.research.eth_modes_v27 import construct_tile_modes, verify_tile_modes

class D44FiniteModeRequestV27(BaseModel):
    edges: list[list[int]] = Field(max_length=64)
    radix: int = Field(default=2,ge=2,le=4)
    a: int = Field(default=2,ge=1,le=3)
    node: int = Field(default=1)
    zeta: int = Field(default=1,ge=0,le=8)
    precision: int = Field(default=5,ge=2,le=12)

class D44FiniteModeCheckV27(BaseModel):
    certificate: dict

@app.post('/v1/research/eth/d44/modes')
def d44_modes_v27(request:D44FiniteModeRequestV27):
    try:
        d3=construct_d3_packing(request.edges,r=request.radix,a=request.a,
                                max_work=500_000,max_packets=1000)
        cert=construct_tile_modes(d3,node=request.node,zeta=request.zeta,
                                  precision=request.precision,max_modes=1000,
                                  max_tuple_count=20_000)
        check=verify_tile_modes(cert)
        if not check['valid']:
            raise ValueError('independent checker rejected generated certificate')
        return {'certificate':cert,'verification':check}
    except (ValueError,TypeError,OverflowError) as exc:
        raise HTTPException(status_code=422,detail=str(exc))

@app.post('/v1/research/eth/d44/check')
def d44_check_v27(request:D44FiniteModeCheckV27):
    return verify_tile_modes(request.certificate)

@app.get('/v1/research/eth/d44/status')
def d44_status_v27():
    return {'version':'2.7.0','scope':'FINITE_SCALAR_D44_TILE_MODES',
            'implemented':['checked v2.6 D3 packet input',
              'cross-group geometric tile expansion at integer evaluation points',
              'valuation lower bounds for each row coefficient',
              'lazy weighted-exponent enumeration with bounded count',
              'independent direct Cauchy matrix reconstruction',
              'small-network complete deformed contraction reference'],
            'not_implemented':['full extension-ring Taylor jets',
                'tapered interpolation integrated with specialized modes',
                'D.4.4 implicit grouped child tensors and recursive contraction',
                'subexponential runtime guarantee']}

# v2.8 finite extension-ring interpolation research (no ETH runtime claim).
from veritas.research.eth_arithmetic.gf2 import first_irreducible as _eth28_irreducible
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing as _Eth28Ring
from veritas.research.eth_interpolation.shifted_cauchy import verify_cauchy_interpolation as _eth28_cauchy

class Eth28CauchyRequest(BaseModel):
    packet_size: int = Field(default=2,ge=1,le=8)
    node: int = 1
    precision: int = Field(default=8,ge=1,le=32)
    extension_degree: int = Field(default=4,ge=1,le=8)

@app.post('/v1/research/eth/extension-cauchy')
def eth28_extension_cauchy(request: Eth28CauchyRequest):
    try:
        ring=_Eth28Ring(request.precision,_eth28_irreducible(request.extension_degree))
        return _eth28_cauchy(request.packet_size,request.node,ring)
    except (ValueError,TypeError,ZeroDivisionError,OverflowError) as exc:
        raise HTTPException(status_code=422,detail=str(exc))

@app.get('/v1/research/eth/v28/status')
def eth28_status():
    return {'version':'2.8.0', 'scope':'FINITE_EXTENSION_RING_TAYLOR_REFERENCE',
            'implemented':['published floor-parameter correction',
                           'distinct GF(2^e) residues and unit-denominator interpolation',
                           'creation-time canonical lifts',
                           'exact rational-to-ring shifted Cauchy polynomial jets',
                           'full-degree polynomial recovery for bounded instances'],
            'not_implemented':['manuscript tapered Hermite with guard precision',
                               'extension-ring D.4.4 weighted-mode recursion',
                               'implicit recursive child tensor construction',
                               'subexponential ETH solver']}

# v2.9 bounded finite-reference research: NO manuscript recursion or
# subexponential complexity claim. No unbounded input accepted.
from veritas.research.eth_interpolation.tapered_hermite import (
    make_tapered_plan as _eth29_tapered_plan,
    sample_integer_polynomial as _eth29_sample_poly,
    reconstruct_tapered as _eth29_recover_tapered,
    check_tapered_against_polynomial as _eth29_check_tapered)
from veritas.research.eth_modes_v29.extension_modes import (
    make_extension_modes as _eth29_modes,
    check_extension_modes as _eth29_check_modes)
from veritas.research.eth_packing_v26.constructor import construct_d3_packing as _eth29_d3

class Eth29TaperedRequest(BaseModel):
    wires: int = Field(default=2,ge=1,le=8)
    a: int = Field(default=1,ge=1,le=5)
    u: int = Field(default=1,ge=1,le=16)
    precision: int = Field(default=8,ge=1,le=128)
    coefficients: list[int] = Field(default_factory=lambda:[12,9,-3,0,2],min_length=1,max_length=32)

@app.post('/v1/research/eth/tapered-reference')
def eth29_tapered(request:Eth29TaperedRequest):
    try:
        p=_eth29_tapered_plan(M=request.wires,a=request.a,u=request.u,p=request.precision)
        j=_eth29_sample_poly(p,request.coefficients)
        return {'plan':p.to_dict(), 'recovery':_eth29_check_tapered(p,j,request.coefficients),
                'result_mod_2p':_eth29_recover_tapered(p,j)}
    except (ValueError,TypeError,ZeroDivisionError,ArithmeticError) as exc:
        raise HTTPException(status_code=422,detail=str(exc))

class Eth29ModesRequest(BaseModel):
    edges: list[list[int]] = Field(default_factory=lambda:[[0,0],[1,1],[0,1],[1,0]],max_length=12)
    radix: int = Field(default=2,ge=2,le=4)
    a: int = Field(default=1,ge=1,le=2)
    node: int = 1
    precision: int = Field(default=8,ge=2,le=32)
    extension_degree: int = Field(default=4,ge=1,le=8)
    jet_length: int = Field(default=3,ge=1,le=8)

@app.post('/v1/research/eth/extension-modes')
def eth29_extension_modes(request:Eth29ModesRequest):
    try:
        base=_eth29_d3(request.edges,r=request.radix,a=request.a,max_work=100_000,max_packets=256)
        cert=_eth29_modes(base,node=request.node,precision=request.precision,
            extension_degree=request.extension_degree,jet_length=request.jet_length)
        checked=_eth29_check_modes(cert)
        if not checked['valid']:raise ArithmeticError(str(checked))
        return {'checker':checked,'certificate':cert}
    except (ValueError,TypeError,ZeroDivisionError,ArithmeticError) as exc:
        raise HTTPException(status_code=422,detail=str(exc))

class Eth29ModesCheckRequest(BaseModel):
    certificate: dict

@app.post('/v1/research/eth/extension-modes/check')
def eth29_check_extension_modes(request:Eth29ModesCheckRequest):
    return _eth29_check_modes(request.certificate)

@app.get('/v1/research/eth/v29/status')
def eth29_status():
    return {'version':'2.9.0','claim':'FINITE_REFERENCE_ONLY',
        'implemented':['bounded tapered Hermite multiplicity/precision schedule',
            'mixed-precision exact rational constant-term reconstruction',
            'independent polynomial oracle checking',
            'finite 2-adic extension-ring rank-one Cauchy jets',
            'independent direct-matrix coefficient and valuation checking'],
        'not_implemented':['paper D.4.4 geometric tile expansion in extension-ring Taylor modes',
            'specialized implicit recursive child tensor networks',
            'subexponential runtime or polynomial-space proof']}


# v3.0 independently checked finite *implicit* child-tensor reference.
# The real D.4.4 geometric-tile recursion is NOT implemented here.
from veritas.research.eth_recursion_v30 import (
    make_bipartite_edges as _eth30_edges,
    make_child_certificate as _eth30_construct,
    check_child_certificate as _eth30_check)

class Eth30ChildrenRequest(BaseModel):
    n: int = Field(default=2, ge=1, le=5)
    clauses: list[list[int]] = Field(default_factory=lambda:[[1,2]], max_length=8)
    radix: int = Field(default=2, ge=2, le=3)
    a: int = Field(default=1, ge=1, le=2)
    node: int = 1
    precision: int = Field(default=8, ge=2, le=32)
    extension_degree: int = Field(default=4, ge=1, le=8)
    jet_length: int = Field(default=3, ge=1, le=6)

@app.post('/v1/research/eth/implicit-children')
def eth30_implicit_children(req:Eth30ChildrenRequest):
    try:
        net=from_cnf(CNF.from_lists(req.n,req.clauses),max_degree=12)
        base=_eth29_d3(_eth30_edges(net),r=req.radix,a=req.a,max_work=150000,max_packets=256)
        cert=_eth30_construct(net,base,node=req.node,precision=req.precision,
                  extension_degree=req.extension_degree,jet_length=req.jet_length,
                  max_assignments=100000,timeout_s=8.0)
        checked=_eth30_check(cert,max_assignments=100000,timeout_s=8.0)
        if not checked['valid']:raise ArithmeticError('independent replay failed: '+str(checked))
        return {'checker':checked,'certificate':cert}
    except (ValueError,TypeError,OverflowError,ArithmeticError,RuntimeError,TimeoutError) as exc:
        raise HTTPException(status_code=422,detail=str(exc))

class Eth30CheckRequest(BaseModel):
    certificate: dict

@app.post('/v1/research/eth/implicit-children/check')
def eth30_check_implicit_children(req:Eth30CheckRequest):
    return _eth30_check(req.certificate,max_assignments=100000,timeout_s=8.0)

@app.get('/v1/research/eth/v30/status')
def eth30_status():
    return {'version':'3.0.0','claim':'FINITE_IMPLICIT_SEPARATOR_REFERENCE_ONLY',
        'implemented':['D.3 group-labelled implicit child tensor functions',
          'extension-ring Cauchy Taylor jets evaluated lazily',
          'exact boundary summation with memoized children',
          'independent 4^M half-edge reference evaluation',
          'replayable fail-closed child certificates'],
        'not_implemented':['D.4.4 geometric-tile modes connected to children',
           'manuscript weighted-mode recursion','M/8 child size guarantee',
           'subexponential time and polynomial-space proof']}


# v3.1 bounded extension-ring geometric-tile mode-indexed scalar children.
from veritas.research.eth_modes_v31 import (
    make_jet_tile_modes as _eth31_modes,
    check_jet_tile_modes as _eth31_verify_modes,
    contract_mode_children as _eth31_contract,
    check_mode_child_certificate as _eth31_verify_children)

class Eth31ModeChildrenRequest(BaseModel):
    n: int = Field(default=2,ge=1,le=4)
    clauses: list[list[int]] = Field(default_factory=lambda:[[1,2]],max_length=6)
    radix: int = Field(default=2,ge=2,le=4)
    a: int = Field(default=1,ge=1,le=2)
    node: int = 1
    precision: int = Field(default=5,ge=2,le=10)
    extension_degree: int = Field(default=3,ge=1,le=8)
    jet_length: int = Field(default=2,ge=1,le=4)

@app.post('/v1/research/eth/geometric-mode-children')
def eth31_geometric_mode_children(req:Eth31ModeChildrenRequest):
    try:
        net=from_cnf(CNF.from_lists(req.n,req.clauses),max_degree=12)
        base=_eth29_d3(_eth30_edges(net),r=req.radix,a=req.a,max_work=150000,max_packets=256)
        cert=_eth31_modes(base,node=req.node,precision=req.precision,
                      extension_degree=req.extension_degree,jet_length=req.jet_length)
        checked=_eth31_verify_modes(cert)
        if not checked['valid']:raise ArithmeticError('mode verification failed')
        result=_eth31_contract(net,cert,max_work=150000,timeout_s=8)
        verified=_eth31_verify_children(result,max_work=150000,timeout_s=8)
        if not verified['valid']:raise ArithmeticError('child replay verification failed')
        return {'mode_checker':checked,'child_checker':verified,'certificate':result}
    except (ValueError,TypeError,OverflowError,ArithmeticError,RuntimeError,TimeoutError) as exc:
        raise HTTPException(status_code=422,detail=str(exc))

class Eth31CheckRequest(BaseModel):
    certificate: dict

@app.post('/v1/research/eth/geometric-mode-children/check')
def eth31_check_geometric_mode_children(req:Eth31CheckRequest):
    return _eth31_verify_children(req.certificate,max_work=150000,timeout_s=8)

@app.get('/v1/research/eth/v31/status')
def eth31_status():
    return {'version':'3.1.0','claim':'FINITE_MODE_INDEXED_SCALAR_CHILDREN_ONLY',
        'implemented':['D.3-packet geometric-tile expansion over extension-ring Taylor jets',
           'exact 2-adic divisibility checks per coefficient',
           'valuation-capped weighted-mode enumeration',
           'symbol-group mode-indexed finite scalar child factorization',
           'independent direct 4**M half-edge oracle and certificate replay'],
        'not_implemented':["the manuscript's recursively shrinking child tensor networks",
          "the manuscript's full recursion and precision accounting",
          'subexponential time or polynomial-space proof']}

# v3.2 finite D.4.4 mode-exponent bond network, exact but not recursive ETH.
from veritas.research.eth_mode_bonds_v32 import (
    construct_bond_certificate as _eth32_contract,
    check_bond_certificate as _eth32_check)

@app.post('/v1/research/eth/mode-bond-network')
def eth32_mode_bonds(req:Eth31ModeChildrenRequest):
    try:
        net=from_cnf(CNF.from_lists(req.n,req.clauses),max_degree=12)
        base=_eth29_d3(_eth30_edges(net),r=req.radix,a=req.a,
                       max_work=150000,max_packets=256)
        modes=_eth31_modes(base,node=req.node,precision=req.precision,
                           extension_degree=req.extension_degree,jet_length=req.jet_length)
        cert=_eth32_contract(net,modes,max_work=180000,timeout_s=9)
        verdict=_eth32_check(cert,max_work=180000,timeout_s=9)
        if not verdict['valid']:raise ArithmeticError('mode bond certificate replay failed')
        return {'checker':verdict,'certificate':cert}
    except (ValueError,TypeError,OverflowError,ArithmeticError,RuntimeError,TimeoutError) as exc:
        raise HTTPException(status_code=422,detail=str(exc))

@app.post('/v1/research/eth/mode-bond-network/check')
def eth32_check_mode_bonds(req:Eth31CheckRequest):
    return _eth32_check(req.certificate,max_work=180000,timeout_s=9)

@app.get('/v1/research/eth/v32/status')
def eth32_status():
    return {'version':'3.2.0','claim':'FINITE_EXACT_SPARSE_MODE_BONDS_ONLY',
      'implemented':['source/target group transfer tensors indexed by geometric mode exponents',
        'exact sparse exponent-bond joins and sum-elimination',
        'full child-entry certificate with independent source replay',
        'direct 4**M Cauchy half-edge cross-check',
        'hard work/entry/timeout limits'],
      'not_implemented':['the manuscript’s recursively smaller packet tensors',
        'the D.4.4 child-size and polynomial-space theorem',
        'subexponential ETH algorithm']}


# v3.3 finite recursive separator mode-bond contraction (NOT manuscript D.4.4 recursion)
from veritas.research.eth_recursive_bonds_v33 import (
    construct_recursive_certificate as _eth33_construct,
    check_recursive_certificate as _eth33_check)

@app.post('/v1/research/eth/recursive-mode-bonds')
def eth33_recursive_mode_bonds(req:Eth31ModeChildrenRequest):
    try:
        net=from_cnf(CNF.from_lists(req.n,req.clauses),max_degree=12)
        base=_eth29_d3(_eth30_edges(net),r=req.radix,a=req.a,
                      max_work=150000,max_packets=256)
        modes=_eth31_modes(base,node=req.node,precision=req.precision,
                          extension_degree=req.extension_degree,jet_length=req.jet_length)
        cert=_eth33_construct(net,modes,max_work=150000,timeout_s=9)
        verdict=_eth33_check(cert,max_work=150000,timeout_s=9)
        if not verdict['valid']:raise ArithmeticError('recursive certificate replay failed')
        return {'checker':verdict,'certificate':cert}
    except (ValueError,TypeError,OverflowError,ArithmeticError,RuntimeError,TimeoutError) as exc:
        raise HTTPException(status_code=422,detail=str(exc))

@app.post('/v1/research/eth/recursive-mode-bonds/check')
def eth33_recursive_mode_bonds_check(req:Eth31CheckRequest):
    return _eth33_check(req.certificate,max_work=150000,timeout_s=9)

@app.get('/v1/research/eth/v33/status')
def eth33_status():
    return {'version':'3.3.0','claim':'FINITE_EXACT_RECURSIVE_MODE_BOND_SUM_PRODUCT_ONLY',
      'implemented':['recursive sparse mode-index conditioning',
        'disconnected-component decomposition and memoization',
        'exact extension-ring Taylor arithmetic',
        'independent v3.2 sparse-elimination and half-edge oracle',
        'source-replayed certificates with resource limits'],
      'not_implemented':['manuscript-specific recursively shrinking packet tensors',
        'M/8 child wire guarantee','complete subexponential ETH algorithm']}

# v3.4 structural child-size preflight (NOT manuscript recursive children).
from veritas.research.eth_child_topology_v34 import (
    construct_topology_certificate as _eth34_construct,
    check_topology_certificate as _eth34_check)

class Eth34TopologyRequest(Eth31ModeChildrenRequest):
    with_modes: bool = True

@app.post('/v1/research/eth/child-topology')
def eth34_child_topology(req:Eth34TopologyRequest):
    try:
        net=from_cnf(CNF.from_lists(req.n,req.clauses),max_degree=12)
        base=_eth29_d3(_eth30_edges(net),r=req.radix,a=req.a,max_work=150000,max_packets=256)
        modes=(_eth31_modes(base,node=req.node,precision=req.precision,
                    extension_degree=req.extension_degree,jet_length=req.jet_length)
                    if req.with_modes else None)
        coordinate=_v2_for_eth34(req.node) if modes is not None else 0
        cert=_eth34_construct(base,mode_certificate=modes,coordinate=coordinate)
        verdict=_eth34_check(cert)
        if not verdict['valid']:raise ArithmeticError('topology replay failed')
        return {'checker':verdict,'certificate':cert}
    except (ValueError,TypeError,IndexError,OverflowError,ArithmeticError,RuntimeError,TimeoutError) as exc:
        raise HTTPException(status_code=422,detail=str(exc))

def _v2_for_eth34(node):
    if type(node) is not int or node==0:raise ValueError('node must be nonzero integer')
    return (abs(node)&-abs(node)).bit_length()-1

@app.post('/v1/research/eth/child-topology/check')
def eth34_child_topology_check(req:Eth31CheckRequest):
    return _eth34_check(req.certificate)

@app.get('/v1/research/eth/v34/status')
def eth34_status():
    return {'version':'3.4.0','claim':'FINITE_D3_PORT_AND_MODE_INCIDENCE_LEDGER_ONLY',
        'implemented':['verified original-half-port group counts','exact D.3 packet-slot ledger',
            'checked finite geometric-mode source/target incidence',
            'conditional numeric D.6 prerequisites','source-replayed structural certificates'],
        'not_implemented':['actual manuscript D.4.4 recursively shrinking packet tensors',
            'proof of M/8 full-child wire bound','subexponential runtime proof']}

from veritas.research.eth_child_topology_v34 import (
    construct_integrated_certificate as _eth34_integrate,
    check_integrated_certificate as _eth34_integrated_check)

@app.post('/v1/research/eth/checked-structure-and-contraction')
def eth34_structure_contraction(req:Eth31ModeChildrenRequest):
    try:
        net=from_cnf(CNF.from_lists(req.n,req.clauses),max_degree=12)
        base=_eth29_d3(_eth30_edges(net),r=req.radix,a=req.a,max_work=150000,max_packets=256)
        modes=_eth31_modes(base,node=req.node,precision=req.precision,
                           extension_degree=req.extension_degree,jet_length=req.jet_length)
        cert=_eth34_integrate(net,modes,max_work=150000,timeout_s=9)
        result=_eth34_integrated_check(cert,max_work=150000,timeout_s=9)
        if not result['valid']:raise ArithmeticError(result['reason'])
        return {'checker':result,'certificate':cert}
    except (ValueError,TypeError,IndexError,OverflowError,ArithmeticError,RuntimeError,TimeoutError) as exc:
        raise HTTPException(status_code=422,detail=str(exc))

@app.post('/v1/research/eth/checked-structure-and-contraction/check')
def eth34_structure_contraction_check(req:Eth31CheckRequest):
    return _eth34_integrated_check(req.certificate,max_work=150000,timeout_s=9)


# v3.5: finite exact child factor scopes and independent replay.
from veritas.research.eth_child_network_v35 import (
    construct_child_network_certificate as _eth35_build,
    check_child_network_certificate as _eth35_check)

@app.post('/v1/research/eth/finite-child-network')
def eth35_child_network(req:Eth31ModeChildrenRequest):
    try:
        net=from_cnf(CNF.from_lists(req.n,req.clauses),max_degree=12)
        base=_eth29_d3(_eth30_edges(net),r=req.radix,a=req.a,max_work=150000,max_packets=256)
        modes=_eth31_modes(base,node=req.node,precision=req.precision,
                           extension_degree=req.extension_degree,jet_length=req.jet_length)
        cert=_eth35_build(net,modes,max_child_scope=64,max_work=150000,timeout_s=9)
        verdict=_eth35_check(cert,max_work=150000,timeout_s=9)
        if verdict.get('valid') is not True:raise ArithmeticError(str(verdict.get('reason')))
        return {'checker':verdict,'certificate':cert}
    except (ValueError,TypeError,IndexError,OverflowError,ArithmeticError,RuntimeError,TimeoutError) as exc:
        raise HTTPException(status_code=422,detail=str(exc))

@app.post('/v1/research/eth/finite-child-network/check')
def eth35_child_network_check(req:Eth31CheckRequest):
    return _eth35_check(req.certificate,max_work=150000,timeout_s=9)

@app.get('/v1/research/eth/v35/status')
def eth35_status():
    return {'version':'3.5.0','claim':'FINITE_MODE_BOND_CHILD_FACTOR_SCOPES_WITH_RESOURCE_GATES_ONLY',
            'implemented':['explicit finite child factor scope','exact mode-bond incidence',
                'total original-halfbit coverage','bounded child-scope construction',
                'independent composite exact-contraction replay'],
            'not_implemented':['manuscript D.4.4 child packet tensors','M/8 theorem','subexponential SAT algorithm']}


# v3.6: exact Boolean-multilinear Cauchy packet tensor reference.
from veritas.research.eth_packet_tensors_v36 import (
    construct_packet_tensor_certificate as _eth36_build,
    check_packet_tensor_certificate as _eth36_check)

@app.post('/v1/research/eth/finite-packet-tensors')
def eth36_packet_tensors(req:Eth31ModeChildrenRequest):
    try:
        net=from_cnf(CNF.from_lists(req.n,req.clauses),max_degree=12)
        base=_eth29_d3(_eth30_edges(net),r=req.radix,a=req.a,max_work=150000,max_packets=256)
        modes=_eth31_modes(base,node=req.node,precision=req.precision,
                           extension_degree=req.extension_degree,jet_length=req.jet_length)
        cert=_eth36_build(net,modes,max_work=350000,timeout_s=9)
        verdict=_eth36_check(cert,max_work=350000,timeout_s=9)
        if verdict.get('valid') is not True:raise ArithmeticError(str(verdict.get('reason')))
        return {'checker':verdict,'certificate':cert}
    except (ValueError,TypeError,IndexError,OverflowError,ArithmeticError,RuntimeError,TimeoutError) as exc:
        raise HTTPException(status_code=422,detail=str(exc))

@app.post('/v1/research/eth/finite-packet-tensors/check')
def eth36_packet_tensors_check(req:Eth31CheckRequest):
    return _eth36_check(req.certificate,max_work=350000,timeout_s=9)

@app.get('/v1/research/eth/v36/status')
def eth36_status():
    return {'version':'3.6.0',
        'claim':'FINITE_BOOLEAN_MULTILINEAR_CAUCHY_PACKET_TENSORS_ONLY',
        'implemented':['packet-level coefficient extraction over the exact extension-jet ring',
            'Boolean idempotent subset-union multiplication',
            'independent Boolean Moebius reconstruction',
            'independent global half-edge contraction',
            'D.3 packet slot and symbol-group provenance',
            'fail-closed source-replayed certificates'],
        'not_implemented':['manuscript D.4.4 recursively shrinking packet tensors',
            'M/8 full recursive child-size theorem','subexponential runtime proof']}


# v3.8: bounded exact elimination of fixed-beta group-local child tensors.
from veritas.research.eth_child_elimination_v38 import (
    construct_elimination_reference as _eth38_build,
    verify_elimination_reference as _eth38_check)
from veritas.research.eth_child_elimination_v38.engine import SharedMeter as _Eth38SharedMeter

@app.post('/v1/research/eth/finite-child-elimination')
def eth38_child_elimination(req:Eth31ModeChildrenRequest):
    try:
        meter = _Eth38SharedMeter(180000, 8)
        meter.phase = 'api_setup'
        meter.tick()
        net=from_cnf(CNF.from_lists(req.n,req.clauses),max_degree=12)
        meter.tick()
        base=_eth29_d3(_eth30_edges(net),r=req.radix,a=req.a,max_work=150000,max_packets=256,
                       _budget=meter)
        meter.tick()
        modes=_eth31_modes(base,node=req.node,precision=req.precision,
                           extension_degree=req.extension_degree,jet_length=req.jet_length,
                           _budget=meter)
        meter.tick()
        cert=_eth38_build(net,modes,max_work=180000,timeout_s=8,max_entries=1024, _shared_meter=meter)
        verdict=_eth38_check(cert,max_work=180000,timeout_s=8,_shared_meter=meter)
        if not verdict.get('valid'):
            raise ArithmeticError(str(verdict.get('reason')))
        meter.phase = 'api_finalization'
        meter.tick()
        return {'checker':verdict,'certificate':cert,
                'budget':{'work':meter.used,'work_by_phase':dict(meter.phase_work),
                          'measure':'cooperative_charged_events_not_bit_operations'}}
    except (ValueError,TypeError,KeyError,IndexError,OverflowError,ArithmeticError,RuntimeError,TimeoutError) as exc:
        raise HTTPException(status_code=422,detail=str(exc))

@app.post('/v1/research/eth/finite-child-elimination/check')
def eth38_child_elimination_check(req:Eth31CheckRequest):
    return _eth38_check(req.certificate,max_work=180000,timeout_s=8)

@app.get('/v1/research/eth/v38/status')
def eth38_status():
    return {'version':__version__,
        'claim':'FINITE_FIXED_BETA_EXACT_JET_CHILD_ELIMINATION_ONLY',
        'implemented':['group-local packet-factor tabulation',
           'bounded exact extension-ring variable elimination',
           'disconnected component factorization',
           'bounded memoization across weighted mode tuples',
           'independent half-edge and optional v3.7 exhaustive oracle',
           'source-replayed certificates and fail-closed resource guards'],
        'not_implemented':['manuscript D.4.4 recursive regeneration at descendant levels',
           'manuscript creation-time precision propagation for all depths',
           'universal M/8 recursive wire guarantee',
           'subexponential complexity proof']}
