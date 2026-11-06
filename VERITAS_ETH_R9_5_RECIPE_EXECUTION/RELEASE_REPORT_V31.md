# VERITAS-ETH v3.1.0 — verification report

## Upgrade

- Preserved the cumulative v3.0 code and registered `veritas-eth31`, research API and browser demo.
- Implemented exact geometric-tile extension-ring jets and 2-adic valuation checks with bounded weighted enumeration.
- Built group-local mode-indexed scalar child contractions with an independent full half-edge Cauchy oracle.
- Added replayable certificates and adversarial certificate rejection.

## Validation carried out on this release

- New v3.1 six-test module: PASS, including 28 seeded random CNFs and negative tests.
- v3.1/v3.0/v2.9/v2.7 selected cross-version run: 48 tests PASS.
- Earlier extended 80-case randomly seeded finite differential run: 80 PASS.
- Cumulative pytest run: reached 81% without reported failures, then hit an execution timeout. **Do not claim the full cumulative suite completed**. A clean full-suite pass remains required for a production-grade release.
- Archive hash verification and extracted-project smoke tests are recorded by the final packaging step.

## Mathematical boundary

The reference is exact in the stated truncated extension ring for supported small inputs. It is **not** the manuscript's asymptotically efficient D.4.4 recursive packet-tensor algorithm; it does not verify the `M_child < M/8` theorem, the complete precision recurrence, polynomial-space behavior or a subexponential runtime. D.3 theorem numeric prerequisites are often unsatisfied for finite toy instances.

## Limitations

- Restricted to up to six tensor edges, packet size L=2 or 4, modest extension-ring precisions and Taylor jet lengths.
- Mode enumeration is bounded and returns inconclusive errors on exceeding caps.
- No performance improvement claim over v3.0 or external #SAT solvers.
- The independent direct Cauchy half-edge oracle is exponential, which is acceptable for finite verification, not for large instances.
