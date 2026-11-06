# Architecture and source map

```text
Browser / CLI
    |
    | validated formal Boolean inputs
    v
Canonical CNF  <---  Propositional AST with unique-extension Tseitin encoding
    |
    +-- /v1/verify -------- bounded DPLL SAT --> direct witness checker
    +-- /v1/count --------- bounded DPLL #SAT --> exhaustive oracle (n<=12)
    |                   \-- optional external Ganak CLI
    +-- /v1/counterexample- premise AND NOT(conclusion) --> original AST checker
    +-- /v1/research/contract --> factor graph --> edge enumeration / bucket elimination
    |
    +-- local content/hash-chained SQLite audit --> /v1/audits/{hash}
```

All variables are 1-indexed in CNF. `CNF.n` includes intentionally unused variables; empty clause is always unsatisfiable; a variable that occurs in no clauses contributes a factor of two to unweighted counts. No probabilistic inference is hidden inside counting.

`src/veritas/research/algebra.py` contains exact proof-relevant identities, but **not** the global structure needed for the ETH theorem. `src/veritas/research/tensor.py` contains a standard tensor-network contraction implementation; the local source-derived Cauchy deformation **is** coded in `research/cauchy_deformation.py` for tiny networks; exception subspace, collision-packing schedule, and recursive ETH contraction remain unimplemented.

## Why unique-extension matters

For each Boolean operation, a fresh auxiliary variable is constrained to equal the operation's output with a complete *bi-implication*. For each assignment to the original named variables, every auxiliary variable is uniquely determined. The top-level formula is enforced as true. Therefore the number of satisfying assignments to all variables of the extended CNF equals the original formula count. Arbitrary equisatisfiable Tseitin encodings lacking this unique extension would not justify this conclusion.

## Failure states

- SAT model that does not satisfy encoded constraints: internal error, no result returned.
- Counterexample violating a premise: internal error, no result returned.
- External count lacking an unambiguous count line: UNKNOWN (never zero).
- Resource deadline / node cap reached: UNKNOWN (never UNSAT).
- Tensor oracle disagrees with expected count: error, no success record.
- Audit write failure: HTTP 503, never a falsely 'audited' verdict.


## v0.6.0 proof-carrying counting and polynomial research

`solvers/count_certificates.py` emits a bounded, complete Shannon decomposition with explicit unit implication, falsified-clause leaves, satisfied-leaf free-variable factors, and complete binary splits. A separate checker verifies the entire tree directly against the original CNF.

`research/violation_polynomial.py` replaces each clause indicator with polynomial value `1` for satisfied or `T` for falsified, retaining equality tensors. Standard bucket elimination over integer polynomials produces a violation histogram and its #SAT coefficient. Exact arithmetic over `Z/(2^p)` can reduce coefficient sizes but cannot supply the paper's unimplemented recursive mode reduction.
