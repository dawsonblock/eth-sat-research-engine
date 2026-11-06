import D3FullPacketModel
import D3CandidateOrder

/-! Independently enumerated finite domains, including empty padded classes.
The address enumeration is by canonical patterns, packet indices and slots;
it is NOT defined as the image of the directed-class enumeration. -/
namespace D3FinitePacketDomain
open D3FullPacketModel D3GlobalPacketAddress

def allPairs (r : Nat) := (List.range r).flatMap fun x => (List.range r).map fun y => (x,y)
def classes (r : Nat) : Nat → List SymbolClass
  | 0 => [[]]
  | a+1 => (allPairs r).flatMap fun p => (classes r a).map fun c => p::c

def positions (r a H : Nat) : List (SymbolClass × Nat) :=
  (classes r a).flatMap fun c => (List.range H).map fun q => (c,q)

def patterns (r a : Nat) : List SymbolClass :=
  (classes r a).filter fun c => c.all fun p => decide (p.1 ≤ p.2)

def addresses (r a H : Nat) : List Address :=
  (patterns r a).flatMap fun pat =>
    (List.range (H / 2 ^ d3EqualCount (equalMask pat))).flatMap fun j =>
      (List.range (2^a)).map fun k => ⟨pat,j,k⟩

def totalEncode (p : SymbolClass × Nat) : Address :=
  (encodeClass p.1 p.2).getD ⟨[],0,0⟩

theorem totalEncode_spec (p : SymbolClass × Nat) :
    encodeClass p.1 p.2 = some (totalEncode p) := by
  obtain ⟨address, h⟩ := encodeClass_exists p.1 p.2
  simp [totalEncode,h]

theorem totalEncode_inverse (p : SymbolClass × Nat) : decodeClass (totalEncode p) = p := by
  exact decodeClass_encodeClass p.1 p.2 _ (totalEncode_spec p)

theorem totalEncode_injective (p q : SymbolClass × Nat) (h : totalEncode p = totalEncode q) : p = q := by
  have := congrArg decodeClass h
  simpa [totalEncode_inverse] using this

theorem pair_mem (r : Nat) (p : Nat × Nat) : p ∈ allPairs r ↔ p.1 < r ∧ p.2 < r := by
  cases p; simp [allPairs]

theorem classes_mem (r a : Nat) (c : SymbolClass) :
    c ∈ classes r a ↔ c.length = a ∧ BoundedClass r c := by
  induction a generalizing c with
  | zero => cases c <;> simp [classes, BoundedClass]
  | succ a ih =>
    cases c with
    | nil => simp [classes, BoundedClass]
    | cons p c =>
      simp [classes, List.mem_flatMap, List.mem_map, ih, pair_mem, BoundedClass]
      constructor
      · rintro ⟨hp, hl, ht⟩; exact ⟨hl, hp, ht⟩
      · rintro ⟨hl, hp, ht⟩; exact ⟨hp, hl, ht⟩

