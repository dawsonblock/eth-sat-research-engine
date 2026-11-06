# Finite cycle transfer and recovery

Commit `1b47f9dd8e5f3ff7f633458e60a2bddb73246e37`; package source SHA-256 `67959db3d49f8d59caf82ad900eb9977f39356bcd8da023a1ad14306ae3afb5a`. The source archive and a clean extraction both passed all 1,127 manifest file hashes. This checks file integrity, not the source theorem.

The separate finite transfer contract uses the singleton-packet identity: each crossing mode occurs in one affine target row, so exponents above one give an identically zero target packet tensor. Each child contraction depends only on its incident binary mode states. For a single simple cycle of crossing modes, a 2×2 transfer product sums the complete potential binary support. The original weighted tuple stream is not enumerated; this is explicitly separate from the unchanged full-tuple driver.

The independent point consumer reconstructs actual child port maps, recipes and creation precision, checks every local contraction, independently eliminates the binary mode sum, and checks the resulting point against half-edge elimination. The full-grid consumer replays every expected point certificate and independently checks coefficientwise rational recovery. Oracles accept or reject; they do not supply the production answer.

## Final-source demonstrations

- **Connected 484-edge nonconstant cycle, one point only:** 512 groups, 242 crossing modes, 1,239 actual calls, point precision 31,488. The complete weighted domain has approximately `3.78e615` tuples; potential binary support has `2^242` tuples. The exact point value and 29,539,153-byte certificate are in `validation/cycle484-nonconstant-point-final.json` and its referenced certificate. Standalone replay passed. This did not recover the parent contraction.
- **Complete recovery for a three-mode group cycle:** the original 22-edge network is a disconnected matching, with a separately audited layout whose three crossing modes form a simple cycle. Fresh tensor references are created over extension degree 7 at target precision 128. All 134 points were computed, their certificates replayed, and exact `17^22 = 1174562876521148458974062689` recovered in 9,899 actual calls. The weighted domain at each nonzero point has 605,159,936 tuples; at most eight binary patterns can contribute. The 1,780,813-byte compressed certificate represents 44,661,427 bytes of cumulative uncompressed evidence. See `validation/mode-cycle22-recovery.json` and its replay.
- **Connected 44-edge nonconstant cycle:** a point and standalone replay passed with 22 crossing modes and 131 calls. Independent 2×2 matrix tests cover scalar and extension-valued points. This is point evidence, not full-grid recovery.

## Remaining limits

The finite engine accepts singleton packets, one simple mode-interaction cycle or no crossing modes, and requires every generated child to be a four-edge leaf. Other topologies or budgets return an inconclusive result. It is not multi-level general recursion or source-qualified execution.

A full 484-edge grid was **not run**. The existing input field has degree two, while 1,453 residue-distinct points per node require degree at least 11; existing tensor coordinates cannot simply be reinterpreted. Even for a fresh suitable-field input with the same admissible layout, the current local-state contract projects **3,599,083 calls**, above the policy's absolute 2,000,000-call cap. Its minimum required raw JSON group-record shapes alone total **81,832,960 bytes**, excluding child data and recovery. That figure is only a lower bound; it does not by itself prove that the 100 MB cap is exceeded. The measured 29.5 MB single-point certificate is not a measurement of the whole grid.

Actual per-group loads pass in both examples, but the source padded packet bound fails. Source qualification, arbitrary graph performance, universal Python refinement, new transfer-specific Lean proofs, bit-operation bounds and peak-space bounds remain unestablished. Work/time limits are cooperative and the report does not claim a hard OS memory bound. Formal source recursion remains separate and is not redirected to this finite engine.

## Verification state

- External cycle-transfer validation: PASS; computational scope described above.
- Inherited validation: 12/12 PASS; all 41 existing Lean module/axiom audits pass. No new universal executable refinement is claimed.
- Portable validation: 20/20 commands PASS, plus wheel-source seal. Clean wheel Python 3.10.19 and Docker Python 3.12.14 both verified the connected 44-edge point and complete 22-edge recovery with independent replay. Docker runtime used no network, two CPUs and 1 GiB memory.
- Full post-meter pytest: **1,845 passed, two optional skips, zero failures** in one completed source-stable run. The earlier interrupted attempts remain separately recorded. See `pytest_summary.json` and `pytest.log`.
- Hosted CI and full-container pytest: NOT_RUN.

Structured details and artifact digests are in `verification.json`, `validation/transfer-validation.json`, `inherited/inherited_checks_summary.json`, `portable/portable_summary.json`, and `release_summary.json`. Previous interrupted and source-drift attempts remain separately recorded outside the source tree.
