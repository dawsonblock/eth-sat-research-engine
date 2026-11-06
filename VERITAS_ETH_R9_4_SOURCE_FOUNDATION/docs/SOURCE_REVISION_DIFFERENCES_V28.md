# Mathematical source audit — v2.8

Source examined: OpenAI, *The Exponential Time Hypothesis is False* (17 Oct 2026, revised 25 Oct 2026), public `preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026/build/quantitative-contraction.tex` on GitHub, viewed October 31, 2026.

URL: https://github.com/openai/math/blob/main/preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026/build/quantitative-contraction.tex

**Source pin status: UNPINNED.** The available reference was the mutable public `main` branch. The repository commit SHA and a snapshot digest were not independently retrieved. Do not call this build an immutable manuscript reproduction or claim that its parameter choice is validated against all historical revisions.

## Material discrepancy resolved in code

- Published Appendix D, `eq:tensor-parameters`: `u_d = floor(epsilon * lambda / 2^d)`, `epsilon = 1/(128*1024)`, `lambda = ceil(log2 s)`.
- v2.5 initially implemented floor; v2.6 and v2.7 switched to **ceiling** and described floor as an error. The published source currently displays **floor**. v2.8 restores it.
- v2.8 uses `lambda // (131072 << d)` with exact integer arithmetic, and `a_d = 2 sum_(j=0..d) u_j`.
- For `s=1000`, `lambda=10` gives `u_0=0`, `a_0=0`, `L=1`. The v2.7 output `u_0=1`, `L=4` was not the published formula.
- The manuscript separately handles small `s` by direct enumeration; with normal sizes the active-call inequalities are generally unavailable. The `eligible` flag is only a numerical predicate, not a theorem certification.
- Existing v2.5/v2.6 tests assuming ceiling were updated, with new boundary cases around all floor transitions.

## Claim levels

- `FINITE_EXTENSION_RING_POLYNOMIAL_RECOVERY_ONLY`: exact identities on bounded computational instances.
- `MANUSCRIPT_PARAMETER_FORMULA_MATCHED_UNPINNED`: published symbolic formula reproduced, repository revision not frozen.
- `FULL_MANUSCRIPT_ALGORITHM`: **NOT IMPLEMENTED**.
- `SUBEXPONENTIAL_COMPLEXITY_PROVEN_FOR_THIS_SOFTWARE`: **NOT ESTABLISHED**.

Next requirement: retrieve immutable commit hash, commit-specific raw source SHA256, compare source formula, update `SOURCE_REVISION_DIFFERENCES_V28.md`, and test against that specific committed edition.
