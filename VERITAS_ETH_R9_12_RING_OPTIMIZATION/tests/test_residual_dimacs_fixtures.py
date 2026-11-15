import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'benchmarks'))

from veritas.core.cnf import CNF
from veritas.research.residual_equivalence import residual_research_metrics
from veritas.solvers.reference import exhaustive_count

def test_example_dimacs_residual_metrics_match_exhaustive():
    cnf = CNF.from_dimacs((ROOT / 'examples' / 'example.cnf').read_text(encoding='utf-8'))
    metrics = residual_research_metrics(cnf, preprocess=True, max_n=22, prefix_depth=min(3, cnf.n))
    assert not metrics['skipped']
    assert metrics['count'] == exhaustive_count(cnf)


def test_contradiction_dimacs_is_unsat():
    cnf = CNF.from_dimacs((ROOT / 'examples' / 'contradiction.cnf').read_text(encoding='utf-8'))
    metrics = residual_research_metrics(cnf, preprocess=True, max_n=22, prefix_depth=1)
    assert not metrics['skipped']
    assert metrics['count'] == 0


def test_discover_dimacs_fixture_suite():
    from residual_benchmark_cnfs import discover_dimacs_fixtures

    found = discover_dimacs_fixtures()
    assert 'dimacs_network_block_motif_4' in found
    assert 'dimacs_block_xy_z' in found


def test_fixture_network_motif_matches_generator():
    from residual_benchmark_cnfs import cnf_network_block_motif, load_dimacs

    generated = cnf_network_block_motif(4)
    loaded = load_dimacs(ROOT / 'fixtures' / 'dimacs' / 'network_block_motif_4.cnf')
    assert generated.digest() == loaded.digest()