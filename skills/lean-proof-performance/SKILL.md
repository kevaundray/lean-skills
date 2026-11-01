---
name: lean-proof-performance
description: Diagnose and fix slow Lean 4 proofs, modules and builds. Use when a Lean file or lake build is slow, hits maxHeartbeats, maxRecDepth or "(kernel) deep recursion", needs many GB of memory, or writes .olean files of tens of MB; when choosing between simp, unfold, rfl, decide, decide +kernel and native_decide; or before raising heartbeat limits.
---

# Lean proof performance

Measure, find the expansion, fix the proof. Do not "fix" a slow proof by raising `maxHeartbeats`/`maxRecDepth`. Numbers are CPU seconds (user+sys) with official Lean 4.34.0 unless stated; `examples/` in this repo (github.com/kevaundray/lean-skills) has every experiment (`examples/run.py <name>`, recorded output in `examples/results/<name>.md`). Real-project numbers are labelled: [ssz-fv](https://github.com/kevaundray/ssz-fv) (`learnings.md`; Lean 4.31.0, often single-run wall-clock), [eth-act/clifv](https://github.com/eth-act/clifv) (`LEARNINGS.md`; Lean 4.34.1, several machines) and our profiles of [ArkLib](https://github.com/Verified-zkEVM/ArkLib) and [evm-asm](https://github.com/kevaundray/evm-asm) (CPU, official toolchains).

## 1. Measure

- **Per module**, dependencies built: `lake env /usr/bin/time -f '%U+%S s %M KB' lean Foo/Bar.lean`. Compare CPU (user+sys), not wall time, on shared machines; take the median of repeats.
- **Per declaration and category**: `set_option profiler true` (or `lean -Dprofiler=true`). Prints `<decl> took <t>` lines and cumulative times: `simp`, `type checking` (= kernel), `typeclass inference`, `tactic execution`, `elaboration`. The `simp` bucket also contains work done under it.
- **Inside a tactic**: `set_option trace.profiler true` and `set_option trace.profiler.threshold 100` (ms) print a timed tree. Look for `[Meta.realizeConst]` (generated equation lemmas/splitters), `[Meta.isDefEq]`/`[Meta.whnf]` with large times (unification unfolding big terms), `[Meta.synthInstance]`.
- **Deterministic before/after**: heartbeats (thousands = the unit of `maxHeartbeats`). Mathlib: `count_heartbeats in`. Core only: `examples/lib/HB.lean` (`count_hb in <command>`, ~10 lines over `IO.getNumHeartbeats`).
- **`.olean` size**: a proof-only module should be well under 1 MB. Tens of MB means generated constants or huge terms. `lean --run examples/lib/OleanStats.lean M.olean` counts stored constants, `match_N.eq_i` equations, splitters and equation lemmas.
- **Test with `theorem`, not `example`**: constants realized inside an `example` (equation lemmas, splitters) are discarded, so an `example` hides what would be stored (`stuck-match`: same 64.9M heartbeats, 2.8 kB instead of 39.4 MB `.olean`).
- **Audit**: `#print axioms thm`. Look for `sorryAx`, `skippedProof` (fast-lean shortcuts) and `thm._native.native_decide.ax_*` (`native_decide`, Lean 4.29–4.35; before 4.29 it shows as `Lean.ofReduceBool`/`Lean.trustCompiler`, checked on 4.26 and 4.28).
- Errors arrive late in heavy modules: ssz-fv's parse error on line 10 surfaced after 128–134 s, so iterate in small modules.

## 2. Pathologies and fixes

### `simp` over a large stuck `match`

- **Symptom**: an importer of an N-constructor `match` function (instruction sets) takes minutes; its `.olean` is tens of MB, mostly private `…match_1.eq_<i>`; `trace.profiler` shows `[Meta.realizeConst] …match_1.splitter`.
- **Cause**: `simp` meets `match x with …` where `x` is a local variable (e.g. after unfolding a `foldl` step function `fun t op => op.effect t`). `Simp.simpMatchCore` calls `Match.getEquationsFor`, which generates the splitter and N equations (private, so every module regenerates them), and tries every equation, each attempt O(N): Θ(N²) per occurrence. Present in official Lean 4.26–4.35 (`examples/results/versions.md`); fix proposed in leanprover/lean4#15755 (included in the fast-lean dev toolchains).
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
- **Fix**: force generation once in the defining module: `attribute [local simp] f` right after `f`. `examples/results/eqns-upstream.md` (N = 400, four importers each `simp [Op.effect]` on a concrete goal): without it each importer took 18–23 s and stored 39.7 MB (87 s in total); with it the defining module took 31 s once and each importer 0.3–0.6 s with a 7 kB `.olean` (33 s in total). Generating them upstream costs the defining module (here 4.9 → 31 s, `.olean` 10.5 → 49.9 MB), so it pays off once two or more importers need them. ssz-fv: eleven importers had regenerated a 458-arm `Op.effect` (52 MB each); after the whole fix (step lemmas plus upstream equations) they took 2–5 s instead of 25–55 s, with oleans under 1 MB.
- When one unfolding suffices, `unfold f`, `rw [f.eq_def]` or `simp only [f.eq_def]` avoid generating the N equations (`examples/results/eq-def.md`, N = 400, no upstream equations: `simp [Op.effect]` 19.6 s and 39.7 MB; `unfold`, `rw [Op.effect.eq_def]`, `simp only [Op.effect.eq_def]` 0.8–1.1 s and 0.1 MB, of which ~0.5 s is the import).

### `:= rfl` lemmas are `@[defeq]`

- The syntax `theorem foo : a = b := rfl` tags `foo` `@[defeq]` (shown by `#print foo`; Lean 4.26–4.35, `examples/results/versions.md`); `:= (rfl)` and `:= by rfl` do not. `simp` applies `@[defeq]` lemmas without recording a proof step (`implicitDefEqProofs`), so the kernel re-derives them by unfolding.
- Cheap for small terms (`examples/results/defeq-step-lemmas.md`: 1,380k vs 1,157k heartbeats, kernel 29–39 ms vs 10–18 ms), expensive when the unfolded terms are big: ssz-fv step lemmas over a 603-arm `match`: 37 → 195 s, 38 → 964 s, one `(kernel) deep recursion`; clifv monad laws on a big concrete state: 23.6 GB / 128 s → 2.1 GB / 21 s after proving them by `rw`.
- **Fix**, either: prove step lemmas used by `simp` on big terms with `(rfl)`, `by rfl` or `rw` (untagged, so `dsimp` cannot use them: `dsimp only [block_cons]` then fails with "`dsimp` made no progress"); or keep `:= rfl` (usable by `dsimp`) and call `simp -implicitDefEqProofs [...]` where the term is big, which records the steps (`examples/results/defeq-step-lemmas.md`: same heartbeats and kernel time as the untagged lemmas). Lean core itself uses `-implicitDefEqProofs` in `bv_omega` and in grind's simp utilities.

### Broad `simp` where a lemma exists

- Each broad `simp [defs…]` re-expands the same structures. ssz-fv: one goal 19.6 s by `simp [block, Op.effect, …]` vs 0.56 s by `exact block_error …`; a module with eight such calls spent 125 of 127 s in `simp`.
- **Fix**: state goals in the form of existing summary lemmas and apply them; use `simp only [small set]`; prove frame lemmas once by induction (`examples/results/frame-lemma.md`: ten call sites 2.1–2.6 s by `simp` vs 0.3–0.4 s by the lemma, which costs 1.5–1.7 s once). Don't unfold a definition before applying the theorem that summarises it.
- `simp` calls that alternate several passes over a big hypothesis, or catch-all equation lemmas with side conditions, multiply the cost (clifv: one `simp only` with the union of the sets, constructor-case lemmas instead of the catch-all: about half the heartbeats per module). A `simp` pre-procedure that only touches the head of a `bind` chain took one of clifv's interpreter evaluations from 180 to 30 s.

### Literal listings and tables

- Facts about concrete data (`prog[k]? = some i`): `by decide` or `by rfl`, not `simp [prog]` (`examples/results/listing-lemmas.md`, 60 fetch lemmas over 80 instructions, above the module without lemmas: `simp [prog]` +5.7 s, `decide`/`rfl`/`by rfl` +0.4–0.7 s, within noise of each other). Avoid the term `:= rfl`: in a 400-entry listing the lemma for entry 390 hit `maximum recursion depth` with `:= rfl` but passed with `by rfl`, `by decide` and `by decide +kernel` (ssz-fv saw the same); it also tags the lemma `@[defeq]`. ssz-fv x86 had 66 such lemmas each running a broad `simp` over a 78-instruction listing.
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

- **Scan `List`s, not `Array`s**: `(Array.range 700).find? (· == 699) = some 699` by `decide +kernel`: 73–90 s CPU (37–38 s user) and 6.5 GB; the same with `List.range`: 0.6–0.7 s and 0.47 GB, the cost of starting Lean (`examples/results/decide.md`). clifv: 4.3 GB / 17–30 s → 0.48 GB / 0.25 s; keep the `Array` code for runtime via `@[csimp]`.
- **Structural, not well-founded recursion** for anything `decide`/`rfl` must evaluate: definitions by well-founded recursion are irreducible to the elaborator (`decide` gets stuck, `rfl` fails); `decide +kernel` did evaluate `sumWF 100` in 0.7 s for the whole file (`examples/decide/WellFoundedKernel.lean`), but clifv found kernel reduction of well-founded definitions impractical ("slowly, or at all in practice"). clifv: rewriting `fitsCl`/`fitsTy` structurally made failing certificates pass.
- **Opaque checked caches** (from Th0rgal/evm.fast-dev via clifv, not measured by us): `opaque boxedValue (v : α) : {r // r = v} := ⟨v, rfl⟩`. Compute a large intermediate value once, refer to it as `(boxedValue v).1` and rewrite with `(boxedValue v).2 : (boxedValue v).1 = v` only where needed; the kernel cannot unfold an `opaque` constant, so it never re-evaluates the value behind it.

### `rfl` and `decide` on big closed terms

- The elaborator's `rfl`/`by rfl`/`decide` evaluate with `whnf`/`isDefEq` in `Meta` before the kernel checks the same thing again; `decide +kernel` and a kernel-only `rfl` skip the first evaluation. A kernel-only `rfl` (clifv's `kernel_rfl`, `examples/lib/KernelRfl.lean`):

  ```lean
  elab "kernel_rfl" : tactic => liftMetaFinishingTactic fun g => g.refl (check := false)
  ```

  The kernel still checks the declaration: on a false goal it fails with `(kernel) declaration type mismatch`. `examples/results/kernel-rfl.md`, goal `(List.range n).foldl (· + ·) 0 = n(n-1)/2`: at n = 100 term `rfl` 362k heartbeats, `by rfl` 172k, `by decide` 156k, `decide +kernel` 74k, `kernel_rfl` 72k; at n = 1000 all elaborator variants fail with `maximum recursion depth` and both kernel-only ones pass (~450k).
