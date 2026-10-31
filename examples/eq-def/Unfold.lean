import Ops
theorem t (s : Nat) : Op.effect .o5 s = s + 5 := by unfold Op.effect; rfl
