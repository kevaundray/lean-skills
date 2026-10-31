# defeq-step-lemmas

Step lemmas proved by `:= rfl` (tagged `@[defeq]`) vs `:= (rfl)` / `:= by rfl`, and
`simp -implicitDefEqProofs`.

Recorded 2026-10-31 by `examples/run.py defeq-step-lemmas` (32 CPUs, load 59; CPU = user + sys seconds, user in parentheses; median of 3 runs where repeated).

Toolchain: `Lean (version 4.34.0, x86_64-unknown-linux-gnu, commit 293d5d0c0c3f3dded4688b3ccd6a33939ac5102b, Release)`. `Ops.lean` from `state_ops_source(200, steps)`: 200 ops updating an 8-field structure, `prog` = 60 ops; `Use.lean` proves `(block prog s).f7 = s.f7` by `simp [prog, block_cons, block_nil, Op.effect]`; `UseNoImplicit.lean` the same with `simp -implicitDefEqProofs`. `Dsimp.lean` tries `dsimp only [block_cons]` on the step equation.

| step lemma proof | call | `@[defeq]` | proof term mentions `block_cons` | CPU | heartbeats | kernel (`profiler`: type checking) | `dsimp only [block_cons]` works |
|---|---|---|---|---|---|---|---|
| `:= rfl` | `simp [...]` | true | false | 1.99 s (user 0.90) | 1,380k | 38.5ms | yes |
| `:= rfl` | `simp -implicitDefEqProofs [...]` | true | true | 2.26 s (user 0.89) | 1,157k | 12.7ms | yes |
| `:= (rfl)` | `simp [...]` | false | true | 2.50 s (user 0.94) | 1,157k | 11.2ms | no: `dsimp` made no progress |
| `:= by rfl` | `simp [...]` | false | true | 2.83 s (user 0.93) | 1,157k | 18ms | no: `dsimp` made no progress |

With `@[defeq]` step lemmas `simp` rewrites without recording a proof step, so the kernel has to re-establish those steps by unfolding. In this small state it is cheap; the large costs reported by ssz-fv and clifv come from large states/terms.
