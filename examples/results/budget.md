# budget

Heartbeat budgets decide which proof a search finds, and failed alternatives cost their
budget on every build.

Recorded 2026-11-01 by `examples/run.py budget` (32 CPUs, load 68; CPU = user + sys seconds, user in parentheses; median of 3 runs where repeated).

Goal `∀ x ∈ List.range 100, x * x % 7 ≠ 3`. `lib/Budget.lean` defines `budget K => tac` (run `tac` with its own budget of K thousand heartbeats; an overrun becomes an ordinary failure). Toolchain `Lean (version 4.34.0, x86_64-unknown-linux-gnu, commit 293d5d0c0c3f3dded4688b3ccd6a33939ac5102b, Release)` for the first table. Heartbeats = whole theorem (`count_hb`), olean = sha256 of `T.olean`.

| proof | budgeted attempt | heartbeats | CPU | olean |
|---|---|---|---|---|
| `decide +kernel` alone | — | 140k | 1.84 s (user 0.82) | f57c23a55dd4 |
| `decide` alone | — | 374k | 1.98 s (user 0.88) | e902f1e9692d |
| `first \| budget 100 => decide \| decide +kernel` | `decide` failed after 100k heartbeats | 230k | 1.42 s (user 0.89) | ba51c5e3f5ae |
| `first \| budget 240 => decide \| decide +kernel` | `decide` failed after 240k heartbeats | 370k | 1.67 s (user 0.91) | ba51c5e3f5ae |
| `first \| budget 250 => decide \| decide +kernel` | `decide` succeeded after 247k heartbeats | 375k | 1.86 s (user 0.94) | d64f7d5b9691 |
| `first \| budget 2000 => decide \| decide +kernel` | `decide` succeeded after 247k heartbeats | 375k | 1.89 s (user 0.82) | d64f7d5b9691 |

The same source on several official toolchains: heartbeats `decide` needs (budget 2000k), and which alternative wins with budgets of 250k and 240k:

| Lean | `decide` needs | winner, budget 250k | winner, budget 240k |
|---|---|---|---|
| v4.29.0 | 272k | fallback `decide +kernel` | fallback `decide +kernel` |
| v4.31.0 | 251k | `decide` | fallback `decide +kernel` |
| v4.33.1 | 247k | `decide` | fallback `decide +kernel` |
| v4.34.0 | 247k | `decide` | fallback `decide +kernel` |
| v4.34.1 | 247k | `decide` | fallback `decide +kernel` |
| v4.35.0 | 228k | `decide` | `decide` |
