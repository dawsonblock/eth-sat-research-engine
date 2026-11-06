# v2.2: exact component-DAG #SAT certificates

## Scope

`src/veritas/solvers/count_dag.py` provides a count-preserving **reference** #SAT
solver with a reusable directed acyclic graph (DAG) certificate, a checker,
explicit resource caps, and no probabilistic arithmetic. It improves the
old `count_certificates.py` proof *representation* for formulas with
components, repeated residual states, or irrelevant variables. Neither
algorithm has a subexponential worst-case runtime guarantee. This feature
does **not** implement the manuscript's D.3 or D.4.4 construction.

## Exact reductions

The certificate is a directed acyclic graph of residual Boolean formulas:

1. **Normalize:** discard tautological clauses and duplicate clauses/literals.
   This preserves the set of satisfying assignments.
2. **Conflict:** a falsified/empty clause gives count zero.
3. **Satisfied:** no active clauses gives `2**len(scope)` assignments.
4. **Free variables:** each scoped variable absent from all remaining clauses
   doubles the count. A single `free` node records the multiplicative factor.
5. **Unit:** for a forced literal `L`, only the branch assigning `L=true`
   can satisfy the formula. Its count is exactly the child's count.
6. **Product:** if the residual clause-variable hypergraph splits into
   components on disjoint variable sets, multiply their independent counts.
7. **Split:** for a selected variable `v`, compute the exact sum of its
   `v=false` and `v=true` residual counts.
8. **Memoize:** reuse *exactly equal* residual states; this does not merge
   states with merely equivalent but differently named variables.

The original declared-variable count is preserved, including unused
variables, tautologies, contradictions and empty-clause cases. Integer
arithmetic is exact. The verifier rebuilds each child state from the original
CNF, checks the corresponding reduction, and recomputes the count bottom-up.
Nodes point exclusively to earlier indices; unreachable or malformed nodes
are rejected. The checker shares the local canonicalization and reduction
kernel with the generator, so this is **a separately executed verifier but
not an independently formalized proof of the Python kernel itself**.
For small instances, a separate exhaustive solver supplies differential
corroboration.

## API and CLI

```bash
python -m pip install -e '.[test]'
veritas-cli cnf examples/example.cnf --certify-count-dag
veritas-cli check-count-dag examples/example.cnf exported-certificate.json
python scripts/validate_v22.py
python benchmarks/v22_count_dag.py
```

API `POST /v1/certify/count-dag` takes `{n,clauses,timeout_s,max_nodes,
max_certificate_bytes}` and returns a certificate and verified count or
`UNKNOWN` with no proof. API `POST /v1/certificates/check-count-dag` takes
`{n,clauses,certificate}` and returns `VALID` or `REJECTED`.

The browser offers *Proof-checked component DAG #SAT (v2.2)*. All previous
versions and endpoints remain in the archive.

## Security/limits

- Source CNF and all declared variables are hashed into the certificate.
- The verifier strictly validates the format, root, child order, rule shape,
  node counts, canonical integer encodings, resource limits, and reachability.
- Request timeouts/node or byte budgets result in `UNKNOWN`, never a partial
  count passed off as complete.
- The system is local-first. Do not expose it on untrusted networks without
  authentication, rate limits, isolation and separate process-level limits.
- Generation includes a wall-clock deadline; verification has node/byte
  caps but **no separate hard OS-level CPU-time or memory limit**. Use a
  restricted subprocess for adversarial proof uploads.

## Benchmark caveat

See `validation/benchmark_v22.json`. On 12 independent two-variable OR clauses
with two unused variables, the new certificate used 39 DAG nodes compared with
12,286 Shannon-tree nodes. Counts were identical (2,125,764). The improvement
comes from exact component factorization and repeated-state caching. Some
small or tightly connected formulas show little or no speedup, and the
algorithm remains exponential in the worst case.
