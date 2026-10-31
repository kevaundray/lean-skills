# listing-lemmas

60 instruction-fetch lemmas over an 80-instruction listing.

Recorded 2026-10-31 by `examples/run.py listing-lemmas` (32 CPUs, load 101; CPU = user + sys seconds, user in parentheses; median of 3 runs where repeated).

Toolchain: `Lean (version 4.34.0, x86_64-unknown-linux-gnu, commit 293d5d0c0c3f3dded4688b3ccd6a33939ac5102b, Release)`. `listing_source(proof)`: an 80-instruction `prog : List Instr` and 60 lemmas `prog[k]? = some (...)` (whole module, including the definitions).

| proof of each fetch lemma | module CPU | olean |
|---|---|---|
| (no fetch lemmas) | 0.68 s (user 0.31) | 0.52 MB |
| `by simp [prog]` | 5.25 s (user 3.75) | 0.67 MB |
| `by decide` | 1.28 s (user 0.90) | 0.58 MB |
| `rfl` | 2.28 s (user 1.10) | 0.56 MB |
