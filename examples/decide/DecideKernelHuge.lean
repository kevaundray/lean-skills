/-! The kernel recurses along the list too: at 5000 elements it reports deep recursion. Chunk instead. -/
theorem d : ∀ x ∈ List.range 5000, x * x % 7 ≠ 3 := by decide +kernel
