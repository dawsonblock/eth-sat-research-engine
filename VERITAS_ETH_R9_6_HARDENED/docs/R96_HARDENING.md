# R9.6 hardening: implementation notes

R9.6 is a **hardening milestone**, not a theorem milestone.  It repairs release
integrity, packaging, admission accounting and coefficient extraction, and it
adds one independently checkable finite parent-to-all-children identity.  It
does **not** implement the source-active regime and it does **not** enable
theorem mode.

## 1. Release-input integrity

**Defect (reproduced).** `.github/workflows/test.yml` ran
`scripts/validate_v08.py` before `scripts/verify_manifest.py`.
`validate_v08.py` rewrote `validation/validation_v08.json`, a manifest-covered
release input.  On an untouched disposable copy of the release:

```
PASS: 820 complete file hashes match release manifest; no unlisted files
(validate_v08.py runs)
FAIL: checksum mismatch: validation/validation_v08.json
```

**Repair.**

* `scripts/release_integrity.py` separates three artifacts: the immutable
  release-input manifest (`SHA256SUMS.txt`, read only), a runtime-evidence
  manifest for freshly generated files, and an integrity snapshot used to prove
  that no release input changed while the job ran.
* `scripts/_evidence.py` gives every validator an explicit `--output`
  destination, then `VERITAS_EVIDENCE_DIR`, then the historical in-tree path.
  All twenty-one writing validators route through it.
* The workflow verifies the manifest before `pip install`, runs every validator
  with `VERITAS_EVIDENCE_DIR` pointing outside the tree, and re-verifies the
  same immutable bytes afterwards, failing if anything changed.
* Historical `validation/*.json` bytes are untouched: their hashes still match
  the R9.5 manifest, so no old evidence was re-signed.

## 2. The pinned manuscript as a packaged resource

**Defect (reproduced).** `source_state.inspect_source_node` derived the
manuscript as `Path(__file__).parents[4] / "paper/quantitative-contraction.tex"`.
A wheel installed into an isolated virtual environment has no `paper/`
directory, so `contract_source_leaf` on the canonical empty-edge node returned

```
{"status": "INCONCLUSIVE_SOURCE_MISMATCH", "reason": "pinned manuscript is absent or changed"}
```

**Repair.** The byte-identical manuscript ships inside the distribution at
`veritas/research/tapered_v4/_resources/quantitative-contraction.tex`, declared
in `[tool.setuptools.package-data]` and read through `importlib.resources`.
`tapered_v4/manuscript.py` accepts exactly two sources: that packaged resource,
or an explicitly named asset (`manuscript=` or `VERITAS_MANUSCRIPT_PATH`).
There is no parent-directory search.  A missing, truncated, re-encoded or
substituted asset refuses with `INCONCLUSIVE_SOURCE_MISMATCH` and yields no
value.  Source checkout and isolated wheel now return the identical result
`((1, 0, 0, 0),)` for `SourceContext(2,1,1,1,1,1,19)` with zero edges.

## 3. One coefficient-admission counter

**Defect (reproduced).** `compile_entry` counted only creation-ring jets, so a
packet carrying four source-mode scalar coefficients was accepted under
`EntryLimits(max_coefficients=1)` and returned `((2, 0),)`.

**Repair.** `tapered_v4/coefficient_budget.py` defines and enforces one
contract: the budget counts *normalized stored coefficients at creation
precision* — dense tables, packet local matrices, target coefficients, source
scalars and clause polarities — in a single atomic counter that refuses before
any ring arithmetic.  `make_reference`'s structural pre-scan is now derived from
the admissible payload size instead of a flat multiple of the coefficient cap,
so a small cap no longer rejects a payload that fits.

## 4. Bounded packet coefficient extraction

**Defect (reproduced).** `evaluate_compiled` visited `product(*row_choices)`
before pruning.  The valid instance `[z](1-z)^15 == -15 == 1 (mod 8)` with a
degree-2 extension and two jet coordinates exhausted the 5,000,000-unit default
budget after ~2.2 s and returned no value.

**Repair.** `tapered_v4/packet_coefficients.py` provides

* `first_order` — the product rule for one mode of exponent one, `3q` ring
  multiplications instead of `q 2^q`, no division;
