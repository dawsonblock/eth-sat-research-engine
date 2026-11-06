"""Independent seeded validation for two v0.6 features; outputs a durable JSON report.

Run at release assembly time using PYTHONPATH=src or editable install.
"""
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from veritas.core.cnf import CNF
from veritas.solvers.reference import exhaustive_count
from veritas.solvers.count_certificates import make_count_certificate, check_count_certificate
from veritas.research.violation_polynomial import (
    eliminate_violation_polynomial, exact_violation_histogram, evaluate_polynomial)

rng = random.Random(20261029)
count_cases = 0
spectrum_cases = 0
residue_cases = 0
for _ in range(1000):
    n = rng.randint(0, 7)
    clauses = [[rng.randint(1,n)*rng.choice((-1,1)) for _ in range(rng.randint(0,3))] if n else []
               for _ in range(rng.randint(0,7))]
    cnf = CNF.from_lists(n, clauses)
    result = make_count_certificate(cnf,max_nodes=15000,timeout_s=5)
    assert result.status == 'COUNT', (result.status,result.reason)
    valid, reason, count, nodes = check_count_certificate(cnf,result.certificate)
    assert valid and count==exhaustive_count(cnf), (reason,cnf)
    count_cases+=1
for _ in range(350):
    n = rng.randint(0,5)
    clauses = [[rng.randint(1,n)*rng.choice((-1,1)) for _ in range(rng.randint(0,3))] if n else []
               for _ in range(rng.randint(0,6))]
    cnf=CNF.from_lists(n,clauses)
    coeffs, stats=eliminate_violation_polynomial(cnf)
    oracle=exact_violation_histogram(cnf)
    assert coeffs==oracle
    assert evaluate_polynomial(coeffs,1)==(1<<n)
    spectrum_cases+=1
    for precision in (1,2,3,n+1):
        residue,_=eliminate_violation_polynomial(cnf,precision_bits=precision)
        assert residue == [v%(1<<precision) for v in coeffs]
        residue_cases+=1
report={"release":"0.6.0","status":"PASS", "seed":20261029,
        "independent_count_certificate_checks":count_cases,
        "independent_violation_spectra":spectrum_cases,
        "modular_residue_cross_checks":residue_cases,
        "scope":"Small bounded random CNF, exact arithmetic, not ETH asymptotic validation"}
path=Path(__file__).resolve().parents[1]/'validation'/'validation_v06.json'
path.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
