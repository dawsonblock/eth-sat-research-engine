# VERITAS-ETH v2.3.0 — proof-carrying rational weighted model counting

## Implemented and integrated

1. `solvers/weighted_dag.py`: exact nonnegative rational weighted model
   counting with count-preserving free-variable, unit, split and component-product
   reductions, DAG memoization, and a separate verifier.
2. `solvers/conditional.py`: exact conditional Bernoulli probabilities with
   verified evidence and joint-count certificates, plus zero-evidence handling.
3. FastAPI endpoints: `/v1/certify/weighted-count-dag`,
   `/v1/certificates/check-weighted-count-dag`, `/v1/probability/conditional`.
4. CLI: `--certify-weighted-dag WEIGHTS.json`, `check-weighted-dag`, and
   `--conditional-query QUERY.cnf --weights WEIGHTS.json`.
5. Local browser interface, examples, engineering guide, benchmarks, tests,
   CI regression step and SHA-256 release manifest.

## Verification performed

- 290 inherited-plus-new automated test cases passed.
- 10,000 inherited seeded SAT and exact counting comparisons passed.
- 2,000 inherited component-DAG validations passed.
- 1,600 new independent weighted counting checks passed.
- 100 new conditional probability validations passed.
- Additional randomized pytest cases, adversarial certificate mutations,
  API tests, and command-line end-to-end tests passed.

## Precise limitations

- Bounded exact exponential worst-case computation and potentially large
  certificates. Not the manuscript D.3 collision packing / D.4.4 contraction.
- Only independent *Bernoulli* literal priors, with no general correlations
  or causal semantics. Conditioning is a literal CNF conjunction.
- The verifier is independently executable but not formal proof-assistant
  certified. Checkers run in process without OS-enforced isolation.
- Differential tests establish test coverage, not mathematical generality.

See `docs/WEIGHTED_COUNTING_V23.md` and `RELEASE_REPORT_V23.md`.