* `sparse_dp` — truncated polynomial multiplication keyed by completable
  exponent vectors only, with a state cap that refuses rather than truncates;
* `unpruned_reference` — the deliberate Cartesian reference, retained for
  differential testing.

The same instance now returns `((1, 0), (1, 0))` in 1,499 work units and about
1 ms.  Measured on identical inputs, the R9.6 path takes 0.317 ms where the
Cartesian path takes 485 ms at sixteen rows; work units are **not** comparable
between the two evaluators and no speedup is claimed from their ratio.

## 5. Canonical encoding and fail-closed validators

`tapered_v4/canonical.py` defines domain-separated, versioned digests of
canonical JSON.  `tapered_v4/validators.py` is total over hostile input: byte
length, nesting depth, node count and integer magnitude are bounded *before*
`json.loads` builds anything; unknown fields and unknown schemas are refused;
an `INCONCLUSIVE_*` document may not carry a result; no document may set a
theorem flag.  A Hypothesis fuzz suite drives arbitrary bytes and arbitrary
documents through both and asserts that only `ValidationRefusal` escapes.

## 6. One finite parent-to-all-children identity

`tapered_v4/parent_child.py` emits a `VERITAS_PARENT_CHILD_CERTIFICATE_V1`
document binding the parent digest, source-context digest, port orders, depth,
parameters, per-point mode construction, the complete ordered tuple domain with
its cardinality, every derived group child, the budgets and the explicit
refusals.  A separate consumer re-derives the packing, the point modes and the
tuple domain from the parent alone, recomputes every child contribution, and
recomputes the parent side with the independent half-edge oracle.

The certified fixture (two wires, degree-2 extension, precision 4, `a=u=1`,
radix 4) reports `points_checked == points_required == 8` and
`classification == FULL_COVERAGE`.  The R9.5 eight-wire transcript reported
`points_checked: 0, points_skipped: 50`.  Twelve adversarial mutations —
omitted term, duplicated term, altered coefficient, altered parent value,
altered tuple sum, altered tuple, wrong cardinality, wrong port permutation,
wrong precision, altered mode weight, omitted point, theorem promotion — are
rejected.

This certifies **one recursion level** on a bounded fixture.  It is not a
recursion theorem and it does not generalise.

## 7. The unreachable source-active schedule

`tapered_v4/source_regime.py` derives, executably, that no admitted
`SourceContext` can reach `ACTIVE_NUMERIC_PRECONDITIONS_MET`:

```
lambda = ceil(log2(s));  e = 4*lambda;  e <= max_extension_degree
=> lambda <= max_extension_degree / 4          (64 -> 16, ceiling 4096 -> 1024)
s.bit_length() <= max_size_bits                (ceiling 65536 -> lambda <= 65536)
base = floor(lambda / 131072);  active needs base >= 1  =>  lambda >= 131072
131072 > 1024
```

Two independent walls, both far below the requirement.  The module separates
`EXPERIMENTAL_SCALED_FINITE` from `SOURCE_THEOREM_PARAMETERIZED`, returns
`INCONCLUSIVE_SOURCE_ACTIVE_PATH_NOT_IMPLEMENTED` for every admitted context,
and keeps theorem mode disabled.  A `SymbolicSourceSize` value describes
`s = 2**lambda` by its exponent only, with its refinement obligations listed as
undischarged; nothing materialises a graph of that size.

## 8. Lean, C++, and measurement

Lean 4 at the pinned commit `eb6cafb7290e8bd5f2937522d8d804f58f02bafc`
(version 4.35.0) was installed in this session and the 36-module proof gate
recompiled from source: `PASS`, axioms limited to `propext`,
`Classical.choice` and `Quot.sound`.  `lean_python_builder_refinement_proven`
remains `false`; the Lean results are model results, not refinements of the
executable.

The C-ABI scorer was rebuilt on macOS/arm64 and its self-test passes; the
differential suite passes with the `cpp-ctypes` backend and six independent
certificate replays.

`scripts/benchmark_r96.py` records packet-coefficient timings and a #SAT
scaling series whose exact counts are brute-force confirmed up to eighteen
variables.  No subexponential, polynomial-space or competitive-performance
claim is made from those numbers.
