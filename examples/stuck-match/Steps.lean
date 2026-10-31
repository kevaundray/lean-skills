import Ops
import HB
/-! Step lemmas: `simp` only ever sees `Op.effect` applied to a constructor. -/
count_hb in
theorem t (s : Nat) : block [.o1, .o2] s = s + 1 + 2 := by
  simp [block_cons, block_nil, Op.effect]
