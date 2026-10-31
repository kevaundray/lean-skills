---
name: lean-asm-proofs
description: Structure Lean 4 proofs about instruction sets, assembly, machine code, bytecode or other large interpreters so that they elaborate and kernel-check fast. Use when modelling programs as lists of instructions (an inductive with hundreds of constructors and an effect/step function defined by match), proving straight-line block or loop semantics, writing frame/projection lemmas about machine states, or when such proofs time out, hit deep recursion, or produce huge .olean files.
---

# Instruction-set and assembly proofs

Large instruction types make a few innocent-looking idioms quadratic. The rules below come from ssz-fv (x86/ARM refinement proofs, `learnings.md`), eth-act/clifv (`LEARNINGS.md`, a verified compiler backend) and the experiments in `examples/` (official Lean 4.34.0, CPU = user+sys). For diagnosis see the `lean-proof-performance` skill.

## The model

Typical shape: `inductive Op` with one constructor per instruction (hundreds), `Op.effect : Op → State → State` by an N-arm `match`, and a block as a fold:

```lean
def block (ops : List Op) (s : State) : State := ops.foldl (fun t op => op.effect t) s
```

## Rules

1. **Never let `simp` unfold the fold.** `simp [block, Op.effect]` exposes `fun t op => op.effect t`, where `op` is a bound variable: the `match` is stuck, and official Lean (checked 4.29–4.35) generates the splitter and all N match equations *in the importing module*, tries each of them several times (Θ(N²)) and stores them in its `.olean`. Give `simp` step lemmas instead, or define the block by structural recursion:

   ```lean
   @[simp] theorem block_nil (s : State) : block [] s = s := (rfl)
   @[simp] theorem block_cons (op : Op) (ops : List Op) (s : State) :
       block (op :: ops) s = block ops (op.effect s) := (rfl)
   -- or: def block : List Op → State → State | [], s => s | op :: ops, s => block ops (op.effect s)
   ```

   and write `simp [block_cons, block_nil, Op.effect, ...]`. Then `simp` only sees `Op.effect .oK s`, which `Op.effect.eq_K` rewrites. Keep `block` itself for proofs that need the fold form (`List.foldl_append`). `examples/results/stuck-match.md`, N = 400: `simp [block, Op.effect]` 64.9M heartbeats, 25.8 s CPU, 39.4 MB `.olean` with 400 match equations; step lemmas 196k heartbeats and 11 kB, structural `block` 203k and 38 kB (imports alone take 1.7 s). ssz-fv ARM (603-constructor `Op`, 21 families fixed, Lean 4.31.0): full build 25,554 → 7,344 CPU-s (1 h 20 min → 14 min wall), build output 7.9 → 1.8 GB, worst module 1,783 → 31 s.

2. **Prove step lemmas with `(rfl)` or `by rfl`, not `:= rfl`.** The syntax `:= rfl` tags the theorem `@[defeq]` (Lean 4.26–4.35 checked; `#print` shows it); `simp` then uses it without recording a proof step and the kernel must re-derive those steps by unfolding `block` and the N-arm `match` on the full state. ssz-fv: a probe with two theorems of one module took 37 s CPU with `(rfl)` steps and 195 s with `:= rfl`, another module went 38 s → 964 s, a third failed with `(kernel) deep recursion`. clifv saw the same with `rfl`-proved monad laws applied to a big concrete state: 23.6 GB / 128 s → 2.1 GB / 21 s after reproving them by `rw`. On small states it costs little (`examples/results/defeq-step-lemmas.md`).

3. **Generate the big equation lemmas once, in the defining module.** `simp [Op.effect]` needs `Op.effect.eq_1..N`; equation lemmas are generated on first use and stored in the module that first needs them, so without an upstream use *every* importer regenerates (and stores) them. Add, right after the definition:

   ```lean
   attribute [local simp] Op.effect   -- forces Op.effect.eq_* here; importers reuse them
   ```

   ssz-fv: eleven importers each regenerated a 458-arm `Op.effect` (52 MB `.olean` each, 25–55 s); afterwards < 1 MB and 2–5 s. `examples/results/eqns-upstream.md` (N = 400, four importers): 18–23 s and 39.7 MB per importer without it; with it 31 s once in the defining module and 0.3–0.6 s, 7 kB per importer. When a proof only needs one unfolding, `unfold Op.effect` / `rw [Op.effect.eq_def]` / `simp only [Op.effect.eq_def]` avoid generating the N equations at all (`examples/results/eq-def.md`: 19.6 s and 39.7 MB vs 0.8–1.1 s and 0.1 MB).

