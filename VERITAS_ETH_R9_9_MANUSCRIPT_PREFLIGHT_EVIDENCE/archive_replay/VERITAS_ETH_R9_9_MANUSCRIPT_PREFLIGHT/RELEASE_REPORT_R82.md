# VERITAS-ETH R8.2 release report

## Release scope

R8.2 is a bounded mathematics and evidence upgrade to VERITAS-ETH v3.8.2.
It adds an independently implemented finite Cauchy/mode-action oracle,
finite unpruned tuple-coefficient checks, independent tuple/pruning checks,
selected parent-vs-child point checks, and source/policy-bound V3 execution
evidence. The theorem branch remains fail-closed with
`INCONCLUSIVE_THEOREM_PATH_NOT_IMPLEMENTED`.

It does not claim universal mode completeness, universal packet packing or
child shrinking, polynomial-space qualification, multilevel source recursion,
the arbitrary-density reduction, a subexponential implementation, or proof
of the manuscript. See [`R82_MATH_AUDIT.md`](docs/R82_MATH_AUDIT.md),
[`R82_MODE_AND_PRUNING_CONTRACT.md`](docs/R82_MODE_AND_PRUNING_CONTRACT.md),
and [`R82_TRANSCRIPT_V3.md`](docs/R82_TRANSCRIPT_V3.md).

## Baseline and retained regressions

The input archive SHA-256 was the expected R8.1 value
`0e4a06fc7f76a3e6d77be06a8cdf914aab3e32f5397bc9a91475eb766c24f1fd`.
Before modification, ZIP CRC/path/duplicate/symlink checks passed, 542 release
manifest entries matched in normal and optimized Python, the full suite ran
1,072/1,072 tests successfully on Python 3.12.0 in 84.84 seconds, and the 47
focused R8.1 tests passed. The historical R8.1 eight-wire figures and dense
scalar counters are preserved in `validation/r81_dense_cauchy.json` and the
R8.1 report; they are not relabelled as R8.2 evidence.

The release comparison found all 543 original ZIP entries in the upgraded
tree. Four original files have intentional R8.2 edits (`README.md`, the
eight-wire validation wrapper, `tapered_v4/recursor.py`, and its V1/V2
compatibility test); the two release manifests are regenerated at packaging.
No baseline file is omitted.

The reproduced eight-wire finite regression is the forced-assignment CNF
fixture. It returns `((1,0,0,0,0),)`, with 12,297 recursive calls, maximum
depth 1, 3,074 retained tuples, 50 independent tuple-count checks, maximum
child size 6 of 8 edges, maximum precision 521 bits, and 2,299,570 observed
work units. These are finite counters; the execution ledger expressly marks
its work accounting incomplete. Dense Cauchy reconstruction counters remain
579,584 (8 wires), 4,033,536 (10 wires), and 24,813,568 (12 wires). They are
scalar operation counters, not elapsed-time, bit-work or memory bounds.

The pinned source tree hash is
`f4a10137d8630cb8ff26d031aca38c23a39db4606a4494ff7e43f59b8c671594` and
the contraction-source file hash is
`671642d7b53154d92344e8c4be0240f18929632ebcfdf73b07c3e9939b873860`.
The final R8.2 package-source digest is
`074b02ae3689c23690a2eaaf65d9fe60720cf819c7df4b8923ecdad2d83cda12`.
It is regenerated from package bytes and includes the conformance pin
document and paper source. It is unsigned.

## R8.2 gates

| Gate | Evidence | Status | Remaining risk |
|---|---|---|---|
| G0 baseline | Expected archive SHA-256; safe ZIP/CRC checks; normal and `python -O` manifests; 1,072 pre-change tests executed | PASS | Python 3.13 toolchain is present but unusable in this environment; see validation record |
| G1 independent Cauchy/mode action | Exact rational polynomial division, independent bounded extension arithmetic, seeded packet cases and adversarial mode mutations | PASS, bounded | Only tested finite packets, nodes, points and arithmetic caps |
| G2 mode/pruning/tuple completeness | Cartesian-product tuple checker, coefficient valuation checks, tiny unpruned coefficient sums, adversarial tuple/support/precision cases | PASS, under enumerated finite premises | Does not prove universal source-mode support, Hall pruning, or source theorem premises |
| G3 direct point equality | Selected 4/6/8-wire checks; pinned 8-wire node has 6 modes, 64 tuples and matching independent parent/child residue | PASS, selected coverage | 3 selected cases are not all interpolation nodes or extension points |
| G4 V3 provenance | Full policy, source/paper/input bindings, canonical digest, dependency certificates and deterministic replay; V1/V2 reported as legacy | PASS, unsigned hash binding | No signature or authenticated build; replay needs matching input state and same code |
| G5 tests and package | Python 3.12 full suite 1,106/1,106; focused suite 55/55; selected-point and eight-wire write/replay; dense Cauchy validation; optimized-Python fault checks; generated and independently checked archive manifest | PASS, finite release gate | Python 3.13 could not run tests because its `pyexpat` linkage is broken and pytest/dependencies are absent; no hard memory cap and no theorem qualification |

The full Python 3.12 run took 93.01 seconds. Focused R8.2/R8.1 repair tests
ran 55/55 in 7.73 seconds. The V3 eight-wire write/replay took 12.74/13.45
seconds and observed peak RSS of 120,094,720/270,516,224 bytes. The selected
point audit checked 3/3 cases and replayed in 1.74 seconds. These are local
measurements; the current work-unit ledger
omits listed arithmetic, allocation, interpolation and validation work, so it
must not be interpreted as complete complexity evidence.

`validation/r82_release_evidence.json` records the test counts, exact
validation statuses, source and manuscript bindings, point coverage, finite
operation counters, Python 3.13 environment failure, and the explicit
limitations. The standard and optimized manifest checks are run after the
deterministic archive build.

## Reproduction commands

Run from the extracted release root with Python 3.12 and project dependencies
installed:

```sh
PYTHONPATH=src python -m pytest -o addopts= -q
PYTHONPATH=src python scripts/validate_r82.py --write validation/r82_point_oracles.json
PYTHONPATH=src python scripts/validate_r82.py --replay validation/r82_point_oracles.json
PYTHONPATH=src python scripts/validate_tapered_v4.py --write validation/r82_eight_wire_v3.json
PYTHONPATH=src python scripts/validate_tapered_v4.py --replay validation/r82_eight_wire_v3.json
PYTHONPATH=src python scripts/validate_dense_v382.py > validation/r82_dense_cauchy.json
python scripts/build_release.py
python scripts/verify_manifest.py
python -O scripts/verify_manifest.py
```

The build command must be the final source-tree edit, followed by both
manifest checks. The machine-readable run record and final gate results are
in `validation/r82_release_evidence.json`. The final archive SHA-256 is
reported with the delivered ZIP; it is not self-embedded because embedding a
ZIP's own digest would be self-referential.
