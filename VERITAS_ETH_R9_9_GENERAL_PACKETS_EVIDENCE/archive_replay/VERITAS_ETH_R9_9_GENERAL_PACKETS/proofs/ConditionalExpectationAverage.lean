import Lean

/-!
Conditional-expectation averaging for the streaming realization of
`lem:tensor-packets` in `paper/quantitative-contraction.tex`.

This proves the exact finite algebraic identity once each ordered edge-pair
contribution is represented by a compatible coordinate-constraint vector and
its number of still-unknown comparisons.  The bridge from concrete graph
edge-pairs to `ConditionalPairTerm` is an executable/refinement obligation;
this file does not prove that bridge, the variance estimate, packet
construction, port loads, child contraction, or the asymptotic theorem.
-/

def sumBy {α : Type} : List α → (α → Nat) → Nat
  | [], _ => 0
  | x :: xs, f => f x + sumBy xs f

theorem sumBy_append {α : Type} (xs ys : List α) (f : α → Nat) :
    sumBy (xs ++ ys) f = sumBy xs f + sumBy ys f := by
  induction xs with
  | nil => simp [sumBy]
  | cons x xs ih => simp [sumBy, ih, Nat.add_assoc]

theorem sumBy_flatMap {α β : Type} (xs : List α) (g : α → List β) (f : β → Nat) :
    sumBy (xs.flatMap g) f = sumBy xs (fun x => sumBy (g x) f) := by
  induction xs with
  | nil => rfl
  | cons x xs ih =>
      simp only [List.flatMap_cons, sumBy_append, sumBy, ih]

theorem sumBy_map {α β : Type} (xs : List α) (g : α → β) (f : β → Nat) :
    sumBy (xs.map g) f = sumBy xs (fun x => f (g x)) := by
  induction xs with
  | nil => rfl
  | cons x xs ih => simp [sumBy, ih]

theorem sumBy_zero {α : Type} (xs : List α) : sumBy xs (fun _ => 0) = 0 := by
  induction xs with
  | nil => rfl
  | cons x xs ih => simp [sumBy, ih]

theorem sumBy_range_const (r k : Nat) :
    sumBy (List.range r) (fun _ => k) = r * k := by
  induction r with
  | zero => simp [List.range_zero, sumBy]
  | succ r ih =>
      rw [List.range_succ, sumBy_append]
      simp only [sumBy]
      rw [ih, Nat.succ_mul]
      simp

theorem sumBy_range_eq (r c k : Nat) :
    sumBy (List.range r) (fun x => if x == c then k else 0) =
      if c < r then k else 0 := by
  induction r with
  | zero => simp [List.range_zero, sumBy]
  | succ r ih =>
      rw [List.range_succ, sumBy_append]
      simp only [sumBy]
      by_cases h : c < r
      · have hne : r ≠ c := by omega
        rw [ih]
        have hnext : c < r + 1 := by omega
        simp [h, hne, hnext]
      · by_cases heq : c = r
        · subst c
          rw [ih]
          simp
        · have hgt : r < c := by omega
          have hne : r ≠ c := by omega
          have hnext : ¬ c < r + 1 := by omega
          rw [ih]
          simp [h, hne, hnext]

def labelWords (r : Nat) : Nat → List (List Nat)
  | 0 => [[]]
  | n + 1 => (List.range r).flatMap (fun x => (labelWords r n).map (fun w => x :: w))

def wordMatches : List (Option Nat) → List Nat → Bool
  | [], [] => true
  | none :: cs, _ :: xs => wordMatches cs xs
  | some c :: cs, x :: xs => (x == c) && wordMatches cs xs
  | _, _ => false

def wildcardCount : List (Option Nat) → Nat
  | [] => 0
  | none :: cs => wildcardCount cs + 1
  | some _ :: cs => wildcardCount cs

