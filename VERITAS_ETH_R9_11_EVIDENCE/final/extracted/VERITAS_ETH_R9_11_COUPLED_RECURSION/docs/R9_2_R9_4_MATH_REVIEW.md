# R9.2–R9.4 implementation route and mathematical review

## Review result and source lock

This audit checked the current R9 branch against the vendored LaTeX, not
against historical Appendix-D aliases. The exact source files are:

| Source | SHA-256 |
|---|---|
| `paper/main_full_version.tex` | `b2e6159d4fb7ea6aa4f89ac15605152b0333a5f7cafe93323492bc20a5c066aa` |
| `paper/quantitative-reduction.tex` | `0b2b136c4f37ee0583dda40ee0c0d692f4751537d3d18539a389cd467ea8359a` |
| `paper/quantitative-contraction.tex` | `671642d7b53154d92344e8c4be0240f18929632ebcfdf73b07c3e9939b873860` |

The focused mathematical regression selection passed **270 tests** in
48.74 seconds on Python 3.12.0 / macOS 26.2 arm64. It includes `tests/test_openai_paper_conformance.py`, source
Hermite recovery, Cauchy deformation, modes, structural tuples, child
construction, packet geometry and finite recursor tests. This validates
finite fixtures and code-to-formula checks. It does not independently prove
the manuscript's universal lemmas. The theorem branch in
`src/veritas/research/tapered_v4/recursor.py` must remain
`INCONCLUSIVE_THEOREM_PATH_NOT_IMPLEMENTED`.

The standalone exact-arithmetic checker
`python scripts/check_r9_2_r9_4_math_identities.py` also passed: 16 pattern
and packet-count cases, Cauchy derivative and `W(0)=I` checks for seven
packet sizes, and 247 distinct Cauchy differences checked by exact
polynomial division. These remain finite sanity checks.

The R9.2 address slice adds 53 passing focused tests and a passing 23-module
Lean gate. Its Lean proofs cover canonical class-to-pattern/orientation
reconstruction and copy/orientation interleaving in both directions. Its
bounded Python oracle exhaustively checks the scalar-offset/address
composition only for finite domains under a configured cap.

## Correct theorem bounds

Do not combine these three results into one claim:

1. `thm:tensor-contraction` in `paper/quantitative-reduction.tex` contracts
   a network of size parameter `s` in
   `(s + description_length)^O(1) 2^O(s/sqrt(log s))` bit operations and
   polynomial space.
2. The fixed-density reduction has `s = O_k(n+m) = O_{k,D}(n)`, so it gives
   `2^O_{k,D}(n/sqrt(log n))` time.
3. The arbitrary-density reduction indexes polynomial lifts using
   `s = O_k(n log log n)` wires. Substitution into the contraction bound gives
   the main `thm:main` bound
   `(n+m)^O_k(1) 2^O_k(n log log n/sqrt(log n))` and polynomial space.

The abstract shorthand `2^{n/(log n)^{1/2+o(1)}}` is consistent with that
scale, but the equation in `thm:main` is the precise statement to use. The
upstream Lean scope note states a weaker machine result with
`n(log log n)^2/sqrt(log n)` and a bit-length parameter `L`; it is not the
same exponent and does not formalize this repository's Python or C++ code.

## Formula-by-formula audit

