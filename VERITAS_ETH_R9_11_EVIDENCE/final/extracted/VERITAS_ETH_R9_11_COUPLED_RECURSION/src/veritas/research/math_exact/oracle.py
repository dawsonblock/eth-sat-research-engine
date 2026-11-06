"""Independent, explicitly bounded model counter over signed clauses."""
from itertools import product
from veritas.core.cnf import CNF


def exhaustive_count(cnf: CNF, *, max_variables: int = 20) -> int:
    if not isinstance(cnf, CNF):
        raise TypeError('CNF required')
    if type(max_variables) is not int or not 0 <= max_variables <= 24:
        raise ValueError('max_variables must be in 0..24')
    if cnf.n > max_variables:
        raise ValueError('exhaustive variable budget exceeded')
    count = 0
    for bits in product((False, True), repeat=cnf.n):
        if all(any(bits[abs(lit)-1] if lit > 0 else not bits[abs(lit)-1]
                   for lit in clause) for clause in cnf.clauses):
            count += 1
    return count
