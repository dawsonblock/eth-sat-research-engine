# v3.8.2 finite Hermite reconstruction

This release adds exact reconstruction of the undeformed dense L=2 Cauchy
contraction at `T=0` from jets at the three nonzero interpolation roots.
The balanced confluent Hermite plan uses exact rational recovery weights and
explicit 2-adic guard bits. The dense transform fails closed under fixed
operation and live-entry caps. The Hermite reference now supports up to 64
samples, covering the degree bound for 16 wires.

The release retains the v3.8.1 fixes to shared work accounting, oracle
resource outcomes, factor cache keys, checksum verification under
optimization, dependency metadata and certificate schema versioning.

This is a finite mathematical reference, not the manuscript's tapered
interpolation schedule or recursive dense-network contraction. No universal
child shrinkage or subexponential complexity claim is made. See
`docs/CORRECTIONS_V382.md` for derivation and limits.
