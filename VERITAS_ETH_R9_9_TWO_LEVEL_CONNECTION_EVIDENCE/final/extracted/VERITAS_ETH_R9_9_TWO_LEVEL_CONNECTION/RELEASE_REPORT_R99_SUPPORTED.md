# R9.9 finite supported packet recursion

This release closes two bounded execution gaps: full recovery of a parent with
crossing packet modes and actual two-level shrinking recursion with nonconstant
tensors. It remains `FINITE_SCALED_EXPERIMENT`. Source theorem qualification,
universal executable refinement and complexity proofs remain unavailable.

Development branch: `dev/r9.9-supported-recursion`, based on `f1b8260`.
The preceding R9.9 checkout and archive were preserved.

Implementation source SHA-256:
`e94e724d60a879b942081cf753017e90da4a7805b12d717cb7456e14debab8be`.
The manuscript remains pinned to commit
`4eaee87548250b2682affda7d05d947c05554bae`; no paper bytes changed.

## Mathematical changes

The separate supported executor combines modes only when their packet,
ownership and complete source linear form agree. It sums their target
coefficients and independently verifies the transformation. Affine row
support is constructed by polynomial-support multiplication and checked by
an independent exponent-to-row matching algorithm. Shared modes can have
exponents above one. The original complete weighted-stream executor is
unchanged; aggregation is explicitly reported, not described as enumeration
of that stream.

Every supported tuple constructs all 64 actual children. Strict recursive
calls independently check `64 M_child <= 6 M_parent` before entering any
child, and only networks with at most four edges succeed as leaves.
Budget exhaustion returns no result. Creation-time canonical residues are
preserved when tensor references are inherited at higher precision.

The degree optimization proves row constancy from complete entry evaluations
at original creation precision. Summing a constant row's Boolean Y factors
gives one. With k ports on nonconstant rows, `k(2L-1)` therefore bounds the
deformation degree. The recursive driver interpolates that entire polynomial
at every prescribed node, accounts for the `(a+1)d` denominator loss, and
requires agreement of all node recoveries. This is separately labelled
degree-certified Taylor recovery. Independent replay uses direct Lagrange
evaluation, not the production interpolation algorithm.

## Validated cases

| Case | Result and scope |
|---|---|
| Shared-mode coefficient fixture | 106 original modes fold into two modes; all six supported coefficients agree with independent parent elimination, including a nonzero exponent-two coefficient. Original weighted count: 345,770,425,887. |
| Multi-slot crossing-parent recovery | Nonconstant row and column tensors; all 90 points across six Hermite nodes and two valuations; 23,680 actual child calls; result `17^2 mod 32 = 1`. Independent child, half-edge and rational recovery checks pass. This small fixture does **not** meet the source shrink factor. |
| Nonconstant matching with 242 edges | Actual largest edge sequence `242 -> 22 -> 2`; 309 active calls across two levels, 792 point evaluations, 882 supported tuples and 56,449 total calls. All 64 children are recomputed for every supported tuple, including empty units. Result `17 * 2^241` at target precision 512. |
| Recursive independent replay | Reconstructs the child recipes, recomputes the leaves and recovers every parent; independently reproduces the full call/point/tuple/depth ledger. |
| Independent large-fixture root oracle | All eight root points agree with the separate formula `2^241 (7 + 10 W_xx(t+4z))` using independent integer-pair extension arithmetic. It supplies no production answers. |

The recursive run has nonconstant active parents at both levels and crossing
modes at both levels. Maximum precision is 17,408 bits. The event stream has
1,101 records and 46,295,340 canonical payload bytes. Production took about
592 seconds and independent replay about 291 seconds on the test host; these
are observations, not bit-complexity guarantees.

## Validation and artifacts

- Full suite: **1,893 passed, two optional pybind skips**, zero failures/errors.
- C++ Release build and scorer self-test: pass.
- 13 inherited/component validation commands: pass, including the existing
  41-module Lean/axiom gate. No new general-recursion Lean theorem is claimed.
- 24 clean-wheel/Docker build and validation commands: pass. Wheel Python
  3.10.19; Docker Python 3.12.14, network disabled, two CPUs and 1 GiB memory.
- Full container pytest and hosted CI: not run.

Fresh evidence is outside the checkout in
`../VERITAS_ETH_R9_9_SUPPORTED_RECURSION_EVIDENCE/`. The final directories are
`final_v2/`, `full_v2/`, `inherited_v2/` and `portable_v2/`; the consolidated
report is `verification.json`. Earlier probes and failures were preserved.
The initial CLI replay exposed an elapsed-time metadata decoding bug. The
corrected reader permits floats only in the elapsed-time field, while all
mathematical certificate decoders remain integer-only. End-to-end CLI replay
and installed-package tests cover the correction.

See [the mathematical contract and commands](docs/R99_SUPPORTED_RECURSION.md).
Evidence hashes bind bytes; they are not signatures or universal proofs.

## Remaining scope

The active `contract_source` path remains gated. Source-compliant padded
packing and its correspondence, general jet-valued input tensors, universal
Python refinement, arbitrary-density SAT reductions, and full bit-time and
peak-space proofs remain unfinished. The original mode inventory is still
materialized under finite caps; large multi-slot recursive instances may
refuse before aggregation. The successful large fixture is a matching, not
evidence for arbitrary connected source-regime networks.

The production path streams evidence and retains active grids, but time
checks are cooperative and memory is not OS-enforced. Both complexity statuses
remain `COMPLEXITY_NOT_ESTABLISHED` and theorem mode remains disabled.
