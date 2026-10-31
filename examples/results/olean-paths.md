# olean-paths

Linter warnings put the source path into the `.olean`.

Recorded 2026-10-31 by `examples/run.py olean-paths` (32 CPUs, load 91; CPU = user + sys seconds, user in parentheses; median of 3 runs where repeated).

`olean-paths/M.lean` (one unused-variable warning) compiled as `lean -o <dir>/M.olean <dir>/M.lean` with absolute paths in two directories:

| Lean | options | olean sha256 (a / b) | identical | olean contains the source path |
|---|---|---|---|---|
| v4.29.0 | default | 23415cc2e2b6 / 23415cc2e2b6 | yes | no |
| v4.29.0 | `-Dlinter.unusedVariables=false` | 23415cc2e2b6 / 23415cc2e2b6 | yes | no |
| v4.31.0 | default | e7dc75e1bce7 / b53d3e339a99 | no | yes |
| v4.31.0 | `-Dlinter.unusedVariables=false` | b807c753e065 / b807c753e065 | yes | no |
| v4.33.1 | default | 25c6ca33012d / ff991bf220e4 | no | yes |
| v4.33.1 | `-Dlinter.unusedVariables=false` | 7ffd8aed1713 / 7ffd8aed1713 | yes | no |
| v4.34.0 | default | 0997e814a8fd / 69efa1987cfa | no | yes |
| v4.34.0 | `-Dlinter.unusedVariables=false` | c9d03ac03319 / c9d03ac03319 | yes | no |
| v4.35.0 | default | 4a1d6bf6f46d / 23b13bf49bee | no | yes |
| v4.35.0 | `-Dlinter.unusedVariables=false` | 63888c633b34 / 63888c633b34 | yes | no |
