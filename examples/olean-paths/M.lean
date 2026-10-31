/-! A module with a linter warning (unused variable). -/
theorem m (n : Nat) (h : n = n) : n + 0 = n := by simp
