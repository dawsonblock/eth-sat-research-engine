# Formalization contract

The system's parser accepts only a deliberately limited propositional grammar:

```text
expression  := implication
implication := disjunction (('->' | '=>') implication)?
disjunction := conjunction (('|' | 'OR') conjunction)*
conjunction := unary (('&' | 'AND') unary)*
unary       := ('!' | '~' | 'NOT') unary | '(' expression ')' | TRUE | FALSE | IDENTIFIER
```

Premises and conclusions are strings in this language. There are no implicit quantifiers, probabilities, types, natural-language semantics, or hidden commonsense assumptions. Statements are treated as Boolean atoms with case-sensitive identifier spelling.

`/v1/formalize` exposes the CNF and primary variable mapping and explicitly returns a REVIEW_REQUIRED status. Count-preserving unique-extension invariants are documented. Any future English model integration must submit a typed, explicit reviewable formalization, not raw user text executed by the solver.
