# ETH-SAT v0.32 Cauchy deformation reference

This isolated Python 3.9+ standard-library reference implements and checks
the local Cauchy deformation, one-wire mode expansion, and tapered Hermite
recovery described in OpenAI's October 25, 2026 ETH manuscript. It constructs
each entry of

```text
W_xy(T) = C(T) / (C'(0) * (T - (y-x)))
C(T) = product_{t=-L}^{L-1} (T-t),   0 <= x,y < L
```

by exact polynomial division over `Fraction`; it never evaluates the apparent
rational expression at its removable poles. It verifies `W(0)=I`, the
weighted-shift structure at every integer grid node, and that local
coordinates `W(t+2^(a+1)z)` have only odd coefficient denominators when
`L=2^a`. It checks 7,440 small crossing-entry geometric expansions modulo
powers of two and 16 two-group mode factorizations against direct deformed
contractions. The companion `tapered_hermite.py` applies node-dependent
Taylor orders and precisions, then reconstructs `F(0)` from exact modular
jets. Its differential checks cover 25 seeded polynomial cases through
packet size 16 and all 81 integer scalar polynomials with degree at most
three. The package also brute-forces tiny two-sided tensor tables to verify
`F(0)` equals the original diagonal contraction.

Run:

```console
python ETH_SAT_v032_cauchy_reference.py --self-test
python -m unittest discover -s tests -v
```

The exhaustive tensor reference is capped at packet size 8. The individual
mode check handles one crossing entry, and the two-group factorization test
uses a tiny fixed packet; neither implements general network packing. The
Hermite code uses rational interpolation multipliers acting coordinatewise
on modular integer vectors. It does not implement the full coefficient
algebra, general polynomial evaluation/interpolation at all residue-field
points, recursive child networks, the global mode-count proof, or total
bit/time/space accounting. Consequently this package does not validate the
complete manuscript algorithm or a subexponential SAT solver. The v0.32
source was not present in the workspace, so this remains a separate
reference package rather than an integration into that build.
