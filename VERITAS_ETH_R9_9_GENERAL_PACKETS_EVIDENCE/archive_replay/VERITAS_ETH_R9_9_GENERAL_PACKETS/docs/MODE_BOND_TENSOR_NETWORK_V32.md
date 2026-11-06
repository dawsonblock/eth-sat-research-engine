# v3.2 — finite exact geometric-mode exponent-bond tensors

## Algorithm and correctness claim

v3.1 expressed the geometric Cauchy expansion as a sum over mode exponent
vectors. v3.2 makes the intermediate **group child tensors explicit** as sparse
maps from incident mode-exponent index tuples to truncated 2-adic extension
ring jets. Each geometric mode has a source group, a target group, and one
nonnegative integer exponent index appearing at both endpoints. The network
contracts these bonds by requiring that both endpoint indices agree and summing
over the index.

For a mode i, let its target coefficient be A_i and source linear form be
L_i. Expanding deformed row factors produces a target group coefficient of
A_i^{beta_i}. The source group contributes L_i^{beta_i}. The bond index
beta_i is a *shared exponent*, not a Boolean wire. For each group g,

    C_g(beta_incident) = sum_{own halfbit assignments}
       original_factors * [target-mode coefficient] * [source moments].

The exact truncated network value is

    sum_{all nonnegative mode exponents beta} product_g C_g(beta_incident).

The arithmetic takes place in

    ((Z / 2^p Z)[U] / (f(U))) [V] / (V^jet_length).

At each group, only incident exponent vectors whose *measured valuation
weight sum* is < p are represented. Contributions with larger target mode
weight vanish modulo 2^p. All transformations are checked against the
canonical v3.1 geometric modes and independently enumerated half-edge Cauchy
network for a small instance.

## Implementation details

* `eth_mode_bonds_v32/bonds.py` builds sparse group tensor tables, then joins
  factors on common exponent indices and marginalizes each bond.
* Joins use indexes on shared exponents rather than testing every pair.
* Exact jets are used throughout; no floating-point computation is involved.
* The certificate includes each child table and its incident mode IDs.
* An independent replay checks all child entries and full 4^M direct contraction.
* Work, table-entry and timeout limits are enforced, failing closed.
* The original SAT/#SAT APIs and all previous mathematical modules remain intact.

## Reproduce

```bash
python -m pip install -e '.[test]'
veritas-eth32 construct --n 2 --clauses-json '[[1,2]]' --output v32.json
veritas-eth32 check --certificate v32.json
python scripts/validate_v32.py
python -m pytest -q tests/test_v32_mode_bonds.py
```

New API endpoints:

* `POST /v1/research/eth/mode-bond-network`
* `POST /v1/research/eth/mode-bond-network/check`
* `GET /v1/research/eth/v32/status`

## Nonclaims / unresolved proof obligations

The child tensors here are local *mode-exponent transfer tensors*, not the
paper's packet tensors with recursively reduced wire count. In particular,
this implementation **does not establish** a child size at most M/8, a
uniform polynomial-space upper bound for the manuscript's algorithm, or
subexponential SAT runtime. Small integer parameters do not satisfy the
manuscript's astronomical asymptotic eligibility inequalities. The compressed
child representation is exact for bounded finite inputs; large instances
may still be exponential. The original manuscript source has not been pinned
to an immutable commit by this release.

Next milestone: explicitly represent mode-selected packet tensors that can
serve as recursive inputs, then prove the required degree, wire and
entry-evaluation bounds and implement the tapered precision schedule across
those recursive calls. Do not infer those bounds from these finite tests.
