# profile

What the stuck-match pathology looks like in `trace.profiler` and in the `.olean`.

Recorded 2026-10-31 by `examples/run.py profile` (32 CPUs, load 68; CPU = user + sys seconds, user in parentheses; median of 3 runs where repeated).

Toolchain: `Lean (version 4.34.0, x86_64-unknown-linux-gnu, commit 293d5d0c0c3f3dded4688b3ccd6a33939ac5102b, Release)`. N = 200, `stuck-match/Bad.lean`, run as `lean -Dtrace.profiler=true -Dtrace.profiler.threshold=100 Bad.lean`:

```
[Elab.command] [2.925556] ✅️ theorem t (s : Nat) : block [.o1, .o2] s = s + 1 + 2 := by simp [block, Op.effect]
  [Elab.definition.value] [2.907943] ✅️ t
    [Elab.step] [2.907648] ✅️ simp [block, Op.effect]
      [Elab.step] [2.907588] ✅️ simp [block, Op.effect]
        [Elab.step] [2.907557] ✅️ simp [block, Op.effect]
          [Meta.realizeConst] [1.189722] ✅️ _private.Bad.0.Op.effect.match_1.splitter
heartbeats: 17136k
[Elab.command] [2.929452] ✅️ count_hb in
      theorem t (s : Nat) : block [.o1, .o2] s = s + 1 + 2 := by simp [block, Op.effect]
[Elab.async] [0.265508] ✅️ Lean.compileDecls
  [Compiler] [0.261240] ✅️ compiling: [_private.Bad.0.Op.effect.match_1.splitter]
```

`lean --run lib/OleanStats.lean Bad.olean Ops.olean`:

| olean | size | constants | match eqns | splitters | eqn lemmas |
|---|---|---|---|---|---|
| Bad | 10.13 MB | 203 | 200 | 1 | 1 |
| Ops | 13.46 MB | 1022 | 200 | 1 | 200 |
