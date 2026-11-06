# VERITAS-ETH v2.3.0 — validation and integration report

## Release contents

Complete cumulative v2.2.0 source, plus `weighted_dag.py` and `conditional.py`,
API/CLI/browser integration, examples, explanatory documentation, a seeded
weighted-model validation script, independent oracle tests, a benchmark and
complete release manifest. All Python tests also run without optional Z3,
Ganak or networkx dependencies unless their specific optional functions are
explicitly requested.

## Observed checks in this build

| Gate | Result |
|---|---|
| Full automated test collection | 290 passed |
| Inherited exact SAT/count regression | 10,000/10,000 |
| Inherited DAG count validation | 2,000/2,000 |
| New exact weighted-dag differential oracle | 1,600/1,600 |
| New exact conditional-probability oracle | 100/100 |
| New CLI end-to-end test | Passed |
| API weighted DAG, independent checker and conditional route | Passed |
| Existing startup smoke | Passed |

## Illustrative 26-variable structured benchmark

12 independent disjunctive clauses, two unused declared variables, normalized
weights `false=1/3`, `true=2/3`:

- Claimed exact sum: `68719476736/282429536481`
- Component-DAG nodes: 39; cache hits: 11
- Generator: ~1.24 ms; independent verification: ~0.72 ms (one local run)

These are small environment-dependent measurements, not a comparison with
competitive weighted model counters and not a demonstrated general speedup.

## Boundary of claims

The new verifier is a finite independent calculation in ordinary Python. It
is not Lean formalization. Its certificates may be exponential-size, and
verifier CPU time is not isolated from an untrusted client. The upgraded
project does not reproduce the paper's D.3/D.4.4 construction and makes no
subexponential complexity claim.
