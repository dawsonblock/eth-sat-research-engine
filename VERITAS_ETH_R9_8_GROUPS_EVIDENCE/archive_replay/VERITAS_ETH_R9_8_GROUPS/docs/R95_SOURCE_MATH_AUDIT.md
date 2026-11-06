# R9.5 source mathematics and entry-execution audit

This is a **partial implementation release**. It adds executable semantics to the R9.4 immutable source-state interface. It does not implement or verify the complete ETH theorem. See `RELEASE_REPORT_R95.md` for measured checks and `R95_REMAINING_OBLIGATIONS.md` for blockers.

## Source identity and review scope

The four vendored LaTeX files match the Git blob identities in OpenAI's `openai/math` repository at commit `4eaee87548250b2682affda7d05d947c05554bae`, retrieved on 2026-11-04. The contraction source SHA-256 is `671642d7b53154d92344e8c4be0240f18929632ebcfdf73b07c3e9939b873860`. No paper bytes were changed. `validation/r95_upstream_review.json` records the remote listing, local SHA-256 values, independently recomputed Git blob hashes, scope-note text and comparator identity.

References:
- [Pinned manuscript sources](https://github.com/openai/math/tree/4eaee87548250b2682affda7d05d947c05554bae/preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026/build)
- [Formalization scope](https://github.com/openai/math/blob/4eaee87548250b2682affda7d05d947c05554bae/lean/docs/378.md)
- [Comparator statement](https://github.com/openai/math/blob/4eaee87548250b2682affda7d05d947c05554bae/lean/ComparatorChallenges/SubexponentialSAT.lean)

The live scope note distinguishes the general manuscript exponent `O_k(n loglog(n)/sqrt(log(n)))`, the bounded-density exponent `O_{k,D}(n/sqrt(log(n)))`, and the Lean scope's weaker `O_k(n (loglog(n))^2/sqrt(log(n)))` exponent. They must not be used interchangeably. The comparator statement is not the full proof. The upstream Lean formalization was not independently rebuilt in this release.

Review covered the complete local quantitative-contraction appendix, reduction definitions, scope statement and implementation contracts. It is not an independent certification of the entire manuscript. Historical `D.x` aliases do not replace the actual labels. The old immutable `paper/README.md` contains superseded appendix-number commentary; `docs/OPENAI_PAPER_CONFORMANCE.md` records the corrected mapping.

## Mathematical rules enforced

1. **Root domain** (`thm:tensor-contraction`, introductory ring convention): original entries belong to the base V-ring. A root leaf rejects dense entries with nonzero positive U coordinates. Packet recipes at the root are unsupported, rather than presumed to satisfy this premise.
2. **Creation precision** (`subsec:tensor-children`): evaluate the complete entry in its creation ring at `p_c`; preserve the resulting coordinate representatives at any `p >= p_c`. Lifting is not a ring homomorphism. For example, `(6+6) mod 8 = 4`; evaluating the same expression modulo 32 gives 12 and changes the retained tensor. The new code enforces the first behavior.
3. **Packet entries** (`subsec:tensor-children`): extract the specified coefficient of the product of affine row factors, then multiply source linear forms to their specified exponents. Empty products, absent target rows and empty source tiles follow the source conventions, including `0^0 = 1` here. No divisions or valuation-based omissions occur inside this entry kernel.
4. **Leaf execution** (`subsec:tensor-cost`): direct Boolean-edge summation is allowed only when `M <= ceil(s/floor(sqrt(ceil(log2(s)))))`. Larger nodes return `INCONCLUSIVE_SOURCE_ACTIVE_PATH_NOT_IMPLEMENTED`. The value of `s` is retained from the context rather than inferred from the current edge count.
5. **Tapered recovery** (`lem:tapered-hermite`, `eq:tensor-hermite-loss`): an independent finite grid checker compares the exact sum of valuations in the product defining `E_t(0)` to the level-count formula. It checks the `-6 D_t h` bound, reciprocal-factor integrality, multiplicities and the precision margin for every coefficient through `q_t-1`. It does not infer a universal recovery proof from these grid cases.

## Executable changes

- `tapered_v4/source_recipes.py`: canonical, versioned, immutable recipe descriptions for dense, equality, clause and packet tensors; explicit limits; exact creation-time arithmetic.
- `tapered_v4/source_leaf.py`: source-leaf contraction and optional complete independent verification; no accepted value on any failure.
- `tapered_v4/source_recipe_bridge.py`: adapter from existing immutable descriptions. Existing dense tables use little-endian port indexing; the new format uses lexicographic order. The bridge explicitly permutes indices. Existing finite interfaces are unchanged.
- `independent_r95/recipe_oracle.py`: separate integer polynomial reduction, full unpruned mode-polynomial convolution, and variable elimination for graph contraction. It imports no production recipe, ring, mode, child or leaf implementation.
- `independent_r95/hermite_grid.py`: independent finite arithmetic audit of source Hermite loss and guard formulas.
- `SourceCreationPrecision.lean`, `SourceCreationContracts.lean`: universal coordinate-representative model lemmas, exact independently typed acceptance contracts, and nonhomomorphism counterexamples. The expanded proof gate clears every positive flag after any failure.

All preexisting source and behavior remain intact except additive gate/CI/documentation changes. New API calls do not enable any existing theorem path.

## Trust boundary

The independent oracle shares the schema, input graph and explicit defining polynomial. It relies on production input admission for graph well-formedness; the arithmetic and contraction algorithms differ. CNF comparisons share the CNF data model and compare tensor execution to independent exhaustive model counting. Tests of old/new recipe adapters share old recipe definitions, so those comparisons are corroboration, not an independent theorem.

The Lean statements establish the natural-number coordinate model and existing packing models, not actual Python bytecode, C++ machine code, the new packet evaluator, or the full recursion. The allowed axiom report is retained by the gate. Hashes establish content consistency, not trusted executor origin or signatures. Hosted CI and branch protection were not executed/configured locally.

Packet descriptions here contain already computed local and mode coefficients. They do not retain a complete source packet/mode-generation certificate, and the bridge does not prove where those coefficients came from. Their mathematical meaning is fully defined as finite tensors, but no parent identity or source-active eligibility is inferred. `SourceNode.depth` also does not prove ancestry.

## Resource scope

The source admission layer has broader structural caps than the arithmetic backend. Execution independently enforces the backend's existing 1024-bit precision and 64-coefficient jet caps, extension degree at most 64, entry arity at most 16, mode/description/coefficient caps, work budgets and cooperative deadlines. Limits are not raised to simulate the asymptotic regime. Requested independent coverage that is unavailable or exhausted fails with no result.

The ledger counts selected scalar operations and description checks. Integer bit costs, irreducibility tests, allocation and peak memory are not fully counted. Independent oracle work has a separate cap. RSS and wall/CPU time are measurements, not complexity proofs or enforced memory isolation.

## Explicit assumptions of the new finite checks

The Hermite grid audit verifies arithmetic identities for the selected integer grids. Applying its guard calculation to a polynomial still requires the lemma's premises: degree at most `M(2L-1)`, integral `F(0)`, and integral shifted coefficients `F(t+alpha*z)` at every required node. The grid checker does not establish these premises for an arbitrary network. Existing bounded Cauchy and reconstruction tests supply separate finite examples.

The packet-entry oracle checks the entire coefficient of a supplied finite recipe, including overlapping supports and multiplicities. It assumes that this supplied recipe is the tensor intended by its caller. Correct origin of the modes, their weights and the complete global tuple sum are separate obligations. The source leaf oracle checks the whole supplied leaf network; it does not prove that this leaf was generated correctly by a parent.
