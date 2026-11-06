import Lean

namespace D3BinaryBits

/-- Little-endian bits, matching coordinate order in packet slots. -/
def bits : Nat → Nat → List Bool
  | 0, _ => []
  | width + 1, value => decide (value % 2 = 1) :: bits width (value / 2)

def value : List Bool → Nat
  | [] => 0
  | bit :: tail => (if bit then 1 else 0) + 2 * value tail

theorem bits_length (width n : Nat) : (bits width n).length = width := by
  induction width generalizing n with
  | zero => simp [bits]
  | succ width ih => simp [bits, ih]

theorem value_bits (width n : Nat) (hn : n < 2 ^ width) :
    value (bits width n) = n := by
  induction width generalizing n with
  | zero =>
    simp at hn
    subst n
    rfl
  | succ width ih =>
    have hdiv : n / 2 < 2 ^ width := by
      apply (Nat.div_lt_iff_lt_mul (by decide : 0 < 2)).2
      simpa [Nat.pow_succ, Nat.mul_comm] using hn
    have hrec := ih (n / 2) hdiv
    have hmod : n % 2 < 2 := Nat.mod_lt n (by decide)
    have hsplit := Nat.mod_add_div n 2
    simp only [bits, value, hrec]
    split <;> simp_all <;> omega

theorem bits_value (bs : List Bool) : bits bs.length (value bs) = bs := by
  induction bs with
  | nil => rfl
  | cons bit tail ih =>
    cases bit <;> simp [bits, value, ih, Nat.add_mod, Nat.add_div]

theorem value_bound (bs : List Bool) : value bs < 2 ^ bs.length := by
  induction bs with
  | nil => simp [value]
  | cons bit tail ih =>
    cases bit <;> simp [value, Nat.pow_succ] at * <;> omega

#print axioms bits_length
#print axioms value_bits
#print axioms bits_value
#print axioms value_bound

end D3BinaryBits