theorem countSatisfyingWords (r : Nat) (constraints : List (Option Nat))
    (hValid : ∀ c, some c ∈ constraints → c < r) :
    sumBy (labelWords r constraints.length)
      (fun w => if wordMatches constraints w then 1 else 0) =
      r ^ wildcardCount constraints := by
  induction constraints with
  | nil => simp [labelWords, wordMatches, sumBy, wildcardCount]
  | cons head tail ih =>
      cases head with
      | none =>
          simp only [List.length_cons, labelWords]
          rw [sumBy_flatMap]
          have hinner (x : Nat) :
              sumBy ((labelWords r tail.length).map (fun w => x :: w))
                (fun w => if wordMatches (none :: tail) w then 1 else 0) =
              sumBy (labelWords r tail.length)
                (fun w => if wordMatches tail w then 1 else 0) := by
            rw [sumBy_map]
            simp only [wordMatches]
            rfl
          let tailCount := sumBy (labelWords r tail.length)
            (fun w => if wordMatches tail w then 1 else 0)
          have hconstant : sumBy (List.range r) (fun x =>
              sumBy ((labelWords r tail.length).map (fun w => x :: w))
                (fun w => if wordMatches (none :: tail) w then 1 else 0)) =
              r * tailCount := by
            calc
              _ = sumBy (List.range r) (fun _ => tailCount) := by
                congr 1
                funext x
                exact hinner x
              _ = r * tailCount := sumBy_range_const r tailCount
          rw [hconstant]
          simp only [wildcardCount]
          have hTailValid : ∀ c, some c ∈ tail → c < r := by
            intro c hc
            apply hValid c
            simp [hc]
          have htail := ih hTailValid
          simp only [tailCount]
          rw [htail]
          simp [Nat.pow_succ, Nat.mul_comm]
      | some target =>
          have hTarget : target < r := hValid target (by simp)
          simp only [List.length_cons, labelWords]
          rw [sumBy_flatMap]
          have hinner (x : Nat) :
              sumBy ((labelWords r tail.length).map (fun w => x :: w))
                (fun w => if wordMatches (some target :: tail) w then 1 else 0) =
              (if x == target then
                sumBy (labelWords r tail.length)
                  (fun w => if wordMatches tail w then 1 else 0)
               else 0) := by
            rw [sumBy_map]
            simp only [wordMatches]
            by_cases hEq : x == target
            · simp [hEq]
            · have hFalse : (x == target) = false := Bool.eq_false_iff.mpr hEq
              simp [hFalse, sumBy_zero]
          let tailCount := sumBy (labelWords r tail.length)
            (fun w => if wordMatches tail w then 1 else 0)
          have hconstant : sumBy (List.range r) (fun x =>
              sumBy ((labelWords r tail.length).map (fun w => x :: w))
                (fun w => if wordMatches (some target :: tail) w then 1 else 0)) =
              tailCount := by
            calc
              _ = sumBy (List.range r) (fun x => if x == target then tailCount else 0) := by
                congr 1
                funext x
                exact hinner x
              _ = (if target < r then tailCount else 0) := sumBy_range_eq r target tailCount
              _ = tailCount := by simp [hTarget]
          rw [hconstant]
          simp only [wildcardCount]
          have hTailValid : ∀ c, some c ∈ tail → c < r := by
            intro c hc
            apply hValid c
            simp [hc]
          have htail := ih hTailValid
          simpa [tailCount] using htail

def fixedCount : List (Option Nat) → Nat
  | [] => 0
  | none :: cs => fixedCount cs
  | some _ :: cs => fixedCount cs + 1

theorem wildcard_fixed_count (cs : List (Option Nat)) :
    wildcardCount cs + fixedCount cs = cs.length := by
  induction cs with
  | nil => rfl
  | cons head tail ih =>
      cases head <;> simp only [wildcardCount, fixedCount, List.length_cons] <;> omega

theorem sumBy_if_constant {α : Type} (xs : List α) (p : α → Bool) (k : Nat) :
    sumBy xs (fun x => if p x then k else 0) =
      sumBy xs (fun x => if p x then 1 else 0) * k := by
  induction xs with
  | nil => simp [sumBy]
  | cons x xs ih =>
      simp only [sumBy]
      by_cases h : p x
      · simp [h, ih]
        rw [Nat.add_mul, Nat.one_mul]
      · simp [h, ih]

