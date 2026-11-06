# R9.8 mathematical corrections: reviewed implementation

The corrections are committed on `fix/r9.8-math-corrections` at `3a923e434f7e9d706181237fd11cfc51febddb37`.
The source binding is `02b315ad0c6698f82442a5db09cf2213460efc036c94189d3b9d228815d53e84`. The sealed R9.7 and R9.8 baselines and all
four pinned manuscript files remain unchanged. This is a development snapshot,
not a newly sealed source release.

## Corrected behavior

- Retain the corrected packet range `0 <= j < H_pad / 2^k`, where k counts
  equal coordinates. Broadened regressions cover a=1,2,3 and the actual six-edge
  layout that the original R9.8 checker rejected.
- Preserve the parent's exact defining polynomial through point modes,
  replay, child tensors and recovery. Valid alternative irreducible
  polynomials no longer fail solely because the generator chose its default.
- Bind child-to-parent adaptation to the recorded parent digest, depth,
  defining polynomial and increased precision. Reject Boolean integer metadata,
  duplicated half-edge identities and noncanonical ordering.
- State tuple coverage over the zero-reduced geometric basis. Exact zero-mode
  elimination is separate from the high-weight divisibility cutoff; neither
  permits truncating the complete retained weighted stream to meet a budget.
- Report current-node numeric preconditions separately from actual packing and
  descendant admission. Per-side load bounds are sufficient for shrinkage,
  not necessary conditions for every individually small child.
- Return `PASS_FINITE_SCALED_LEAF` when no parent-to-child transition ran.
  Edge-free networks still evaluate their inherited scalar tensors.
- Preserve the existing source resource-limit refusal in mode replay, while
  rejecting missing or null defining-polynomial metadata.

The source precision formula is unchanged. The proof notes explain canonical
creation-coordinate lifting, coefficientwise Hermite precision and the
conditional group factorization. They do not claim a universal executable proof.
See [the derivations](../VERITAS_ETH_R9_8_MATH_REVIEW/docs/R98_MATHEMATICAL_CORRECTIONS.md).

## Verification

- Full suite: **1554 passed, 2 optional pybind skips**,
  zero failures/errors. Focused corrections and resource regression: **49 passed**.
- All **11** standalone validators passed, including the 41-module Lean gate,
  R98 parent-child checks and inherited R94–R97 evidence generation/replay.
  Every required Lean axiom record passed; allowed axioms are Classical.choice,
  Quot.sound and propext. These remain conditional finite-model theorems.
- Fresh installed-wheel checks passed on Python 3.10.19; corresponding Docker
  checks passed on Python 3.12.14, with network disabled and a 1 GiB limit.
  These are targeted installed checks, not the entire suite inside Docker.
- The real two-level scaled singleton fixture recovered `7 mod 32`, with
  124,929 actual calls. Nonshrinking children are recorded as
  `FAIL_SCALED_NONSHRINKING`. The cross-group point validator covers the
  complete retained weighted stream and all 64 children per tuple.
- Alternative-ring tests cover nonscalar point values, cross modes and full
  one-level Hermite recovery. The separate two-mode test checks seven selected
  coefficient contributions; it does not claim all 66,795 tuples were summed.
- The exact rational audit checked 1,300 shifted Cauchy polynomials, 6,000
  geometric remainders and six independent confluent-Vandermonde recoveries.
  These bounded calculations corroborate the formulas; they are not proofs
  over every admissible parameter.

The first final-suite attempt exposed a resource-error precedence regression
introduced by this correction. Its failed test and original evidence remain in
`attempt_1/`; the fix passed fresh focused, full and portable checks. Final
reports use only the current source digest.

Source qualification and theorem mode remain **false**. Bit-time and peak-space
bounds remain **COMPLEXITY_NOT_ESTABLISHED**. Practical 12–16-edge finite boundary
and elimination results retain their separate qualification. Hosted CI was not run.

Machine-readable evidence: [verification.json](verification.json).
Detailed before/after cases: [counterexamples.json](counterexamples.json).
Artifact integrity uses unsigned SHA-256 hashes in `REVIEW_SHA256.json`; those
hashes do not authenticate provenance or establish mathematical correctness.
