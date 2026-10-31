# lean-skills

Agent skills for writing Lean 4 proofs that build fast. Each skill is a directory with a `SKILL.md` (YAML front matter `name` and `description`, saying when to use it, then concise instructions) in the format read by Claude Code and other agents that load skills from `~/.claude/skills` or `~/.agents/skills`.

| Skill | Use it when |
|---|---|
| [`lean-proof-performance`](skills/lean-proof-performance/SKILL.md) | a proof, module or build is slow, times out, needs too much memory or writes huge `.olean`s; profiling recipe and a catalogue of pathologies with fixes |
| [`lean-asm-proofs`](skills/lean-asm-proofs/SKILL.md) | proving things about instruction sets, assembly, machine code or interpreters with large `match`es |
| [`fast-lean`](skills/fast-lean/SKILL.md) | iterating on a project with the fast-lean development toolchain (`fast-lean build`, `LEAN_DEV`) |
| [`lean-build-hygiene`](skills/lean-build-hygiene/SKILL.md) | lakefile options, deterministic `.olean`s, import structure, caches, memory |

## Install

Clone once and link the skills into your agent's skill directory:

```sh
git clone git@github.com:kevaundray/lean-skills.git ~/src/lean-skills
mkdir -p ~/.claude/skills ~/.agents/skills
for s in ~/src/lean-skills/skills/*/; do
  ln -sfn "$s" ~/.claude/skills/"$(basename "$s")"   # Claude Code
  ln -sfn "$s" ~/.agents/skills/"$(basename "$s")"   # agents reading ~/.agents/skills
done
```

Copy instead of linking (`cp -r skills/* ~/.claude/skills/`) if the agent runs where the clone is not visible. For a single project, put them under `<project>/.claude/skills/`. `git pull` updates linked skills.

## Examples and evidence

Every claim in the skills is either measured by an experiment in [`examples/`](examples/) (official Lean 4.34.0 unless stated) or taken from the sources below, which the skills name next to the number.

```sh
examples/run.py --list          # experiments
examples/run.py                 # rerun all (writes examples/results/*.md); ~1 h on a loaded 32-core machine
examples/run.py stuck-match     # one experiment
```

Requirements: elan with `leanprover/lean4:v4.34.0` (and v4.29.0, v4.31.0, v4.33.1, v4.35.0 for `olean-paths`), Python 3; `fast-lean` and its dev toolchain for `fast-lean` and the dev row of `stuck-match` (skipped otherwise). Recorded results are in [`examples/results/`](examples/results/); CPU times are user+sys, medians of three runs, on a shared, loaded machine, so compare rows within a table rather than across machines.

## Sources

- ssz-fv `learnings.md`, section "`simp [block]` over a large instruction `match`" and the bottleneck measurements (x86/ARM refinement proofs; Lean 4.31.0).
- [eth-act/clifv](https://github.com/eth-act/clifv) `LEARNINGS.md` and `docs/` (verified compiler backend; Lean 4.34.1).
- leanprover/lean4#15754 (`simp` and stuck `match`es) and its fix leanprover/lean4#15755.
- The fast-lean toolchains: `script/fast-lean` in the `dev-fast-*` branches and the `fast-lean-dist` branch of [eth-act/lean4](https://github.com/eth-act/lean4).
- Our own profiles of ArkLib, clean, evm-asm and ssz-fv builds (Oct 2026).
- Lean source (`src/Lean/Meta/Tactic/Simp/Rewrite.lean`, `src/Lean/DefEqAttrib.lean`, `src/Lean/Elab/MutualDef.lean`, `src/lake/Lake/Config/LeanConfig.lean`) for mechanisms.
