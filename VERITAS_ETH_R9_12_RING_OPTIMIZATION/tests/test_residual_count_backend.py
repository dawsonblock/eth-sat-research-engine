from veritas.core.cnf import CNF
from veritas.research.cnf_structure import structure_aware_count
from veritas.research.residual_count_backend import residual_research_count
from veritas.solvers.reference import exhaustive_count


def test_residual_research_backend_count():
    cnf = CNF.from_lists(3, [[1, 3], [2, 3]])
    out = residual_research_count(cnf, preprocess=True)
    assert out['engine'] == 'EXACT_RESIDUAL_MEMO_SHANNON'
    assert out['count'] == '5'
    assert out['execution']['distinct_residual_states'] >= 2
    tree = out.get('tree_ledger') or {}
    assert tree.get('unique_subproblems') == out['execution']['distinct_residual_states']


def test_structure_hybrid_residual_primary_backend():
    cnf = CNF.from_lists(3, [[1, 3], [2, 3]])
    out = structure_aware_count(
        cnf,
        count_backend='residual_research',
        preprocess=False,
        timeout_s=5,
        verify_direct=True,
    )
    assert out['count'] == str(exhaustive_count(cnf))
    assert out['engine'] == 'EXACT_RESIDUAL_MEMO_SHANNON'


def test_residual_backend_on_decomposed_components():
    cnf = CNF.from_lists(4, [[1, 2], [3, 4]])
    out = structure_aware_count(
        cnf,
        count_backend='residual_research',
        preprocess=False,
        timeout_s=5,
    )
    engines = {p['engine'] for p in out['structure']['parts']}
    assert engines == {'EXACT_RESIDUAL_MEMO_SHANNON'}


def test_dual_backend_matches_and_comparison():
    cnf = CNF.from_lists(3, [[1, 3], [2, 3]])
    out = structure_aware_count(
        cnf,
        count_backend='dual',
        preprocess=True,
        timeout_s=5,
    )
    cmp = out['ledger_comparison']
    assert not cmp['skipped']
    assert cmp['counts_match'] is True
    assert cmp['residual_distinct_states'] is not None
    assert cmp.get('hybrid_work_per_residual_state') is not None
    assert cmp.get('residual_tree_unique_subproblems') is not None