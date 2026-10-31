# snippets

The code snippets of the skills compile with the official toolchain.

Recorded 2026-10-31 by `examples/run.py snippets` (32 CPUs, load 62; CPU = user + sys seconds, user in parentheses; median of 3 runs where repeated).

Toolchain: `Lean (version 4.34.0, x86_64-unknown-linux-gnu, commit 293d5d0c0c3f3dded4688b3ccd6a33939ac5102b, Release)`. `lean snippets/Snippets.lean`: ok, 3.29 s (user 0.92) CPU. Output:

```
heartbeats: 236k
'kernel_decide' does not depend on any axioms
@[defeq] theorem rfl_tagged : ∀ (n : Nat), n + 0 = n :=
fun n => rfl
theorem rfl_untagged : ∀ (n : Nat), n + 0 = n :=
fun n => rfl
```
