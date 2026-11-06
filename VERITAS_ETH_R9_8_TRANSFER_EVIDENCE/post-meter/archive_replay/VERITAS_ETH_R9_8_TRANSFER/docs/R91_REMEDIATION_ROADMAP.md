# R9.1 remediation roadmap

Status of each obligation, with the precise next step.

| Obligation | Status | Next step |
|---|---|---|
| Sorted vertex order model | done (`D3PythonOrder.lean`) | — |
| Order fixture `22/16/16/12` | done, kernel-checked and cross-checked against CPython | — |
| CPython score transcription | done (`D3PythonScoreModel.lean`) | — |
| Per-comparison equality | done (`py_side_unknown`, `py_side_mismatch`) | — |
| Pair-level aggregation | done (`pyPairUnknown_eq`, `pyPairMismatch_eq`) | — |
| `wordMatches` alignment | **done** (`wordMatches_range_any`) | — |
| Score equality with `concreteD3ScoreCandidate` | **done** (`pyCandidateScore_eq`) | — |
| First-minimiser selection lemma | **open** | `labelWords` lexicographic strictness plus a fold lemma |
| Full-run correspondence | **open**, depends on the two rows above | induction over `d3PythonOrderedVertices` |
| C++ scorer equivalence | tested on a corpus | extend the corpus; a proof would need a verified compiler |
| Packet slot bijection | done (`D3PacketBijection.lean`) | — |
| Edge-to-class assignment in the address space | **open** | compose `D3ClassAccounting` with `D3PacketBijection` |
| Recursive child correctness (Stage 2B) | **blocked**, unchanged | needs universal mode support, all-node contraction, creation-time precision, termination |
| Complexity bounds (Stage 2C) | analysis only | a Lean operation-count model for `_candidate_score` |
| Theorem mode | disabled | requires all of the above |

## Policy

* No `sorry`, `admit`, or custom axioms. The proof gate rejects them.
* No theorem contract may be weakened to make a gate pass; the gate checks the
  exact axiom report of each named theorem.
* A failed stage keeps its strongest verified partial result and records the
  missing lemma here.
