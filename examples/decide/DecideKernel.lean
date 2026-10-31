import HB
/-! `decide +kernel`: only the kernel evaluates. -/
count_hb in
theorem d : ∀ x ∈ List.range 100, x * x % 7 ≠ 3 := by decide +kernel
#print axioms d