theorem classes_length (r a : Nat) : (classes r a).length = (r*r)^a := by
  have hp : (allPairs r).length = r*r := by
    simp [allPairs, List.length_flatMap, List.map_const', List.sum_replicate_nat]
  induction a with
  | zero => simp [classes]
  | succ a ih =>
    simp [classes, List.length_flatMap, ih, List.map_const', List.sum_replicate_nat, hp,
      Nat.pow_succ, Nat.mul_comm]

/-- A general disjoint-fibre lemma; injectivity explicitly includes the outer tag. -/
theorem nodup_fibres {α β γ : Type} (xs : List α) (ys : α → List β) (f : α → β → γ)
    (hx : xs.Nodup) (hy : ∀ x, x ∈ xs → (ys x).Nodup)
    (hinj : ∀ x ∈ xs, ∀ y ∈ ys x, ∀ x' ∈ xs, ∀ y' ∈ ys x',
      f x y = f x' y' → x=x' ∧ y=y') :
    (xs.flatMap fun x => (ys x).map (f x)).Nodup := by
  rw [List.nodup_iff_pairwise_ne, List.pairwise_flatMap]
  constructor
  · intro x hxm
    rw [List.pairwise_map]
    exact List.Pairwise.imp_of_mem (fun hym hzm hne heq =>
      hne (hinj x hxm _ hym x hxm _ hzm heq).2) (hy x hxm)
  · apply List.Pairwise.imp_of_mem _ hx
    intro x z hxm hzm hne p hp q hq heq
    obtain ⟨y,hy,rfl⟩ := List.mem_map.mp hp
    obtain ⟨w,hw,rfl⟩ := List.mem_map.mp hq
    exact hne (hinj x hxm y hy z hzm w hw heq).1


theorem allPairs_nodup (r : Nat) : (allPairs r).Nodup := by
  apply nodup_fibres _ _ _ List.nodup_range (fun _ _ => List.nodup_range)
  intro x hx y hy z hz w hw heq
  exact Prod.mk.inj heq

theorem classes_nodup (r a : Nat) : (classes r a).Nodup := by
  induction a with
  | zero => simp [classes]
  | succ a ih =>
    apply nodup_fibres _ _ _ (allPairs_nodup r) (fun _ _ => ih)
    intro x hx y hy z hz w hw heq
    exact List.cons.inj heq

theorem positions_mem (r a H : Nat) (p : SymbolClass × Nat) :
    p ∈ positions r a H ↔ p.1.length = a ∧ BoundedClass r p.1 ∧ p.2 < H := by
  simp only [positions, List.mem_flatMap, List.mem_map, List.mem_range]
  constructor
  · rintro ⟨c,hc,q,hq,he⟩
    subst p
    exact ⟨((classes_mem r a c).1 hc).1, ((classes_mem r a c).1 hc).2, hq⟩
  · rintro ⟨hl,hb,hq⟩
    exact ⟨p.1,(classes_mem r a p.1).2 ⟨hl,hb⟩,p.2,hq,rfl⟩

theorem positions_nodup (r a H : Nat) : (positions r a H).Nodup := by
  apply nodup_fibres _ _ _ (classes_nodup r a) (fun _ _ => List.nodup_range)
  intro x hx y hy z hz w hw heq
  exact Prod.mk.inj heq

theorem positions_length (r a H : Nat) : (positions r a H).length = r^(2*a)*H := by
  simp [positions, List.length_flatMap, List.map_const', List.sum_replicate_nat, classes_length]
  rw [Nat.pow_mul, Nat.pow_two]

theorem patterns_mem (r a : Nat) (p : SymbolClass) :
    p ∈ patterns r a ↔ p.length=a ∧ CanonicalPattern p ∧ (∀ pair ∈ p, pair.2 < r) := by
  simp only [patterns, List.mem_filter, classes_mem, List.all_eq_true, decide_eq_true_eq]
  unfold BoundedClass CanonicalPattern
  constructor
  · rintro ⟨⟨hl,hb⟩,hc⟩
    exact ⟨hl,hc,fun pair hp => (hb pair hp).2⟩
  · rintro ⟨hl,hc,hb⟩
    exact ⟨⟨hl,fun pair hp => ⟨Nat.lt_of_le_of_lt (hc pair hp) (hb pair hp),hb pair hp⟩⟩,hc⟩

theorem addresses_mem (r a H : Nat) (ad : Address) :
    ad ∈ addresses r a H ↔ ValidPaddedAddress a H ad ∧ (∀ pair ∈ ad.pattern, pair.2 < r) := by
  simp only [addresses, List.mem_flatMap, List.mem_map, List.mem_range]
  constructor
  · rintro ⟨pat,hp,j,hj,k,hk,he⟩
    subst ad
    obtain ⟨hl,hc,hb⟩ := (patterns_mem r a pat).1 hp
    exact ⟨⟨hl,hc,hj,hk⟩,hb⟩
  · rintro ⟨⟨hl,hc,hj,hk⟩,hb⟩
    exact ⟨ad.pattern,(patterns_mem r a ad.pattern).2 ⟨hl,hc,hb⟩,
      ad.packet,hj,ad.slot,hk,rfl⟩

theorem addresses_nodup (r a H : Nat) : (addresses r a H).Nodup := by
  -- First enumerate each (pattern, packet) tag, then its slot fibre.
  have hpat : (patterns r a).Nodup := (classes_nodup r a).filter _
  have htags := nodup_fibres (patterns r a)
    (fun pat => List.range (H / 2 ^ d3EqualCount (equalMask pat)))
    (fun pat j => (pat,j)) hpat (fun _ _ => List.nodup_range)
    (by intro x hx y hy z hz w hw heq; exact Prod.mk.inj heq)
  have h := nodup_fibres _ (fun _ => List.range (2^a))
    (fun p k => Address.mk p.1 p.2 k) htags (fun _ _ => List.nodup_range)
    (by intro x hx y hy z hz w hw heq
        cases x; cases z
        simp only [Address.mk.injEq] at heq
        exact ⟨by simp [heq.1,heq.2.1],heq.2.2⟩)
  simpa [addresses, List.flatMap_assoc, List.flatMap_map, List.map_map, Function.comp_def] using h

theorem bounded_of_pattern (r : Nat) (c : SymbolClass)
    (h : ∀ pair ∈ patternOfClass c, pair.2 < r) : BoundedClass r c := by
  induction c with
  | nil => simp [BoundedClass]
  | cons p c ih =>
    have hp := h (min p.1 p.2, max p.1 p.2) (by simp [patternOfClass])
    have hc := ih (fun pair hm => h pair (by simp [patternOfClass,hm]))
    intro pair hm
    cases hm with
    | head => exact ⟨Nat.lt_of_le_of_lt (Nat.le_max_left _ _) hp,
                       Nat.lt_of_le_of_lt (Nat.le_max_right _ _) hp⟩
    | tail _ ht => exact hc pair ht

theorem forward_mem (r a H : Nat) (hpad : 2^a ∣ H) (p : SymbolClass × Nat)
    (hp : p ∈ positions r a H) : totalEncode p ∈ addresses r a H := by
  obtain ⟨hl,hb,hoff⟩ := (positions_mem r a H p).1 hp
  obtain ⟨ad,he,hv,hd⟩ := paddedClass_forward p.1 p.2 H (by simpa [hl] using hpad) hoff
  have ht : ad = totalEncode p := Option.some.inj (he.symm.trans (totalEncode_spec p))
  subst ad
  apply (addresses_mem r a H _).2
  refine ⟨by simpa [hl] using hv, ?_⟩
  rw [encodeClass_pattern _ _ _ (totalEncode_spec p)]
  exact pattern_bounded r p.1 hb

theorem reverse_mem (r a H : Nat) (hpad : 2^a ∣ H) (ad : Address)
    (ha : ad ∈ addresses r a H) : decodeClass ad ∈ positions r a H ∧ totalEncode (decodeClass ad) = ad := by
  obtain ⟨hv,hb⟩ := (addresses_mem r a H ad).1 ha
  obtain ⟨hoff,he⟩ := paddedClass_reverse a H ad hpad hv
  have hpat := encodeClass_pattern _ _ _ he
  have hlen := class_pattern_length (decodeClass ad).1
  simp only [equalMask, List.length_map] at hlen
  apply And.intro
  · apply (positions_mem r a H _).2
    refine ⟨?_,bounded_of_pattern r _ ?_,hoff⟩
    · rw [← hpat] at hlen; exact hlen.symm.trans hv.1
    · simpa [hpat] using hb
  · simp [totalEncode, he]

/-- Both separately defined lists enumerate the same positions via the actual
numeric address codec. No completeness/cardinality premise is assumed. -/
theorem domain_permutation (r a H : Nat) (hpad : 2^a ∣ H) :
    ((positions r a H).map totalEncode).Perm (addresses r a H) := by
  have hmap : ((positions r a H).map totalEncode).Nodup :=
    List.Pairwise.map totalEncode (fun _ _ hn he => hn (totalEncode_injective _ _ he))
      (positions_nodup r a H)
  apply (List.perm_ext_iff_of_nodup hmap (addresses_nodup r a H)).2
  intro ad
  constructor
  · rintro hm
    obtain ⟨p,hp,rfl⟩ := List.mem_map.mp hm
    exact forward_mem r a H hpad p hp
  · intro ha
    obtain ⟨hp,he⟩ := reverse_mem r a H hpad ad ha
    exact List.mem_map.mpr ⟨decodeClass ad,hp,he⟩

theorem domain_cardinality (r a H : Nat) (hpad : 2^a ∣ H) :
    (addresses r a H).length = r^(2*a)*H := by
  have h := (domain_permutation r a H hpad).length_eq
  simpa [positions_length] using h.symm

#print axioms totalEncode_inverse
#print axioms totalEncode_injective
#print axioms classes_mem
#print axioms positions_length
#print axioms addresses_mem
#print axioms addresses_nodup
#print axioms forward_mem
#print axioms reverse_mem
#print axioms domain_permutation
#print axioms domain_cardinality
end D3FinitePacketDomain
