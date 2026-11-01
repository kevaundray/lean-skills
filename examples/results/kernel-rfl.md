# kernel-rfl

Closing a closed computation `a = b`: elaborator `rfl`/`decide` vs kernel-only
`decide +kernel`/`kernel_rfl` vs `decide_cbv`.

Recorded 2026-11-01 by `examples/run.py kernel-rfl` (32 CPUs, load 56; CPU = user + sys seconds, user in parentheses; median of 3 runs where repeated).

Toolchain: `Lean (version 4.34.0, x86_64-unknown-linux-gnu, commit 293d5d0c0c3f3dded4688b3ccd6a33939ac5102b, Release)`. Goal `(List.range n).foldl (· + ·) 0 = n(n-1)/2`, one theorem per module; `kernel_rfl` from `lib/KernelRfl.lean` (`MVarId.refl` with `check := false`). Heartbeats = whole theorem incl. the kernel check (`count_hb`, synchronous); CPU = whole module.

| n | proof | result | heartbeats | CPU | olean |
|---|---|---|---|---|---|
| 100 | `rfl` | ok | 362k | 2.50 s (user 0.89) | 6.9 kB |
| 100 | `by rfl` | ok | 172k | 2.06 s (user 0.85) | 6.7 kB |
| 100 | `by decide` | ok | 156k | 2.03 s (user 0.88) | 7.9 kB |
| 100 | `by decide_cbv` | ok | 3,239k | 2.97 s (user 1.55) | 3.91 MB |
| 100 | `by decide +kernel` | ok | 74k | 1.78 s (user 0.73) | 8.1 kB |
| 100 | `by kernel_rfl` | ok | 72k | 1.60 s (user 0.68) | 6.7 kB |
| 1000 | `rfl` | error: `maximum recursion depth has been reached` | 169k | 1.16 s (user 0.59) |  |
| 1000 | `by rfl` | error: `maximum recursion depth has been reached` | 173k | 1.60 s (user 0.72) |  |
| 1000 | `by decide` | error: `maximum recursion depth has been reached` | 171k | 1.17 s (user 0.64) |  |
| 1000 | `by decide_cbv` | error: `maximum recursion depth has been reached` | 172k | 1.65 s (user 0.66) |  |
| 1000 | `by decide +kernel` | ok | 444k | 1.49 s (user 0.70) | 8.1 kB |
| 1000 | `by kernel_rfl` | ok | 449k | 1.58 s (user 0.72) | 6.7 kB |

`kernel_rfl` on a false goal (`(List.range 20).foldl (· + ·) 0 = 1`): the kernel rejects it:

```
F.lean:2:8: error: (kernel) declaration type mismatch, 'bad' has type
  List.foldl (fun x1 x2 => x1 + x2) 0 (List.range 20) = List.foldl (fun x1 x2 => x1 + x2) 0 (List.range 20)
but it is expected to have type
  List.foldl (fun x1 x2 => x1 + x2) 0 (List.range 20) = 1
```
