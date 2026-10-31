# eqns-upstream

Four importers each `simp [Op.effect]`: equation lemmas generated in each of them vs once in
the defining module.

Recorded 2026-10-31 by `examples/run.py eqns-upstream` (32 CPUs, load 84; CPU = user + sys seconds, user in parentheses; median of 3 runs where repeated).

Toolchain: `Lean (version 4.34.0, x86_64-unknown-linux-gnu, commit 293d5d0c0c3f3dded4688b3ccd6a33939ac5102b, Release)`. N = 400; `U1`..`U4` each prove `Op.effect .oK s = s + K` by `simp [Op.effect]`.

| `attribute [local simp] Op.effect` in `Ops` | `Ops` CPU | `Ops` olean | `U1..U4` CPU | `U1..U4` oleans | total CPU |
|---|---|---|---|---|---|
| no | 4.88 s (user 3.87) | 10.53 MB | 17.93 / 22.57 / 22.64 / 19.36 s | 39.68 MB / 39.68 MB / 39.68 MB / 39.68 MB | 87.38 s (user 56.37) |
| yes | 31.29 s (user 19.64) | 49.91 MB | 0.32 / 0.64 / 0.54 / 0.53 s | 7.1 kB / 7.1 kB / 7.1 kB / 7.1 kB | 33.33 s (user 20.41) |
