# listing-lemmas

60 instruction-fetch lemmas over an 80-instruction listing.

Recorded 2026-10-31 by `examples/run.py listing-lemmas` (32 CPUs, load 55; CPU = user + sys seconds, user in parentheses; median of 3 runs where repeated).

Toolchain: `Lean (version 4.34.0, x86_64-unknown-linux-gnu, commit 293d5d0c0c3f3dded4688b3ccd6a33939ac5102b, Release)`. `listing_source(proof)`: an 80-instruction `prog : List Instr` and 60 lemmas `prog[k]? = some (...)` (whole module, including the definitions).

| proof of each fetch lemma | module CPU | olean |
|---|---|---|
| (no fetch lemmas) | 1.05 s (user 0.36) | 0.52 MB |
| `by simp [prog]` | 6.73 s (user 3.60) | 0.67 MB |
| `by decide` | 1.70 s (user 0.93) | 0.58 MB |
| `rfl` | 1.73 s (user 1.09) | 0.56 MB |
| `by rfl` | 1.40 s (user 0.81) | 0.56 MB |

A 400-instruction listing with one lemma for entry 390 (single run, whole module):

| proof | result | module CPU |
|---|---|---|
| `rfl` | error: `maximum recursion depth has been reached` | 1.38 s (user 0.66) |
| `by rfl` | ok | 1.96 s (user 0.80) |
| `by decide` | ok | 1.44 s (user 0.73) |
| `by decide +kernel` | ok | 1.38 s (user 0.72) |
