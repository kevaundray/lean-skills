---
name: lean-proof-performance
description: Diagnose and fix slow Lean 4 proofs, modules and builds. Use when a Lean file or lake build is slow, hits maxHeartbeats, maxRecDepth or "(kernel) deep recursion", needs many GB of memory, or writes .olean files of tens of MB; when choosing between simp, unfold, rfl, decide, decide +kernel and native_decide; or before raising heartbeat limits.
---

# Lean proof performance

Measure, find the expansion, fix the proof. Do not "fix" a slow proof by raising `maxHeartbeats`/`maxRecDepth`. Numbers are CPU seconds (user+sys) with official Lean 4.34.0 unless stated; `examples/` in this repo (github.com/kevaundray/lean-skills) has every experiment (`examples/run.py <name>`, recorded output in `examples/results/<name>.md`). Real-project numbers are credited to ssz-fv (`learnings.md`), eth-act/clifv (`LEARNINGS.md`) or our profiles of ArkLib/evm-asm.

## 1. Measure

- **Per module**, dependencies built: `lake env /usr/bin/time -f '%U+%S s %M KB' lean Foo/Bar.lean`. Compare CPU (user+sys), not wall time, on shared machines; take the median of repeats.
- **Per declaration and category**: `set_option profiler true` (or `lean -Dprofiler=true`). Prints `<decl> took <t>` lines and cumulative times: `simp`, `type checking` (= kernel), `typeclass inference`, `tactic execution`, `elaboration`. The `simp` bucket also contains work done under it.
- **Inside a tactic**: `set_option trace.profiler true` and `set_option trace.profiler.threshold 100` (ms) print a timed tree. Look for `[Meta.realizeConst]` (generated equation lemmas/splitters), `[Meta.isDefEq]`/`[Meta.whnf]` with large times (unification unfolding big terms), `[Meta.synthInstance]`.
- **Deterministic before/after**: heartbeats (thousands = the unit of `maxHeartbeats`). Mathlib: `count_heartbeats in`. Core only: `examples/lib/HB.lean` (`count_hb in <command>`, ~10 lines over `IO.getNumHeartbeats`).
- **`.olean` size**: a proof-only module should be well under 1 MB. Tens of MB means generated constants or huge terms. `lean --run examples/lib/OleanStats.lean M.olean` counts stored constants, `match_N.eq_i` equations, splitters and equation lemmas.
- **Test with `theorem`, not `example`**: constants realized inside an `example` (equation lemmas, splitters) are discarded, so an `example` hides what would be stored (`stuck-match`: same 64.9M heartbeats, 2.8 kB instead of 39.4 MB `.olean`).
- **Audit**: `#print axioms thm`. Look for `sorryAx`, `skippedProof` (fast-lean shortcuts) and `thm._native.native_decide.ax_*` (`native_decide`, Lean 4.29–4.35).
- Errors arrive late in heavy modules: ssz-fv's parse error on line 10 surfaced after 128–134 s, so iterate in small modules.

## 2. Pathologies and fixes

### `simp` over a large stuck `match`

- **Symptom**: an importer of an N-constructor `match` function (instruction sets) takes minutes; its `.olean` is tens of MB, mostly private `…match_1.eq_<i>`; `trace.profiler` shows `[Meta.realizeConst] …match_1.splitter`.
- **Cause**: `simp` meets `match x with …` where `x` is a local variable (e.g. after unfolding a `foldl` step function `fun t op => op.effect t`). `Simp.simpMatchCore` calls `Match.getEquationsFor`, which generates the splitter and N equations (private, so every module regenerates them), and tries every equation, each attempt O(N): Θ(N²) per occurrence. Present in official Lean 4.29–4.35 (checked); fix proposed in leanprover/lean4#15755 (included in the fast-lean dev toolchains).
- **Fix**: never let `simp` unfold a function that matches on a variable of a large inductive. Give it per-constructor or per-cons step lemmas (`block_cons`/`block_nil`), or define the recursion structurally. See `lean-asm-proofs`.
- **Numbers** (`examples/results/stuck-match.md`, goal `block [.o1, .o2] s = s + 1 + 2`):

  | N | `simp [block, Op.effect]` | step lemmas `simp [block_cons, block_nil, Op.effect]` |
  |---|---|---|
  | 100 | 4.5M heartbeats, 2.7 MB olean | 79k, 11 kB |
  | 200 | 17.0M, 10.1 MB | 119k, 11 kB |
  | 400 | 64.9M, 39.4 MB, 25.8 s CPU (imports alone 1.7 s) | 196k, 11 kB |

  Structural recursion behaves like the step lemmas (203k at N = 400); the dev toolchain with the fix needs 781k for the bad proof. leanprover/lean4#15754: N = 800 exceeds the default `maxHeartbeats`. ssz-fv ARM: whole build 25,554 → 7,344 CPU-s.

### Equation lemmas generated in every importer

