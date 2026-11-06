# VERITAS-ETH R8.1 Archive Audit

## Artifact identity

- Archive: `VERITAS_ETH_v3.8.2_FULL_UPGRADED.zip`
- SHA-256: `0e4a06fc7f76a3e6d77be06a8cdf914aab3e32f5397bc9a91475eb766c24f1fd`
- ZIP entries: 543
- Release manifest: 542 file hashes matched; no unlisted files
- Extraction: completed after checking for duplicate paths and path traversal

## Executed validation

The archive was extracted to a fresh temporary directory and its own code was
used for all checks below.

```text
PYTHONPATH=src python -m pytest -o addopts= -q
1072 passed in 85.24s
```

The full suite includes injected duplicate, same-count substitution, reverse
ordering, invalid tuple, omitted tuple, shared generator/precount corruption,
checker-budget exhaustion, direct point-oracle corruption, and legacy V1
transcript replay cases. Each injected invalid stream returns no partial count
or certificate.

## Eight-wire point check

The eight-variable forced-assignment fixture was reconstructed from the
extracted archive and checked at one nonzero interpolation point using the
complete finite child expansion and the direct half-edge oracle:

- Node: `-1`
- Precision: 521 bits
- Extension degree: 5
- Point: `(1, 0, 0, 0, 0)`
- Modes: 6
- Structural tuples: 64
- Child expansion: `169600000000`
- Direct half-edge contraction: `169600000000`
- Equality: passed
- Child-expansion work units: 36,844
- Direct-oracle work units: 198,144
- Elapsed time: 1.103 seconds

This is a single finite point check. It does not qualify the complete
interpolation or theorem recursion.

## Source-level findings and remaining R8.2 work

- The tuple verifier establishes completeness for the structural domain
  defined by the supplied mode records. It does not independently enumerate
  the source mode records.
- `check_point_modes` reconstructs every finite Cauchy matrix entry from the
  supplied local and mode terms and compares it with the shifted-polynomial
  reference. It then canonical-replays `make_point_modes`; that replay uses
  the production generator, so it is not a second mode enumerator.
- Listed mode coefficients are checked against their declared valuation
  weights. The archive does not provide a separate per-discarded-term
  coefficient audit for all pruning paths.
- V1 replay is returned with `legacy_v1_replay: true` and
  `independent_proof: false`; it is not relabeled as a V2 certificate.
- V2 transcript events include mode-certificate hashes and packing parameters.
  The source revision is a hard-coded identifier rather than a hash of the
  audited source archive, and default point-policy fields are omitted for
  compatibility. Content-addressed source and fully explicit policy binding
  remain transcript hardening items.
- The theorem execution path remains disabled. These finite checks establish
  neither universal child-contraction correctness nor the paper's complexity
  bound.

## Reproduction

From an extracted archive directory:

```sh
python scripts/verify_manifest.py
PYTHONPATH=src python -m pytest -o addopts= -q
```

The selected eight-wire point check used the exported finite APIs
`make_source_tapered_plan`, `construct_implicit_packing`,
`implicit_sparse_mode_source`, `make_point_modes`, and
`contract_point_child_expansion`, with explicit limits of 8 parent wires,
100,000 tuples, 2,000,000 work units, and 30 seconds.