theorem constrained_pair_average (r a parentExp : Nat)
    (constraints : List (Option Nat))
    (hlen : constraints.length = a)
    (hValid : ∀ c, some c ∈ constraints → c < r) :
    sumBy (labelWords r a)
      (fun word => if wordMatches constraints word
        then r ^ (parentExp + fixedCount constraints) else 0) =
      r ^ a * r ^ parentExp := by
  rw [sumBy_if_constant]
  have hCount := countSatisfyingWords r constraints hValid
  have hCountA : sumBy (labelWords r a)
      (fun word => if wordMatches constraints word then 1 else 0) =
      r ^ wildcardCount constraints := by
    rw [← hlen]
    exact hCount
  rw [hCountA]
  have hcounts := wildcard_fixed_count constraints
  rw [hlen] at hcounts
  have hExp : wildcardCount constraints + (parentExp + fixedCount constraints) = a + parentExp := by omega
  calc
    _ = r ^ (wildcardCount constraints + (parentExp + fixedCount constraints)) := by
      rw [← Nat.pow_add]
    _ = r ^ (a + parentExp) := by rw [hExp]
    _ = r ^ a * r ^ parentExp := by rw [Nat.pow_add]

theorem sum_map_eq_sumBy {α : Type} (xs : List α) (f : α → Nat) :
    (xs.map f).sum = sumBy xs f := by
  induction xs with
  | nil => rfl
  | cons x xs ih => simp [sumBy, ih]

theorem labelWords_length (r a : Nat) : (labelWords r a).length = r ^ a := by
  induction a with
  | zero => simp [labelWords]
  | succ a ih =>
      unfold labelWords
      rw [List.length_flatMap]
      have hmap :
          List.map (fun x => ((labelWords r a).map (fun w => x :: w)).length) (List.range r) =
          List.map (fun _ => (labelWords r a).length) (List.range r) := by
        apply List.map_congr_left
        intro x hx
        simp
      rw [hmap, sum_map_eq_sumBy, sumBy_range_const, ih, Nat.pow_succ]
      ac_rfl

theorem sumBy_add {α : Type} (xs : List α) (f g : α → Nat) :
    sumBy xs (fun x => f x + g x) = sumBy xs f + sumBy xs g := by
  induction xs with
  | nil => rfl
  | cons x xs ih => simp [sumBy, ih, Nat.add_left_comm, Nat.add_comm]

theorem sumBy_swap {α β : Type} (xs : List α) (ys : List β) (f : α → β → Nat) :
    sumBy xs (fun x => sumBy ys (f x)) =
      sumBy ys (fun y => sumBy xs (fun x => f x y)) := by
  induction xs with
  | nil => simp [sumBy, sumBy_zero]
  | cons x xs ih =>
      simp only [sumBy]
      rw [ih, ← sumBy_add]

theorem sumBy_mul_left {α : Type} (xs : List α) (f : α → Nat) (c : Nat) :
    sumBy xs (fun x => c * f x) = c * sumBy xs f := by
  induction xs with
  | nil => simp [sumBy]
  | cons x xs ih => simp [sumBy, ih, Nat.mul_add]

theorem constrained_pair_average_coeff (r a parentExp coefficient : Nat)
    (constraints : List (Option Nat))
    (hlen : constraints.length = a)
    (hValid : ∀ c, some c ∈ constraints → c < r) :
    sumBy (labelWords r a)
      (fun word => if wordMatches constraints word
        then coefficient * r ^ (parentExp + fixedCount constraints) else 0) =
      r ^ a * (coefficient * r ^ parentExp) := by
  calc
    _ = sumBy (labelWords r a) (fun word => coefficient *
          (if wordMatches constraints word
            then r ^ (parentExp + fixedCount constraints) else 0)) := by
      congr 1
      funext word
      by_cases h : wordMatches constraints word <;> simp [h]
    _ = coefficient * sumBy (labelWords r a) (fun word =>
          if wordMatches constraints word
            then r ^ (parentExp + fixedCount constraints) else 0) :=
          sumBy_mul_left _ _ _
    _ = coefficient * (r ^ a * r ^ parentExp) := by
      rw [constrained_pair_average r a parentExp constraints hlen hValid]
    _ = r ^ a * (coefficient * r ^ parentExp) := by
      ac_rfl

structure ConditionalPairTerm where
  constraints : Option (List (Option Nat))
  parentUnknown : Nat
  coefficient : Nat
  deriving Repr, DecidableEq

