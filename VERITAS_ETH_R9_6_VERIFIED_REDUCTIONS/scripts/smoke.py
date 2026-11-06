"""Pure Python smoke check; optionally installed editable package."""
from veritas.core.cnf import CNF
from veritas.solvers.reference import solve, exhaustive_count
from veritas.research.tensor import from_cnf, eliminate
from veritas.core.logic import entailment_query
from veritas.solvers.certificates import make_unsat_certificate, check_unsat_certificate
from veritas.solvers.projected import projected_count
from veritas.solvers.count_certificates import make_count_certificate, check_count_certificate
from veritas.research.violation_polynomial import eliminate_violation_polynomial, recover_zero_from_positive_nodes, evaluate_polynomial
from veritas.research.wire_deformation import deform_polynomial, check_deformation_invariants

if __name__ == '__main__':
    cnf = CNF.from_lists(3,[[1,2],[-1,3]])
    assert solve(cnf, count=True).count == exhaustive_count(cnf) == eliminate(from_cnf(cnf)) == 4
    e, *_ = entailment_query(['A -> B','A'], 'B')
    assert solve(e).status == 'UNSAT'
    certificate = make_unsat_certificate(e)
    assert certificate.status == 'UNSAT' and check_unsat_certificate(e,certificate.certificate)[0]
    assert projected_count(cnf,[1,3]).count == 3
    counted = make_count_certificate(cnf)
    assert counted.status == 'COUNT' and check_count_certificate(cnf,counted.certificate)[2] == 4
    coeffs, _ = eliminate_violation_polynomial(cnf)
    assert coeffs[0] == 4 and sum(coeffs) == 8
    assert recover_zero_from_positive_nodes([evaluate_polynomial(coeffs,j) for j in range(1,len(coeffs)+1)]) == 4
    deformed, _ = deform_polynomial(from_cnf(cnf))
    assert deformed[0] == 4 and check_deformation_invariants(from_cnf(cnf),deformed)['rank_one_nodes_checked']
    print('PASS: split-wire deformation, reference #SAT, exhaustive oracle, tensor baseline, entailment, checked UNSAT/count certificates, projected counting, polynomial tensor contraction')
