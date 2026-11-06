# Tapered v4 finite experiment evidence

## Source identity

- Project: `VERITAS_ETH_v3.8.2`
- Base: `810fd783f7fc599bf74a2a0e56a2307db8a8b825` on branch `main`
- Project-only binary patch: `project-working-tree.patch`
- Patch SHA-256: `6b511a203dc81c301a29c1a17f82c21a4a73e45639d23347f32c79187db7af02`
- Manifest SHA-256: `001c382e5eb1539c94b5547a1c458f773af591347f361f1ee15c9ecaa3e37448`
- Unrelated working-tree changes were excluded from the patch.

## Verification

The current project-only patch passed **710 tests in 54.31s** locally and **710 tests in 54.53s** in a clean temporary checkout made with `git archive` from the base commit and applying the patch. The clean replay also passed the project manifest in normal and optimized Python and `compileall`. This patch includes the sparse occupied-slot source, trace replay and child-load audit, their tests, the theorem-plan updates, and refreshed manifests. Exact commands, environment versions, complete logs, patch, and hashes are included here.

The final eight-wire finite experiment returned the known forced-assignment count 1. Its generated transcript replayed successfully. It used a 120-second cooperative cap. The run recorded 3,074 retained tuples, 12,296 generated children and finite leaf contractions, 50 point evaluations, maximum recursion depth 1, and 521 maximum precision bits. Generation took 32.58 seconds with about 86.8 MB peak RSS; transcript replay took 33.28 seconds with about 138.1 MB peak RSS. Largest child size was 6 edges for an 8-edge parent; this does **not** meet the one-eighth shrink target. The run's ledger marks itself incomplete: mode/packing arithmetic, interpolation bit work, allocation, and process peak memory are not fully accounted. The deterministic transcript replay is not an independent proof. Optional direct-node oracle work is separately recorded from algorithm leaf work.

Earlier 30-second replay attempts and certificates generated before the source pin are retained as historical diagnostics. Use only the `final2` certificate and replay output as the final finite experiment.

The child-size certificate reproduces group wire counts `6, 6, 2, 2`, including inherited half-wire provenance and all packet-factor ports. It reports `D=16`, `H=2`, `delta=1`, `D*H=32 > 3M=24`, and the failed D.3 numeric preconditions. The conditional accounting lemma is: if both per-side symbol loads are at most `3M/r`, then every child has at most `6M/r` wires; for `r=64`, this is `3M/32 < M/8`. The audit checks the finite instance only and never sets theorem eligibility to true. See `eight_wire_child_size_certificate.json`, `eight_wire_child_size_run.json`, and the source script `scripts/audit_v4_child_sizes.py` in the project patch.

## P versus NP scope

The workspace did not contain the described Exact Complexity Research Engine v1.5.0 ZIP, so its implementation-specific claims were not inspected. The source includes a general proof that the stated full clause compatibility matrix has rank `2^c` over every field, while explaining why that only excludes flat rank-one compression and is not a general SAT time lower bound. No polynomial-time SAT algorithm or P=NP proof is established.

## Evidence limits

The finite tapered path is experimental. The theorem schedule, uniform packet applicability, one-eighth child shrink, complete bit/time/space recurrence, and arbitrary-input polynomial bound remain unproved/unimplemented. This evidence is engineering reproducibility for the finite code path only.
