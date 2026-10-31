import Ops
import HB
/-! Same proof as `Bad.lean` in an `example`: constants realized inside it are discarded. -/
count_hb in
example (s : Nat) : block [.o1, .o2] s = s + 1 + 2 := by
  simp [block, Op.effect]
