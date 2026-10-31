import Ops
import HB
/-! Unfolding `block` exposes `fun t op => op.effect t`: `Op.effect`'s `match` is stuck on `op`. -/
count_hb in
theorem t (s : Nat) : block [.o1, .o2] s = s + 1 + 2 := by
  simp [block, Op.effect]
