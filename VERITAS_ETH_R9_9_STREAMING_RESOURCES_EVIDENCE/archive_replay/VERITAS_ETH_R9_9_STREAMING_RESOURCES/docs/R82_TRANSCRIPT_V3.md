# R8.2 transcript V3 format and trust boundary

## Canonical content

`VERITAS_FINITE_TAPERED_V4_TRANSCRIPT_V3` contains schema and algorithm
versions, the complete dataclass execution policy including default values,
the loaded package source manifest and digest, pinned manuscript tree and
contraction-source digests, the root network digest, normalized root state,
extension polynomial/degree, target precision, jet length, per-tensor
creation-precision bindings, events, dependency digests, coverage totals,
result, and resource ledger limitations. V3 embeds the packet-source
certificate, each finite point-mode certificate, and each checked
child-recipe certificate in the event stream alongside their content
digests. A canonical SHA-256 digest binds the entire certificate except its
own digest field. Replay checks dependency bindings by rerunning and
comparing the recomputed complete certificate.

The outer `scripts/validate_tapered_v4.py` R8.2 evidence wrapper has its own
V3 schema and digest. It binds the CNF, full policy, finite execution
certificate, ledger, source/manuscript bindings, network digest and coverage.
The evidence digest excludes only its own digest field. JSON object key order
is normalized; array order remains significant because event order is part of
the transcript.

## Source and manuscript hashes

The source digest is SHA-256 over a canonical sorted mapping from UTF-8 POSIX
relative paths to SHA-256 of exact file bytes. It includes all `.py` files
under `src/veritas`, `docs/OPENAI_PAPER_CONFORMANCE.md`, optional
`pyproject.toml` and `VERSION`, and all files under `paper/`. Symlinks in the
audited trees are rejected. Tests, scripts, validation output, generated
release manifests, transcripts, ZIPs, bytecode and cache directories are
excluded. This binds executable package source and its pinned specification,
but is not a signature or authenticated build provenance statement.

The manuscript pin is the exact vendored tree
`f4a10137d8630cb8ff26d031aca38c23a39db4606a4494ff7e43f59b8c671594` and
`paper/quantitative-contraction.tex` digest
`671642d7b53154d92344e8c4be0240f18929632ebcfdf73b07c3e9939b873860`.
Replay checks the current bytes against both pinned values.

## Replay outcomes and legacy policy

V3 replay requires all binding fields, the full current policy, matching
source/manuscript/input bindings, a recognized unsigned hash trust class, a
valid canonical evidence digest, and exact deterministic re-execution. A
successful result is `FINITE_TRANSCRIPT_REPLAYED` with
`trust_class=HASH_MATCH_UNSIGNED`; it is not a signature, independent proof,
or theorem qualification. Changed or missing fields, content, policy,
dependencies, or transcript events fail closed.

V1 and V2 execution schemas retain their historical policy/replay handling.
Replay explicitly returns `legacy_v1_replay` or `legacy_v2_replay` and
`LEGACY_SAME_CODE_REPLAY`; a legacy transcript cannot gain V3 point,
independence, or source-binding claims by being read with the new code. The
old V1 outer eight-wire wrapper remains readable and is marked
`legacy_evidence_wrapper` by the validation CLI.

## Limitations

SHA-256 detects accidental or adversarial content mismatch only when the
checker and expected pin are trusted; it does not authenticate the author or
origin of a transcript. No signature, reproducible binary build, isolated
runtime, or proof assistant artifact is supplied. Cooperative work/time caps
are recorded, but complete bit-work and an OS-enforced memory limit are not
implemented. Transcript replay is deterministic same-implementation
re-execution; the independent mathematical point oracle is separate finite
evidence and does not upgrade replay to an independent proof.