- `simp [f]`/`rw [f]` on a definition by pattern matching needs `f.eq_1..eq_N`. They are generated when first needed and stored in that module; for an N-arm `match` this costs O(N²) in official Lean. If no upstream module needed them, every importer regenerates them.
- **Fix**: force generation once in the defining module: `attribute [local simp] f` right after `f`. `examples/results/eqns-upstream.md` (N = 400, four importers each `simp [Op.effect]` on a concrete goal): without it each importer took 18–23 s and stored 39.7 MB (87 s in total); with it the defining module took 31 s once and each importer 0.3–0.6 s with a 7 kB `.olean` (33 s in total). ssz-fv: eleven importers dropped from 52 MB / 25–55 s to < 1 MB / 2–5 s.
- When one unfolding suffices, `unfold f`, `rw [f.eq_def]` or `simp only [f.eq_def]` avoid generating the N equations (`examples/results/eq-def.md`, N = 400, no upstream equations: `simp [Op.effect]` 19.6 s and 39.7 MB; `unfold`, `rw [Op.effect.eq_def]`, `simp only [Op.effect.eq_def]` 0.8–1.1 s and 0.1 MB, of which ~0.5 s is the import).

### `:= rfl` lemmas are `@[defeq]`

- The syntax `theorem foo : a = b := rfl` tags `foo` `@[defeq]` (shown by `#print foo`; Lean 4.26–4.35); `:= (rfl)` and `:= by rfl` do not. `simp` applies `@[defeq]` lemmas without recording a proof step (`implicitDefEqProofs`), so the kernel re-derives them by unfolding.
- Cheap for small terms (`examples/results/defeq-step-lemmas.md`: 1,380k vs 1,157k heartbeats, kernel 29 ms vs 10 ms), expensive when the unfolded terms are big: ssz-fv step lemmas over a 603-arm `match`: 37 → 195 s, 38 → 964 s, one `(kernel) deep recursion`; clifv monad laws on a big concrete state: 23.6 GB / 128 s → 2.1 GB / 21 s after proving them by `rw`.
- **Fix**: prove unfolding/step lemmas used by `simp` on big terms with `(rfl)`, `by rfl` or `rw`.

### Broad `simp` where a lemma exists

- Each broad `simp [defs…]` re-expands the same structures. ssz-fv: one goal 19.6 s by `simp [block, Op.effect, …]` vs 0.56 s by `exact block_error …`; a module with eight such calls spent 125 of 127 s in `simp`.
- **Fix**: state goals in the form of existing summary lemmas and apply them; use `simp only [small set]`; prove frame lemmas once by induction (`examples/results/frame-lemma.md`: ten call sites 2.6 s by `simp` vs 0.3 s by the lemma, which costs 1.7 s once). Don't unfold a definition before applying the theorem that summarises it.
- `simp` calls that alternate several passes over a big hypothesis, or catch-all equation lemmas with side conditions, multiply the cost (clifv: one `simp only` with the union of the sets, constructor-case lemmas instead of the catch-all: about half the heartbeats per module). A `simp` pre-procedure that only touches the head of a `bind` chain took one of clifv's interpreter evaluations from 180 to 30 s.

### Literal listings and tables

- Facts about concrete data (`prog[k]? = some i`): `decide` or `rfl`, not `simp [prog]` (`examples/results/listing-lemmas.md`, 60 fetch lemmas over 80 instructions, above the module without lemmas: `simp [prog]` 4.6 s, `rfl` 1.6 s, `decide` 0.6 s). ssz-fv x86 had 66 such lemmas each running a broad `simp` over a 78-instruction listing.
- Never reduce a whole generated table in one proof. Generate literal data with an untrusted generator, check it leaf-wise with small `decide +kernel` certificates (clifv: whole-table `decide`/`native_decide` hit 20+ GB). Chunk leaves whose environments blow up (clifv: killed at 22 GB → 4.5 GB / 119 s with 32-environment chunks; chunk size is per leaf).
- Evaluate a shared expensive computation once per certificate: one `decide +kernel` over the conjunction instead of seven over the parts (clifv: 748 → 66 s).

### `decide`, `decide +kernel`, `native_decide`

`examples/results/decide.md`, goal `∀ x ∈ List.range n, x * x % 7 ≠ 3`:

| Tactic | Evaluates in | Trust | Measured |
|---|---|---|---|
| `decide` | elaborator (`whnf` of the instance), then the kernel again | kernel | n = 100: 374k heartbeats; n = 150: `maximum recursion depth has been reached` |
| `decide +kernel` | kernel only | kernel, no extra axioms | n = 100: 140k heartbeats; n = 3000 fine; n = 5000: `(kernel) deep recursion detected` |
| `native_decide` | compiled code | adds the axiom `thm._native.native_decide.ax_*`; trusts the compiler | n = 100: 69k heartbeats; often banned in verification projects (clifv removed all of them from its theorems) |

