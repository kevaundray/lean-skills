---
name: fast-lean
description: Iterate on Lean 4 projects faster with fast-lean, a wrapper around Lake that builds with a patched development toolchain (eth-act/lean4 dev-fast-*) which can skip proof elaboration, kernel checking and SAT certificate checking in the modules you are not working on. Use when a Lean project on a supported version builds slowly while developing, when you need to check one module or file quickly against freshly changed dependencies, or when asked about fast-lean, LEAN_DEV, LEAN_DEV_CHECK, dev.skipProofs or the skippedProof axiom. Always finish with an official lake build.
---

# fast-lean

`fast-lean build` instead of `lake build` while iterating; plain `lake build` (official toolchain) before you report success, which re-checks everything fast-lean built. Source: `script/fast-lean` and `fast-lean --help` in the `dev-fast-<version>` branches of eth-act/lean4, `README.md` of its `fast-lean-dist` branch.

## Install and check support

```sh
curl -sSfL https://raw.githubusercontent.com/eth-act/lean4/fast-lean-dist/install.sh | sh   # needs elan, bash, curl
fast-lean --help
```

The installer only puts the script into `~/.local/bin`. On first use in a project, fast-lean reads `lean-toolchain` and installs the matching fast toolchain with elan, from the version map (`versions.txt` on the `fast-lean-dist` branch). At the time of writing: v4.31.0, v4.33.1 and v4.34.0. Other versions (e.g. v4.34.1) run plain `lake` with the note `fast-lean: no fast toolchain for ...`. A locally built toolchain linked as `dev-fast-vX.Y.Z` (`elan toolchain link`) takes precedence. `lean-toolchain` and elan overrides are never changed.

## Use

```sh
fast-lean build                    # like `lake build`, with shortcuts (default LEAN_DEV=proofs,sat)
fast-lean build My.Module          # check My.Module fully; its dependencies take shortcuts
fast-lean build +Foo               # the module Foo (a bare `Foo` is a library/package target)
fast-lean lean My/Module.lean      # like `lake lean`: this file fully (except `sat`), imports with shortcuts
LEAN_DEV= fast-lean build          # faithful: dev toolchain, no shortcuts
LEAN_DEV_CHECK=My.Area fast-lean build   # also check modules with these name prefixes fully
LEAN_DEV_NATIVE=1 fast-lean build  # also run dependencies' tactics natively (Linux)
lake build                         # official toolchain: rebuilds and fully checks what fast-lean built
```

`LEAN_DEV` is a comma-separated list applied to modules Lake (re)builds:

| Mode | Effect | Visible as |
|---|---|---|
| `proofs` | theorem/example proofs are not elaborated; they become the axiom `skippedProof`. Kept: `rfl`, `by rfl`, `by exact rfl`, `Eq.refl _` (cheap; `:= rfl` ones are `@[defeq]` and used by `dsimp`), and proofs whose goal still has metavariables | `#print axioms` lists `skippedProof` |
| `checks` | no kernel type checking, no linters | — |
| `sat` | `bv_decide` trusts the SAT solver's UNSAT answer (no LRAT check) and caches solved problems in `~/.cache/lean/trusted-unsat` | `skippedProof` |

Statements, definitions and their compiled code are still elaborated, so type errors in statements and broken downstream uses show up; errors inside skipped proofs do not.

`LEAN_DEV_NATIVE=1` (Linux, opt-in, in dev toolchains whose `fast-lean --help` lists it) compiles the dependencies' modules that the project imports to a native shared library per package and loads them, so Mathlib/Batteries/Aesop tactics and linters run natively instead of in the interpreter. Outputs are unchanged and it works with faithful mode (`LEAN_DEV=`). The first build compiles the dependencies (minutes for Mathlib; cached in `~/.cache/fast-lean/native`), later builds save about 5–10% CPU on Mathlib-heavy projects: in faithful mode ArkLib −8% total / −13% user CPU, clean −7.5% user. It covers dependency packages only; tactics defined in the project itself stay interpreted.

## Guarantees

- Everything fast-lean builds (modules, native code, elaborated Lake configs) carries a trace the official toolchain does not accept: a later plain `lake build` rebuilds and fully checks each such module; official outputs that are still up to date are kept.
- fast-lean reuses official outputs (e.g. the Mathlib cache from `lake exe cache get`) as they are; the dev toolchains identify as the upstream release and stay compatible with its compiled code.
- With `LEAN_DEV=` (empty) the dev toolchain elaborates and checks everything like the official one. It also carries performance patches that do not change results (e.g. `simp` skipping inapplicable `match` equations, leanprover/lean4#15755; faster `match` equation generation; retained interpreter caches), so faithful dev builds can already be faster on those pathologies.

## Agent workflow

1. `fast-lean build` once to bring dependencies up to date cheaply.
2. Edit; check the module you are working on with `fast-lean build My.Module` (or `fast-lean lean My/Module.lean`). Its proofs are fully checked; only its dependencies take shortcuts.
3. Never report a proof as done based on a fast-lean build alone. Finish with `lake build` and `#print axioms` on the main theorems: no `skippedProof`, no `sorryAx`. Until `lake build` has rebuilt them, `lake env lean` against fast-lean outputs still shows `skippedProof` for theorems from shortcut modules.

## What it buys

- Proof-skipping mode (`proofs`), our measurements: ArkLib (Mathlib-heavy, v4.34.0) 1.7× faster, clean (v4.33.1) 2.3×.
- Demo project (`examples/results/fast-lean.md`: a 400-instruction module plus a module with the slow stuck-`match` `simp`), CPU of clean builds:

  | Step | CPU | `#print axioms` afterwards |
  |---|---|---|
  | `lake build` (official) | 55.7 s | `[propext]` |
  | `fast-lean build` | 13.8 s | `[Lean.skippedProof]` |
  | then `lake build` (official): rebuilds all 4 targets | 59.9 s | `[propext]` |
  | `LEAN_DEV= fast-lean build` (faithful, perf patches only) | 10.4 s | `[propext]` |
  | `fast-lean build Demo.Top` (`Top` checked, its imports shortcut) | 6.5 s | `top` inherits `skippedProof` from `t` |

  On this demo the gain comes from the performance patches (faithful mode is as fast): the `simp` fix and faster `match` equation generation (`Demo.Ops` alone: 25.9 s official vs 9.2 s dev). The proof-skipping gain is the ArkLib/clean figure above.

It does not speed up the final official build, which a merge gate still needs. clifv found that wrapper tools (turbo-lean) do not help builds dominated by kernel checking of single large declarations (`decide +kernel`/`rfl` over generated data, `bv_decide`). Proof skipping doesn't help the module you are checking either (it is elaborated in full; only the result-preserving performance patches apply); fix the proof (`lean-proof-performance` skill).
