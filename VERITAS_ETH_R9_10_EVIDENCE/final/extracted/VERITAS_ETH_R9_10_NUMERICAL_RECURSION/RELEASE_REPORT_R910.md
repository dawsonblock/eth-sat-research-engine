# R9.10 — Certified finite two-level numerical execution, partial

Baseline: R9.9 commit `8a10b85`. Development branch:
`r9.10-certified-two-level`, in a separate checkout preserving R9.9.
Implementation source SHA-256:
`b27dc09a233e843d933e329d84df92f3bb94284f7767efff68782a93666e22da`.
The inherited Python distribution version remains `3.8.2.post98`; the R9.10
research revision is identified by its branch, source digest and archive manifest,
not by that legacy package version. Installed checks force-reinstall the built
wheel and verify the imported source digest.

## Completed numerical calculations

| Measurement | Minimal 235-edge fixture | Inherited 242-edge fixture |
|---|---:|---:|
| Largest wires by level | 235 → 22 → 2 | 242 → 22 → 2 |
| Exact answer | 31 × 2^234 | 17 × 2^241 |
| Active calls: root / child | 1 / 18 | 1 / 18 |
| Actual computations | 151 | 149 |
| Exact cache hits | 10,346 | 10,348 |
| Evaluated points, all levels | 140 | 140 |
| Retained tuple contributions | 164 | 164 |
| Checked child transitions | 10,496 | 10,496 |
| Producer policy work units | 10,772,960 | 10,162,978 |
| Producer elapsed seconds | 139.17 | 110.39 |
| Independent replay seconds | 60.11 | 49.08 |
| Process peak RSS bytes | 35,405,824 | 34,275,328 |

These are completed arithmetic runs, not topology-only projections. Both roots
and some depth-one calls have positive deformation degree. Each child satisfies
strict decrease and `64*M_child <= 6*M_parent`. Independent replay reconstructs
each child using separate construction/evaluation code, checks all required
support, recomputes leaf values, products, point sums and Hermite recovery, and
reconciles deterministic call/point/tuple/transition/cache counts.

The separate reference enumerates the two assignments per independent matching
edge. It reads the input tables and confirms the full integer products, both
smaller than their root moduli. No oracle value is substituted into the executor.
The retained contributions in these two fixtures are nonzero. Zero results and
zero children are exercised by a separate 22-edge run and small exhaustive tests.

The original 22-edge baseline is also rerun through the unchanged R9.9 executor:
134 points, 135 actual computations, 8,576 child transitions, and independent
replay. Its reference is 31^22.

## Why the previously refused calculation now completes

The creation-bound constant-row certificate proves degree three for both roots.
The new executor obtains all required Taylor coefficients using four residue
points at each of the two nodes and an exact zero tail. It retains the original
q=3M multiplicities, p+64M precision and `eq:tensor-hermite-origin` functional.
Its exact binomial prefix computation avoids constructing weights that multiply
certified zeros. The 242 root therefore uses eight points instead of 1,454.

At the same 1,000,000-work policy cap, a fresh legacy probe refuses at its
33,865,497-unit conservative plan charge, before any point evaluation. The new
probe reaches depth two, 23 actual computations and seven completed descendant
points before refusing at 1,001,715 charged units. Both probes return no result.
The legacy charge is an admission allowance, not measured bit operations or
hardware exhaustion. The completed run above uses a larger explicit policy cap.

## Validation

- 24 focused tests passed, including small exhaustive parent contractions,
  cancellation/boundary cases, original-functional comparisons, independent
  consumer isolation, dependency tampering and resource refusals.
- All four pinned manuscript LaTeX files were freshly compared with upstream
  commit `4eaee87548250b2682affda7d05d947c05554bae`: byte-for-byte matches.
- C++ Release build and self-test passed.
- Installed Python 3.10 wheel independently replayed the complete 235-edge evidence
  with the same source binding and reference result.
- All 13 inherited validation commands passed, including the 41-module
  Lean 4.35.0/axiom gate. These are existing model proofs, not new refinement proofs.
- All 31 inherited wheel/Docker commands passed. Three additional installed
  replays passed: the 235-edge certificate on Python 3.10, and both the 235- and
  242-edge certificates in network-disabled, 1 GB Docker containers.
- Full pytest: **1957 passed, 2 skipped**, zero failures/errors.
  Results are bound to the same frozen implementation source.

## Boundaries and remaining obligations

The finite schedule is a=u=1 and ell=1. Its actual group shrinkage is checked;
it does not satisfy all manuscript-active packing/schedule premises. This is
not a source-qualified implementation of the general preprint algorithm.

Preflight predicts root grid sizes and independently projects descendant
topologies. Runtime certificates determine descendant degrees. Per-call point
predictions match actual evaluations, and exclusive stage work charges sum to
the total. A proved total recursive resource bound remains absent.

**Exact bit-operation accounting is not implemented.** Process RSS is measured,
including Python overhead and imports, but is not a hard limit or polynomial-space
proof. The checker verifies numerical and structural counts; producer stage
charges receive an internal sum check, not independent bit-cost reconstruction.
The complete R9.10 resource contract consequently remains partial.

General valuation tapering with higher-valuation nodes, arbitrary ell, connected
multi-slot/exponent-two two-level acceptance, general CNF/density integration,
resumable numerical checkpoints, solver comparisons, formal executable refinement,
and the asymptotic time/space proofs remain open. The inherited Lean models do
not prove the new Python code. Source qualification and theorem mode stay disabled.

See [mathematical details and reproduction](docs/R910_NUMERICAL_RECURSION.md).
Frozen-source evidence is in `../VERITAS_ETH_R9_10_EVIDENCE/final/`; development
probes are excluded from these release measurements.
