import Ops
import HB
/-! Structurally recursive block: its equation lemmas are the step lemmas. -/
count_hb in
theorem t (s : Nat) : blockS [.o1, .o2] s = s + 1 + 2 := by
  simp [blockS, Op.effect]
