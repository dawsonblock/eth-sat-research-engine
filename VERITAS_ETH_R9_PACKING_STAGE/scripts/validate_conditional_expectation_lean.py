#!/usr/bin/env python3
"""Compile the conditional-expectation Lean proofs and write local evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
PINNED_CONTRACTION_SHA256 = "671642d7b53154d92344e8c4be0240f18929632ebcfdf73b07c3e9939b873860"
PROOF_FILES = (
    "proofs/ConditionalExpectationAverage.lean",
    "proofs/ConcreteD3ConditionalExpectation.lean",
    "proofs/D3VarianceBound.lean",
    "proofs/D3PotentialIdentity.lean",
    "proofs/D3CollisionBridge.lean",
    "proofs/D3InitialScore.lean",
    "proofs/ConditionalExpectationSelection.lean",
    "proofs/D3SelectionBridge.lean",
    "proofs/D3CanonicalSequence.lean",
    "proofs/D3StateInvariants.lean",
    "proofs/D3ParentScoreIndependence.lean",
    "proofs/D3ChildTransition.lean",
    "proofs/D3RealizedLoads.lean",
    "proofs/D3ClassAccounting.lean",
    "proofs/D3VarianceAlgebra.lean",
    "proofs/D3SymbolPorts.lean",
    "proofs/D3PythonOrder.lean",
    "proofs/D3PythonScoreModel.lean",
    "proofs/D3SlotSplit.lean",
    "proofs/D3PacketBijection.lean",
    "proofs/D3GlobalPacketAddress.lean",
    "proofs/D3OccurrenceRank.lean",
    "proofs/D3BinaryBits.lean",
    "proofs/D3NumericSlot.lean",
    "proofs/D3FullPacketModel.lean",
    "proofs/D3PaddedConstruction.lean",
    "proofs/D3FirstMinimum.lean",
    "proofs/D3R93Contracts.lean",
    "proofs/D3ExpectedContracts.lean",
    "proofs/ConditionalChildShrink.lean",
)
PROOF_OUTPUTS = {
    "proofs/ConditionalExpectationAverage.lean": "ConditionalExpectationAverage.olean",
    "proofs/ConcreteD3ConditionalExpectation.lean": "ConcreteD3ConditionalExpectation.olean",
    "proofs/D3VarianceBound.lean": "D3VarianceBound.olean",
    "proofs/D3PotentialIdentity.lean": "D3PotentialIdentity.olean",
    "proofs/D3CollisionBridge.lean": "D3CollisionBridge.olean",
    "proofs/D3InitialScore.lean": "D3InitialScore.olean",
    "proofs/ConditionalExpectationSelection.lean": "ConditionalExpectationSelection.olean",
    "proofs/D3SelectionBridge.lean": "D3SelectionBridge.olean",
    "proofs/D3CanonicalSequence.lean": "D3CanonicalSequence.olean",
    "proofs/D3StateInvariants.lean": "D3StateInvariants.olean",
    "proofs/D3ParentScoreIndependence.lean": "D3ParentScoreIndependence.olean",
    "proofs/D3ChildTransition.lean": "D3ChildTransition.olean",
    "proofs/D3RealizedLoads.lean": "D3RealizedLoads.olean",
    "proofs/D3ClassAccounting.lean": "D3ClassAccounting.olean",
    "proofs/D3VarianceAlgebra.lean": "D3VarianceAlgebra.olean",
    "proofs/D3SymbolPorts.lean": "D3SymbolPorts.olean",
    "proofs/D3PythonOrder.lean": "D3PythonOrder.olean",
    "proofs/D3PythonScoreModel.lean": "D3PythonScoreModel.olean",
    "proofs/D3SlotSplit.lean": "D3SlotSplit.olean",
    "proofs/D3PacketBijection.lean": "D3PacketBijection.olean",
    "proofs/D3GlobalPacketAddress.lean": "D3GlobalPacketAddress.olean",
    "proofs/D3OccurrenceRank.lean": "D3OccurrenceRank.olean",
    "proofs/D3BinaryBits.lean": "D3BinaryBits.olean",
    "proofs/D3NumericSlot.lean": "D3NumericSlot.olean",
    "proofs/D3FullPacketModel.lean": "D3FullPacketModel.olean",
    "proofs/D3PaddedConstruction.lean": "D3PaddedConstruction.olean",
    "proofs/D3FirstMinimum.lean": "D3FirstMinimum.olean",
    "proofs/D3R93Contracts.lean": "D3R93Contracts.olean",
    "proofs/D3ExpectedContracts.lean": "D3ExpectedContracts.olean",
}
CENTRAL_THEOREMS_BY_FILE = {
    "proofs/ConditionalExpectationSelection.lean": (
        "sum_lower_bound_of_all_gt",
        "exists_candidate_le_of_sum_le",
        "exists_minimizing_candidate_no_worse_than_parent",
    ),
    "proofs/ConditionalChildShrink.lean": (
        "conditional_group_wire_bound",
        "conditional_sixty_four_group_load",
        "conditional_sixty_four_group_shrink",
    ),
    "proofs/ConditionalExpectationAverage.lean": (
        "countSatisfyingWords",
        "constrained_pair_average",
        "conditional_pair_term_average",
        "conditional_pair_sum_average",
        "conditional_score_average",
        "coordinate_pair_term_average",
        "coordinate_pair_sum_average",
        "coordinate_score_average",
    ),
    "proofs/ConcreteD3ConditionalExpectation.lean": (
        "concretePairCoordinate_valid",
        "concrete_d3_pair_term_average",
        "concrete_d3_pair_terms_average",
        "concrete_d3_score_average",
        "ordered_overlap_count_le_two_m_delta",
    ),
    "proofs/D3VarianceBound.lean": (
        "edgePairLabelSamples_length",
        "edgePairAgreementCount_eq",
        "edgePairScaledAgreement_count_identity",
        "edgePairScaledAgreement_eq_one_of_disjoint",
        "scaledPairSecondMoment_eq_centered_add_mul",
        "scaled_centered_pair_sum_le",
        "scaled_pair_second_moment_sub_square_le",
    ),
    "proofs/D3PotentialIdentity.lean": (
        "d3_edge_class_square_sum_eq_ordered_collision_count",
        "d3_scaled_ordered_collision_count_eq",
    ),
    "proofs/D3CollisionBridge.lean": (
        "ordered_pair_sum_decomposition",
        "d3_scaled_class_square_eq_diagonal_plus_unordered",
        "scaled_pair_second_moment_eq_diagonal_plus_unordered",
        "initial_unordered_pair_score_le",
    ),
    "proofs/D3InitialScore.lean": (
        "empty_coordinates",
        "empty_pair_parent_eq",
        "empty_concrete_score_eq_second_moment",
        "empty_concrete_score_le",
    ),
    "proofs/D3SelectionBridge.lean": (
        "concreteD3CandidateScores_sum",
        "concrete_d3_exists_nonincreasing_candidate",
    ),
    "proofs/D3CanonicalSequence.lean": (
        "d3_assign_word_valid",
        "d3_canonical_word_mem",
        "d3_canonical_word_nonincreasing",
        "d3_first_canonical_candidate_with_initial_bound",
        "d3_conditional_canonical_run",
    ),
    "proofs/D3StateInvariants.lean": (
        "d3_fresh_empty",
        "d3_fresh_assign",
        "d3_run_preserves_unlisted",
        "d3_run_preserves_valid",
        "d3_run_labels_all",
        "d3_fresh_canonical_run_monotone",
        "d3_fresh_run_initial_bound",
    ),
    "proofs/D3ParentScoreIndependence.lean": (
        "classify_unknown_independent",
        "classify_mismatch_independent",
        "fresh_pair_parent_independent",
        "fresh_parent_score_independent",
        "fresh_pair_parent_eq_raw",
        "fresh_parent_eq_raw_potential",
        "fresh_raw_potential_eq_parent",
        "d3_raw_run_initial_bound",
    ),
    "proofs/D3ChildTransition.lean": (
        "classify_assign_transition",
        "coordinate_fixed_is_sum",
        "coordinate_rejects_is_constraint",
        "concrete_coordinate_assign_transition",
        "coordinate_transition_list",
        "concrete_pair_coordinate_transitions",
        "coordinate_mismatch_preserved",
        "raw_pair_parent_independent",
        "pair_mismatch_preserved",
        "fresh_pair_candidate_eq_raw_child",
        "fresh_candidate_eq_raw_child",
        "d3_raw_canonical_run_bound",
    ),
    "proofs/D3RealizedLoads.lean": (
        "complete_classification",
        "complete_coordinate",
        "mismatch_map_false_iff",
        "complete_pair_unknown_zero",
        "complete_pair_mismatch_iff_color",
        "complete_pair_term_is_collision",
        "unordered_pair_endpoints_mem",
        "complete_raw_potential_eq_class_square",
        "canonical_run_edges_complete",
        "d3_realized_run_class_square_bound",
        "d3_unique_vertices_mem",
        "d3_unique_vertices_nodup",
        "d3_graph_vertices_nodup",
        "d3_graph_vertices_cover",
        "d3_generated_run_class_square_bound",
    ),
    "proofs/D3ClassAccounting.lean": (
        "class_loads_sum",
        "class_squares_sum",
        "valid_word_indicator_count",
        "valid_color_indicator_count",
        "canonical_run_color_indicator_count",
        "generated_class_accounting",
    ),
    "proofs/D3VarianceAlgebra.lean": (
        "d3_centered_scalar_identity",
        "d3_centered_sum_identity",
        "d3ZSum_member_le",
        "d3_centered_class_square_bound",
        "d3_generated_centered_class_bound",
        "d3_centered_bound_implies_load_bound",
        "d3_generated_class_load_bound",
        "d3_class_load_le_max",
        "d3_max_class_load_scaled_bound",
        "d3_padded_class_load_bounds",
        "d3_generated_padded_load_bound",
        "d3_generated_packet_count_bound",
    ),
    "proofs/D3SymbolPorts.lean": (
        "word_symbol_count",
        "color_symbol_count",
        "color_symbol_scaled_count",
        "d3_symbol_loads_equal_ports",
        "d3_symbol_port_bound_from_padded_classes",
        "d3_generated_symbol_port_bound",
        "d3_any_order_padded_bound",
        "d3_generated_group_half_wire_shrink",
        "d3_any_order_symbol_port_bound",
        "d3_order_audit_fixture",
    ),
    "proofs/D3PythonOrder.lean": (
        "d3_unique_nat_ids_mem",
        "d3_unique_nat_ids_nodup",
        "d3_python_sorted_ids_sorted",
        "d3_python_sorted_ids_perm",
        "d3_python_ordered_vertices_nodup",
        "d3_python_ordered_vertices_membership",
        "d3_python_ordered_vertices_cover",
        "d3_python_ordered_vertices_edge_permutation",
        "d3_python_order_audit_fixture",
        "d3_python_sorted_order_port_bound",
        "d3_python_order_padded_bound",
        "d3_python_order_packet_count",
    ),
    "proofs/D3PythonScoreModel.lean": (
        "D3PythonScore.py_side_unknown",
        "D3PythonScore.py_side_mismatch",
        "D3PythonScore.pyPairUnknown_eq",
        "D3PythonScore.pyPairMismatch_eq",
        "D3PythonScore.sumBy_pythonEdgePairs",
        "D3PythonScore.pyCoordUnknown_add_fixed",
        "D3PythonScore.fixedCount_constraints",
        "D3PythonScore.coordinate_constraint_wordMatches",
        "D3PythonScore.wordMatches_range_any",
        "D3PythonScore.pyPairMismatch_iff",
        "D3PythonScore.pyPairUnknown_eq_parent",
        "D3PythonScore.pyPairTerm_eq",
        "D3PythonScore.pyCandidateScore_eq",
    ),
    "proofs/D3SlotSplit.lean": (
        "d3_merge_split_slot",
        "d3_split_merge_slot",
        "d3_split_slot_lengths",
        "d3_offset_address_bounded",
        "d3_offset_address_injective",
        "d3_offset_address_inverse",
        "d3_symbol_pair_roundtrip",
        "d3_unequal_pair_orientation",
        "d3_merge_unique_components",
    ),
    "proofs/D3PacketBijection.lean": (
        "D3PacketBijection.decode_encode",
        "D3PacketBijection.encode_decode",
        "D3PacketBijection.encode_injective",
        "D3PacketBijection.decode_surjective",
        "D3PacketBijection.slot_packet_count",
        "D3PacketBijection.packet_count_exact",
        "D3PacketBijection.empty_class_still_padded",
        "D3PacketBijection.packet_positions_distinct",
        "D3PacketBijection.d3_edge_slot_accounting",
    ),
    "proofs/D3GlobalPacketAddress.lean": (
        "D3GlobalPacketAddress.encode_decode",
        "D3GlobalPacketAddress.decode_encode",
        "D3GlobalPacketAddress.equal_symbol_orientation_is_false",
        "D3GlobalPacketAddress.class_orientation_reconstructs",
        "D3GlobalPacketAddress.class_pattern_orientation_roundtrip",
    ),
    "proofs/D3OccurrenceRank.lean": (
        "D3OccurrenceRank.decode_prefix_rank",
        "D3OccurrenceRank.decode_encode",
        "D3OccurrenceRank.encode_spec",
        "D3OccurrenceRank.encode_succ",
        "D3OccurrenceRank.encode_decode",
        "D3OccurrenceRank.encode_injective",
        "D3OccurrenceRank.encode_exists",
        "D3OccurrenceRank.decode_in_bounds",
        "D3OccurrenceRank.prefix_rank_lt_load",
    ),
    "proofs/D3BinaryBits.lean": (
        "D3BinaryBits.bits_length",
        "D3BinaryBits.value_bits",
        "D3BinaryBits.bits_value",
        "D3BinaryBits.value_bound",
    ),
    "proofs/D3NumericSlot.lean": (
        "D3NumericSlot.merge_length",
        "D3NumericSlot.merge_exists",
        "D3NumericSlot.encode_exists",
        "D3NumericSlot.decode_encode",
        "D3NumericSlot.encode_decode",
        "D3NumericSlot.encode_bounds",
        "D3NumericSlot.decode_bounds",
    ),
    "proofs/D3FullPacketModel.lean": (
        "D3FullPacketModel.class_orientation_length",
        "D3FullPacketModel.class_pattern_length",
        "D3FullPacketModel.encodeClass_exists",
        "D3FullPacketModel.decodeClass_encodeClass",
        "D3FullPacketModel.encodeClass_bounds",
        "D3FullPacketModel.pattern_orientations_inverse",
        "D3FullPacketModel.pattern_canonical",
        "D3FullPacketModel.pattern_bounded",
        "D3FullPacketModel.encodeClass_pattern",
        "D3FullPacketModel.encodeClass_decodeClass",
        "D3FullPacketModel.decodeClass_bounds",
        "D3FullPacketModel.paddedClass_forward",
        "D3FullPacketModel.paddedClass_reverse",
        "D3FullPacketModel.encodeEdge_exists",
        "D3FullPacketModel.decodeEdge_encodeEdge",
        "D3FullPacketModel.encodeEdge_injective",
        "D3FullPacketModel.encodeEdge_decodeEdge",
        "D3FullPacketModel.decodedEdge_in_bounds",
        "D3FullPacketModel.encodeEdge_bounds",
        "D3FullPacketModel.encodeEdge_valid",
        "D3FullPacketModel.padding_has_no_edge",
    ),
    "proofs/D3PaddedConstruction.lean": (
        "D3PaddedConstruction.member_le_max",
        "D3PaddedConstruction.absent_count_zero",
        "D3PaddedConstruction.load_le_max",
        "D3PaddedConstruction.height_divisible",
        "D3PaddedConstruction.max_le_height",
        "D3PaddedConstruction.height_lt_max_add_width",
        "D3PaddedConstruction.empty_height",
        "D3PaddedConstruction.constructed_real_edge_contract",
    ),
    "proofs/D3FirstMinimum.lean": (
        "d3_canonical_word_first_minimum",
    ),
    "proofs/D3R93Contracts.lean": (
        "r93_constructed_edge_contract",
        "r93_real_edge_packet_contract",
        "r93_occupied_packet_contract",
        "r93_padded_slot_contract",
        "r93_first_minimum_contract",
    ),
    "proofs/D3ExpectedContracts.lean": (
        "r9_checked_any_order_port_contract",
        "r9_checked_generated_group_contract",
        "r9_checked_slot_roundtrip_contract",
        "r9_checked_class_offset_contract",
        "r9_checked_python_sorted_port_contract",
    ),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def proof_manifest_sha256(root: Path = ROOT) -> str:
    """Hash the exact proof-input inventory used by this validator.

    Paths use POSIX separators and UTF-8 JSON with sorted keys and compact
    separators. Missing modules are included with a null digest so an old
    report cannot survive deletion of a proof input.
    """
    entries = []
    for relative in sorted(PROOF_FILES):
        path = root / relative
        entries.append({
            "path": relative.replace("\\", "/"),
            "sha256": sha256(path) if path.is_file() and not path.is_symlink() else None,
        })
    payload = json.dumps(entries, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


ALLOWED_LEAN_AXIOMS = frozenset({"propext", "Classical.choice", "Quot.sound"})
AXIOM_REPORT = re.compile(
    r"^'([^']+)' (?:depends on axioms: \[([^\]]*)\]|(does not depend on any axioms))$"
)


def check_axiom_reports(output: str, required_names) -> dict:
    """Check exact Lean reports and reject nonstandard transitive axioms.

    The source and Lean executable remain trust inputs; stdout checking is
    not an authenticated proof of provenance or executable correspondence.
    """
    reports = {}
    malformed = []
    duplicates = []
    unexpected_axioms = set()
    for line in output.splitlines():
        match = AXIOM_REPORT.fullmatch(line)
        if match:
            name, names, _ = match.groups()
            if name in reports:
                duplicates.append(name)
            axioms = [] if names is None or not names.strip() else [
                item.strip() for item in names.split(",")]
            reports[name] = axioms
            unexpected_axioms.update(set(axioms) - ALLOWED_LEAN_AXIOMS)
        elif "depends on axioms:" in line or "does not depend on any axioms" in line:
            malformed.append(line)
    missing = sorted(set(required_names) - reports.keys())
    return {
        "passed": not (missing or malformed or duplicates or unexpected_axioms),
        "reports": reports,
        "missing": missing,
        "malformed": malformed,
        "duplicates": sorted(duplicates),
        "unexpected_axioms": sorted(unexpected_axioms),
    }


def check_lean_version(toolchain: str, output: str) -> bool:
    expected = re.fullmatch(r"leanprover/lean4:v([^\s]+)", toolchain)
    actual = re.search(r"\bLean \(version ([^,\s)]+)", output)
    return bool(expected and actual and expected.group(1) == actual.group(1))


def clear_failed_qualifications(evidence: dict, qualification_fields) -> None:
    """Never expose proof qualifications from an incomplete or failed gate."""
    if evidence.get("status") != "PASS":
        for name in qualification_fields:
            evidence[name] = False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", default="validation/r9_conditional_expectation_proof.json",
        help="evidence JSON path, relative to the repository root",
    )
    args = parser.parse_args()
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = ROOT / output_path

    lean = os.environ.get("LEAN_BIN") or shutil.which("lean")
    run_env = os.environ.copy()
    if not run_env.get("ELAN_HOME") and lean:
        resolved_lean = Path(lean).resolve()
        if len(resolved_lean.parents) > 3:
            candidate_elan_home = resolved_lean.parents[3]
            if (candidate_elan_home / "toolchains").is_dir():
                run_env["ELAN_HOME"] = str(candidate_elan_home)
    evidence = {
        "schema": "VERITAS_ETH_R9_CONDITIONAL_EXPECTATION_LEAN_EVIDENCE_V3",
        "claim": "COMPILED_D3_PAIR_VARIANCE_AND_ONE_STEP_SELECTION",
        "qualification": "FORMAL_FINITE_LEMMA_ONLY",
        "theorem_mode_enabled": False,
        "finite_pair_marginal_variance_bound_proven": False,
        "pointwise_collision_potential_identity_proven": False,
        "unordered_pair_potential_decomposition_proven": False,
        "empty_lean_score_matches_pair_marginals_proven": False,
        "canonical_lean_first_step_bound_proven": False,
        "canonical_run_monotone_under_explicit_transition_hypotheses": False,
        "lean_labeling_freshness_validity_and_completion_proven": False,
        "full_run_bound_under_score_potential_equalities": False,
        "fresh_lean_parent_score_equals_raw_potential_proven": False,
        "raw_run_bound_under_child_transition_hypothesis": False,
        "lean_child_score_transition_proven": False,
        "lean_canonical_raw_score_bound_proven": False,
        "lean_generated_run_realized_class_square_bound_proven": False,
        "lean_generated_class_accounting_proven": False,
        "lean_generated_padded_class_bound_proven": False,
        "lean_generated_symbol_port_bound_proven": False,
        "lean_generated_group_half_wire_bound_proven": False,
        "lean_any_distinct_covering_order_port_bound_proven": False,
        "lean_slot_bit_split_inverse_proven": False,
        "lean_class_offset_address_bijection_proven": False,
        "lean_single_coordinate_orientation_proven": False,
        "lean_central_contract_types_checked": False,
        "lean_python_sorted_vertex_order_model_proven": False,
        "lean_python_sorted_order_port_bound_proven": False,
        "lean_python_sorted_trace_fixture_proven": False,
        "lean_python_score_transcription_compiles": False,
        "lean_python_pair_aggregation_proven": False,
        "lean_python_word_matches_bridge_proven": False,
        "lean_python_score_equality_proven": False,
        "lean_packet_slot_bijection_proven": False,
        "lean_global_pattern_slot_bijection_proven": False,
        "lean_raw_class_to_pattern_bijection_proven": False,
        "lean_occurrence_rank_model_bijection_proven": False,
        "lean_binary_slot_model_proven": False,
        "lean_numeric_slot_model_bijection_proven": False,
        "lean_global_edge_occurrence_model_bijection_proven": False,
        "lean_padded_packet_model_bounds_proven": False,
        "lean_first_minimum_model_proven": False,
        "lean_computed_padding_model_proven": False,
        "lean_r93_contracts_checked": False,
        "lean_full_padded_offset_to_global_address_proven": False,
        "lean_python_builder_refinement_proven": False,
        "one_step_concrete_selection_proven": False,
        "global_product_space_variance_bridge_proven": False,
        "universal_packing_lemma_proven": False,
        "universal_python_refinement_proven": False,
        "manuscript_source": "paper/quantitative-contraction.tex",
        "manuscript_sha256": sha256(ROOT / "paper/quantitative-contraction.tex"),
        "lean_toolchain": (ROOT / "lean-toolchain").read_text(encoding="utf-8").strip(),
        # These hashes make the evidence invalid when proof inputs or the
        # checker implementation changes. They are integrity/freshness data,
        # not signatures and do not authenticate the Lean executable.
        "proof_manifest_sha256": proof_manifest_sha256(ROOT),
        "validator_sha256": sha256(Path(__file__).resolve()),
        # Avoid leaking machine-specific absolute paths into packaged evidence.
        "lean_binary": Path(lean).name if lean else None,
        "lean_binary_path_recorded": False,
        "results": [],
    }
    evidence["manuscript_pin_matches"] = (
        evidence["manuscript_sha256"] == PINNED_CONTRACTION_SHA256
    )
    qualification_fields = tuple(
        key for key, value in evidence.items()
        if type(value) is bool and key not in ("theorem_mode_enabled", "manuscript_pin_matches")
    )
    if not lean:
        evidence["status"] = "NOT_RUN_TOOLCHAIN_UNAVAILABLE"
        evidence["reason"] = "Lean executable not found; set LEAN_BIN or install the pinned toolchain"
    else:
        start = time.perf_counter()
        try:
            version = subprocess.run(
                [lean, "--version"], cwd=ROOT, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
                timeout=60, env=run_env,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            evidence["lean_version_output"] = str(exc)
            evidence["pinned_lean_version_matches"] = False
            evidence["allowed_lean_axioms"] = sorted(ALLOWED_LEAN_AXIOMS)
            evidence["lean_binary_authenticated"] = False
            evidence["status"] = "FAIL_TOOLCHAIN_EXECUTION"
            evidence["reason"] = "Lean executable could not be run or timed out"
            version = None
        if version is not None:
            evidence["lean_version_output"] = version.stdout.strip()
            evidence["pinned_lean_version_matches"] = (
                version.returncode == 0 and
                check_lean_version(evidence["lean_toolchain"], version.stdout)
            )
            evidence["allowed_lean_axioms"] = sorted(ALLOWED_LEAN_AXIOMS)
            evidence["lean_binary_authenticated"] = False
        valid = (version is not None and
                 evidence["pinned_lean_version_matches"] and
                 evidence["manuscript_pin_matches"])
        build_dir = Path(tempfile.mkdtemp(prefix="veritas-r9-lean-"))
        existing_lean_path = run_env.get("LEAN_PATH")
        run_env["LEAN_PATH"] = str(build_dir) + (
            os.pathsep + existing_lean_path if existing_lean_path else ""
        )
        try:
            for relative in PROOF_FILES:
                source = ROOT / relative
                if not source.is_file():
                    evidence["results"].append({
                        "file": relative, "status": "MISSING",
                    })
                    valid = False
                    continue
                command = [lean]
                output_name = PROOF_OUTPUTS.get(relative)
                if output_name:
                    command.extend([
                        "-o", str(build_dir / output_name),
                    ])
                command.append(relative)
                try:
                    result = subprocess.run(
                        command, cwd=ROOT, text=True,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        check=False, timeout=120, env=run_env,
                    )
                except (OSError, subprocess.TimeoutExpired) as exc:
                    evidence["results"].append({
                        "file": relative,
                        "status": "TOOLCHAIN_EXECUTION_FAILED",
                        "error": str(exc),
                        "return_code": None,
                    })
                    valid = False
                    continue
                entry = {
                    "file": relative,
                    "sha256": sha256(source),
                    "return_code": result.returncode,
                    "output": result.stdout.strip(),
                    "sorryAx_absent": "sorryAx" not in result.stdout,
                }
                theorem_names = CENTRAL_THEOREMS_BY_FILE.get(relative)
                if theorem_names:
                    audit = check_axiom_reports(result.stdout, theorem_names)
                    entry["axiom_audit"] = audit
                    entry["central_theorems_printed"] = {
                        name: name in audit["reports"] for name in theorem_names
                    }
                    entry["axiom_lines"] = [
                        line for line in result.stdout.splitlines()
                        if "depends on axioms:" in line
                    ]
                    entry["central_theorems_present"] = all(
                        entry["central_theorems_printed"].values()
                    )
                    entry["central_theorems_qualified"] = (
                        entry["central_theorems_present"] and audit["passed"] and
                        evidence["pinned_lean_version_matches"] and
                        evidence["manuscript_pin_matches"]
                    )
                    valid &= entry["central_theorems_qualified"]
                if relative == "proofs/D3VarianceBound.lean":
                    evidence["finite_pair_marginal_variance_bound_proven"] = (
                        result.returncode == 0 and entry["sorryAx_absent"] and
                        entry.get("central_theorems_qualified", False)
                    )
                if relative == "proofs/D3PotentialIdentity.lean":
                    evidence["pointwise_collision_potential_identity_proven"] = (
                        result.returncode == 0 and entry["sorryAx_absent"] and
                        entry.get("central_theorems_qualified", False)
                    )
                if relative == "proofs/D3CollisionBridge.lean":
                    evidence["unordered_pair_potential_decomposition_proven"] = (
                        result.returncode == 0 and entry["sorryAx_absent"] and
                        entry.get("central_theorems_qualified", False)
                    )
                if relative == "proofs/D3InitialScore.lean":
                    evidence["empty_lean_score_matches_pair_marginals_proven"] = (
                        result.returncode == 0 and entry["sorryAx_absent"] and
                        entry.get("central_theorems_qualified", False)
                    )
                if relative == "proofs/D3CanonicalSequence.lean":
                    checked = (result.returncode == 0 and entry["sorryAx_absent"] and
                               entry.get("central_theorems_qualified", False))
                    evidence["canonical_lean_first_step_bound_proven"] = checked
                    evidence["canonical_run_monotone_under_explicit_transition_hypotheses"] = checked
                if relative == "proofs/D3StateInvariants.lean":
                    checked = (result.returncode == 0 and entry["sorryAx_absent"] and
                               entry.get("central_theorems_qualified", False))
                    evidence["lean_labeling_freshness_validity_and_completion_proven"] = checked
                    evidence["full_run_bound_under_score_potential_equalities"] = checked
                if relative == "proofs/D3ParentScoreIndependence.lean":
                    checked = (result.returncode == 0 and entry["sorryAx_absent"] and
                               entry.get("central_theorems_qualified", False))
                    evidence["fresh_lean_parent_score_equals_raw_potential_proven"] = checked
                    evidence["raw_run_bound_under_child_transition_hypothesis"] = checked
                if relative == "proofs/D3ChildTransition.lean":
                    checked = (result.returncode == 0 and entry["sorryAx_absent"] and
                               entry.get("central_theorems_qualified", False))
                    evidence["lean_child_score_transition_proven"] = checked
                    evidence["lean_canonical_raw_score_bound_proven"] = checked
                if relative == "proofs/D3RealizedLoads.lean":
                    evidence["lean_generated_run_realized_class_square_bound_proven"] = (
                        result.returncode == 0 and entry["sorryAx_absent"] and
                        entry.get("central_theorems_qualified", False)
                    )
                if relative == "proofs/D3ClassAccounting.lean":
                    evidence["lean_generated_class_accounting_proven"] = (
                        result.returncode == 0 and entry["sorryAx_absent"] and
                        entry.get("central_theorems_qualified", False)
                    )
                if relative == "proofs/D3VarianceAlgebra.lean":
                    evidence["lean_generated_padded_class_bound_proven"] = (
                        result.returncode == 0 and entry["sorryAx_absent"] and
                        entry.get("central_theorems_qualified", False)
                    )
                if relative == "proofs/D3SymbolPorts.lean":
                    checked = (result.returncode == 0 and entry["sorryAx_absent"] and
                               entry.get("central_theorems_qualified", False))
                    evidence["lean_generated_symbol_port_bound_proven"] = checked
                    evidence["lean_generated_group_half_wire_bound_proven"] = checked
                    evidence["lean_any_distinct_covering_order_port_bound_proven"] = checked
                if relative == "proofs/D3PythonScoreModel.lean":
                    checked = (result.returncode == 0 and entry["sorryAx_absent"] and
                               entry.get("central_theorems_qualified", False))
                    evidence["lean_python_score_transcription_compiles"] = checked
                    evidence["lean_python_pair_aggregation_proven"] = checked
                    evidence["lean_python_word_matches_bridge_proven"] = checked
                    evidence["lean_python_score_equality_proven"] = checked
                if relative == "proofs/D3SlotSplit.lean":
                    evidence["lean_slot_bit_split_inverse_proven"] = (
                        result.returncode == 0 and entry["sorryAx_absent"] and
                        entry.get("central_theorems_qualified", False)
                    )
                    evidence["lean_class_offset_address_bijection_proven"] = evidence[
                        "lean_slot_bit_split_inverse_proven"]
                    evidence["lean_single_coordinate_orientation_proven"] = evidence[
                        "lean_slot_bit_split_inverse_proven"]
                if relative == "proofs/D3PacketBijection.lean":
                    evidence["lean_packet_slot_bijection_proven"] = (
                        result.returncode == 0 and entry["sorryAx_absent"] and
                        entry.get("central_theorems_qualified", False)
                    )
                if relative == "proofs/D3GlobalPacketAddress.lean":
                    evidence["lean_global_pattern_slot_bijection_proven"] = (
                        result.returncode == 0 and entry["sorryAx_absent"] and
                        entry.get("central_theorems_qualified", False)
                    )
                    evidence["lean_raw_class_to_pattern_bijection_proven"] = (
                        result.returncode == 0 and entry["sorryAx_absent"] and
                        entry.get("central_theorems_qualified", False)
                    )
                if relative == "proofs/D3OccurrenceRank.lean":
                    checked = (result.returncode == 0 and entry["sorryAx_absent"] and
                               entry.get("central_theorems_qualified", False))
                    evidence["lean_occurrence_rank_model_bijection_proven"] = checked
                if relative == "proofs/D3BinaryBits.lean":
                    checked = (result.returncode == 0 and entry["sorryAx_absent"] and
                               entry.get("central_theorems_qualified", False))
                    evidence["lean_binary_slot_model_proven"] = checked
                if relative == "proofs/D3NumericSlot.lean":
                    checked = (result.returncode == 0 and entry["sorryAx_absent"] and
                               entry.get("central_theorems_qualified", False))
                    evidence["lean_numeric_slot_model_bijection_proven"] = checked
                if relative == "proofs/D3FullPacketModel.lean":
                    checked = (result.returncode == 0 and entry["sorryAx_absent"] and
                               entry.get("central_theorems_qualified", False))
                    evidence["lean_global_edge_occurrence_model_bijection_proven"] = checked
                    evidence["lean_padded_packet_model_bounds_proven"] = checked
                if relative == "proofs/D3FirstMinimum.lean":
                    checked = (result.returncode == 0 and entry["sorryAx_absent"] and
                               entry.get("central_theorems_qualified", False))
                    evidence["lean_first_minimum_model_proven"] = checked
                if relative == "proofs/D3PaddedConstruction.lean":
                    checked = (result.returncode == 0 and entry["sorryAx_absent"] and
                               entry.get("central_theorems_qualified", False))
                    evidence["lean_computed_padding_model_proven"] = checked
                if relative == "proofs/D3R93Contracts.lean":
                    checked = (result.returncode == 0 and entry["sorryAx_absent"] and
                               entry.get("central_theorems_qualified", False))
                    evidence["lean_r93_contracts_checked"] = checked
                    evidence["lean_full_padded_offset_to_global_address_proven"] = checked
                if relative == "proofs/D3ExpectedContracts.lean":
                    evidence["lean_central_contract_types_checked"] = (
                        result.returncode == 0 and entry["sorryAx_absent"] and
                        entry.get("central_theorems_qualified", False)
                    )
                if relative == "proofs/D3PythonOrder.lean":
                    checked = (result.returncode == 0 and entry["sorryAx_absent"] and
                               entry.get("central_theorems_qualified", False))
                    evidence["lean_python_sorted_vertex_order_model_proven"] = checked
                    evidence["lean_python_sorted_order_port_bound_proven"] = checked
                    evidence["lean_python_sorted_trace_fixture_proven"] = checked
                if relative == "proofs/D3SelectionBridge.lean":
                    evidence["one_step_concrete_selection_proven"] = (
                        result.returncode == 0 and entry["sorryAx_absent"] and
                        entry.get("central_theorems_qualified", False)
                    )
                evidence["results"].append(entry)
                valid &= result.returncode == 0 and entry["sorryAx_absent"]
        finally:
            shutil.rmtree(build_dir, ignore_errors=True)
        evidence["elapsed_seconds"] = round(time.perf_counter() - start, 6)
        evidence["status"] = "PASS" if valid else "FAIL"

    clear_failed_qualifications(evidence, qualification_fields)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": evidence["status"],
        "output": str(output_path),
        "lean_version": evidence.get("lean_version_output"),
    }, sort_keys=True))
    return 0 if evidence["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
