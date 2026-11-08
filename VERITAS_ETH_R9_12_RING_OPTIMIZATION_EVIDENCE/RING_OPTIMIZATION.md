# RING_OPTIMIZATION candidate — implemented recommendations, measured 2026-11-07

Separate copy at `/Users/dawsonblock/MATH SPEED/VERITAS_ETH_R9_12_RING_OPTIMIZATION`,
cloned from sealed COMPONENT_OPTIMIZATION. Pure-Python reuse/caching only; no native
code, no algorithm or semantic changes. Frozen candidates and evidence untouched.

## Changes (3 files, semantics-identical)

- `ring.py`: `e`, `mask`, `zero_scalar`, `one_scalar`, `zero`, `one`, `f_bits`
  computed once in `__post_init__` via `object.__setattr__` — replaces
  getter-only `@property` recomputation (~30–38M `bit_length` calls eliminated
  per earlier profile). `scalar_mul` accumulates unmasked and masks once per
  output (mod-2^p-linear ops preserve residues exactly), uses cached `f_bits`
  and skips zero high coefficients. `scalar_sub` is a direct masked subtract
  (was add∘neg, two tuple allocs). `mul` drops the per-row slice.
- `sparse.py`: `comb_cached` (`functools.lru_cache`) applied to
  `subset_unrank`/`subset_rank` inner `comb` calls.
- `sparse_query.py`: `comb_cached` in `_decode_block` and the `build_network`
  width table; unused `comb` import removed.

## Equivalence evidence

- Digest check: 8000 `scalar_mul` + `scalar_sub`/`add` + jet `mul`/`add`/`sub`/
  `canonical`/`residue` across 4 ring configs (p=3,5,8,21) — **byte-identical**
  SHA-256 vs unchanged copy (`05bf0cae…f8b` both).
- Focused tests on the new copy: **333 passed** (scaled CNF, zero-branch,
  degree-exception, input-validation, certified two-level, recursive bonds,
  shrinking precision, streaming packet entry, supported packets, dense
  testbed) — files exercise every changed code path.

## Measured profile deltas (same script/caps as DEVIN_PROFILE.md)

| Case | Old wall | New wall | Ratio | Count |
|---|---|---|---|---|
| direct_grouped_sparse_small | 16.27 s | 4.32 s | **3.8×** | 262144 (identical) |
| scaled_certified_n5_1cl | 2.36 s | 1.12 s | **2.1×** | 24 (identical) |
| cnf_reference_count | 0.036 s | 0.037 s | ~1.0× | 1764 |
| direct_factored_two_components | 0.001 s | 0.000 s | n/a | 102400 |
| 3 capped cases | 30.00 s | 30.00 s | — | still INCONCLUSIVE, no count |

`scalar_mul` tottime: 9.13 s → 3.33 s on the grouped case (138,600 calls in
both). `Ring.e`/`bit_length`/`mask`/`zero*` calls dropped out of the profile
entirely (was ~29.6M+140k calls). Residual hotspot is now `scalar_mul`'s
remaining inner loop and `scalar_add`'s genexpr — next candidates would be the
packed-u64 native kernel or further loop restructuring.

## Reproduce

```
PYTHONDONTWRITEBYTECODE=1 python3 profile_routes.py        # in this directory
```
Evidence: `profile_routes.py`, `profile_summary.json`, `pstats_*.txt`,
plus digest script output above (reproduce via /tmp/ring_digest.py pattern).

## Scope

Measured wall-time deltas on these inputs only; not an asymptotic or
general speedup claim. Capped cases remain capped (same work, faster per-op
but still beyond 30 s). All qualification flags unchanged/false. Full-suite
and release gates NOT run on this candidate — focused coverage only.
