# frame-lemma

Ten call sites that need "the block leaves `f7` alone": `simp` through the block each time
vs a frame lemma proved once by `cases op` and induction.

Recorded 2026-10-31 by `examples/run.py frame-lemma` (32 CPUs, load 67; CPU = user + sys seconds, user in parentheses; median of 3 runs where repeated).

Toolchain: `Lean (version 4.34.0, x86_64-unknown-linux-gnu, commit 293d5d0c0c3f3dded4688b3ccd6a33939ac5102b, Release)`. `Ops` = `state_ops_source(400, "(rfl)")` (400 ops updating fields `f0`..`f6` of an 8-field structure, equation lemmas generated there). `UseSimp` and `UseFrame` each prove `(block p s).f7 = s.f7` for 10 different 60-op programs `p`; `UseSimp` by `simp [block_cons, block_nil, Op.effect]`, `UseFrame` by the lemma `block_f7` from `frame-lemma/Frame.lean` as `block_f7 _ s`. `Base*` import only. The probes prove the first of these goals with the list restated: `UseFrameExplicit` by `exact block_f7 [<the list>] s`, `UseFrameTerm` by the term `block_f7 [<the list>] s`, `UseFrameHave` by `have h := block_f7 [<the list>] s; exact h` (the application is elaborated without the expected type, then `h`'s type is unified with the goal).

| module | CPU |
|---|---|
| `Ops` | 29.15 s (user 21.27) |
| `Frame` | 2.13 s (user 1.55) |
| `BaseOps` | 0.80 s (user 0.21) |
| `UseSimp` | 2.87 s (user 1.85) |
| `BaseFrame` | 0.59 s (user 0.22) |
| `UseFrame` | 0.98 s (user 0.37) |
| `UseFrameExplicit` (1 theorem, single run) | 9.59 s (user 9.18); error: `(deterministic) timeout at `whnf`, maximum number of heartbeats (200000) has been reached` |
| `UseFrameTerm` (1 theorem, single run) | 9.98 s (user 9.60); error: `(deterministic) timeout at `whnf`, maximum number of heartbeats (200000) has been reached` |
| `UseFrameHave` (1 theorem, single run) | 0.66 s (user 0.24); ok |
