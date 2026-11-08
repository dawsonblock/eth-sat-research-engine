# R9.3: packet occurrence correctness

This release implements and proves the global packet-address **Lean model**
and checks its finite correspondence with both existing Python builders.
It does not implement or prove the complete OpenAI counting theorem.

## Source and mathematical contract

The authority is `paper/quantitative-contraction.tex`, SHA-256
`671642d7b53154d92344e8c4be0240f18929632ebcfdf73b07c3e9939b873860`,
specifically `lem:tensor-packets` and `eq:tensor-packing-conditions`.
The local pinned bytes were inspected; an attempted live GitHub fetch was
unavailable. No upstream revision or paper pin was changed.

An input edge is its original **list index**, not its endpoint pair. Row and
column vertices remain separately tagged even when their numeric IDs agree.
For occurrence `i`, its class is the coordinate list
`[(R(u_i)[d], C(v_i)[d])]`. Its rank `q_i` counts earlier occurrences of the
same class. Let `P` contain each coordinate's `(min, max)` pair and let `e`
be the number of equal coordinates. Then

```
copies = 2^e
packet = q_i / copies       (integer quotient)
copy   = q_i mod copies
```

Slot bit `d` is `R[d] > C[d]` for unequal symbols; otherwise it is the next
little-endian bit of `copy`, with equal coordinates visited increasingly.
The address is `(P, packet, slot)`. This is the manuscript's fixed orientation
convention, with `2^e` slots from each directed class in a packet.

The constructed common height is exactly

```
H = ((maximum_class_load + 2^a - 1) / 2^a) * 2^a.
```

For a canonical pattern, the padded codomain satisfies `slot < 2^a` and
`packet < H / 2^e`. A valid unoccupied position decodes to `None`. Invalid
addresses raise a validation error; they are not treated as padding.

## What is proved by Lean

All new proof inputs are included in the 30-module pinned-toolchain gate.
The exact statements, including every hypothesis, are in the proof files;
`D3R93Contracts.lean` restates the main nontrivial contracts separately.

| Module | Result |
|---|---|
| `D3OccurrenceRank` | Count-of-earlier-occurrences encoder and independent occurrence-search decoder are inverses on real entries; decoding never invents an edge. |
| `D3BinaryBits` | Little-endian numeric value and bounded bit lists are inverses. |
| `D3NumericSlot` | Equal/unequal bit splitting composes with integer packet/copy division; both inverse laws and numeric bounds hold. |
| `D3FullPacketModel` | Canonical class orientation, class rank, and numeric slot compose into global edge addresses; both inverses, injectivity, valid-address bounds, and padding characterization hold. |
| `D3PaddedConstruction` | Computed common height is divisible by the slot width, contains every class load, is less than maximum load plus width, and is zero on the empty graph. |
| `D3FirstMinimum` | The Lean whole-word chooser selects the earliest minimum in its candidate list, including exact ties. |
| `D3R93Contracts` | Separate type contracts consume these proofs and prevent replacing the underlying results with `True`. |

`r93_constructed_edge_contract` quantifies over every finite class sequence of
common width and every valid edge index. It derives the padding premises from
the computed height, then proves existence of a valid address, decoding to the
original index, and uniqueness of that index. It is a universal combinatorial
statement about this Lean model, not merely a theorem for sampled fixtures.

`r93_occupied_packet_contract` states that, for a valid padded address, decoding
to an index is equivalent to encoding that index to that address. The padding
theorem additionally characterizes positions with no source occurrence.
The model allows natural-number symbols; `pattern_bounded` proves the radix
restriction when source symbols are bounded. The finite Python adapter checks
that restriction explicitly.

Approved transitive axiom dependencies are only `propext`, `Classical.choice`,
and `Quot.sound`. The gate rejects `sorryAx`, unexpected axioms, missing
reports, wrong compiler versions, and stale pins. A failed gate clears every
positive proof flag. This is conditional on the local Lean executable and
its kernel behaving as specified; a hash does not authenticate the executor.

## Executable corrections and checks

`global_packet_address.py` adds an immutable bounded occurrence index. It
validates the actual class buckets against original edge order, their exact
multiplicities, tagged label domains, and common height before calling the
production codec. It exposes `build_global_packet_index`, `address_of`, and
`edge_at`. The module-level `decode_packet_address(packing, address)` is an
adapter; the package exports it as `decode_global_packet_address` to preserve
the existing class-offset decoder API.

`global_packet_address_check.py` independently rebuilds expected class ranks
and addresses from the original edge list, compares actual builder lookups,
and enumerates the entire bounded padded domain with the separately written
R9.2 reference decoder. It shares the address datatype and that reference
decoder, but does not use the production encoder to generate expected results.

