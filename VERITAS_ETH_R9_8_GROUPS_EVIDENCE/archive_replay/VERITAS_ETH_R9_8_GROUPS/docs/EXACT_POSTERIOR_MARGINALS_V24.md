# v2.4: One-pass exact posterior marginals with replay-checked evidence

The new `solvers/marginals.py` takes an evidence CNF and a **fully specified** normalized pair of nonnegative rational weights for each declared variable. No floating-point or approximate counts are used. Given independent Bernoulli priors,

\[
Z=\sum_{x\models F}\prod_vw_{v,x_v},\qquad
P(X_v=b\mid F)=\frac{w_{v,b}}{Z}\frac{\partial Z}{\partial w_{v,b}}.
\]

A proof-carrying weighted component-DAG from v2.3 represents the exact partition function. `check_weighted_dag_certificate` first independently validates all residual CNF transformations and exact arithmetic. The v2.4 engine then uses reverse-mode accumulation on the checked DAG to calculate the derivatives of **all** variables in one pass. Products are differentiated using prefix/suffix products rather than division, so zero weights and zero-valued intermediate subgraphs remain valid. Every posterior pair must sum exactly to 1.

If `Z=0`, conditioning is undefined and status is `UNDEFINED` with `marginals=null`. If a computation budget is exceeded, status is `UNKNOWN` and no partial posterior is published. A dedicated marginal checker takes the original CNF, the original normalized prior, and a bound marginal certificate: it checks the underlying weighted DAG and recomputes every derivative and posterior. Its verdict is bound to the exact formula, prior weights, and DAG. The envelope hash is an integrity check, not a replacement for replay validation.

## CLI

```powershell
veritas-cli cnf examples/query_v23.cnf --marginals --weights examples/weights_v23.json
# Store the JSON output in output.json, then replay it:
veritas-cli check-marginals examples/query_v23.cnf examples/weights_v23.json output.json
```

## API

- `POST /v1/probability/marginals` accepts `n`, `clauses`, `weights`, `timeout_s`, `max_certificate_bytes`.
- `POST /v1/certificates/check-marginals` accepts the same with `certificate`.

The returned `marginals` object maps each one-based variable ID to `[P(false|evidence), P(true|evidence)]`, encoded as reduced canonical rational strings. Unused variables retain their original independent priors. All zero-weight or deterministic prior variables are handled without divide-by-weight shortcuts.

## Limits and non-claims

- Worst-case exponential count-DAG construction and certificate storage.
- Python exact-rational arithmetic and independent check overhead; bounded by existing DAG limits and a separate 2,000,000-operation reverse budget.
- Marginals are **probabilistic consequences of explicitly modeled independent priors**, not causal conclusions, belief in a natural-language statement, or arbitrary dependent-prior inference.
- The result does **not** implement the manuscript D.3 collision-packing theorem or D.4.4 subexponential recursion.

Validate with `python -m pytest -q`, `python scripts/validate_v24.py`, and `python benchmarks/v24_marginals.py`.
