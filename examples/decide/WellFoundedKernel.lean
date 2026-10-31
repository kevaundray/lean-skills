/-! The kernel ignores irreducibility: `decide +kernel` evaluates the well-founded definition. -/
def sumWF (n : Nat) : Nat := if _h : n = 0 then 0 else n + sumWF (n - 1)
termination_by n
theorem w2 : sumWF 100 = 5050 := by decide +kernel
