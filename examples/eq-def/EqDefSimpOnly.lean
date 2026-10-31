import Ops
/-! `f.eq_def` unfolds to the `match`, which `simp` reduces on a constructor. -/
theorem t (s : Nat) : Op.effect .o5 s = s + 5 := by simp only [Op.effect.eq_def]
