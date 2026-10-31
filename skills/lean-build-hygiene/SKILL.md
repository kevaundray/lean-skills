---
name: lean-build-hygiene
description: Keep Lean 4 / Lake builds reproducible, cacheable and cheap to rebuild. Use when configuring a lakefile (leanOptions, moreLeanArgs, weakLeanArgs), when .olean files differ between worktrees or machines and defeat a shared build cache, when a small change rebuilds far too many modules, when Lean processes run out of memory, or when planning toolchain bumps and import structure in a large Lean project.
---

# Lean build hygiene

Rebuild cost is decided by the import graph and by whether outputs are byte-identical. Facts below are from official Lean/Lake experiments in this repo (`examples/results/`) or from eth-act/clifv `LEARNINGS.md` (credited as clifv).

## Deterministic `.olean`s: keep linter warnings out of them

- Lean stores every linter warning in the `.olean` together with the source file name Lake passed, which is absolute. The same module built in two directories gives different `.olean` bytes, so every importer misses a shared cache. Measured (`examples/results/olean-paths.md`): with one unused-variable warning, Lean 4.31.0, 4.33.1, 4.34.0 and 4.35.0 write different `.olean`s that contain the path; with the linter off they are identical. Lean 4.29.0 does not store the warning.
- Fix: turn noisy linters off for builds only, in `weakLeanArgs`:

  ```toml
  [[lean_lib]]
  name = "MyLib"
  weakLeanArgs = ["-Dlinter.unusedVariables=false", "-Dlinter.unusedSimpArgs=false"]
  ```

  `weakLeanArgs` is not part of the module trace: adding it did not rebuild anything, while the same flag in `moreLeanArgs` did, and fresh builds in two directories were then byte-identical (`examples/results/lake-weak-args.md`). The editor (`lake serve` uses `leanOptions`) still shows the warnings. clifv found 337 of 1,922 oleans carrying a worktree path, from `unusedSimpArgs`, `unusedVariables`, `unnecessarySimpa`, `unusedSectionVars`, `defProp`, `constructorNameAsVariable`; a nondeterministic `IselTermFactsCall` rebuilt 30 downstream modules (one ~1,930 s).
- To find the culprits: `grep -c "$PWD" .lake/build/lib/lean/**/*.olean`, or build the same commit in two directories and compare hashes.
- Use `leanOptions`/`moreLeanArgs` only for options that change results (they are traced); use `weakLeanArgs` for diagnostics-only options.

## Import graph

- Import only the modules you use; never import an umbrella module from a hub file. clifv: replacing one umbrella import in a generated hub cut the modules rebuilt after a backend change from 1,630–1,690 to 330–445 (≈12.3 h → 2 h of module time).
- Keep heavy dependencies (Mathlib) out of the main graph when only a leaf needs them: put the leaf in its own Lake package that nothing imports. clifv: making a core module import Mathlib-dependent code put 1,778 Mathlib modules upstream of 2,624 of 2,812 modules, +1.4 GB peak memory and +3–4 s import per module.
- Loading a Mathlib-sized environment costs ~1.3 s CPU per module (ArkLib profile, Lean 4.34.0); imports were ~20% of that project's build CPU.
- A leaf package can pin its own `lean-toolchain` instead of bumping the whole repository for one dependency (clifv: a repo-wide 4.34.1 → 4.35.0 bump stalled on breakages; the leaf package on 4.35.0 compiled the shared core modules unchanged).

## Module size and memory

- One `lean` process per module; its peak memory is roughly its heaviest declarations together. Splitting a heavy module into parts (keep the old module as a file importing the parts, so importers don't change) lowers the peak and lets the parts build in parallel. clifv: 19.3 → 6.1 GB, 15.2 → 4.5 GB; no gain when one declaration alone is the peak. Splitting does not make the same reduction cheaper; it only helps when it isolates obligations or dependencies (ssz-fv).
- Memory-cap every Lean process (cgroup/`systemd-run --user -p MemoryMax=...`) on shared machines; one runaway `lean` can trigger global OOM kills (clifv).
- More threads per Lean process rarely help: slow modules spend their time in one declaration (clifv: median CPU/wall 1.01 over 4,198 module builds). Exception: keep `Elab.async` on for `bv_decide`-heavy modules (clifv: 1,652 s off vs 174–186 s on, at about twice the memory).

## Caches and rebuild checks

- Official `lake exe cache get` (Mathlib) oleans are reused as is, also by the fast-lean dev toolchains (see the `fast-lean` skill).
- Ask Lake once what is out of date instead of starting one `lake build <M>` per module: `lake build --no-build <targets>` builds nothing; it names each out-of-date module (`error: target is out-of-date and needs to be rebuilt`) and exits non-zero (3 with Lake 4.34), and prints `All targets up-to-date` otherwise. clifv's scheduler uses one such call per batch: a fully cached 3,138-module check went from 27.5 min to 1.9 s.
- Don't build the same module concurrently in two worktrees that share a cache; the second build gains nothing (clifv serialises them with a per-module `flock`).
- Hard-linked cache outputs are read-only; building over them fails with `permission denied` at the end of the build (clifv). Unlink a module's outputs before rebuilding it.

## Keep limits at their defaults

Keep `maxHeartbeats`/`maxRecDepth` at their defaults; raise them only locally (`set_option maxHeartbeats N in`) with a reason. A raised limit hides the expansion that the `lean-proof-performance` skill would find.