| Source item | Independent check | Current code status |
|---|---|---|
| `eq:tensor-parameters` | With `lambda = ceil(log2 s)`, `u_d = floor(lambda/(131072*2^d)`; integer `base >> d` is exact. `a_d = 2 sum_{j<=d} u_j`, `L=2^a`, `D_arr=64^(2a)=2^(12a)`. | `appendix_d_schedule.py` and conformance tests match. The preflight checks caller-supplied states; it does not prove the recursion supplies all states. |
| `eq:tensor-packing-conditions` | `M >= 2 D_arr^2 Delta`, `M >= L D_arr`, `2L <= Delta`. If an active call has `u>=1`, then `a>=2`, `D_arr>=2^24`, `Delta>=8`, and therefore `M>=2^52`. This is only a necessary lower bound from the hypotheses. | Exact integer preflight and `inspect_active_theorem_capacity` match. No theorem-scale graph was constructed. |
| `lem:tensor-packets` | The variance bound gives each class load `<= M/D_arr + sqrt(2 M Delta)`. The first two inequalities imply `H_pad <= M/D_arr + sqrt(2M Delta)+L <= 3M/D_arr`. At each coordinate a fixed side-symbol occurs in `1/r` of directed classes, so side port load is `<=3M/r`. | Conditional-expectation labelers and rational replay are finite. The numeric preflight alone is not a universal construction certificate. |
| Child-size deduction in `subsec:tensor-children` | A group child retains at most one row-side and one column-side port load: `M_g <= 6M/r`. For `r=64`, `M_g<=3M/32<M/8`. A packet vertex degree is at most `2L<=Delta`. | Finite children check actual edges and degree. No all-call construction theorem is proved. |
| Packet slot layout | For a pattern with `a'` unequal coordinates, each directed class is split into `2^(a-a')` copies per packet. Orientation bits occupy unequal coordinates; copy bits occupy equal coordinates. `H_pad` is divisible by `L`, hence by every copy count. Summing packets over patterns gives `(H_pad/L) sum_pattern 2^a' = D_arr H_pad/L`. | The production implicit lookup and packet materializers now call the bounded Python codec; an independent finite checker compares the complete finite domain and real edge occurrences. Lean proves canonical class-to-pattern/orientation reconstruction and pattern/copy/orientation-to-slot-word inverses. Scalar offset-to-copy-bit formal composition and source refinement remain open. |
| `eq:tensor-cauchy` and `lem:tensor-integrality` | `S={-L,...,L-1}` has `2L=2^(a+1)` residues; `C'(0)=(-1)^(L-1)L!(L-1)!`. The canceled `W_xy` is degree `2L-1`, and `W_xy(0)=1` iff `x=y`. At shifted points, cancel known powers of two before inverting the odd part. | Exact rational and two-adic finite evaluators agree in tests. No general Lean proof currently covers the executable evaluators. |
| `eq:tensor-mode-expansion` | For `y=y0+2^(i+1)j`, `1/(T-y+x) = (1/(T-y0+x)) sum_b (2^(i+1)j/(T-y0+x))^b`. The base coefficient has valuation at least one; each added power contributes at least one more. Weight `b+1` and truncation at `b+1<p_t` are therefore consistent modulo `2^p_t`. | Point-mode certificates reconstruct every finite Cauchy matrix entry. Mode-name equality is not the proof criterion; the action and valuation bound are. |
| `eq:tensor-mode-budget` and structural pruning | Product of `R` affine row forms has total degree at most `R`; for each mode its exponent is at most its support-row count. Those are necessary zero-coefficient constraints in addition to `sum w_Z beta_Z < p_t`. | `structural_tuples` and its independent generating-function count check finite domain completeness. It does not prove that production generated every source mode. |
| `lem:tapered-hermite` | `h=ceil(3M/u)`, `q_t=h max(0,u-v2(t))`, and `p_t=p+8h(L/2^i)+8M(a+1)`. There are `L` odd nodes, so `sum q_t >= Lhu >=3ML > M(2L-1)`. Also `h<=4M/u`. | `source_hermite.py` computes exact rational weights, checks the polynomial basis through the configured degree, and rejects inadequate coefficient precision. Its finite caps and tests do not prove the uniform 2-adic loss bound for arbitrary parameters. |
| `eq:tensor-recursion-identity` | Expanding every row factor in its local term and all crossing modes, then grouping mode exponents by their unique target/source, gives the complete weighted sum of the `r=64` group child contractions. Terms of total weight at least `p_t` vanish. | Finite parent-versus-child oracles check selected nodes. Universal all-mode completeness, recipe preservation and all-node equality remain open. |
| `subsec:tensor-cost` | `M_d<=Cs 8^-d` and `u_d=Theta(lambda/2^d)` give `M_d/sqrt(u_d) <= Cs/sqrt(lambda) * (sqrt(2)/8)^d`; summing this geometric series explains the contraction exponent. The leaf threshold contributes `2^H=2^O(s/sqrt(lambda))`. | This checks the paper's algebraic exponent. It is not a cost proof for the current executable, whose code paths, bit lengths, descriptions and certificate work lack a complete recurrence. |

No formula mismatch was found in the formula-level checks above. The R9.2
correction is now partially formalized: `D3GlobalPacketAddress.lean` proves
the pattern/orientation/copy interleaving and the raw symbol-pair
canonicalization in Lean. The integer offset-to-copy-bit composition and the
correspondence from arbitrary Python builder execution to that Lean model
remain open; a bounded exhaustive Python oracle covers finite cases only.

## Implement R9.2: global packet bijection

Use a distinct **edge occurrence id** `eid : Fin M`; never use an edge pair as
an identity because repeated parallel edges are separate occurrences. Keep
`Row id` and `Column id` tagged even when the integers are equal. Sort each
directed class bucket by `eid`; that makes the executable convention total
and deterministic.

For each unordered symbol pattern `P : (Fin r × Fin r)^a` with `x_i<=y_i`, let
`a'(P)` be the number of unequal coordinates and
`c(P)=2^(a-a'(P))`. For an edge occurrence in a directed class with within-class
offset `k`, define:

```text
packet_in_pattern = k / c(P)
copy_index        = k % c(P)
slot_bit[i]       = orientation_bit[i] if P[i] is unequal
                    copy_bit[rank_equal_coordinate(i)] otherwise
slot              = sum_i slot_bit[i] * 2^i
```