Default to `decide +kernel` for closed computations. Split long recursions into chunks (lemmas over sublists) rather than raising `maxRecDepth`.

### Kernel evaluation

- **Scan `List`s, not `Array`s**: `(Array.range 700).find? (· == 699) = some 699` by `decide +kernel`: 88 s CPU (38 s user) and 6.5 GB; the same with `List.range`: 0.6 s and 0.46 GB, the cost of starting Lean (`examples/results/decide.md`). clifv: 4.3 GB / 17–30 s → 0.48 GB / 0.25 s; keep the `Array` code for runtime via `@[csimp]`.
- **Structural, not well-founded recursion** for anything `decide`/`rfl` must evaluate: definitions by well-founded recursion are irreducible to the elaborator (`decide` gets stuck, `rfl` fails); `decide +kernel` did evaluate `sumWF 100` (`examples/decide/WellFounded.lean`), but clifv found kernel reduction of well-founded definitions impractical ("slowly, or at all in practice"). clifv: rewriting `fitsCl`/`fitsTy` structurally made failing certificates pass.
- **Opaque checked caches** (from Th0rgal/evm.fast-dev via clifv, not measured by us): `opaque boxedValue (v : α) : {r // r = v} := ⟨v, rfl⟩` stops the kernel from reopening a large intermediate value.

### Unification that unfolds big definitions

- `assumption`, `exact`, `refine` and `first | exact a | exact b | …` unify at default transparency and may unfold large definitions on every failed attempt. Use `with_reducible assumption`/`with_reducible exact h`, and name the right lemma per goal (clifv: 33.2 G → 0.39 G heartbeats; 815 s / 8.3 GB → 16 s / 0.4 GB; a `first | exact …` chain over goals mentioning a big planner exceeded 200,000 heartbeats, explicit lemmas: ~9 s).
- Let unification fill big arguments of a lemma (`foo _ s`, `rw [foo]`, `apply foo`) instead of restating them: elaborating a big concrete argument separately makes `isDefEq` compare two copies and it may evaluate them (`examples/results/frame-lemma.md`: `exact block_f7 [<60 ops>] s` hit the heartbeat limit after 10 s; `block_f7 _ s` took milliseconds per site).
- `subst_vars` `whnf`s both sides of every equation per rescan (clifv: 95% of a 1,420 s proof; a `whnfR` variant: 838 → 28 s).

### Kernel deep recursion, huge terms, memory

- `(kernel) deep recursion` and multi-GB kernel checks come from huge terms: expanded machine states, `@[defeq]` steps over them, whole-structure equalities. Split into opaque summaries (ssz-fv: deep-recursion failure after ~112 s → 4.5 s module), prove only the fields you need (ssz-fv: whole-memory equality timed out at 592 s / 16M heartbeats; field observations 38 s).
- Peak memory per module ≈ its heaviest declarations together; split modules to lower it (`lean-build-hygiene`).

### Search tactics

- Tactics that try methods in order under budgets (a custom `bv` search, `first | omega | bv_decide | …`) pay for every failing method. Find which goal shapes reach the expensive fallback (log goal and winning method) and add the one lemma that closes that shape to the first method (clifv: 4,541 → 152 s, 6,575 → 290 s per module).
- Budgets reset inside such searches may hide their cost from `maxHeartbeats` (clifv's `kbv`): measure the search separately.
- `bv_decide` produces and checks an LRAT certificate; keep `Elab.async` on in `bv_decide`-heavy modules (clifv: 1,652 s off vs 174–186 s on). fast-lean's `sat` mode trusts the solver while iterating.
- evm-asm profile: `isDefEq` inside `simp` ~43% of CPU, then interpreted tactics and `omega`.

### Mathlib-heavy projects

ArkLib (official 4.34.0, 3,394 CPU-s full build): ~45% of CPU under the IR interpreter (Mathlib/Batteries/Aesop tactics and linters run interpreted; core tactics are native), imports ~20% (~1.3 s per module), typeclass search ~15%. Most expensive interpreted tactics: `nlinarith` 113 s, Mathlib's flexible-tactic linter 71 s, `linarith` 23 s, `field_simp` 16 s, then `calc`, `positivity`, `ring_nf`. Look at those calls first. The fast-lean dev toolchains retain interpreter caches across calls.

## 3. Checklist

1. Profile the slow module (`profiler`, then `trace.profiler` on the slow declaration); check `.olean` size.
2. Generated constants in the `.olean`? → stuck `match`/equation regeneration fixes.
3. Kernel (`type checking`) dominates? → `@[defeq]` steps, `Array`/WF evaluation, huge terms.
4. `isDefEq`/`whnf` dominate? → reducible-transparency tactics, explicit lemmas.
5. One `simp` dominates? → summary/frame lemmas, smaller simp sets.
6. Re-measure; keep `maxHeartbeats` default.
