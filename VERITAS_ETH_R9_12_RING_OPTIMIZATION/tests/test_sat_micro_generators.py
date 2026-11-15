"""Seeded micro generators and branch-order probe (benchmark tier)."""
from veritas.research.sat_micro_benchmark import run_micro_benchmark_suite
from veritas.research.sat_micro_generators import (
    adversarial_random_3cnf,
    coupled_chain_3cnf,
    micro_generator_suite,
)
from veritas.research.sat_phase_c_preprocess import apply_phase_c_preprocess
from veritas.research.sat_preprocess_options import PreprocessOptions
from veritas.research.sat_residual_equivalence import (
    count_by_residual_equivalence,
    probe_branch_orders_benchmark,
)
from veritas.solvers.reference import exhaustive_count


def test_micro_generator_suite_countable_in_ci():
    assert len(micro_generator_suite()) >= 5
    name, cnf = coupled_chain_3cnf(5, 0)
    rep = count_by_residual_equivalence(cnf)
    assert rep["agreement"] is True
    assert name.startswith("coupled_")


def test_adversarial_generator_agrees_with_exhaustive():
    _name, cnf = adversarial_random_3cnf(5, 1, m=10)
    rep = count_by_residual_equivalence(cnf)
    assert rep["agreement"] is True
    assert rep["distinct_residual_classes"] is not None


def test_branch_order_probe_benchmark_only():
    _name, cnf = coupled_chain_3cnf(5, 1)
    probe = probe_branch_orders_benchmark(cnf)
    assert probe["schema"] == "VERITAS_RESIDUAL_BRANCH_ORDER_PROBE_V1"
    assert len(probe["probes"]) == 3
    assert probe["best_compression_ratio_branches_over_classes"] is not None


def test_component_safe_pure_literals_preserve_count_disjoint():
    from veritas.core.cnf import CNF

    cnf = CNF.from_lists(4, [[1, 2], [3, -4]])
    opts = PreprocessOptions(enable_component_safe_pure_literals=True)
    reduced, detail, _ = apply_phase_c_preprocess(cnf, w_old=16, options=opts)
    assert exhaustive_count(cnf) == exhaustive_count(reduced)
    assert detail["pure_literal_eliminations"] == 0


def test_component_unit_pure_literal_is_count_safe():
    from veritas.core.cnf import CNF

    cnf = CNF.from_lists(3, [[1], [1, 2], [-2, 3]])
    opts = PreprocessOptions(
        enable_component_safe_pure_literals=True,
        enable_unit_propagation=False,
    )
    reduced, detail, _ = apply_phase_c_preprocess(cnf, w_old=8, options=opts)
    assert exhaustive_count(cnf) == exhaustive_count(reduced)


def test_micro_suite_includes_generator_families():
    report = run_micro_benchmark_suite(
        include_branch_order_probe=True, include_generator_cases=True
    )
    families = {c.get("family") for c in report["cases"]}
    assert "coupled" in families
    assert "adversarial" in families