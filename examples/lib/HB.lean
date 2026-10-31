import Lean

/-!
`count_hb in <command>`: elaborates the command synchronously and logs the heartbeats it used,
in thousands (the unit of `maxHeartbeats`). Core-only stand-in for Mathlib's `count_heartbeats in`.
-/

open Lean Elab Command

elab "count_hb " "in" cmd:command : command => do
  let h0 ← IO.getNumHeartbeats
  withScope (fun s => { s with opts := Elab.async.set s.opts false }) (elabCommand cmd)
  let h1 ← IO.getNumHeartbeats
  logInfo m!"heartbeats: {(h1 - h0) / 1000}k"
