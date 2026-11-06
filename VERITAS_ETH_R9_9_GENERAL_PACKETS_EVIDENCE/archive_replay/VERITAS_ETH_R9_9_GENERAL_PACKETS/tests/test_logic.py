import itertools
import pytest
from veritas.core.logic import parse, encode, entailment_query
from veritas.solvers.reference import solve, exhaustive_count


@pytest.mark.parametrize('expression',["A -> B", "(A OR B) & !B", "!A & (B | !C)", "TRUE", "FALSE", "A -> B -> C", "A & A", "A | !A", "!!A", "(A -> B) -> (!B -> !A)"])
def test_equivalent_count(expression):
    expr = parse(expression)
    cnf, mapping = encode(expr)
    brute = sum(expr.eval(dict(zip(sorted(mapping), bits))) for bits in itertools.product([False, True], repeat=len(mapping)))
    assert solve(cnf, count=True).count == brute


def test_entailment_counterexample():
    cnf, mapping, premises, target = entailment_query(["A -> B", "A"], "B")
    assert solve(cnf).status == 'UNSAT'
    cnf, mapping, premises, target = entailment_query(["A -> B"], "B")
    res = solve(cnf)
    assert res.status == 'SAT'
    example = {name: res.model[idx] for name, idx in mapping.items()}
    assert all(p.eval(example) for p in premises) and not target.eval(example)

@pytest.mark.parametrize('source',["A = B", "A && B", "A B", "(A", "A)", "", "A OR "])
def test_parser_rejects_invalid(source):
    with pytest.raises(ValueError): parse(source)
