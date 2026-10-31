# lake-weak-args

`weakLeanArgs` is not part of the trace: it can silence linters without rebuilding.

Recorded 2026-10-31 by `examples/run.py lake-weak-args` (32 CPUs, load 91; CPU = user + sys seconds, user in parentheses; median of 3 runs where repeated).

Toolchain: `leanprover/lean4:v4.34.0` (Lake). Project `Weak` = `olean-paths/M.lean` built with `lake build` in two directories `a` and `b`.

| build | olean sha256 (a / b) | identical |
|---|---|---|
| no `weakLeanArgs`, fresh builds in `a` and `b` | d4f686f70571 / 523b6ab02b80 | no |
| with `weakLeanArgs`, fresh builds in `a` and `b` | 93a8ab028ac6 / 93a8ab028ac6 | yes |

Adding `weakLeanArgs = ["-Dlinter.unusedVariables=false"]` to the built `a` and running `lake build` again rebuilt `Weak`: **no**. Renaming it to `moreLeanArgs` and running `lake build` rebuilt `Weak`: **yes**.
