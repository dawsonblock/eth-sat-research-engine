# R9.6 finite reduction audit

## Which algorithm returns the value

The finite DIMACS entry point converts a CNF to integer clause and equality tables. A variable with no occurrences contributes a scalar 2. It chooses precision p = n+1 so the residue determines the exact count throughout the possible range 0 through 2^n. The tensor API also accepts signed integer tables and an explicit target precision. Its result is a residue.

For a partition of factor vertices A,B, partition the wire IDs into I (both endpoints in A), J (both in B), and K (one on each side). For bits b on K, let L_b(x) and R_b(y) be the products of the restricted factors on each side. The implemented identity is

    sum_{b,x,y} L_b(x) R_b(y) = sum_b (sum_x L_b(x)) (sum_y R_b(y)).

Each full assignment has exactly one restriction to each of K,I,J, and their disjoint union recovers the assignment. At fixed b the two inner variables are independent. Distributivity gives the identity over the integers. Taking residues commutes with all these finite additions and multiplications. No divisions or precision increases occur at a boundary split.

The constructor uses a deterministic search of breadth-first prefixes of the factor graph. It minimizes the number of crossing wires among the eligible prefixes, then maximum child size, then prefix length. A second check derives the wire sets from factor scopes. Each restricted factor table is built by a bit-offset gather, then checked against the original factor's assignment evaluator entry by entry. The saved mask is an integer in canonical wire order. The verifier regenerates both children at each mask and the whole mask range. The two children at one mask are multiplied. Adding one child contraction per term without this product would give a different identity.

Each accepted cut has two children of at most ceil(M/2) wires and strictly fewer than M. Empty factor products and zero-wire scalar factors retain their integer meanings. A failed cut, depleted budget, wrong table or disagreeing direct oracle yields a refusal without a residue. The independent parent sum is optional and only checks the returned value. The measured runs disable it inside the algorithm and compare against separately executed brute force.

The direct leaf policy accepts up to eight wires. A stricter leaf cutoff exercises additional levels. An explicitly selected tapered piece policy instead forces an active finite packet/Hermite step on each nonempty eligible piece and requires every generated child to shrink. The finite parameters are a=1, u=1, r=4. A rejected six-wire piece is in the regression suite. This policy can be expensive even on a disjoint union of trivial components.

## Point construction and interpolation

The separate recipe-point API accepts a described parent and a finite point certificate binding packing, node, extension point and precision. It checks the supplied certificate, parent endpoints and packet action. For each retained beta it checks independent membership and builds the actual occupied group graphs. The existing topology and coefficient checker validates their inherited tensors, packet factors and actual ports. The constructor converts them to immutable executable creation-time recipes. Every radix group appears once. A vacant group with no required endpoint is represented by an empty zero-wire network with contraction one. Source-shaped creation precision is retained when a recipe is evaluated at higher point precision.

The complete evaluator combines an independent bounded generating-function count with membership, strict ordering and a small unpruned audit. It contracts all group recipes, sums the tuple products, and checks the answer against a separately implemented parent half-edge evaluator. The term constructor alone establishes a weaker postcondition than this full-sum check. The certificate hashes bind the parent, mode and packing inputs, policy, point, per-group recipe ordering, captured precisions, group values and products. Replay takes an externally supplied parent and mode certificate and regenerates the calculation. Content hashes identify the bytes and cannot authenticate the executor.

The grid validation supplies those computed child sums to extension-ring Newton interpolation, retains the specified Taylor coordinates at each node, and runs the guarded Hermite recovery for every output coordinate. The independent parent values only test equality. The four-wire two-clause case has 26 checked points across its two nodes. The eight-wire forced-assignment case has 50 checked points across its two nodes, including all 3,074 retained tuples. The previously distributed V3 transcript and the new grid run are separate records. Replaying the former does not add the latter's coverage to it.

| Mathematical object | Executable or proof | Scope exercised |
|---|---|---|
| Boolean cut and restricted tables | finite_reductions/boundary.py | Complete assignments at accepted cuts of explicit integer tables |
| Product of independent Boolean sums modulo 2^p | proofs/FiniteBoundaryReduction.lean and FiniteBoundaryContract.lean | All finite bit lengths and signed integer functions on the three sets of assignments |
| Mode and child coefficients | finite_reductions/recipe_point.py, child_recipe_check.py and the R8.2 independent oracles | Bounded certificate, scalar jet, at most eight parent wires |
| All-point finite recipe recovery | scripts/validate_r96_recipe_grid.py | Two fixed finite grids, 76 independently compared points |
| Recursion and re-execution | finite_reductions/boundary.py and inherited tapered_v4/recursor.py | Boolean cuts, optional finite Hermite pieces, bounded resource policy |

The Lean theorem assumes two functions with the displayed separated scopes. Its independently typed contract checks the exact modular equality. Its reported axiom dependencies are propext and Quot.sound. Connecting Python's particular port numbering, restriction code, dictionary and exact arithmetic to this Lean statement still requires executable refinement. Tests corrupt the cut children, tuple stream, group set, point result, proof statement and saved replay data.

## Source and outstanding proof obligations

All four packaged TeX files match the vendored files and the upstream pinned commit byte for byte. The manuscript's contraction step uses its own scheduled packing, complete mode expansion, group contractions and tapered recovery. The Boolean cut is a different finite reduction chosen for 12–16-wire experiments. The integrated 16-wire demonstration has a Boolean cut at the root and two scaled eight-wire Hermite pieces. The separate all-grid experiment evaluates the new recipe interpreter on its two fixed parents.

The finite evidence does not cover arbitrary input networks, 64 source-scheduled children at every recursive level, or a universal Cauchy/Hermite recurrence. Source scheduling requires u0 = floor(lambda/131072); a positive initial active value already requires extension degree 4 lambda >= 524288. The bounded source representation cannot admit that regime. Open obligations include the construction and identity for every eligible child, composition of creation precision across arbitrary depth, executable refinement, the outer count-preserving reduction and bit-time/peak-space analysis. The engine returns explicit inconclusive statuses for active source and theorem calls. See the [pinned contraction source](https://github.com/openai/math/blob/4eaee87548250b2682affda7d05d947c05554bae/preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026/build/quantitative-contraction.tex) and [upstream formalization scope](https://github.com/openai/math/blob/main/lean/docs/378.md).

## Resource interpretation

The outer cut can enumerate 2^|K| boundary masks. Each accepted mask constructs and checks both restricted graphs and recursively contracts them. The nested Hermite backend charges its own observed work and returns separate tuple, group and interpolation counters. Its calls include the piece root, which is also an outer visit. The outer call cap applies to boundary visits. Time and work budgets also apply to a nested piece. Certificate size guards and structural dimension caps bound accepted objects. Peak RSS in the measurements is the process-lifetime high-water mark. RSS, total allocated bytes, scalar-operation counts, wall time and bit complexity measure different things. There is no general bit-work or polynomial-space qualification.
