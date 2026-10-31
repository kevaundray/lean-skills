import Ops
/-! Frame lemmas proved once: no instruction writes `f7`, so no block does. -/
theorem effect_f7 (op : Op) (s : S) : (op.effect s).f7 = s.f7 := by
  cases op <;> rfl

theorem block_f7 (ops : List Op) (s : S) : (block ops s).f7 = s.f7 := by
  induction ops generalizing s with
  | nil => rfl
  | cons op ops ih => rw [block_cons, ih, effect_f7]
