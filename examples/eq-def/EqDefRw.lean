import Ops
/-! `rw` unfolds to the `match` and closes the goal with `rfl`. -/
theorem t (s : Nat) : Op.effect .o5 s = s + 5 := by rw [Op.effect.eq_def]
