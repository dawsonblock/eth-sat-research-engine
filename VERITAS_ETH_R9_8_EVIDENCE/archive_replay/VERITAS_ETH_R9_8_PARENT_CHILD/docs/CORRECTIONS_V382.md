# v3.8.2 finite zero-reconstruction correction

## What this adds

The v3.8.1 dense experiment evaluated one deformation at `T=4`. That value
was outside the L=2 interpolation root set and did not reconstruct the
undeformed contraction at `T=0`. v3.8.2 adds `reconstruct_zero` in
`src/veritas/research/dense_cauchy_testbed.py` to close that finite identity
gap.

For L=2, `C(T)=(T+2)(T+1)T(T-1)`, so every Cauchy entry
`W_xy(T)=C(T)/(C'(0)(T-(y-x)))` has degree at most 3. There is one affine
row factor per wire, hence the full dense contraction polynomial `F(T)` has
degree at most `3M`. The routine shifts each nonzero node by `T=t+4z`,
computes its exact Taylor coefficients modulo `2^P`, and uses the three
nonzero roots `t=-2,-1,1`.

Balanced multiplicities provide exactly `3M+1` confluent samples. A rational
Hermite linear functional recovers `F(0)`; the exact denominators determine a
sufficient guard `g`, and the routine requires `P=p+g` before dividing out
`2^g`. For `M=8`, the multiplicities are `(9,8,8)` and `g=13`. For `M=10`,
they are `(11,10,10)` and `g=17`. The L=2 shifted coefficients have odd
denominators (in fact they are integral); conversion rejects any even
denominator rather than inverting it modulo a power of two.

The reconstructed residue is checked against the original exact dense dot
product. At 8 wires, the full jet polynomial is also evaluated at two local
coordinates around each of the three roots and compared modulo `2^P` with a
separate half-edge enumeration using the independently product-defined
integer kernel. This checks six nonzero-node polynomial evaluations. The
Hermite helper now supports at most 64 samples so the degree bound through
`M=16` can be planned.

## Resource and theorem boundary

The dense jet transform is explicitly capped at 40,000,000 counted scalar
operations and 2,000,000 live jet entries by default. It fails closed before
the transform if the estimate exceeds either cap. The default seeded run
checks zero reconstruction at 8 and 10 wires; larger cases are recorded as
`BLOCKED_RESOURCE_LIMIT` with no partial value. Matrix generation, rational
plan construction, input validation, modular-reduction bit costs and peak
bytes are outside the scalar-operation ledger.

This is an exact finite Hermite identity check, **not** the manuscript's
tapered Lemma D.5 schedule. The dense input tables themselves have `2^M`
entries, and the local transformation still costs exponential time in `M`.
The largest child scope remains `M`; there is no D.4.4 geometric mode bound,
recursive child regeneration, `M/8` guarantee, or subexponential runtime
claim. The original v3.8 child engine remains limited to six wires.

Run:

```bash
python -m pip install -e '.[test]'
python -m pytest -q tests/test_hermite_ring.py tests/test_v382_dense_testbed.py
PYTHONPATH=src python scripts/validate_dense_v382.py
python scripts/verify_manifest.py
```

The validation script records deterministic table hashes, exact residues,
guard bits, work estimates and resource-blocked cases. Passing it validates
these finite identities only; it does not verify the manuscript theorem.
