import FiniteBoundaryReduction
open FiniteBoundaryReduction

theorem finite_boundary_expected (cut left right precision : Nat)
    (L R : List Bool → List Bool → Int) :
    (assignments cut (fun b => assignments left (fun x =>
       assignments right (fun y => L b x * R b y)))) % (2:Int)^precision =
    (assignments cut (fun b => assignments left (L b) * assignments right (R b))) % (2:Int)^precision :=
  boundary_mod cut left right precision L R

#print axioms finite_boundary_expected