This gives the address `(P, packet_in_pattern, slot)`. Decoding the unequal
slot bits recovers the directed orientation; decoding equal-coordinate bits
recovers `copy_index`; then `k = packet_in_pattern*c(P)+copy_index` recovers
the edge id from its sorted bucket, or padding if that offset is not real.
If Python needs a single dense packet number, enumerate patterns in canonical
lexicographic order and add the prefix
`sum_{P'<P} H_pad/c(P')`. Prove that the block lengths sum to
`(H_pad/L) sum_P 2^a'(P) = D_arr H_pad/L`.

Implement this first as a pure Python `packet_address.py` and a separate
checker, then formalize finite pattern/edge types and both inverse laws in
Lean. Required Lean statements are: edge occurrence coverage, no duplicate
real address, all real edges decode, every padded address has exactly one
slot, and exact cardinality. Then prove the Python builder's sorted-bucket
and bit-order convention corresponds to those definitions. Unit fixtures are
not a substitute for the inverse laws.

## Implement R9.3: contraction, precision, recursion

1. Freeze an immutable network description type: ports carry occurrence ids;
   each tensor recipe stores its creation precision, extension polynomial,
   jet length and canonical coefficient lift. A later call may reduce this
   created value at higher precision, but must never recompute it from a
   different lift.
2. Formalize `F(t+alpha*zeta)` as a polynomial in a mode vector. Prove the
   packet-local mode expansion first, including unit-denominator hypotheses
   after extracting powers of two. Prove every coefficient's valuation bound.
3. Define the required tuple domain from those modes. Prove the structural
   degree pruning only when its row-support premise is present; an unsupported
   valuation or missing support certificate returns `INCONCLUSIVE`.
4. Define all 64 child recipes for each retained tuple. Prove their product
   equals that tuple coefficient after source substitution, and sum over the
   complete tuple domain to get `eq:tensor-recursion-identity`. The proof must
   include zero-support modes and padding, not only real ports.
5. Prove `lem:tapered-hermite` over the source's integral coefficient ring:
   rational interpolation weights, exact 2-adic valuations, coefficientwise
   input precision and recovery modulo `2^p`. Use the finite Fraction code as
   a differential oracle, not as the proof.
6. Define recursion state with `(s, depth, M, Delta, p, ell, f, recipes)` and
   the source hypotheses as invariants. Active calls must prove every numeric
   hypothesis before packing. Leaves use only the source leaf rule. Every
   active child must satisfy `M_child<=3M/32<M/8`; use `M` as a termination
   measure. Unsupported states fail closed.
7. Test every algebraic layer independently: Cauchy matrix, unpruned mode
   action, retained/pruned tuple sum, all 64 children, Hermite node data, then
   a full recursive induction. Finite point equality alone is not a universal
   proof.

## Implement R9.4: complete complexity and outer reduction

Build a cost recurrence for the exact representation above. It must count
conditional-expectation candidate scores, all `M^2` edge pairs where they
occur, construction of every mode and tuple, every interpolation point,
each of 64 children, tensor-entry evaluation, big-integer multiplication,
2-adic unit inversion, rational Hermite denominators, certificate creation
and checking, all recursive calls, and leaf assignments. Derive bit lengths
from `p_t`, extension degree `e=4 ceil(log2 s)`, `ell`, and recipe size.
Then prove depth-first peak live memory from the parent stack and one child
at a time. Keep measured RSS and scalar work counters in a separate evidence
section.

For the main theorem, finish a second, separate reduction layer: implement
and verify the count-preserving fixed-density CNF-to-network construction;
then implement the paper's arbitrary-density sparsification/parity-test and
sparse-polynomial reduction. The local `eth_counting_v39` shared-linear
summary work does not by itself implement `sec:hashes` or prove the
arbitrary-density reduction. Prove the modulo-`2^(n+1)` count recovery and
unused-variable factor before claiming `thm:main`.

## Remaining status

| Obligation | Status |
|---|---|
| Formula conformance tests for schedule, Cauchy, modes and finite Hermite | `TESTED`; 270 selected tests passed |
| Global packet address finite checker | `TESTED`; 53 focused tests passed, bounded exhaustive domain only |
| Canonical pattern/slot model | `LEAN_KERNEL_CHECKED`; 23-module proof gate passed |
| Sorted-order and candidate-score Lean model | `LEAN_KERNEL_CHECKED`; it does not establish Python/C++ execution refinement or full run selection |
| Scalar padded-offset/copy-bit composition and source-builder refinement | `NOT_PROVED` |
| Universal all-mode completeness and D.16 identity | `NOT_PROVED` |
| Hermite recovery at every recursive depth | `NOT_PROVED` |
| Termination and full recursion | `NOT_IMPLEMENTED` |
| Complete bit-time and peak-space recurrence | `COMPLEXITY_NOT_ESTABLISHED` |
| Arbitrary-density reduction and full `thm:main` implementation | `NOT_IMPLEMENTED` |
| Theorem mode | `DISABLED` |
