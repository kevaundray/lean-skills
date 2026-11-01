---
name: lean-asm-proofs
description: Structure Lean 4 proofs about instruction sets, assembly, machine code, bytecode or other large interpreters so that they elaborate and kernel-check fast. Use when modelling programs as lists of instructions (an inductive with hundreds of constructors and an effect/step function defined by match), proving straight-line block or loop semantics, writing frame/projection lemmas about machine states, or when such proofs time out, hit deep recursion, or produce huge .olean files.
---

# Instruction-set and assembly proofs

Large instruction types make a few innocent-looking idioms quadratic. The rules come from [ssz-fv](https://github.com/kevaundray/ssz-fv) (`learnings.md`; x86/ARM refinement proofs, Lean 4.31.0, often single-run wall-clock timings), [eth-act/clifv](https://github.com/eth-act/clifv) (`LEARNINGS.md`; a verified compiler backend, Lean 4.34.1) and the experiments in this repo's `examples/` (official Lean 4.34.0). The `lean-proof-performance` skill has the diagnosis recipe and the measured numbers for rules 1–4 and 8–9; they are not repeated here.

## The model

Typical shape: `inductive Op` with one constructor per instruction (hundreds), `Op.effect : Op → State → State` by an N-arm `match`, and a block as a fold:

```lean
def block (ops : List Op) (s : State) : State := ops.foldl (fun t op => op.effect t) s
```

## Rules

1. **Never let `simp` unfold the fold.** `simp [block, Op.effect]` exposes `fun t op => op.effect t`, where `op` is a bound variable: the `match` is stuck, and official Lean (4.26–4.35 checked) generates the splitter and all N match equations *in the importing module*, tries each of them several times (Θ(N²)) and stores them in its `.olean`. Give `simp` step lemmas instead, or define the block by structural recursion:

   ```lean
   theorem block_nil (s : State) : block [] s = s := (rfl)
   theorem block_cons (op : Op) (ops : List Op) (s : State) :
       block (op :: ops) s = block ops (op.effect s) := (rfl)
   -- or: def block : List Op → State → State | [], s => s | op :: ops, s => block ops (op.effect s)
   ```

   and write `simp [block_cons, block_nil, Op.effect, ...]`. Then `simp` only sees `Op.effect .oK s`, which `Op.effect.eq_K` rewrites. Keep `block` itself for proofs that need the fold form (`List.foldl_append`). Think before tagging the step lemmas `@[simp]`: they then fire in every plain `simp` of every importer and change its normal forms (ssz-fv: one importing module broke). ssz-fv ARM (603-constructor `Op`, 21 families fixed): full build 25,554 → 7,344 CPU-s (1 h 20 min → 14 min wall), build output 7.9 → 1.8 GB, worst module 1,783 → 31 s.

2. **Keep `@[defeq]` step lemmas out of `simp` on big states.** `theorem … := rfl` (that exact syntax) tags the lemma `@[defeq]`; `simp` then rewrites with it without recording a proof step, and the kernel must re-derive the steps by unfolding `block` and the N-arm `match` on the full state (ssz-fv: a probe 37 s → 195 s CPU, another module 38 s → 964 s, a third `(kernel) deep recursion`). Two fixes:
   - prove the step lemmas by `(rfl)` or `by rfl` (not tagged; `dsimp` can then no longer use them), or
   - keep `:= rfl` (usable by `dsimp`) and call `simp -implicitDefEqProofs [...]` where the term is big; it records the steps like the untagged lemmas do.

3. **Generate the big equation lemmas once, in the defining module.** `simp [Op.effect]` needs `Op.effect.eq_1..N`; they are generated on first use and stored in the module that first needs them, so without an upstream use *every* importer regenerates (and stores) them. Add, right after the definition:

   ```lean
   attribute [local simp] Op.effect   -- forces Op.effect.eq_* here; importers reuse them
   ```

   This costs the defining module the generation (N = 400: 4.9 → 31 s, `.olean` 10.5 → 49.9 MB), so it pays off once two or more importers need the equations. ssz-fv: eleven importers each regenerated a 458-arm `Op.effect` (52 MB `.olean` each); after the whole fix (step lemmas plus upstream equations) they took 2–5 s instead of 25–55 s, with oleans under 1 MB. When a proof needs one unfolding only, `unfold Op.effect`, `rw [Op.effect.eq_def]` or `simp only [Op.effect.eq_def]` avoid the N equations entirely.

4. **Prove frame/projection facts once, by induction, and apply them.** A field or register that no instruction (or no instruction of a family) writes deserves a lemma `(op.effect s).r = s.r` proved by `cases op <;> rfl` (or `<;> simp`) once, lifted to blocks by induction:

   ```lean
   theorem effect_f7 (op : Op) (s : S) : (op.effect s).f7 = s.f7 := by cases op <;> rfl
   theorem block_f7 (ops : List Op) (s : S) : (block ops s).f7 = s.f7 := by
     induction ops generalizing s with
     | nil => rfl
     | cons op ops ih => rw [block_cons, ih, effect_f7]
   ```

   Apply it as `block_f7 _ s`, `rw [block_f7]` or `apply block_f7`, letting unification fill the program; elaborating a restated program against the goal (`exact block_f7 [<60 ops>] s`) evaluated the block and hit the heartbeat limit. ssz-fv: a goal took 19.6 s by broad `simp [block, Op.effect, ...]` and 0.56 s by `exact block_error ...`, an existing fold lemma that plain `simp` never fired because the projection was not in its simp set. Before writing `simp`, look for an existing summary lemma and state the goal in its form.

5. **Do `cases op` over all instructions once, in a module few others import.** Each case of a `cases` over hundreds of constructors re-runs the following tactic; ssz-fv's slowest remaining module after the fix spent 256 s in two `cases op` proofs over 603 instructions. Prove such facts once and generically (rule 4), or split by instruction family (ssz-fv: a 16-op `cases` invariance lemma proved in 0.3–0.7 s and then applied in milliseconds).

6. **Summarise blocks with opaque contracts.** Expose only entry/exit PCs, the logical result, the frame (unchanged registers/memory) and resource effects; prove it once from the real semantics; higher-level proofs apply the contract and never reopen the nested state updates. Separate execution, arithmetic and frame arguments. ssz-fv: a monolithic ARM ordering proof failed after ~112 s with kernel deep recursion; split into result-byte, frame, return-PC and path contracts it checked in ~4.5 s. x86 paired carry: a 694 s timeout became helper contracts of 0.7–3.8 s each plus a 1.1 s composition; an ARM division loop iteration failing after ~863 s checked in 1.1 s with opaque finish-state summaries.

7. **Normalise representations at boundaries.** Mismatches such as `read_pc s` vs the register accessor, zero at different widths, or an opaque `toNat` of a literal were ssz-fv's recurring cause of failed closes (not semantic gaps); add small conversion lemmas and a consistent boundary form. Cache decoded instructions as literal ASTs with `rfl` decoder witnesses instead of evaluating the decoder in every proof (ssz-fv: a 5-instruction block then checked in 6.7 s). If `simp` leaves dependent instances (e.g. an `OfNat` instance indexed by a stale expression), `simp +instances` on the originating step fixed it in ssz-fv; don't raise limits.

8. **Avoid unification that unfolds the state, and don't keep searching.** Use `with_reducible assumption`/`with_reducible exact h`, name the lemma per goal instead of `first | exact a | exact b | ...` (once a search tactic has found the proof, call the winning alternative directly: failed alternatives are paid on every build, and heartbeat-budgeted ones can pick a different proof on another Lean version), and beware `subst_vars` on contexts with many equations between big terms (clifv's numbers and its `whnfR` variant: `lean-proof-performance`, "Unification that unfolds big definitions").

9. **Big tables and listings.** Prove instruction-fetch facts by `by decide` or `by rfl`, not `simp [prog]`, and not by the term `:= rfl`, which hit `maxRecDepth` deep in a 400-entry listing (ssz-fv saw the same; `by rfl` passed). For properties of large generated tables, compute with an untrusted generator that emits literal data and check it leaf-wise with small `decide +kernel` (or kernel-only `rfl`) certificates (clifv); avoid `decide_cbv` there, whose proof terms are huge. Scan `List`s, not `Array`s, in kernel-evaluated code. Chunk huge literals (ssz-fv: one literal for a whole code gap caused recursion problems; chunking bounded the depth) and mark proof-only data `noncomputable` to skip code generation.

10. **Keep modules small and their importers cheap.** A proof-only module's `.olean` should be well under 1 MB; tens of MB means generated equations or expanded states (ssz-fv: 69 modules ≥ 50 MB before the fix, 2 after). Check the smallest useful dependency frontier: one contract and its proof per module, fix the first real error, then build the next layer. Lean reports errors late in heavy modules (ssz-fv: a parse error on line 10 surfaced after 128–134 s), so check new code in a small module or with `fast-lean lean` first.
