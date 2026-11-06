# R0/R1 source lock and proof-obligation register

Scope: this is a bounded development reference in the VERITAS-ETH snapshot,
not a theorem implementation or a performance claim. The separate root
`eth_sat` engine uses a different construction and is not integrated here.

## Source lock

Target: OpenAI, *The Exponential Time Hypothesis is False*, 25 October 2026,
upstream Git commit `4eaee87548250b2682affda7d05d947c05554bae`.
The source bytes and SHA-256 values are recorded in `paper/README.md` and
checked by `tests/test_openai_paper_conformance.py`. The mathematical labels
and mapping to legacy D.x names are in `docs/OPENAI_PAPER_CONFORMANCE.md`.
A source hash establishes byte identity, not validity of a proof or correctness
of this software. No source file was edited.

## Contract and evidence register

| Component | Classification | Contract and evidence needed |
|---|---|---|
| `core.cnf.CNF` | Finite reference | Immutable declared variables and signed clauses; DIMACS parser; unused variables retained. Test empty clauses, repeats, tautologies and malformed input. |
| `research.tensor.from_cnf`, `brute_contract`, `eliminate` | Finite reference | One equality factor per variable and one clause factor, with one wire per occurrence; contraction equals the count, including factor 2 for unused variables. Compare to independently implemented `math_exact.oracle.exhaustive_count`. Dense degree, table, edge and runtime caps apply. This is not the paper's exact bounded-degree encoding. |
| `math_exact.Ring`, `Element`, `Polynomial` | Finite reference | `(Z/2^p Z)[U,V]/(f(U),V^ell)` with monic binary-lift irreducible `f`; p=1..1024, degree=1..32, ell=1..64. Unit iff the V-constant has nonzero mod-2 residue; valuation capped at p. Coefficients and original creation precision are immutable; arithmetic rejects incompatible rings; reduction is explicit, never an increase. Operations create new values at current precision. Compare to independent integer convolution/reduction and inverse identities. |
| `eth_packing.cauchy`, `eth_interpolation.shifted_cauchy` | Finite approximation | `eq:tensor-cauchy` polynomial cancellation over Q, shift before conversion to integral 2-adic residues; reject even reduced denominators. Tests compare with a separate product formula and modular evaluations. No weighted-mode theorem follows. |
| `appendix_d_schedule`, `appendix_d_contract` | Finite approximation | `eq:tensor-parameters`, `eq:tensor-packing-conditions`: tests check selected integer formulas and call preconditions, not universal validity or all recursive hypotheses. See source conformance document. |
| `eth_packing_v26` and `tapered_v4.child_partition` | Finite approximation | `lem:tensor-packets` constructions and checks at bounded sizes. The theorem's active parameter regime is not qualified. Independent general proof and full-size execution remain open. |
| `eth_recursive_contraction_v39` children, modes and `tapered_v4` | Finite approximation | Finite child references and separate capped recursion experiments; source-defined shrinking, structural coverage, inherited precision and universal parent-child identity remain proof obligations. |
| `eth_interpolation.tapered_hermite` | Finite approximation | `lem:tapered-hermite`: exact rational reconstruction for supported inputs; general source-faithful precision recovery requires independent proof and adversarial tests. |
| Manuscript recursive theorem branch and full complexity analysis | Unimplemented | No theorem-scale recursive engine, independent correctness proof, polynomial-space proof, complete branch ledger, or asymptotic runtime bound exists here. |

The classifications above apply to the named components and their stated
contracts, not every function in the snapshot. The requested function-by-function
legacy audit has **not** been completed; unreviewed functions do not inherit a
source-faithful designation. `math_exact.status.execution_status()` reports
this explicitly and is unaffected by test results. Consequently the complete
R0 and R1 acceptance gates remain open. Completing R0 requires a full symbol
inventory, source mapping and independent review; completing R1 requires
broader independent arithmetic verification and qualification of resource
and input bounds. Passing finite tests is necessary evidence, not a proof.

## Reproduction

From this directory, `PYTHONPATH=src python -m pytest -q` runs the snapshot
suite. `tests/test_r1_exact_foundation.py` is deterministic and includes
exhaustive small CNFs, independent integer ring arithmetic, inverse and
precision failures, deep immutability and Cauchy cancellation tests. The
exhaustive oracle has a default 20-variable cap and a maximum cap of 24.
The ring interface has no implicit lift, and no type in this package upgrades
an observed finite result into a theorem claim.
