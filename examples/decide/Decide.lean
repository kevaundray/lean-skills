import HB
/-! Elaborator `decide`: evaluates the `Decidable` instance with `whnf`, then the kernel re-checks. -/
count_hb in
theorem d : ∀ x ∈ List.range 100, x * x % 7 ≠ 3 := by decide
#print axioms d
