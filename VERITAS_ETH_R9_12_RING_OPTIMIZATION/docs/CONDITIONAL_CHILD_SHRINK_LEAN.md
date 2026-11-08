# Lean check of the conditional child-size calculation

`proofs/ConditionalChildShrink.lean` formalizes the elementary arithmetic
step used in the group-load argument. If each of a group's row and column
loads is at most `3M/64` and `M>0`, then their sum is at most `3M/32`
and is strictly less than `M/8`. Equivalently the hypotheses and conclusions
are written with integer multiplication, so there is no rounding ambiguity.

This is a **conditional arithmetic proof**. It assumes the port-load
inequalities and that the relevant child size is the sum of the two loads.
It does not construct or verify a packing, prove this equality for every
program-generated child, establish parent-to-child tensor identities, or
prove the uniform running time or space bound. It is not a replay of the
OpenAI Comparator proof.

The file was checked with the official Lean 4.34.1 Linux ARM64 distribution,
commit `5045d0056413266e57c625dcd7c365b10e377c52`, in an isolated
network-disabled container. The release archive's SHA-256 was
`fdb974c2cdb4627e090d5d4007b913e09d13c4868720fb5594e22808b3de9e37`.
The checked proof file's SHA-256 was
`61a649c876a4261c62a25410ac00ac24e05ee8f3edbae93b20c159e4e9f62360`.
With that Lean version installed, reproduce the check from the project root:

```sh
lean proofs/ConditionalChildShrink.lean
```

The file prints the axioms Lean associates with each theorem; it contains no
`sorry` or user-declared axioms. The check reported only Lean's standard
`propext` and `Quot.sound` for the included lemmas. The full upstream
Comparator challenge requires additional source, dependencies, and review;
it was not run during this check.
