# first-chain

`first | a | b | c`: the failing alternatives are paid on every build.

Recorded 2026-11-01 by `examples/run.py first-chain` (32 CPUs, load 114; CPU = user + sys seconds, user in parentheses; median of 3 runs where repeated).

Toolchain: `Lean (version 4.34.0, x86_64-unknown-linux-gnu, commit 293d5d0c0c3f3dded4688b3ccd6a33939ac5102b, Release)`. Ten theorems `∀ x ∈ List.range m, x * x % 7 ≠ 3` (m = 90..99), each proved by the given tactic; heartbeats summed over the ten.

| proof | heartbeats | module CPU |
|---|---|---|
| `first \| omega \| (simp; done) \| decide +kernel` | 2,346k | 1.94 s (user 1.12) |
| `decide +kernel` | 1,346k | 2.20 s (user 1.05) |
