# VERITAS-ETH v2.5.0 — tested release report

## Source baseline

The pristine `/mnt/data/VERITAS_ETH_v2.4.0_FULL_UPGRADED.zip` was extracted
into a fresh v2.5 directory and extended without removing existing source.
No user code was overwritten in place. Package version bumped to 2.5.0.

## New mathematical modules

- `eth_packing/parameters.py` exact source parameter formulas; separate
  scaled and exact modes. Threshold `s=2**131072` at depth zero results in
  `u_0=1`, and practical `s=1000` has `u_0=0`.
- `eth_packing/labels.py` small local conditional-expectation assignment
  over per-side endpoint counts (NOT the paper's full collision objective).
- `eth_packing/packing.py` orientation-aligned finite packet arrangement.
- `eth_packing/checker.py` independent, fail-closed checking of each wire,
  symbol/slot alignment, packing count and per-symbol load conditions.
- `eth_packing/cauchy.py` exact bounded Cauchy polynomial identity.
- `eth_arithmetic/gf2.py` deterministic GF(2) irreducibility checking.
- `eth_arithmetic/extension_ring.py` exact 2-adic extension arithmetic,
  unit inverses by lifting and truncated precision.
- `eth_arithmetic/jets.py` exact truncated V-polynomial arithmetic.
- API, CLI, browser, test harness, benchmark and scoped docs.

## Validation in build container

- Full project pytest: **349 passed** (Python 3.13, Linux).
- New scripted validation: **600** independent packet-certificate checks,
  **400** extension-ring comparisons, **5** Cauchy-size checks passed.
- Inherited `validate_10000.py`: completed (10,000 small CNF instances).
- Inherited `scripts/smoke.py`: PASS.
- v2.5 benchmark uses fixed RNG seed 2500, 4 configurations, NOT
  statistically representative and not a measured solver speedup.

## Example diagnostic (not a theorem)

| Vertices | Wires | Packets | 3M/L bound met | Run seconds |
|---:|---:|---:|:---:|---:|
| 8 | 24 | 20 | No | 0.00181 |
| 16 | 48 | 33 | Yes | 0.00343 |
| 32 | 96 | 64 | Yes | 0.00652 |
| 64 | 192 | 126 | Yes | 0.01283 |

A small case fails the packet-count condition. The checker reports this
accurately. A general guarantee is not established by the new constructor.

## Formal scope and missing work

No ETH runtime theorem is reproduced. Full manuscript D.3 packing,
recursive interpolation, D.4.4 mode bound, specialized recursive child
construction and polynomial-space analysis remain unimplemented.
See `docs/ETH_V25_MATHEMATICAL_SCOPE.md` for the exact open/closed gates.
