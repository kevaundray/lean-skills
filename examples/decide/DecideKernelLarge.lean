/-! `decide +kernel` has no elaborator recursion limit: 3000 elements check. -/
theorem d : ∀ x ∈ List.range 3000, x * x % 7 ≠ 3 := by decide +kernel
