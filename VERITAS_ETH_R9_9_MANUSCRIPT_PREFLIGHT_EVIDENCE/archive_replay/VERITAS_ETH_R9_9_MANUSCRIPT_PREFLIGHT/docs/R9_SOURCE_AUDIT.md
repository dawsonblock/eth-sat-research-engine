# Source audit of the R9 packing work

This is a targeted source-to-implementation audit, not an independent proof
of the manuscript or a complete audit of every VERITAS module. The pinned
`paper/quantitative-contraction.tex` has SHA-256
`671642d7b53154d92344e8c4be0240f18929632ebcfdf73b07c3e9939b873860`.
The comparison uses `eq:tensor-parameters`, `eq:tensor-packing-conditions`,
`lem:tensor-packets`, `eq:tensor-recursion-identity`, and
`lem:tapered-hermite`.

## Errors found and corrected

1. **Wrong minimum scheduled exponent.** Earlier R9 prose called `a=1` the
   smallest manuscript active exponent. Under the source's positive-`u`
   active regime, `a_d=2 sum_{j<=d} u_j` is even and at least 2. For `a=2`,
   `L=4`, `D_arr=64^4=2^24`, and `Delta>=8`; the first packing inequality
   implies the necessary lower bound `M>=2^52`. This bound alone does not
   establish the source schedule: the paper fixes `Delta=ceil(s^(9/10))`
   and additional `s`, depth, leaf, and size conditions apply. The `a=1`
   examples remain valid experiments for the packing lemma's inequalities.

2. **Unsound eligibility terminology.** The streaming builder and checker
   previously derived `paper_active_call_eligible` from radix 64 and three
   inequalities calculated using the input graph's actual maximum degree.
   They received no `s` or `d`, and could not check the source-defined
   `Delta`, the scheduled `a_d`, or whether the call was active. Similarly,
   the compressed `K_N,N` example used `a=1` while calling itself an active
   call. V2 certificates now decline those active-call claims. V1 replay
   verifies the historical schema and labels the replay as legacy, but
   discards the old eligibility claim. This is a qualification repair, not
   a proof of a complete source-schedule implementation.

3. **Wrapper did not require every recorded bound.** The finite rational
   checker distinguishes a valid execution trace from whether the variance,
   packet-count, and port-load bounds hold. The wrapper previously tested
   only the trace's `valid` flag. It now requires all of those bounds and the
   numeric inequalities before returning a packing. Fault-injection tests
   cover each individual failure. No naturally occurring counterexample or
   incorrect count was established by this audit.

4. **Incorrect appendix statement.** The pinned main file has three appendix
   sections before its `quantitative-reduction.tex` input; that input starts
   the fourth appendix section (`app:quantitative`). The contraction source
   is a subsection of it. The historical project names `D.3` and `D.4.4` are
   aliases, not authoritative numbered references. The vendored
   `paper/README.md` also contains the erroneous assertion that the paper has
   no Appendix D; it is left unchanged by the source-pinning policy. Use
   source labels rather than the historical names.

## Important limitations that remain

### Review of the proof gate and executable refinement

The original local Lean validator checked only the presence of `sorryAx`,
looked for theorem names as substrings, and recorded rather than enforced the
pinned compiler version. It also crashed for an executable at a shallow path
such as `/tmp/lean`. A false test theorem depending on a custom axiom compiled
without `sorryAx`; a wrapper reporting `0.0.0` previously produced a PASS.
The validator now checks exact axiom-report lines, rejects dependencies other
than `propext`, `Classical.choice`, and `Quot.sound`, enforces the declared
Lean version, and handles shallow executable paths. This verifies reported
axiom dependencies from the configured compiler; it does not authenticate
that compiler or the source tree.
If any module or toolchain check fails, the resulting evidence now clears
all positive proof-qualification fields rather than retaining partial flags.
`D3ExpectedContracts.lean` separately states and checks the types of four
central port and slot claims. It does not independently specify every
supporting theorem, nor prove that the Lean definitions refine the paper or
Python. The manuscript hash is now checked against the pinned value.

A kernel-checked fixture establishes that the Lean-generated vertex order
and the Python order can differ in practice. For edges `[(0,0),(1,1),(0,1)]`,
`r=2`, `a=1`, Lean visits row 1 before row 0 and assigns row labels 1 and 0
to rows 0 and 1 respectively; Python visits rows 0 then 1 and assigns 0 and 1.
See `d3_order_audit_fixture` in `D3SymbolPorts.lean` and
`test_sorted_python_order_differs_from_lean_order_audit_fixture`. This does
not contradict the Lean arbitrary-order port bound, but it rules out direct
equality with the current generated Lean run as a Python refinement proof.

The Lean theorems now prove finite combinatorial statements for the Lean-defined
labeling, a common padded class size, and the row/column symbol-port bounds.
They do not yet prove the packet slot bijection, Python refinement, the universal
packing lemma, or the algorithm's bit/space complexity. The Python certificate
checker checks finite instances and shares input representations with the
builder. Passing it does not establish a universal theorem.

The default `schedule_preflight` limit is 4,096 input bits. A positive root
`u_0` requires `lambda >= 131072`, so the default cannot reach the paper's
positive-`u` active schedule. An explicit larger cap can exercise symbolic
schedule calculations, but does not make the graph or contraction executable.
This limit is deliberate and has not been raised by the audit.

The paper additionally requires complete source-weighted mode support,
all-node parent-to-child contraction with creation-time lifts, exact tapered
Hermite recovery, decreasing child sizes and degree invariants at every
recursive level, plus the arbitrary-density reduction and cost analysis.
These are not supplied by the present audit. The theorem recursor still
returns `INCONCLUSIVE_THEOREM_PATH_NOT_IMPLEMENTED`.

The source paper and the separately published Lean scope make different time
claims: the latter states a weaker exponent with an extra `log log n` factor.
Neither the upstream Lean result nor these finite tests establishes that this
Python implementation refines the relevant formal machine.
