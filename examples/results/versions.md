# versions

Version ranges: `:= rfl` tagging, `native_decide` axioms, the stuck-`match` pathology.

Recorded 2026-10-31 by `examples/run.py versions` (32 CPUs, load 105; CPU = user + sys seconds, user in parentheses; median of 3 runs where repeated).

Official toolchains. `@[defeq]` tagging of `theorem a : f n = n + 1 := rfl` (and `(rfl)`, `by rfl`) as shown by `#print`; axioms of `theorem nd : 2 + 2 = 4 := by native_decide`; `stuck-match/Bad.lean` at N = 100 (match equations / splitters stored in `Bad.olean`).

| Lean | tagged `@[defeq]` | `native_decide` axioms | stuck match: match eqns / splitters |
|---|---|---|---|
| v4.26.0 | `:= rfl` | Lean.ofReduceBool, Lean.trustCompiler | 100 / 1 |
| v4.28.0 | `:= rfl` | Lean.ofReduceBool, Lean.trustCompiler | 100 / 1 |
| v4.29.0 | `:= rfl` | nd._native.native_decide.ax_1_1 | 100 / 1 |
| v4.31.0 | `:= rfl` | nd._native.native_decide.ax_1_1 | 100 / 1 |
| v4.33.1 | `:= rfl` | nd._native.native_decide.ax_1_1 | 100 / 1 |
| v4.34.0 | `:= rfl` | nd._native.native_decide.ax_1_1 | 100 / 1 |
| v4.35.0 | `:= rfl` | nd._native.native_decide.ax_1_1 | 100 / 1 |
