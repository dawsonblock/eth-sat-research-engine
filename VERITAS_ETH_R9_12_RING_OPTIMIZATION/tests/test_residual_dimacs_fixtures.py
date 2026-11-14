from pathlib import Path

from veritas.core.cnf import CNF
from veritas.research.residual_equivalence import residual_research_metrics
from veritas.solvers.reference import exhaustive_count

ROOT = Path(__file__).resolve().parents[1]


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