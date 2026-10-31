# Examples

Runnable experiments behind the claims in `../skills`. `run.py` generates the parametric sources (large instruction types, listings, Lake projects) into a scratch directory, compiles them with `lean` (official `leanprover/lean4:v4.34.0` unless stated), and writes outputs and timings to `results/<experiment>.md`.

```sh
./run.py --list
./run.py                       # all experiments
./run.py stuck-match decide    # some
WORK=/scratch REPEATS=5 ./run.py eq-def
```

CPU is user + sys seconds of the `lean`/`lake` process and its children (user in parentheses), the median of `REPEATS` runs. Heartbeats (thousands, the unit of `maxHeartbeats`) are deterministic and the better before/after measure on a loaded machine. The recorded results come from a shared machine under heavy load and memory pressure; small differences (< 1 s) are noise.

| Experiment | Files | Shows |
|---|---|---|
| `stuck-match` | `stuck-match/*.lean`, `ops_source` | `simp [block, Op.effect]` over a `foldl` with an N-arm `match` vs step lemmas vs structural recursion vs `example`; dev toolchain with the `simp` fix |
| `profile` | `stuck-match/Bad.lean` | what that looks like in `trace.profiler` and in the `.olean` |
| `defeq-step-lemmas` | `defeq-step-lemmas/Use.lean`, `state_ops_source` | `:= rfl` makes `@[defeq]` lemmas that `simp` uses without proof steps; `(rfl)`/`by rfl` don't |
| `frame-lemma` | `frame-lemma/Frame.lean` | a frame lemma proved once by `cases`+induction vs `simp` through the block at each call site; restating big arguments in `exact` |
| `eq-def` | `eq-def/*.lean` | `simp [f]` (generates all equation lemmas) vs `unfold`/`f.eq_def` |
| `eqns-upstream` | generated | equation lemmas generated once in the defining module vs in every importer |
| `listing-lemmas` | `listing_source` | instruction-fetch lemmas by `simp [prog]` vs `decide` vs `rfl` |
| `decide` | `decide/*.lean` | `decide` vs `decide +kernel` vs `native_decide`; `List` vs `Array` scans in the kernel; well-founded recursion |
| `olean-paths` | `olean-paths/M.lean` | linter warnings store the source path in the `.olean` (Lean 4.29–4.35) |
| `lake-weak-args` | generated Lake project | `weakLeanArgs` is not traced and makes the `.olean`s path-independent |
| `fast-lean` | generated Lake project | `fast-lean build` vs `lake build`, faithful mode, axioms after each step |
| `snippets` | `snippets/Snippets.lean` | the code snippets quoted in the skills compile |

`lib/HB.lean` (`count_hb in <command>`: heartbeats of one command, core-only) and `lib/OleanStats.lean` (`lean --run lib/OleanStats.lean M.olean`: size, constants, match equations, splitters, equation lemmas) are reusable on their own.
