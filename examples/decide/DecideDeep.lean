/-! Elaborator `decide` recurses along the list: at 150 elements it exceeds the default `maxRecDepth`. -/
theorem d : ∀ x ∈ List.range 150, x * x % 7 ≠ 3 := by decide