def pairTermParent (r a : Nat) (term : ConditionalPairTerm) : Nat :=
  match term.constraints with
  | none => 0
  | some _ => term.coefficient * (r ^ (2 * a) / r ^ term.parentUnknown)

def pairTermCandidate (r a : Nat) (term : ConditionalPairTerm) (word : List Nat) : Nat :=
  match term.constraints with
  | none => 0
  | some constraints =>
      if wordMatches constraints word then
        term.coefficient * (r ^ (2 * a) / r ^ (term.parentUnknown - fixedCount constraints))
      else 0

theorem pow_div_eq_pow_sub (r total exponent : Nat)
    (hr : 0 < r) (hexponent : exponent ≤ total) :
    r ^ total / r ^ exponent = r ^ (total - exponent) := by
  have hpos : 0 < r ^ exponent := Nat.pow_pos hr
  have hmul : r ^ total = r ^ (total - exponent) * r ^ exponent :=
    (Nat.pow_sub_mul_pow r hexponent).symm
  exact Nat.div_eq_of_eq_mul_left hpos hmul

theorem conditional_pair_term_average (r a : Nat) (term : ConditionalPairTerm)
    (hr : 0 < r)
    (hactive : ∀ cs, term.constraints = some cs →
      cs.length = a ∧ fixedCount cs ≤ term.parentUnknown ∧
      term.parentUnknown ≤ 2 * a ∧
      (∀ c, some c ∈ cs → c < r)) :
    sumBy (labelWords r a) (pairTermCandidate r a term) =
      r ^ a * pairTermParent r a term := by
  cases hcs : term.constraints with
  | none =>
      change sumBy (labelWords r a) (fun word => pairTermCandidate r a term word) =
        r ^ a * pairTermParent r a term
      have hfn : (fun word => pairTermCandidate r a term word) = (fun _ => 0) := by
        funext word
        simp [pairTermCandidate, hcs]
      rw [hfn]
      simp [pairTermParent, hcs, sumBy_zero]
  | some cs =>
      obtain ⟨hlen, hfixed, hunknown, hvalid⟩ := hactive cs hcs
      change sumBy (labelWords r a) (fun word => pairTermCandidate r a term word) =
        r ^ a * pairTermParent r a term
      have hfn : (fun word => pairTermCandidate r a term word) =
          (fun word => if wordMatches cs word then
            term.coefficient * (r ^ (2 * a) /
              r ^ (term.parentUnknown - fixedCount cs)) else 0) := by
        funext word
        simp [pairTermCandidate, hcs]
      have hparent := pow_div_eq_pow_sub r (2 * a) term.parentUnknown hr hunknown
      have hchild := pow_div_eq_pow_sub r (2 * a)
        (term.parentUnknown - fixedCount cs) hr (by omega)
      have hchildFn :
          (fun word => if wordMatches cs word then
            term.coefficient * (r ^ (2 * a) /
              r ^ (term.parentUnknown - fixedCount cs)) else 0) =
          (fun word => if wordMatches cs word then
            term.coefficient * r ^ (2 * a - (term.parentUnknown - fixedCount cs)) else 0) := by
        funext word
        split <;> simp [hchild]
      rw [hfn, hchildFn]
      simp only [pairTermParent, hcs]
      rw [hparent]
      have hexp : 2 * a - (term.parentUnknown - fixedCount cs) =
          (2 * a - term.parentUnknown) + fixedCount cs := by omega
      rw [hexp]
      exact constrained_pair_average_coeff r a (2 * a - term.parentUnknown)
        term.coefficient cs hlen hvalid

theorem sumBy_congr {α : Type} (xs : List α) (f g : α → Nat)
    (h : ∀ x, x ∈ xs → f x = g x) : sumBy xs f = sumBy xs g := by
  induction xs with
  | nil => rfl
  | cons x xs ih =>
      have hx := h x (by simp)
      have htail : ∀ y, y ∈ xs → f y = g y := by
        intro y hy
        exact h y (by simp [hy])
      simp [sumBy, hx, ih htail]

