# fast-lean

`fast-lean build` vs `lake build` on a project with one slow proof.

Recorded 2026-10-31 by `examples/run.py fast-lean` (32 CPUs, load 81; CPU = user + sys seconds, user in parentheses; median of 3 runs where repeated).

Project `Demo` (`lean-toolchain` = `leanprover/lean4:v4.34.0`): `Demo.Ops` = `ops_source(400, warm=True)`, `Demo.Heavy` proves `t` by the slow `simp [block, Op.effect]`, `Demo.Top` uses `t`. After each step, `lake env lean Axioms.lean` prints the axioms of `t` and `top` (`Built` = modules and other artifacts Lake reported as built).

| step | result | CPU | `Built` lines | axioms |
|---|---|---|---|---|
| `lake build` (official), clean | ok | 48.48 s (user 35.25) | 4 | 't' depends on axioms: [propext]; 'top' depends on axioms: [propext] |
| `fast-lean build`, clean (`LEAN_DEV=proofs,sat`) | ok | 9.03 s (user 5.82) | 4 | 't' depends on axioms: [Lean.skippedProof]; 'top' depends on axioms: [Lean.skippedProof] |
| then `lake build` (official) | ok | 56.04 s (user 40.16) | 4 | 't' depends on axioms: [propext]; 'top' depends on axioms: [propext] |
| `LEAN_DEV= fast-lean build`, clean (faithful) | ok | 11.75 s (user 6.13) | 4 | 't' depends on axioms: [propext]; 'top' depends on axioms: [propext] |
| `fast-lean build Demo.Top`, clean | ok | 11.03 s (user 5.88) | 3 | 't' depends on axioms: [Lean.skippedProof]; 'top' depends on axioms: [Lean.skippedProof] |
