# fast-lean

`fast-lean build` vs `lake build` on a project with one slow proof.

Recorded 2026-10-31 by `examples/run.py fast-lean` (32 CPUs, load 43; CPU = user + sys seconds, user in parentheses; median of 3 runs where repeated).

Project `Demo` (`lean-toolchain` = `leanprover/lean4:v4.34.0`): `Demo.Ops` = `ops_source(400, warm=True)`, `Demo.Heavy` proves `t` by the slow `simp [block, Op.effect]`, `Demo.Top` uses `t`. After each step, `lake env lean Axioms.lean` prints the axioms of `t` and `top` (`Built` = modules and other artifacts Lake reported as built).

| step | result | CPU | `Built` lines | axioms |
|---|---|---|---|---|
| `lake build` (official), clean | ok | 55.65 s (user 42.89) | 4 | 't' depends on axioms: [propext]; 'top' depends on axioms: [propext] |
| `fast-lean build`, clean (`LEAN_DEV=proofs,sat`) | ok | 13.76 s (user 6.32) | 4 | 't' depends on axioms: [Lean.skippedProof]; 'top' depends on axioms: [Lean.skippedProof] |
| then `lake build` (official) | ok | 59.88 s (user 39.40) | 4 | 't' depends on axioms: [propext]; 'top' depends on axioms: [propext] |
| `LEAN_DEV= fast-lean build`, clean (faithful) | ok | 10.43 s (user 6.06) | 4 | 't' depends on axioms: [propext]; 'top' depends on axioms: [propext] |
| `fast-lean build Demo.Top`, clean | ok | 6.53 s (user 4.72) | 3 | 't' depends on axioms: [Lean.skippedProof]; 'top' depends on axioms: [Lean.skippedProof] |

`Demo/Ops.lean` alone with `lean` (equation generation for the 400-arm `match`): `leanprover/lean4:v4.34.0` 25.87 s (user 19.52); `dev-fast-v4.34.0` 9.15 s (user 5.36).
