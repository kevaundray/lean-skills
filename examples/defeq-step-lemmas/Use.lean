import Ops
import HB
/-! Is `block_cons` a `@[defeq]` lemma, and does the proof term of `t` mention it? -/
open Lean in
#eval show CoreM Unit from do
  IO.println s!"block_cons is @[defeq]: {defeqAttr.hasTag (← getEnv) ``block_cons}"
count_hb in
theorem t (s : S) : (block prog s).f7 = s.f7 := by
  simp [prog, block_cons, block_nil, Op.effect]
open Lean in
#eval show CoreM Unit from do
  let some v := (← getEnv).find? ``t |>.bind (·.value? (allowOpaque := true)) | throwError "no value"
  IO.println s!"proof of t mentions block_cons: {v.getUsedConstants.contains ``block_cons}"