theorem conditional_pair_sum_average (r a : Nat) (terms : List ConditionalPairTerm)
    (hr : 0 < r)
    (hterms : ∀ term, term ∈ terms → ∀ cs, term.constraints = some cs →
      cs.length = a ∧ fixedCount cs ≤ term.parentUnknown ∧
      term.parentUnknown ≤ 2 * a ∧
      (∀ c, some c ∈ cs → c < r)) :
    sumBy (labelWords r a) (fun word => sumBy terms (fun term =>
      pairTermCandidate r a term word)) =
      r ^ a * sumBy terms (pairTermParent r a) := by
  rw [sumBy_swap]
  calc
    _ = sumBy terms (fun term => r ^ a * pairTermParent r a term) := by
      apply sumBy_congr
      intro term hin
      exact conditional_pair_term_average r a term hr (hterms term hin)
    _ = r ^ a * sumBy terms (pairTermParent r a) := sumBy_mul_left _ _ _

def conditionalScoreCandidate (base r a : Nat)
    (terms : List ConditionalPairTerm) (word : List Nat) : Nat :=
  base + sumBy terms (fun term => pairTermCandidate r a term word)

def conditionalScoreParent (base r a : Nat)
    (terms : List ConditionalPairTerm) : Nat :=
  base + sumBy terms (pairTermParent r a)

theorem sumBy_constant {α : Type} (xs : List α) (c : Nat) :
    sumBy xs (fun _ => c) = xs.length * c := by
  induction xs with
  | nil => simp [sumBy]
  | cons x xs ih =>
      simp only [sumBy, List.length_cons]
      rw [ih, Nat.succ_mul]
      omega

inductive PairComparison where
  | resolved
  | unresolved
  | candidate (target : Nat)
  | mismatch
  deriving Repr, DecidableEq

abbrev PairCoordinate := PairComparison × PairComparison

def coordinateConstraint : PairCoordinate → Option Nat
  | (.candidate x, _) => some x
  | (_, .candidate y) => some y
  | _ => none

def comparisonUnknown : PairComparison → Nat
  | .unresolved => 1
  | .candidate _ => 1
  | _ => 0

def coordinateUnknown (p : PairCoordinate) : Nat :=
  comparisonUnknown p.1 + comparisonUnknown p.2

def coordinateFixed (p : PairCoordinate) : Nat :=
  match coordinateConstraint p with
  | none => 0
  | some _ => 1

def coordinateIsValid (r : Nat) (p : PairCoordinate) : Prop :=
  match p.1, p.2 with
  | .mismatch, _ => False
  | _, .mismatch => False
  | .candidate _, .candidate _ => False
  | .candidate x, _ => x < r
  | _, .candidate y => y < r
  | _, _ => True

def constraintsFromCoordinates : List PairCoordinate → List (Option Nat)
  | [] => []
  | p :: ps => coordinateConstraint p :: constraintsFromCoordinates ps

def pairUnknownComparisons (ps : List PairCoordinate) : Nat :=
  sumBy ps coordinateUnknown

def pairTermOfCoordinates (ps : List PairCoordinate) : ConditionalPairTerm :=
  { constraints := some (constraintsFromCoordinates ps)
    parentUnknown := pairUnknownComparisons ps
    coefficient := 2 }

theorem coordinate_fixed_le_unknown (r : Nat) (p : PairCoordinate)
    (hvalid : coordinateIsValid r p) : coordinateFixed p ≤ coordinateUnknown p := by
  cases p with
  | mk left right =>
      cases left <;> cases right <;>
        simp [coordinateFixed, coordinateConstraint, coordinateUnknown,
          comparisonUnknown, coordinateIsValid] at * <;> omega

theorem coordinate_unknown_le_two (p : PairCoordinate) : coordinateUnknown p ≤ 2 := by
  cases p with
  | mk left right => cases left <;> cases right <;>
      simp [coordinateUnknown, comparisonUnknown] <;> omega

theorem sumBy_le_of_pointwise {α : Type} (xs : List α) (f g : α → Nat)
    (h : ∀ x, x ∈ xs → f x ≤ g x) : sumBy xs f ≤ sumBy xs g := by
  induction xs with
  | nil => simp [sumBy]
  | cons x xs ih =>
      have hx := h x (by simp)
      have htail : ∀ y, y ∈ xs → f y ≤ g y := by
        intro y hy
        exact h y (by simp [hy])
      have hsum := ih htail
      simp only [sumBy]
      omega

