# decide

`decide` vs `decide +kernel` vs `native_decide`; List vs Array scans in the kernel;
well-founded recursion.

Recorded 2026-10-31 by `examples/run.py decide` (32 CPUs, load 62; CPU = user + sys seconds, user in parentheses; median of 3 runs where repeated).

Toolchain: `Lean (version 4.34.0, x86_64-unknown-linux-gnu, commit 293d5d0c0c3f3dded4688b3ccd6a33939ac5102b, Release)`.

| file | result | CPU | max RSS | output (start) |
|---|---|---|---|---|
| `Decide` | ok | 1.87 s (user 0.85) | 1.55 GB | heartbeats: 374k 'd' does not depend on any axioms |
| `DecideDeep` | error | 0.57 s (user 0.22) | 0.46 GB | DecideDeep.lean:2:54: error: maximum recursion depth has been reached use `set_option maxRecDepth <num>` to increase limit use `set_option diagnostics true` to  |
| `DecideKernel` | ok | 1.93 s (user 0.80) | 1.55 GB | heartbeats: 140k 'd' does not depend on any axioms |
| `DecideKernelLarge` | ok | 1.48 s (user 0.79) | 0.56 GB |  |
| `DecideKernelHuge` | error | 2.04 s (user 1.07) | 0.60 GB | DecideKernelHuge.lean:2:55: error: (kernel) deep recursion detected, use `set_option maxRecDepth <num>` to increase the limit |
| `NativeDecide` | ok | 1.71 s (user 0.78) | 1.55 GB | heartbeats: 69k 'd' depends on axioms: [d._native.native_decide.ax_1] |
| `ListScan` | ok | 0.73 s (user 0.30) | 0.47 GB |  |
| `ArrayScan` | ok | 90.32 s (user 37.89) | 6.56 GB |  |
| `WellFounded` | error | 1.64 s (user 0.35) | 0.45 GB | WellFounded.lean:8:36: error: Tactic `decide` failed for proposition sumWF 100 = 5050 because its `Decidable` instance |
| `WellFoundedKernel` | ok | 0.80 s (user 0.25) | 0.47 GB |  |

`WellFounded.lean` output:

```
WellFounded.lean:8:36: error: Tactic `decide` failed for proposition
  sumWF 100 = 5050
because its `Decidable` instance
  instDecidableEqNat (sumWF 100) 5050
did not reduce to `isTrue` or `isFalse`.

After unfolding the instances `instDecidableEqNat` and `Nat.decEq`, reduction got stuck at the `Decidable` instance
  match h : (sumWF 100).beq 5050 with
  | true => isTrue ⋯
  | false => isFalse ⋯
WellFounded.lean:9:36: error: Tactic `rfl` failed: The left-hand side
  sumWF 100
is not definitionally equal to the right-hand side
  5050

⊢ sumWF 100 = 5050
```
