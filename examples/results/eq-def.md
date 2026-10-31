# eq-def

`simp [f]` vs `f.eq_def` / `unfold f` for an N-arm `match` whose equations were not
generated upstream.

Recorded 2026-10-31 by `examples/run.py eq-def` (32 CPUs, load 90; CPU = user + sys seconds, user in parentheses; median of 3 runs where repeated).

Toolchain: `Lean (version 4.34.0, x86_64-unknown-linux-gnu, commit 293d5d0c0c3f3dded4688b3ccd6a33939ac5102b, Release)`. `Ops.lean` = `ops_source(400, warm=False)` (no equation lemmas generated upstream). Each file proves `Op.effect .o5 s = s + 5`.

| proof | CPU | olean | equation lemmas stored | match equations stored |
|---|---|---|---|---|
| `SimpF` | 19.59 s (user 13.69) | 39.68 MB | 400 | 400 |
| `EqDefSimpOnly` | 0.96 s (user 0.37) | 0.11 MB | 1 | 0 |
| `EqDefRw` | 1.11 s (user 0.36) | 0.12 MB | 1 | 0 |
| `Unfold` | 0.80 s (user 0.20) | 0.11 MB | 0 | 0 |