theorem constraints_length (ps : List PairCoordinate) :
    (constraintsFromCoordinates ps).length = ps.length := by
  induction ps with
  | nil => rfl
  | cons p ps ih => simp [constraintsFromCoordinates, ih]

theorem fixedCount_constraints_eq_sum (ps : List PairCoordinate) :
    fixedCount (constraintsFromCoordinates ps) = sumBy ps coordinateFixed := by
  induction ps with
  | nil => rfl
  | cons p ps ih =>
      change fixedCount (coordinateConstraint p :: constraintsFromCoordinates ps) =
        coordinateFixed p + sumBy ps coordinateFixed
      cases h : coordinateConstraint p <;>
        simp [fixedCount, coordinateFixed, h, ih, Nat.add_comm]

theorem pair_unknown_le_twice_length (ps : List PairCoordinate) :
    pairUnknownComparisons ps ≤ 2 * ps.length := by
  unfold pairUnknownComparisons
  calc
    sumBy ps coordinateUnknown ≤ sumBy ps (fun _ => 2) :=
      sumBy_le_of_pointwise ps coordinateUnknown (fun _ => 2)
        (by intro p hp; exact coordinate_unknown_le_two p)
    _ = ps.length * 2 := sumBy_constant ps 2
    _ = 2 * ps.length := Nat.mul_comm _ _

theorem pair_fixed_le_unknown (r : Nat) (ps : List PairCoordinate)
    (hvalid : ∀ p, p ∈ ps → coordinateIsValid r p) :
    fixedCount (constraintsFromCoordinates ps) ≤ pairUnknownComparisons ps := by
  rw [fixedCount_constraints_eq_sum]
  unfold pairUnknownComparisons
  exact sumBy_le_of_pointwise ps coordinateFixed coordinateUnknown
    (by intro p hp; exact coordinate_fixed_le_unknown r p (hvalid p hp))

theorem pair_constraints_symbols_valid (r : Nat) (ps : List PairCoordinate)
    (hvalid : ∀ p, p ∈ ps → coordinateIsValid r p) :
    ∀ c, some c ∈ constraintsFromCoordinates ps → c < r := by
  intro c hc
  induction ps with
  | nil => simp [constraintsFromCoordinates] at hc
  | cons p ps ih =>
      simp only [constraintsFromCoordinates, List.mem_cons] at hc
      rcases hc with hc | hc
      · have hp := hvalid p (by simp)
        cases p with
        | mk left right =>
            cases left <;> cases right <;>
              simp_all [coordinateConstraint, coordinateIsValid]
      · apply ih
        · intro q hq
          exact hvalid q (by simp [hq])
        · exact hc

theorem coordinate_pair_term_average (r a : Nat) (ps : List PairCoordinate)
    (hr : 0 < r) (hlen : ps.length = a)
    (hvalid : ∀ p, p ∈ ps → coordinateIsValid r p) :
    sumBy (labelWords r a) (pairTermCandidate r a (pairTermOfCoordinates ps)) =
      r ^ a * pairTermParent r a (pairTermOfCoordinates ps) := by
  have hlen' : (constraintsFromCoordinates ps).length = a := by
    rw [constraints_length, hlen]
  have hfixed := pair_fixed_le_unknown r ps hvalid
  have hunknown' := pair_unknown_le_twice_length ps
  have hunknown : pairUnknownComparisons ps ≤ 2 * a := by
    rw [← hlen]
    exact hunknown'
  have hsymbols := pair_constraints_symbols_valid r ps hvalid
  have hactive : ∀ cs,
      (pairTermOfCoordinates ps).constraints = some cs →
      cs.length = a ∧ fixedCount cs ≤ (pairTermOfCoordinates ps).parentUnknown ∧
      (pairTermOfCoordinates ps).parentUnknown ≤ 2 * a ∧
      (∀ c, some c ∈ cs → c < r) := by
    intro cs hcs
    injection hcs with hcs
    subst cs
    exact ⟨hlen', hfixed, hunknown, hsymbols⟩
  exact conditional_pair_term_average r a (pairTermOfCoordinates ps) hr hactive