- `decide_cbv` stores the evaluation steps in the proof term: n = 100 3,239k heartbeats and a 3.9 MB `.olean` (vs 8 kB for `decide +kernel`); it also hit `maxRecDepth` at n = 1000. clifv: replacing `decide_cbv` by `of_decide_eq_true (by kernel_rfl)` shrank a 30.6 MB `.olean` to 33 kB; its `KillTermIds` `decide_cbv` proof was 245 MB and 475 s (official 4.34.1). When one big `decide +kernel` does not fit in memory either (clifv: `KillTermIds` was OOM-killed at 20 GB), chunk the check into per-entry certificates (clifv's `RelocProvTab` pattern; see "Literal listings and tables").
- clifv profiles (official 4.34.1, gperftools): `RuleShifts1` spent 627 s of 1,249 s of profiled events in `eqRefl`/`applyRfl` (elaborator `rfl` on big terms); `decide` on huge goals in `RuleImm` spent 25–37% of samples in `Expr.equal`, from `inferType` cache-key comparisons on huge terms (`mkDecideProof`). Both point to the kernel-only variants above.

### Unification that unfolds big definitions

- `assumption`, `exact`, `refine` and `first | exact a | exact b | …` unify at default transparency and may unfold large definitions on every failed attempt. Use `with_reducible assumption`/`with_reducible exact h`, and name the right lemma per goal (clifv: 33.2 G → 0.39 G heartbeats; 815 s / 8.3 GB → 16 s / 0.4 GB; a `first | exact …` chain over goals mentioning a big planner exceeded 200,000 heartbeats, explicit lemmas: ~9 s).
- Let unification fill big arguments of a lemma (`foo _ s`, `rw [foo]`, `apply foo`) instead of restating them in an application elaborated against the goal (`examples/results/frame-lemma.md`: `exact block_f7 [<60 ops>] s` and the term `block_f7 [<60 ops>] s` hit the heartbeat limit after ~10 s, evaluating the block; `have h := block_f7 [<60 ops>] s; exact h` checked in 0.66 s for the whole module; `block_f7 _ s` took milliseconds per site).
- `subst_vars` `whnf`s both sides of every equation per rescan (clifv: 95% of a 1,420 s proof). clifv's `FV/Backend/Proof/FastSubst.lean` copies `substVars` with `whnfR` instead of `whnf` of the sides: 838 → 28 s.

### Kernel deep recursion, huge terms, memory

- `(kernel) deep recursion` and multi-GB kernel checks come from huge terms: expanded machine states, `@[defeq]` steps over them, whole-structure equalities. Split into opaque summaries (ssz-fv: deep-recursion failure after ~112 s → 4.5 s module), prove only the fields you need (ssz-fv: whole-memory equality timed out at 592 s / 16M heartbeats; field observations 38 s).
- Peak memory per module ≈ its heaviest declarations together; split modules to lower it (`lean-build-hygiene`).
- Kernel-heavy `decide +kernel` modules hold big kernel caches: clifv's (official 4.34.1) peak at 4–9 GB RSS, and their time goes to kernel cache upkeep (lookups, inserts, freeing: ~60% of `StockScalarAddCode`) and first-touch page faults (18–25%); here `(Array.range 700).find?` took 6.5 GB. Keep one entry per `decide`, and use `boxedValue`-style checkpoints ("Kernel evaluation") where one evaluation is shared.

### Search tactics, `first` chains and heartbeat budgets

- `first | a | b | c | d` pays for every failed alternative on every build, not only while you search. Once a proof is found, call the winning alternative directly (or have the search tactic record the winner per goal). `examples/results/first-chain.md`: ten goals by `first | omega | (simp; done) | decide +kernel` 2,346k heartbeats vs 1,346k by `decide +kernel` alone (CPU within noise here, because these alternatives fail fast; expensive failing alternatives cost real time). clifv `RuleShifts1` (official 4.34.1, one run each): calling only the winning template per theorem instead of a `first` over four templates cut module CPU ~11% and peak RSS 6.3 → 4.9 GB.
- Search tactics that try methods in order (a custom `bv` search, `first | omega | bv_decide | …`) pay most for goals that only a late method closes. Find which goal shapes reach the expensive fallback (log goal and winning method) and add the one lemma that closes that shape to the first method (clifv: 4,541 → 152 s, 6,575 → 290 s per module).
- **Don't let the proof depend on a heartbeat budget.** Heartbeats count work units, not time: one per small Lean object allocated (`lean_alloc_small_object`) plus one per node visited by `Expr.equal` (`src/runtime/alloc.cpp`, `src/kernel/expr_eq_fn.cpp`). They are deterministic for a given Lean build but change with Lean's implementation. A search that gives each alternative a fixed budget (`maxHeartbeats` on a sub-tactic, caught with `tryCatchRuntimeEx`; plain `try`/`first` do not catch heartbeat errors) therefore picks its winner by Lean version. `examples/results/budget.md` (`lib/Budget.lean`, goal `∀ x ∈ List.range 100, x * x % 7 ≠ 3`): `decide` needs 272k heartbeats on 4.29.0, 251k on 4.31.0, 247k on 4.33.1–4.34.1 and ~228k on 4.35.0, so `first | budget 250 => decide | decide +kernel` proves the theorem with `decide` on 4.31–4.35 and with the fallback on 4.29 (budget 240k: only 4.35 uses `decide`); the `.olean` differs accordingly. A failing budgeted alternative costs its whole budget on every build (budget 240k: 370k heartbeats in total vs 140k for the fallback alone). clifv saw the same with a Lean patch: making `Expr.equal` check binder names first (same answers, fewer counted steps) changed `RuleImm`'s `.olean` and made it slower (228.6 → 241.0 user-s), because budgeted alternatives got further before failing.
  - Record the winning alternative per goal, or bound the search with structural fuel (a step count you control); keep heartbeat budgets only as a safety net that never decides between proofs.
- Budgets reset inside such searches hide their cost from `maxHeartbeats` (clifv's `kbv`): measure the search separately.
- `bv_decide` produces and checks an LRAT certificate; keep `Elab.async` on in `bv_decide`-heavy modules (clifv: 1,652 s off vs 174–186 s on). fast-lean's `sat` mode trusts the solver while iterating.
- evm-asm profile: `isDefEq` inside `simp` ~43% of CPU, then interpreted tactics and `omega`.
- clifv simp-heavy rule proofs (official 4.34.1, gperftools on `RuleBitops3/4`): 75–77% of CPU in `simp`, ~37% in `Meta.whnf` (lemma unification in `Simp.tryTheoremCore` 19%, discrimination-tree key reduction 11%). Every candidate lemma is unified against big terms, so narrow the set (`simp only [...]`) and keep big definitions out of simp sets; unfold them once, upstream, into the lemmas you need.

### Mathlib-heavy projects

ArkLib (official 4.34.0, 3,394 CPU-s full build): ~45% of CPU under the IR interpreter (Mathlib/Batteries/Aesop tactics and linters run interpreted; core tactics are native), imports ~20% (~1.3 s per module), typeclass search ~15%. Most expensive interpreted tactics: `nlinarith` 113 s, Mathlib's flexible-tactic linter 71 s, `linarith` 23 s, `field_simp` 16 s, then `calc`, `positivity`, `ring_nf`. Look at those calls first. The fast-lean dev toolchains retain interpreter caches across calls.

## 3. Checklist

1. Profile the slow module (`profiler`, then `trace.profiler` on the slow declaration); check `.olean` size.
2. Generated constants in the `.olean`? → stuck `match`/equation regeneration fixes.
3. Kernel (`type checking`) dominates? → `@[defeq]` steps, `Array`/WF evaluation, huge terms.
4. `isDefEq`/`whnf` dominate? → reducible-transparency tactics, explicit lemmas.
5. One `simp` dominates? → summary/frame lemmas, smaller simp sets.
6. Re-measure; keep `maxHeartbeats` default.
