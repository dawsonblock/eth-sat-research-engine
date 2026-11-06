import SourceCreationPrecision

theorem source_creation_chain_contract (pc : Nat) (ps xs : List Nat)
    (h : ∀ p ∈ ps, pc ≤ p) :
    SourceCreationPrecision.liftChain ps (SourceCreationPrecision.captureCoordinates pc xs) =
      SourceCreationPrecision.captureCoordinates pc xs :=
  SourceCreationPrecision.coordinates_lift_chain pc ps xs h

#print axioms source_creation_chain_contract

/- Exact external acceptance types. Replacing the named model theorem by
True cannot satisfy this contract. No assumption states the conclusion. -/
theorem source_creation_coordinate_contract (p P x : Nat) (h : p ≤ P) :
    (x % 2^p) % 2^P = x % 2^p ∧
    ((x % 2^p) % 2^P) % 2^p = x % 2^p :=
  ⟨SourceCreationPrecision.lift_unchanged p P x h,
   SourceCreationPrecision.lift_roundtrip p P x h⟩

theorem source_creation_vector_contract (p P : Nat) (h : p ≤ P) (xs : List Nat) :
    (xs.map (fun x => x % 2^p)).map (fun x => x % 2^P) =
      xs.map (fun x => x % 2^p) :=
  SourceCreationPrecision.coordinates_lift_unchanged p P h xs

#print axioms source_creation_coordinate_contract
#print axioms source_creation_vector_contract
