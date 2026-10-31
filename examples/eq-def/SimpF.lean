import Ops
/-! `simp [f]` generates `f`'s equation lemmas (and the match equations behind them). -/
theorem t (s : Nat) : Op.effect .o5 s = s + 5 := by simp [Op.effect]
