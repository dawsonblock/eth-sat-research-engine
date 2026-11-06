import Lean

namespace D3OccurrenceRank

variable {α : Type} [DecidableEq α]

/-- Number of occurrences of a class in a prefix, preserving multiplicity. -/
def countClass (target : α) : List α → Nat
  | [] => 0
  | c :: cs => (if c = target then 1 else 0) + countClass target cs

/-- The occurrence rank is zero based and counts only earlier entries of the
same class. The input list represents the actual ordered edge occurrences. -/
def encode (classes : List α) (edgeId : Nat) : Option (α × Nat) :=
  (classes[edgeId]?).map fun c => (c, countClass c (classes.take edgeId))

/-- Locate the requested occurrence of a class, returning its edge index. -/
def decode (target : α) : List α → Nat → Option Nat
  | [], _ => none
  | c :: cs, rank =>
      if c = target then
        match rank with
        | 0 => some 0
        | n + 1 => (decode target cs n).map Nat.succ
      else (decode target cs rank).map Nat.succ

theorem decode_prefix_rank (classes : List α) (edgeId : Nat) (c : α)
    (h : classes[edgeId]? = some c) :
    decode c classes (countClass c (classes.take edgeId)) = some edgeId := by
  induction classes generalizing edgeId with
  | nil => simp at h
  | cons head tail ih =>
    cases edgeId with
    | zero =>
      simp only [List.getElem?_cons_zero, Option.some.injEq] at h
      subst c
      simp [decode, countClass]
    | succ i =>
      have ht : tail[i]? = some c := by simpa using h
      have hrec := ih i ht
      by_cases heq : head = c
      · subst head
        simp [decode, countClass, Nat.one_add, hrec]
      · simp [decode, countClass, heq, hrec]

theorem decode_encode (classes : List α) (edgeId : Nat) (c : α) (rank : Nat)
    (h : encode classes edgeId = some (c, rank)) :
    decode c classes rank = some edgeId := by
  unfold encode at h
  cases hc : classes[edgeId]? with
  | none => simp [hc] at h
  | some x =>
    simp [hc] at h
    rcases h with ⟨rfl, rfl⟩
    exact decode_prefix_rank classes edgeId x hc

theorem encode_spec (classes : List α) (edgeId : Nat) (c : α) (rank : Nat)
    (h : encode classes edgeId = some (c, rank)) :
    classes[edgeId]? = some c ∧ rank = countClass c (classes.take edgeId) := by
  unfold encode at h
  cases hc : classes[edgeId]? with
  | none => simp [hc] at h
  | some x =>
    simp [hc] at h
    rcases h with ⟨rfl, rfl⟩
    exact ⟨rfl, rfl⟩

theorem encode_succ (head : α) (tail : List α) (i : Nat) :
    encode (head :: tail) (i + 1) =
      (encode tail i).map (fun p =>
        (p.1, if head = p.1 then p.2 + 1 else p.2)) := by
  cases hc : tail[i]? with
  | none => simp [encode, hc]
  | some c =>
    by_cases heq : head = c <;>
      simp [encode, hc, countClass, heq, Nat.add_comm]

/-- Decoding cannot invent an edge: it returns exactly the entry whose
class and earlier-occurrence rank equal the requested occupied slot. -/
theorem encode_decode (classes : List α) (target : α) (rank edgeId : Nat)
    (h : decode target classes rank = some edgeId) :
    encode classes edgeId = some (target, rank) := by
  induction classes generalizing rank edgeId with
  | nil => simp [decode] at h
  | cons head tail ih =>
    by_cases heq : head = target
    · cases rank with
      | zero =>
        simp [decode, heq] at h
        subst edgeId
        subst head
        simp [encode, countClass]
      | succ rank =>
        cases hd : decode target tail rank with
        | none => simp [decode, heq, hd] at h
        | some i =>
          simp [decode, heq, hd] at h
          subst edgeId
          have hrec := ih rank i hd
          simp [encode_succ, hrec, heq]
    · cases hd : decode target tail rank with
      | none => simp [decode, heq, hd] at h
      | some i =>
        simp [decode, heq, hd] at h
        subst edgeId
        have hrec := ih rank i hd
        simp [encode_succ, hrec, heq]

theorem encode_injective (classes : List α) (left right : Nat) (address : α × Nat)
    (hl : encode classes left = some address)
    (hr : encode classes right = some address) : left = right := by
  rcases address with ⟨c, rank⟩
  have hleft := decode_encode classes left c rank hl
  have hright := decode_encode classes right c rank hr
  rw [hleft] at hright
  exact Option.some.inj hright

theorem encode_exists (classes : List α) (edgeId : Nat)
    (h : edgeId < classes.length) : ∃ address, encode classes edgeId = some address := by
  refine ⟨(classes[edgeId], countClass classes[edgeId] (classes.take edgeId)), ?_⟩
  simp [encode, List.getElem?_eq_getElem h]

theorem decode_in_bounds (classes : List α) (c : α) (rank edgeId : Nat)
    (h : decode c classes rank = some edgeId) : edgeId < classes.length := by
  have henc := encode_decode classes c rank edgeId h
  by_cases hbound : edgeId < classes.length
  · exact hbound
  · have hout : classes[edgeId]? = none := List.getElem?_eq_none_iff.mpr (by omega)
    simp [encode, hout] at henc

/-- A real edge's prefix rank is strictly below the load of its class. -/
theorem prefix_rank_lt_load (classes : List α) (edgeId : Nat) (c : α)
    (h : classes[edgeId]? = some c) :
    countClass c (classes.take edgeId) < countClass c classes := by
  induction classes generalizing edgeId with
  | nil => simp at h
  | cons head tail ih =>
    cases edgeId with
    | zero =>
      simp only [List.getElem?_cons_zero, Option.some.injEq] at h
      subst head
      simp [countClass]
      omega
    | succ i =>
      have ht : tail[i]? = some c := by simpa using h
      have hlt := ih i ht
      by_cases heq : head = c <;>
        simp [countClass, heq] at hlt ⊢ <;> omega

example : encode [3, 5, 3, 3] 2 = some (3, 1) := by decide
example : decode 3 [3, 5, 3, 3] 2 = some 3 := by decide
example : decode 3 [3, 5, 3, 3] 3 = none := by decide

#print axioms decode_prefix_rank
#print axioms decode_encode
#print axioms encode_spec
#print axioms encode_succ
#print axioms encode_decode
#print axioms encode_injective
#print axioms encode_exists
#print axioms decode_in_bounds
#print axioms prefix_rank_lt_load

end D3OccurrenceRank