theorem coordinate_pair_sum_average (r a : Nat)
    (pairCoordinates : List (List PairCoordinate))
    (hr : 0 < r)
    (hlen : ∀ ps, ps ∈ pairCoordinates → ps.length = a)
    (hvalid : ∀ ps, ps ∈ pairCoordinates → ∀ p, p ∈ ps → coordinateIsValid r p) :
    sumBy (labelWords r a) (fun word => sumBy pairCoordinates (fun ps =>
      pairTermCandidate r a (pairTermOfCoordinates ps) word)) =
      r ^ a * sumBy pairCoordinates (fun ps =>
        pairTermParent r a (pairTermOfCoordinates ps)) := by
  rw [sumBy_swap]
  calc
    _ = sumBy pairCoordinates (fun ps => r ^ a *
          pairTermParent r a (pairTermOfCoordinates ps)) := by
      apply sumBy_congr
      intro ps hps
      exact coordinate_pair_term_average r a ps hr (hlen ps hps)
        (hvalid ps hps)
    _ = r ^ a * sumBy pairCoordinates (fun ps =>
          pairTermParent r a (pairTermOfCoordinates ps)) := sumBy_mul_left _ _ _

theorem coordinate_score_average (r a base : Nat)
    (pairCoordinates : List (List PairCoordinate))
    (hr : 0 < r)
    (hlen : ∀ ps, ps ∈ pairCoordinates → ps.length = a)
    (hvalid : ∀ ps, ps ∈ pairCoordinates → ∀ p, p ∈ ps → coordinateIsValid r p) :
    sumBy (labelWords r a) (fun word => base + sumBy pairCoordinates (fun ps =>
      pairTermCandidate r a (pairTermOfCoordinates ps) word)) =
      r ^ a * (base + sumBy pairCoordinates (fun ps =>
        pairTermParent r a (pairTermOfCoordinates ps))) := by
  calc
    _ = sumBy (labelWords r a) (fun _ => base) +
          sumBy (labelWords r a) (fun word => sumBy pairCoordinates (fun ps =>
            pairTermCandidate r a (pairTermOfCoordinates ps) word)) := by
      rw [sumBy_add]
    _ = r ^ a * base + r ^ a * sumBy pairCoordinates (fun ps =>
          pairTermParent r a (pairTermOfCoordinates ps)) := by
      rw [sumBy_constant, labelWords_length,
        coordinate_pair_sum_average r a pairCoordinates hr hlen hvalid]
    _ = r ^ a * (base + sumBy pairCoordinates (fun ps =>
          pairTermParent r a (pairTermOfCoordinates ps))) := by
      rw [Nat.mul_add]

theorem conditional_score_average (r a base : Nat)
    (terms : List ConditionalPairTerm)
    (hr : 0 < r)
    (hterms : ∀ term, term ∈ terms → ∀ cs, term.constraints = some cs →
      cs.length = a ∧ fixedCount cs ≤ term.parentUnknown ∧
      term.parentUnknown ≤ 2 * a ∧
      (∀ c, some c ∈ cs → c < r)) :
    sumBy (labelWords r a) (conditionalScoreCandidate base r a terms) =
      r ^ a * conditionalScoreParent base r a terms := by
  calc
    sumBy (labelWords r a) (fun word => conditionalScoreCandidate base r a terms word) =
        sumBy (labelWords r a) (fun _ => base) +
          sumBy (labelWords r a) (fun word => sumBy terms (fun term =>
            pairTermCandidate r a term word)) := by
      change sumBy (labelWords r a) (fun word => base +
        sumBy terms (fun term => pairTermCandidate r a term word)) = _
      rw [sumBy_add]
    _ = r ^ a * base + r ^ a * sumBy terms (pairTermParent r a) := by
      rw [sumBy_constant, labelWords_length,
        conditional_pair_sum_average r a terms hr hterms]
    _ = r ^ a * conditionalScoreParent base r a terms := by
      simp [conditionalScoreParent, Nat.mul_add]

#print axioms countSatisfyingWords
#print axioms constrained_pair_average
#print axioms conditional_pair_term_average
#print axioms conditional_pair_sum_average
#print axioms conditional_score_average
#print axioms coordinate_pair_term_average
#print axioms coordinate_pair_sum_average
#print axioms coordinate_score_average
