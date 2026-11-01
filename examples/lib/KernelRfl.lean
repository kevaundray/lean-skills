import Lean

/-! `kernel_rfl`: closes `a = b` by `Eq.refl a` without checking `a =?= b` in the elaborator; the
kernel checks it when the declaration is added (clifv's `kernel_rfl`). -/

open Lean Elab Tactic

elab "kernel_rfl" : tactic => liftMetaFinishingTactic fun g => g.refl (check := false)
