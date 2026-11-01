import Lean

/-!
`budget K => tac`: runs `tac` with its own budget of `K` thousand heartbeats, like the per-alternative
budgets of search tactics. A budget overrun becomes an ordinary failure (so `first` moves on) and
the outcome is printed to stdout (`first` discards the messages of failed alternatives).
-/

open Lean Elab Tactic

elab "budget " k:num " => " tac:tactic : tactic => do
  let s ← saveState
  let h0 ← IO.getNumHeartbeats
  let used := fun _ : Unit => do return ((← IO.getNumHeartbeats) - h0) / 1000
  -- plain `try`/`catch` (and `first`) do not catch heartbeat exceptions
  tryCatchRuntimeEx
    (do
      withTheReader Core.Context (fun ctx => { ctx with maxHeartbeats := k.getNat * 1000 }) <|
        withCurrHeartbeats <| evalTactic tac
      IO.println s!"budget {k.getNat}k: `{← PrettyPrinter.ppTactic tac}` succeeded after {← used ()}k heartbeats")
    fun _ => do
      let n ← used ()
      s.restore (restoreInfo := true)
      IO.println s!"budget {k.getNat}k: `{← PrettyPrinter.ppTactic tac}` failed after {n}k heartbeats"
      throwError "budget {k.getNat}k: `{tac}` failed"