`validate_r93_packet_model.py` compiles fresh Lean dependencies, evaluates the
Lean numeric codec and computed height, and compares them against both Python
builders. It covers all real edges, the first invalid edge index, selected
padding positions, duplicates, high-degree vertices, equal numeric vertex
IDs on both sides, permuted edges, and deterministic random graphs. Its Python
audit checks the entire padded domain within its cap. Its Lean `#eval` address
samples are finite differential tests, not kernel proofs about Python.

The source manifest dynamically inventories all package `.py` files, includes
all gate proof inputs and immutable policy/configuration inputs, uses sorted
POSIX relative paths and UTF-8 compact sorted-key JSON, and rejects symlinked
files. Generated reports, caches, and release manifests are excluded. The
script checks its manifest both before and after execution. Evidence records
the complete fixed corpus policy and generated Lean input digest.

Negative tests cover substituted/duplicate addresses, altered inverse maps,
wrong class bucket order, missing occurrences, mutated builder lookups,
changed padding capacity, invalid bits/IDs, exact-tie mutations, reordered
selection traces, budget exhaustion, stale proof evidence, and substitution of
`True` for both an existing port theorem and the new computed-packet theorem.

## Corrected ordering scope

The two existing builders do not have identical semantics:

* `construct_implicit_packing`: degree-first vertex order, one coordinate at a
  time, using `assign_full_d3_labels`.
* `construct_streaming_d3_packing`: sorted row IDs then sorted column IDs,
  whole-word candidates, first minimum by the Python candidate order.

For `edges=[(0,0),(1,1)]`, `r=2`, `a=1`, the former assigns both rows label 0;
the latter assigns row labels 0 and 1. Both can produce valid packet mappings.
No labels were changed to hide this difference. The Lean sorted-order and
first-minimum theorems concern the whole-word model, not the coordinate builder.
The misleading equivalence in the coordinate builder's documentation was fixed.

## Remaining proof-to-executable obligations

The Python-to-Lean correspondence is **TESTED, NOT PROVED**. In particular,
there is no verified extraction or source-language semantics bridge for the
Python dictionary/bucket implementation, binary search, or CPython execution.
`labelWords` versus `itertools.product` enumeration correspondence and the
complete labeling-run simulation remain open. The new first-minimum theorem
does not by itself close those obligations. C++ semantics remain differential
evidence and are unchanged by this packet release.

The manuscript's packet count/port load bounds depend on its labeling and
numeric hypotheses. This release's address inverse theorem does not discharge
those hypotheses for arbitrary executions, nor qualify a finite fixture as a
source-active recursive call. In particular `a=1` examples are not the smallest
positive scheduled active regime; see `docs/R9_SOURCE_AUDIT.md`.

The index caps edges at 1,000,000 and width at 64; the independent dense audit
caps padded slots at 1,000,000 (default 50,000). Vertex IDs are capped at 4,096
bits. Work admission estimates are coarse, include coordinate and search
costs, and are not bit-operation or RAM bounds. The dense checker does not
enforce an OS memory limit. None of these finite methods is offered as a way to
materialize the manuscript's enormous active regime.

Full source mode completeness, all-node parent-child contraction, recursive
creation-precision preservation, tapered Hermite recovery, termination and
child shrinkage, the outer count-preserving reduction, and implementation-level
bit/time/space recurrences remain separate obligations. The existing
`INCONCLUSIVE_THEOREM_PATH_NOT_IMPLEMENTED` behavior is unchanged.

## Reproduction

Use the repository-pinned Lean toolchain and install `.[test,matching]`.

```sh
cmake -S cpp -B build/cpp -DCMAKE_BUILD_TYPE=Release
cmake --build build/cpp --parallel 2
./build/cpp/veritas_d3_selftest
python scripts/validate_conditional_expectation_lean.py
python scripts/validate_r93_packet_model.py
PYTHONPATH=src python -m pytest -q -o addopts=''
PYTHONPATH=src python -O -m pytest -q -o addopts='' tests/test_r93_global_packet_address.py
python scripts/validate_r91.py --output validation/r9_3_release_aggregate.json
python scripts/build_release.py --output-name VERITAS_ETH_R9_3_PACKET_MODEL_PARTIAL_FULL_UPGRADED.zip
python scripts/verify_manifest.py
python -O scripts/verify_manifest.py
```

The Lean CI job now also runs the finite packet-model differential and retains
its report. Hosted CI execution and branch-protection enforcement are not
claimed from local runs. Read `RELEASE_REPORT_R93.md` for actual release results.
