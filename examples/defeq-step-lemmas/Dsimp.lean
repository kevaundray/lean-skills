import Ops
/-! `dsimp` only uses `@[defeq]` lemmas. -/
theorem d (op : Op) (ops : List Op) (s : S) : block (op :: ops) s = block ops (op.effect s) := by
  dsimp only [block_cons]
