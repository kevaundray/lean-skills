import HB
/-! The code snippets of the skills, checked to compile with the official toolchain. -/

structure S where
  f0 : Nat
  f7 : Nat

inductive Op where
  | inc | clear

def Op.effect : Op → S → S
  | .inc, s => { s with f0 := s.f0 + 1 }
  | .clear, s => { s with f0 := 0 }
attribute [local simp] Op.effect   -- forces Op.effect.eq_* here; importers reuse them

def block (ops : List Op) (s : S) : S := ops.foldl (fun t op => op.effect t) s

theorem block_nil (s : S) : block [] s = s := (rfl)
theorem block_cons (op : Op) (ops : List Op) (s : S) :
    block (op :: ops) s = block ops (op.effect s) := (rfl)

def blockS : List Op → S → S
  | [], s => s
  | op :: ops, s => blockS ops (op.effect s)

theorem effect_f7 (op : Op) (s : S) : (op.effect s).f7 = s.f7 := by cases op <;> rfl
theorem block_f7 (ops : List Op) (s : S) : (block ops s).f7 = s.f7 := by
  induction ops generalizing s with
  | nil => rfl
  | cons op ops ih => rw [block_cons, ih, effect_f7]

theorem uses_steps (s : S) : (block [.inc, .clear, .inc] s).f0 = 1 := by
  simp [block_cons, block_nil, Op.effect]
def blockR (ops : List Op) (s : S) : S := ops.foldl (fun t op => op.effect t) s
theorem blockR_cons (op : Op) (ops : List Op) (s : S) :
    blockR (op :: ops) s = blockR ops (op.effect s) := rfl
theorem blockR_nil (s : S) : blockR [] s = s := rfl
theorem no_implicit (s : S) : (blockR [.inc, .clear, .inc] s).f0 = 1 := by
  simp -implicitDefEqProofs [blockR_cons, blockR_nil, Op.effect]
theorem dsimp_defeq (op : Op) (ops : List Op) (s : S) :
    blockR (op :: ops) s = blockR ops (op.effect s) := by
  dsimp only [blockR_cons]
theorem uses_structural (s : S) : (blockS [.inc, .clear, .inc] s).f0 = 1 := by
  simp [blockS, Op.effect]
theorem one_unfold (s : S) : Op.effect .inc s = { s with f0 := s.f0 + 1 } := by
  rw [Op.effect.eq_def]
theorem one_unfold' (s : S) : Op.effect .inc s = { s with f0 := s.f0 + 1 } := by
  unfold Op.effect; rfl
theorem one_unfold'' (s : S) : Op.effect .inc s = { s with f0 := s.f0 + 1 } := by
  simp only [Op.effect.eq_def]
theorem reducible_assumption (s : S) (h : (block [.inc] s).f7 = 3) : (block [.inc] s).f7 = 3 := by
  with_reducible assumption
theorem reducible_exact (s : S) (h : (block [.inc] s).f7 = 3) : (block [.inc] s).f7 = 3 := by
  with_reducible exact h
theorem with_instances (s : S) : (block [.clear] s).f0 = 0 := by
  simp +instances [block_cons, block_nil, Op.effect]

count_hb in
theorem kernel_decide : ∀ x ∈ List.range 200, x * x % 7 ≠ 3 := by decide +kernel
#print axioms kernel_decide

theorem rfl_tagged (n : Nat) : n + 0 = n := rfl
theorem rfl_untagged (n : Nat) : n + 0 = n := (rfl)
#print rfl_tagged
#print rfl_untagged

opaque boxedValue {α : Type} (v : α) : { r : α // r = v } := ⟨v, rfl⟩