4. **Prove frame/projection facts once, by induction, and apply them.** A field or register that no instruction (or no instruction of a family) writes deserves a lemma `(op.effect s).r = s.r` proved by `cases op <;> rfl` or `<;> simp` once, lifted to blocks by induction:

   ```lean
   theorem effect_f7 (op : Op) (s : S) : (op.effect s).f7 = s.f7 := by cases op <;> rfl
   theorem block_f7 (ops : List Op) (s : S) : (block ops s).f7 = s.f7 := by
     induction ops generalizing s with
     | nil => rfl
     | cons op ops ih => rw [block_cons, ih, effect_f7]
   ```

   Call sites then cost a lemma application instead of a symbolic execution (`examples/results/frame-lemma.md`, N = 400, ten 60-op blocks: 2.6 s by `simp` vs 0.3 s by `block_f7 _ s`; the two lemmas cost 1.7 s once). Let unification fill the big arguments: `block_f7 _ s`, `rw [block_f7]` or `apply block_f7`. Restating the program, as in `exact block_f7 [<60 ops>] s`, made `isDefEq` compare two copies by evaluating the block and hit the default heartbeat limit after 10 s in the same experiment. ssz-fv: the same goal took 19.6 s by broad `simp [block, Op.effect, ...]` and 0.56 s by `exact block_error ...`, an existing fold lemma that plain `simp` never fired because the projection was not in the simp set. Before writing `simp`, look for an existing summary lemma and state the goal in its form.

5. **Do `cases op` over all instructions once, in a module few others import.** Each case of a `cases` over hundreds of constructors re-runs the following tactic; ssz-fv's slowest remaining module after the fix spent 256 s in two `cases op` proofs over 603 instructions. Keep such proofs in modules few others import, prove them once and generically (rule 4), or split by instruction family (ssz-fv: a 16-op `cases` invariance lemma proved in 0.3–0.7 s and then applied in milliseconds).

6. **Summarise blocks with opaque contracts.** Expose only entry/exit PCs, the logical result, the frame (unchanged registers/memory) and resource effects; prove it once from the real semantics; higher-level proofs apply the contract and never reopen the nested state updates. Separate execution, arithmetic and frame arguments. ssz-fv: a monolithic ARM ordering proof failed after ~112 s with kernel deep recursion; split into result-byte, frame, return-PC and path contracts it checked in ~4.5 s. x86 paired carry: a 694 s timeout became helper contracts of 0.7–3.8 s each plus a 1.1 s composition; an ARM division loop iteration failing after ~863 s checked in 1.1 s with opaque finish-state summaries.

7. **Normalise representations at boundaries.** Mismatches such as `read_pc s` vs the register accessor, zero at different widths, or an opaque `toNat` of a literal were ssz-fv's recurring cause of failed closes (not semantic gaps); add small conversion lemmas and a consistent boundary form. Cache decoded instructions as literal ASTs with `rfl` decoder witnesses instead of evaluating the decoder in every proof (ssz-fv: a 5-instruction block then checked in 6.7 s). If `simp` leaves dependent instances (e.g. an `OfNat` instance indexed by a stale expression), `simp +instances` on the originating step fixed it in ssz-fv; don't raise limits.

8. **Avoid unification that unfolds the state.** Use `with_reducible assumption`/`with_reducible exact` (clifv: an `assumption` unfolding `ArmState` ran out of 8M heartbeats; at reducible transparency the module took ~30 s; elsewhere 815 s → 16 s), name the lemma per goal instead of `first | exact a | exact b | ...` (each failing `exact` unfolds the big definition), and beware `subst_vars` on contexts with many equations between big terms (it `whnf`s both sides each rescan; clifv: 1,420 s in one call, 838 → 28 s with a `whnfR` variant).

9. **Big tables and listings.** Prove instruction-fetch facts by `decide` or `rfl`, not `simp [prog]` (`examples/results/listing-lemmas.md`: 60 lemmas over 80 instructions, 4.6 s by `simp [prog]`, 1.6 s by `rfl`, 0.6 s by `decide`). For properties of large generated tables, compute with an untrusted generator that emits literal data and check it leaf-wise with small `decide +kernel` certificates; whole-table `decide`/`native_decide` hit 20+ GB in clifv. Scan `List`s, not `Array`s, in kernel-evaluated code (`lean-proof-performance`). Chunk huge literals (ssz-fv: one literal for a whole code gap caused recursion problems; chunking bounded the depth) and mark proof-only data `noncomputable` to skip code generation.

10. **Keep modules small and their importers cheap.** A proof-only module's `.olean` should be well under 1 MB; tens of MB means generated equations or expanded states (ssz-fv: 69 modules ≥ 50 MB before the fix, 2 after). Check the smallest useful dependency frontier: one contract and its proof per module, fix the first real error, then build the next layer. Lean reports errors late in heavy modules (ssz-fv: a parse error on line 10 surfaced after 128–134 s), so check new code in a small module or with `fast-lean lean` first.
