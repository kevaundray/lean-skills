import HB
/-! `native_decide`: compiles and runs the decision procedure; trusts the compiler. -/
count_hb in
theorem d : ∀ x ∈ List.range 100, x * x % 7 ≠ 3 := by native_decide
#print axioms d
