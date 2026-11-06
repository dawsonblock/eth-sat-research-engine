# Remaining theorem-to-executable dependencies

The new formal-model results remove candidate enumeration, key update, run
induction and complete finite packet cardinality from the missing Lean-model
list. They do not close the following obligations.

| Dependency | Current evidence | Required next result |
|---|---|---|
| Source state | Bounded Python structural admission | A typed denotation for every recipe, creation-time evaluation semantics, and uniform entry-cost contract |
| Labeling executable | General Lean-to-Lean model run identity; finite CPython/C++ agreement | Justified source/model translation or verified extraction, including selector loop and runtime boundary |
| Packet executable | General Lean codec inverses/cardinality; finite Python address checks | Formal relation of actual class dictionaries, occurrence ranks, implicit padding and packet access to the model |
| Source-active packing | Existing conditional port proofs; numeric preflight | Complete source-hypothesis instantiation and actual child-port construction; no promotion from local numeric inequalities |
| Mode support and pruning | Bounded independent Cauchy/mode and tuple checks | Universal source expansion with all required modes, valuation and multiplicity proofs, and safe precision lifting |
| Recursive children | Finite child-recipe checks and shallow regression | All-node parent-to-child identity with inherited recipes and every group/tuple accounted for |
| Hermite recursion | Bounded exact reference recovery | Source-prescribed node orders, coefficientwise guard loss, depth composition and exact parent recovery |
| Termination | Conditional shrink inequalities | Strict shrinking for the actual generated children and preservation of every recursive invariant |
| Cost and space | Partial work counters; some measured runtime/RSS | Bit-time and peak-space recurrence for the same complete executable, including arithmetic, descriptions and certificate costs |
| Outer #k-SAT reduction | Count-preserving finite CNF encodings | Source-faithful arbitrary-density reductions and their counting/cost proofs |

The dependency chain is: recipe semantics -> executable packing refinement
-> complete mode/child identity -> source recovery -> multilevel recursion
-> termination and complexity -> arbitrary-density theorem qualification.
Finite exact #SAT and the existing finite recursor remain useful regression
paths. They are not substitutes for a missing obligation in theorem mode.

The default and hard extension-degree admission caps do not reach a
source-active call. From the paper's necessary packing inequality alone,
r=64, a=2 gives D=2^24 and Delta>=8 gives M>=2^52; satisfying that
inequality is still insufficient for all source hypotheses. Materializing
such a graph is not a proof strategy.

Qualification remains:

* MODEL_REFINEMENT_PROVED for the explicitly stated new Lean models.
* EXECUTABLE_REFINEMENT_NOT_PROVED.
* RECURSIVE_THEOREM_NOT_IMPLEMENTED.
* COMPLEXITY_NOT_ESTABLISHED.
* THEOREM_MODE_DISABLED, with INCONCLUSIVE_THEOREM_PATH_NOT_IMPLEMENTED.

Next implement the recipe denotation and its independent evaluator, then
link the concrete implicit packet builder to the proved codec. Do not remove
the theorem guard to make these missing obligations appear complete.
