/-! Definitions by well-founded recursion do not reduce in the elaborator. -/
def sumWF (n : Nat) : Nat := if _h : n = 0 then 0 else n + sumWF (n - 1)
termination_by n
def sumS : Nat → Nat
  | 0 => 0
  | n + 1 => (n + 1) + sumS n
theorem s1 : sumS 100 = 5050 := by decide   -- structural: fine
theorem w1 : sumWF 100 = 5050 := by decide  -- fails: stuck
theorem w3 : sumWF 100 = 5050 := by rfl     -- fails
