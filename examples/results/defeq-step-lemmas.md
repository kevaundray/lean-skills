# defeq-step-lemmas

Step lemmas proved by `:= rfl` (tagged `@[defeq]`) vs `:= (rfl)` / `:= by rfl`.

Recorded 2026-10-31 by `examples/run.py defeq-step-lemmas` (32 CPUs, load 68; CPU = user + sys seconds, user in parentheses; median of 3 runs where repeated).

Toolchain: `Lean (version 4.34.0, x86_64-unknown-linux-gnu, commit 293d5d0c0c3f3dded4688b3ccd6a33939ac5102b, Release)`. `Ops.lean` from `state_ops_source(200, steps)`: 200 ops updating an 8-field structure, `prog` = 60 ops; `Use.lean` proves `(block prog s).f7 = s.f7` by `simp [prog, block_cons, block_nil, Op.effect]`.

| step lemma proof | `@[defeq]` | proof term mentions `block_cons` | CPU | heartbeats | kernel (`profiler`: type checking) |
|---|---|---|---|---|---|
| `:= rfl` | true | false | 3.20 s (user 0.97) | 1,380k | 29ms |
| `:= (rfl)` | false | true | 2.25 s (user 0.84) | 1,157k | 10.6ms |
| `:= by rfl` | false | true | 2.42 s (user 0.88) | 1,157k | 10.4ms |

With `@[defeq]` step lemmas `simp` rewrites without recording a proof step, so the kernel has to re-establish those steps by unfolding. In this small state it is cheap; the large costs reported by ssz-fv and clifv come from large states/terms.
