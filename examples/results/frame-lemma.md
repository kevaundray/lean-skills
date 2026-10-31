# frame-lemma

Ten call sites that need "the block leaves `f7` alone": `simp` through the block each time
vs a frame lemma proved once by `cases op` and induction.

Recorded 2026-10-31 by `examples/run.py frame-lemma` (32 CPUs, load 127; CPU = user + sys seconds, user in parentheses; median of 3 runs where repeated).

Toolchain: `Lean (version 4.34.0, x86_64-unknown-linux-gnu, commit 293d5d0c0c3f3dded4688b3ccd6a33939ac5102b, Release)`. `Ops` = `state_ops_source(400, "(rfl)")` (400 ops updating fields `f0`..`f6` of an 8-field structure, equation lemmas generated there). `UseSimp` and `UseFrame` each prove `(block p s).f7 = s.f7` for 10 different 60-op programs `p`; `UseSimp` by `simp [block_cons, block_nil, Op.effect]`, `UseFrame` by the lemma `block_f7` from `frame-lemma/Frame.lean` as `block_f7 _ s`. `Base*` import only. `UseFrameExplicit` proves the first of these goals by `exact block_f7 [<the list>] s`, restating the list instead of letting unification fill it.

| module | CPU |
|---|---|
| `Ops` | 29.42 s (user 21.75) |
| `Frame` | 2.19 s (user 1.67) |
| `BaseOps` | 0.59 s (user 0.20) |
| `UseSimp` | 3.22 s (user 1.91) |
| `BaseFrame` | 0.52 s (user 0.20) |
| `UseFrame` | 0.79 s (user 0.35) |
| `UseFrameExplicit` (1 theorem, single run) | 10.05 s (user 9.67); error: `(deterministic) timeout at `whnf`, maximum number of heartbeats (200000) has been reached` |
