# v2.8 — Exact extension-ring Taylor / Cauchy reference

## Coefficient ring

We implement `R_p = (Z/2^pZ)[U]/(f(U))`, with monic `f` irreducible modulo 2, using the preexisting v2.7 `ExtensionRing`. This is not a field for `p > 1`. An element is invertible exactly when its reduction in `GF(2^e)` is nonzero. `residue_points.py` chooses canonical coefficient-bit representatives of distinct field residues, checks each value, and prohibits duplicate residue points.

## Polynomial interpolation

A polynomial `P(z)` of degree < `n` can be reconstructed from `n` samples at pairwise distinct residue classes because every Vandermonde denominator is a *unit* in `R_p`. `extension_lagrange.py` uses Newton divided differences and converts the Newton basis back to monomial coefficients; it independently replays every sample. Inputs are constrained to <=256 sample points and `n <= 2^e`.

This is an exact, **full-degree small-reference** interpolation implementation. It is not the manuscript's tapered finite-ring Hermite reconstruction, which needs a deeper precision schedule and separate proof.

## Cauchy coefficient calculation

For packet size `L=2^a`, the manuscript kernel is

`W_xy(T) = C(T) / (C'(0) (T-(y-x)))`, `C(T)=product_{t=-L}^{L-1}(T-t)`.

The v2.8 implementation obtains the deleted-factor polynomial `C(T)/(T-(y-x))` exactly in `Q[T]`; shifts it to `T=t+2^(a+1) z`; and reduces to `R_p[z]` **only after exact cancellation of rational denominators**. If any resulting rational coefficient has an even denominator, it fails closed. It never inverts a power of two in the coefficient ring.

For every supported matrix entry, `verify_cauchy_interpolation` evaluates the shifted coefficients at `2L` distinct residue classes and reconstructs them by independent Newton interpolation. That verifies a local algebraic component, not a full network contraction.

## Creation-time representatives

`CreationEntry` stores the *canonical* coordinates of a tensor entry modulo its creation precision and defining irreducible polynomial. A descendant call at greater precision reuses the same coordinates. The operation is not a ring homomorphism: lifting `(3+3 mod 4)=2` to mod 32 yields 2 while lifting `3` and `3` before addition yields 6. The distinction is tested.

## Examples

```bash
python -m pip install -e '.[test]'
veritas-eth28 parameters --s 1000
veritas-eth28 cauchy --packet-size 2 --node 1 --precision 8 --extension-degree 4
veritas-eth28 cauchy --packet-size 4 --node -1 --precision 12 --extension-degree 4
python -m pytest -q tests/manuscript_invariants/test_eth28_interpolation.py
```

API: `POST /v1/research/eth/extension-cauchy`, `GET /v1/research/eth/v28/status`.

## What remains unresolved

- Neither an immutable manuscript commit pin nor Lean correspondence proof is supplied.
- Tapered Hermite schedule with 2-adic guard precision and general `A_{p,ell}` arithmetic.
- Full D.4.4 weighted mode expansion *over the extension ring*, not just integer mode samples.
- Real implicit recursive child tensors and associated size/entry-cost invariants.
- End-to-end subexponential algorithm and its proof of runtime / space.

These are research milestones; passing finite unit tests cannot establish the manuscript's asymptotic theorem.
