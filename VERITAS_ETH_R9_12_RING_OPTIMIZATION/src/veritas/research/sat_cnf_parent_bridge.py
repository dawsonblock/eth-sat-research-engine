"""Scaffold: fixed-density CNF encode → ParentCall (tiny class only).

Uses ``source_cnf_network`` + ``describe_integer_network`` + ``ParentCall.from_described``.
Not R9.4 arbitrary density; jet fast path still requires interaction certificate.
"""
from __future__ import annotations

from dataclasses import dataclass

from veritas.core.cnf import CNF
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_recursive_contraction_v39.described_network import (
    describe_integer_network,
)
from veritas.research.parent_child_r98.model import from_described
from veritas.research.source_cnf import SourceCNFNetwork


@dataclass(frozen=True)
class ParentBridgeBounds:
    max_vars: int = 16
    max_clauses: int = 32
    max_subdivided_edges: int = 64
    max_original_edges: int = 32
    max_precision: int = 32
    extension_degree: int = 5

    def to_dict(self) -> dict:
        return {
            "max_vars": self.max_vars,
            "max_clauses": self.max_clauses,
            "max_subdivided_edges": self.max_subdivided_edges,
            "max_original_edges": self.max_original_edges,
            "max_precision": self.max_precision,
            "extension_degree": self.extension_degree,
        }


DEFAULT_PARENT_BRIDGE_BOUNDS = ParentBridgeBounds()


@dataclass(frozen=True)
class TinyFixedCnfClass:
    """Explicit CNF class for ParentCall bridge (fail closed outside)."""

    max_vars: int = 16
    max_clauses: int = 32
    max_clause_width: int = 3

    def to_dict(self) -> dict:
        return {
            "max_vars": self.max_vars,
            "max_clauses": self.max_clauses,
            "max_clause_width": self.max_clause_width,
            "schema": "VERITAS_TINY_FIXED_CNF_CLASS_V1",
        }


DEFAULT_TINY_CNF_CLASS = TinyFixedCnfClass()


def admit_tiny_fixed_cnf_class(
    cnf: CNF, spec: TinyFixedCnfClass = DEFAULT_TINY_CNF_CLASS
) -> dict | None:
    """Return refusal dict if outside class; else None."""
    if cnf.n > spec.max_vars:
        return {
            "status": "REFUSED_OUT_OF_CLASS",
            "reason": f"n={cnf.n} > max_vars={spec.max_vars}",
            "admitted_class": spec.to_dict(),
        }
    if len(cnf.clauses) > spec.max_clauses:
        return {
            "status": "REFUSED_OUT_OF_CLASS",
            "reason": f"m={len(cnf.clauses)} > max_clauses={spec.max_clauses}",
            "admitted_class": spec.to_dict(),
        }
    if not all(0 < len(c) <= spec.max_clause_width for c in cnf.clauses):
        return {
            "status": "REFUSED_OUT_OF_CLASS",
            "reason": "not 3-CNF within max_clause_width",
            "admitted_class": spec.to_dict(),
        }
    return None


def build_parent_call_from_encoded_cnf(
    cnf: CNF,
    encoded: SourceCNFNetwork,
    *,
    bounds: ParentBridgeBounds = DEFAULT_PARENT_BRIDGE_BOUNDS,
    cnf_class: TinyFixedCnfClass = DEFAULT_TINY_CNF_CLASS,
) -> dict:
    """Return ParentCall metadata or explicit refusal."""
    class_refusal = admit_tiny_fixed_cnf_class(cnf, cnf_class)
    if class_refusal:
        return {
            "schema": "VERITAS_CNF_PARENT_BRIDGE_V1",
            "status": "REFUSED",
            "reason": class_refusal["reason"],
            "admitted_class": class_refusal["admitted_class"],
            "bounds": bounds.to_dict(),
            "jet_fast_path_eligible": False,
        }
    if cnf.n > bounds.max_vars:
        return _refuse("n exceeds parent bridge cap", bounds)
    if len(cnf.clauses) > bounds.max_clauses:
        return _refuse("clause count exceeds parent bridge cap", bounds)
    net = encoded.network
    if net.edges > bounds.max_subdivided_edges:
        return _refuse("subdivided edges exceed cap", bounds)
    if encoded.original_edges > bounds.max_original_edges:
        return _refuse("original edges exceed cap", bounds)

    precision = cnf.n + 1
    if precision > bounds.max_precision:
        return _refuse("precision cap", bounds)
    degree = bounds.extension_degree
    if not 2 <= degree <= 8:
        return _refuse("invalid extension_degree", bounds)

    try:
        polynomial = first_irreducible(degree)
        described = describe_integer_network(
            net,
            creation_precision=precision,
            defining_polynomial=polynomial,
        )
        root_s = max(4, encoded.original_edges * 2)
        parent = from_described(
            described,
            root_s=root_s,
            depth=0,
            precision=precision,
        )
    except (ValueError, TypeError) as exc:
        return _refuse(str(exc), bounds)

    return {
        "schema": "VERITAS_CNF_PARENT_BRIDGE_V1",
        "status": "PARENT_CALL_BUILT",
        "edge_count": parent.edge_count,
        "original_edges": encoded.original_edges,
        "root_s": parent.root_s,
        "precision": parent.precision,
        "defining_polynomial": parent.defining_polynomial,
        "content_digest": parent.content_digest,
        "semantics": parent.semantics.value,
        "bounds": bounds.to_dict(),
        "count_preserving_reduction_proved": False,
        "jet_fast_path_eligible": False,
        "qualification": "describe_integer_network_scaffold_not_interaction_cert",
    }


def _refuse(reason: str, bounds: ParentBridgeBounds) -> dict:
    return {
        "schema": "VERITAS_CNF_PARENT_BRIDGE_V1",
        "status": "REFUSED",
        "reason": reason,
        "bounds": bounds.to_dict(),
        "jet_fast_path_eligible": False,
    }
