# v2.3.0: independently checked rational weighted model counting

## Exact semantics

Given CNF `F` on declared variables 1..n, the result is:

`WMC(F) = SUM_{x satisfies F} PRODUCT_{i=1}^n w_i(x_i)`.

Weights are nonnegative exact rationals, supplied as a JSON map of **variable ID** to
`[weight_when_false, weight_when_true]`. Omitted variables are assigned `[1,1]`
for unweighted compatibility. A normalized probability model must explicitly
specify a pair summing to **1 for every declared variable**. Weight components
are canonical decimal integers or positive-denominator fractions, each
numerator and denominator at most 1,000,000.

The generator and independent checker use Python's `fractions.Fraction`, never
floating point. Unsatisfied branches carry weight zero. A satisfied residual
formula multiplies `(w_false + w_true)` across all remaining variables.
Branches on a variable sum weighted child counts. Unit propagation multiplies
by the fixed literal's weight. Independent components multiply; free variables
contribute their weight sum. This preserves declared but unused variables.

## Exact conditional probabilities

`P(Q | E) = WMC(E AND Q) / WMC(E)` under independent normalized Bernoulli
priors for all original variables. The numerator and denominator each have
separate complete DAG proof certificates. If `WMC(E)=0`, the result is
`UNDEFINED`, not zero; resource exhaustion produces `UNKNOWN`. This is a
logical probabilistic model, **not causal inference**, learning or a general
probabilistic programming system.

## Proof verification and limitations

The certificate contains canonical fraction values, a hash of the source CNF,
a canonical digest of all weights (including defaults), postorder DAG edges,
and typed reduction nodes. The checker reconstructs every residual formula
from the original CNF and independently recomputes every rational result. It
rejects mismatched weight/formula digests, malformed fractions, cycles,
illegal node sharing, forged counts, and unreachable nodes. Generator and
checker share the deterministic logical branching specification, but not the
claimed node values. Both must be included in the trusted codebase; a checked
proof does not replace formal verification of the checker itself.

The algorithm remains **exponential worst-case**, and its certificate can be
exponential in the problem size. Limits include <=128 variables, <=80,000
proof nodes, <=8 MB certificate, 30-second maximum per counting request,
8,192-bit intermediate rational limits, and stricter configurable limits.
The API's default maximum certificate size is 1 MB. A timeout or exceeded
resource limit fails closed to `UNKNOWN` and never reports a partial count as
verified. None of this implements the paper's D.3 packing proof or D.4.4
subexponential weighted-mode contraction.

## API examples

`POST /v1/certify/weighted-count-dag`

```json
{
  "n": 2,
  "clauses": [[1, 2]],
  "weights": {"1": ["1/2", "1/2"], "2": ["1/3", "2/3"]}
}
```

`POST /v1/certificates/check-weighted-count-dag`: send the same CNF and
weights, plus the returned `certificate` object.

`POST /v1/probability/conditional`:

```json
{
  "n": 2,
  "clauses": [[1, 2]],
  "query_clauses": [[1]],
  "weights": {"1": ["1/2", "1/2"], "2": ["1/2", "1/2"]}
}
```

Expected conditional probability is `2/3`, because exactly two of the three
satisfying assignments have variable 1 true.

## Command line

```sh
veritas-cli cnf examples/example.cnf --certify-weighted-dag examples/weights_v23.json
veritas-cli check-weighted-dag examples/example.cnf examples/weights_v23.json weighted_proof.json
veritas-cli cnf examples/example.cnf --conditional-query examples/query_v23.cnf --weights examples/weights_v23.json
```

The check command exits with status 2 for rejected proofs. API outputs may
contain large proof trees. Use resource limits and private/local deployment.

## Validation

```sh
python -m pytest -q
python scripts/validate_v23.py
python benchmarks/v23_weighted_dag.py
python scripts/verify_manifest.py
```

Independent brute-force oracles compare rational results on seeded random CNFs;
negative tests tamper with proof nodes, weights and formula digests. These
finite tests are evidence of local correctness, not proof of the ETH theorem.
