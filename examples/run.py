#!/usr/bin/env python3
"""Reruns the examples of the lean-skills skills and records outputs and timings.

Usage: examples/run.py [EXPERIMENT ...]       (default: all; `--list` lists them)

Environment:
  LEAN_TOOLCHAIN  official toolchain (default leanprover/lean4:v4.34.0)
  DEV_TOOLCHAIN   elan toolchain of a fast-lean dev toolchain for the same version, used by
                  `stuck-match` and `fast-lean` (default dev-fast-v4.34.0, else the fast-lean
                  release eth-act/lean4:dev-fast-v4.34.0-5); skipped when not installed
  FAST_LEAN       the fast-lean script (default: `fast-lean` on PATH)
  WORK            scratch directory (default /tmp/lean-skills-exp)
  REPEATS         runs per CPU measurement, the median is reported (default 3)

Writes examples/results/<experiment>.md. CPU = user + sys of the process and its children.
"""

import hashlib
import os
import re
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
WORK = Path(os.environ.get("WORK", "/tmp/lean-skills-exp"))
OFFICIAL = os.environ.get("LEAN_TOOLCHAIN", "leanprover/lean4:v4.34.0")
REPEATS = int(os.environ.get("REPEATS", "3"))


class Cpu(float):
    """CPU seconds (user + sys, incl. children) that also carries the user part."""

    def __new__(cls, total, user):
        x = super().__new__(cls, total)
        x.user = user
        return x


def secs(c):
    return f"{c:.2f} s (user {c.user:.2f})"


def sh(cmd, cwd=None, env=None, check=False):
    """Runs `cmd`; returns (exit code, Cpu, wall seconds, output)."""
    t0 = time.monotonic()
    p = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True)
    out = p.stdout.read()
    _, status, ru = os.wait4(p.pid, 0)
    p.returncode = os.waitstatus_to_exitcode(status)
    wall = time.monotonic() - t0
    if check and p.returncode != 0:
        raise RuntimeError(f"{' '.join(map(str, cmd))} failed:\n{out}")
    return p.returncode, Cpu(ru.ru_utime + ru.ru_stime, ru.ru_utime), wall, out


def toolchain_prefix(tc):
    rc, _, _, out = sh(["lean", f"+{tc}", "--print-prefix"])
    return Path(out.strip().splitlines()[-1]) if rc == 0 else None


class Lean:
    def __init__(self, tc):
        self.tc = tc
        self.prefix = toolchain_prefix(tc)
        if self.prefix is None:
            raise RuntimeError(f"toolchain {tc} not installed")
        self.bin = str(self.prefix / "bin" / "lean")
        self.version = sh([self.bin, "--version"])[3].strip()

    def run(self, file, cwd, olean=True, args=(), path=None):
        """Elaborates `file` (in `cwd`, importing from `path` or `cwd`)."""
        env = dict(os.environ, LEAN_PATH=str(path or cwd))
        cmd = [self.bin, *args, str(file)]
        if olean:
            cmd[1:1] = ["-o", str(Path(file).with_suffix(".olean"))]
        return sh(cmd, cwd=cwd, env=env)

    def cpu(self, file, cwd, **kw):
        """Median CPU of REPEATS runs, plus the output of the first."""
        runs = [self.run(file, cwd, **kw) for _ in range(REPEATS)]
        if runs[0][0] != 0:
            raise RuntimeError(f"{file} failed:\n{runs[0][3]}")
        return median(r[1] for r in runs), runs[0][3]

    def stats(self, cwd, *oleans):
        """Output of lib/OleanStats.lean for `oleans` (as a dict by file name)."""
        rc, _, _, out = sh([self.bin, "--run", str(HERE / "lib/OleanStats.lean"),
                            *map(str, oleans)], cwd=cwd,
                           env=dict(os.environ, LEAN_PATH=str(cwd)))
        res = {}
        for line in out.splitlines():
            m = re.match(r"(.*?): (\d+) bytes, (\d+) constants, (\d+) match equations, "
                         r"(\d+) splitters, (\d+) equation lemmas", line)
            if m:
                res[Path(m[1]).stem] = dict(bytes=int(m[2]), consts=int(m[3]),
                                            matchEqns=int(m[4]), splitters=int(m[5]),
                                            eqns=int(m[6]))
        return res


def median(cpus):
    cpus = list(cpus)
    return Cpu(statistics.median(cpus), statistics.median(c.user for c in cpus))


def heartbeats(out):
    m = re.search(r"heartbeats: (\d+)k", out)
    return int(m[1]) if m else None


def fresh(*parts):
    d = WORK.joinpath(*parts)
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    return d


def setup(lean, d, files=(), sources=None, libs=("HB",)):
    """Copies example files and libraries into `d`, writes `sources`, compiles the libraries."""
    for f in files:
        shutil.copy(f, d)
    for name, text in (sources or {}).items():
        (d / f"{name}.lean").write_text(text)
    for lib in libs:
        shutil.copy(HERE / "lib" / f"{lib}.lean", d)
        lean.run(d / f"{lib}.lean", d)


def mb(n):
    return f"{n / 1e6:.2f} MB" if n >= 1e5 else f"{n / 1e3:.1f} kB"


def table(header, rows):
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(lines)


def trim(out, n=40, width=200):
    lines = [l[:width] for l in out.strip().splitlines()]
    if len(lines) > n:
        lines = lines[:n] + [f"... ({len(lines) - n} more lines)"]
    return "```\n" + "\n".join(lines) + "\n```"


# --- generated sources -----------------------------------------------------------------------


def ops_source(n, warm=False, steps="(rfl)"):
    """An `n`-constructor instruction type, its `match`-based effect, a fold-based block with step
    lemmas, and a structurally recursive block."""
    L = ["inductive Op where " + " ".join(f"| o{i}" for i in range(n)),
         "def Op.effect : Op → Nat → Nat"]
    L += [f"  | .o{i}, s => s + {i}" for i in range(n)]
    if warm:
        L += ["-- Generate `Op.effect`'s equation lemmas here, once, for all importers.",
              "attribute [local simp] Op.effect"]
    L += ["def block (ops : List Op) (s : Nat) : Nat := ops.foldl (fun t op => op.effect t) s",
          f"theorem block_nil (s : Nat) : block [] s = s := {steps}",
          "theorem block_cons (op : Op) (ops : List Op) (s : Nat) :",
          f"    block (op :: ops) s = block ops (op.effect s) := {steps}",
          "def blockS : List Op → Nat → Nat",
          "  | [], s => s",
          "  | op :: ops, s => blockS ops (op.effect s)"]
    return "\n".join(L) + "\n"


def state_ops_source(n, steps, prog_len=60):
    """Like `ops_source`, with an 8-field state structure, record updates and a fixed program."""
    L = ["structure S where"] + [f"  f{j} : Nat" for j in range(8)]
    L += ["inductive Op where " + " ".join(f"| o{i}" for i in range(n)),
          "def Op.effect : Op → S → S"]
    L += [f"  | .o{i}, s => {{ s with f{i % 7} := s.f{(i + 1) % 7} + {i} }}" for i in range(n)]
    L += ["attribute [local simp] Op.effect",
          "def block (ops : List Op) (s : S) : S := ops.foldl (fun t op => op.effect t) s",
          f"theorem block_nil (s : S) : block [] s = s := {steps}",
          "theorem block_cons (op : Op) (ops : List Op) (s : S) :",
          f"    block (op :: ops) s = block ops (op.effect s) := {steps}",
          "def prog : List Op := [" + ", ".join(f".o{(7 * k + 3) % n}" for k in range(prog_len))
          + "]"]
    return "\n".join(L) + "\n"


PROOFS = {"simp": "by simp [prog]", "rfl": "rfl", "by-rfl": "by rfl", "decide": "by decide",
          "decide-kernel": "by decide +kernel"}


def listing_source(proof, n_instr=80, n_lemmas=60, indices=None):
    """A program listing and instruction-fetch lemmas (for `indices`, default `n_lemmas` spread
    over the listing) proved by `PROOFS[proof]`."""
    instrs = []
    for i in range(n_instr):
        k = i % 4
        if k == 0:
            instrs.append(f".add {i % 32} {(i * 3) % 32} {(i * 5) % 32}")
        elif k == 1:
            instrs.append(f".addi {i % 32} {(i * 7) % 32} ({i * 4 - 100})")
        elif k == 2:
            instrs.append(f".load {i % 32} 2 ({i * 8})")
        else:
            instrs.append(f".branch {i % 32} {(i + 1) % 32} ({-(i * 4)})")
    L = ["inductive Instr where",
         "  | add (rd rs1 rs2 : Nat)",
         "  | addi (rd rs1 : Nat) (imm : Int)",
         "  | load (rd rs1 : Nat) (off : Int)",
         "  | branch (rs1 rs2 : Nat) (off : Int)",
         "  deriving DecidableEq",
         "def prog : List Instr := [\n  " + ",\n  ".join(instrs) + "]"]
    if indices is None:
        indices = [(j * 37) % n_instr for j in range(n_lemmas)]
    for j, k in enumerate(indices):
        L.append(f"theorem fetch_{j} : prog[{k}]? = some (Instr{instrs[k]}) := {PROOFS[proof]}")
    return "\n".join(L) + "\n"


# --- experiments -----------------------------------------------------------------------------


def exp_stuck_match():
    """`simp [block, Op.effect]` over a fold whose step function contains a large `match`."""
    lean = Lean(OFFICIAL)
    out = [f"Toolchain: `{lean.version}`.\n",
           "`Ops.lean` (generated by `ops_source(N, warm=True)` in `run.py`) defines an N-constructor "
           "`Op`, `Op.effect` by an N-arm `match`, generates `Op.effect`'s equation lemmas "
           "(`attribute [local simp] Op.effect`), and defines `block` (a `foldl`), its step lemmas "
           "`block_nil`/`block_cons` (proved by `(rfl)`), and `blockS` (structural recursion). "
           "Each importer proves `block [.o1, .o2] s = s + 1 + 2`.\n"]
    rows = []
    variants = ["Bad", "Steps", "Structural", "Example"]
    for n in (100, 200, 400):
        d = fresh("stuck-match", f"n{n}")
        setup(lean, d, [HERE / "stuck-match" / f"{v}.lean" for v in variants],
              {"Ops": ops_source(n, warm=True)})
        lean.run(d / "Ops.lean", d)
        (d / "Base.lean").write_text("import Ops\nimport HB\n")
        base, _ = lean.cpu(d / "Base.lean", d)
        for v in variants:
            cpu, o = lean.cpu(d / f"{v}.lean", d)
            st = lean.stats(d, d / f"{v}.olean")[v]
            rows.append([n, f"`{v}`", secs(cpu), f"{heartbeats(o):,}k", mb(st["bytes"]),
                         st["matchEqns"], st["splitters"]])
        rows.append([n, "(imports only)", secs(base), "", "", "", ""])
    out.append(table(["N", "importer", "CPU", "heartbeats", "olean", "match eqns in olean",
                      "splitters"], rows))
    dev = dev_lean()
    if dev:
        n = 400
        d = fresh("stuck-match", f"dev-n{n}")
        setup(dev, d, [HERE / "stuck-match/Bad.lean"], {"Ops": ops_source(n, warm=True)})
        dev.run(d / "Ops.lean", d)
        cpu, o = dev.cpu(d / "Bad.lean", d)
        st = dev.stats(d, d / "Bad.olean")["Bad"]
        out.append(f"\nWith the dev toolchain `{dev.tc}` (contains the `simp` fix of "
                   f"leanprover/lean4#15755), N = {n}, `Bad`: CPU {secs(cpu)}, "
                   f"{heartbeats(o):,}k heartbeats, olean {mb(st['bytes'])}, "
                   f"{st['matchEqns']} match equations.")
    return "\n".join(out)


def exp_profile():
    """What the stuck-match pathology looks like in `trace.profiler` and in the `.olean`."""
    lean = Lean(OFFICIAL)
    d = fresh("profile")
    setup(lean, d, [HERE / "stuck-match/Bad.lean"], {"Ops": ops_source(200, warm=True)})
    lean.run(d / "Ops.lean", d)
    _, _, _, o = lean.run(d / "Bad.lean", d, args=["-Dtrace.profiler=true",
                                                    "-Dtrace.profiler.threshold=100"])
    st = lean.stats(d, d / "Bad.olean", d / "Ops.olean")
    return "\n".join([
        f"Toolchain: `{lean.version}`. N = 200, `stuck-match/Bad.lean`, run as "
        "`lean -Dtrace.profiler=true -Dtrace.profiler.threshold=100 Bad.lean`:\n",
        trim(o, 30),
        "\n`lean --run lib/OleanStats.lean Bad.olean Ops.olean`:\n",
        table(["olean", "size", "constants", "match eqns", "splitters", "eqn lemmas"],
              [[k, mb(v["bytes"]), v["consts"], v["matchEqns"], v["splitters"], v["eqns"]]
               for k, v in st.items()])])


def exp_defeq_step_lemmas():
    """Step lemmas proved by `:= rfl` (tagged `@[defeq]`) vs `:= (rfl)` / `:= by rfl`, and
    `simp -implicitDefEqProofs`."""
    lean = Lean(OFFICIAL)
    rows = []
    variants = (("`:= rfl`", "rfl", "Use", "`simp [...]`"),
                ("`:= rfl`", "rfl", "UseNoImplicit", "`simp -implicitDefEqProofs [...]`"),
                ("`:= (rfl)`", "(rfl)", "Use", "`simp [...]`"),
                ("`:= by rfl`", "by rfl", "Use", "`simp [...]`"))
    for name, steps, use, call in variants:
        d = fresh("defeq-step-lemmas", (re.sub(r"\W", "", steps) or "rfl") + use)
        setup(lean, d, [HERE / "defeq-step-lemmas" / f for f in
                        ("Use.lean", "UseNoImplicit.lean", "Dsimp.lean")],
              {"Ops": state_ops_source(200, steps)})
        lean.run(d / "Ops.lean", d)
        cpu, o = lean.cpu(d / f"{use}.lean", d)
        defeq = re.search(r"block_cons is @\[defeq\]: (\w+)", o)[1]
        used = re.search(r"mentions block_cons: (\w+)", o)[1]
        prof = lean.run(d / f"{use}.lean", d, args=["-Dprofiler=true"])[3]
        kernel = re.search(r"\ttype checking ([\d.]+m?s)", prof)
        rc, _, _, ds = lean.run(d / "Dsimp.lean", d)
        dsimp = "yes" if rc == 0 else "no: " + next(
            (l.split("error: ")[-1] for l in ds.splitlines() if "error" in l), "error")
        rows.append([name, call, defeq, used, secs(cpu), f"{heartbeats(o):,}k",
                     kernel[1] if kernel else "n/a", dsimp])
    return "\n".join([
        f"Toolchain: `{lean.version}`. `Ops.lean` from `state_ops_source(200, steps)`: 200 ops "
        "updating an 8-field structure, `prog` = 60 ops; `Use.lean` proves "
        "`(block prog s).f7 = s.f7` by `simp [prog, block_cons, block_nil, Op.effect]`; "
        "`UseNoImplicit.lean` the same with `simp -implicitDefEqProofs`. `Dsimp.lean` tries "
        "`dsimp only [block_cons]` on the step equation.\n",
        table(["step lemma proof", "call", "`@[defeq]`", "proof term mentions `block_cons`", "CPU",
               "heartbeats", "kernel (`profiler`: type checking)", "`dsimp only [block_cons]` works"],
              rows),
        "\nWith `@[defeq]` step lemmas `simp` rewrites without recording a proof step, so the "
        "kernel has to re-establish those steps by unfolding. In this small state it is cheap; "
        "the large costs reported by ssz-fv and clifv come from large states/terms."])


def exp_frame_lemma():
    """Ten call sites that need "the block leaves `f7` alone": `simp` through the block each time
    vs a frame lemma proved once by `cases op` and induction."""
    lean = Lean(OFFICIAL)
    n, sites = 400, 10
    d = fresh("frame-lemma")
    progs = [[(7 * k + 13 * j + 3) % n for k in range(60)] for j in range(sites)]

    def use(proof, imp):
        L = [f"import {imp}"]
        for j, p in enumerate(progs):
            lst = ", ".join(f".o{i}" for i in p)
            L.append(f"theorem t{j} (s : S) : (block [{lst}] s).f7 = s.f7 := {proof(lst)}")
        return "\n".join(L) + "\n"

    setup(lean, d, [HERE / "frame-lemma/Frame.lean"], {
        "Ops": state_ops_source(n, "(rfl)"),
        "UseSimp": use(lambda l: "by\n  simp [block_cons, block_nil, Op.effect]", "Ops"),
        "UseFrame": use(lambda l: "block_f7 _ s", "Frame"),
        "BaseOps": "import Ops\n", "BaseFrame": "import Frame\n"}, libs=())
    lst = ", ".join(f".o{i}" for i in progs[0])
    head = f"import Frame\ntheorem t0 (s : S) : (block [{lst}] s).f7 = s.f7 :="
    probes = {"UseFrameExplicit": f"{head} by\n  exact block_f7 [{lst}] s\n",
              "UseFrameTerm": f"{head}\n  block_f7 [{lst}] s\n",
              "UseFrameHave": f"{head} by\n  have h := block_f7 [{lst}] s\n  exact h\n"}
    for name, text in probes.items():
        (d / f"{name}.lean").write_text(text)
    rows = []
    for f in ("Ops", "Frame", "BaseOps", "UseSimp", "BaseFrame", "UseFrame"):
        cpu, _ = lean.cpu(d / f"{f}.lean", d)
        rows.append([f"`{f}`", secs(cpu)])
    for name in probes:
        rc, cpu, _, o = lean.run(d / f"{name}.lean", d)
        err = next((l for l in o.splitlines() if "error" in l), "")
        rows.append([f"`{name}` (1 theorem, single run)", f"{secs(cpu)}; "
                     + ("ok" if rc == 0 else f"error: `{err.split('error: ')[-1]}`")])
    return "\n".join([
        f"Toolchain: `{lean.version}`. `Ops` = `state_ops_source({n}, \"(rfl)\")` (400 ops "
        "updating fields `f0`..`f6` of an 8-field structure, equation lemmas generated there). "
        f"`UseSimp` and `UseFrame` each prove `(block p s).f7 = s.f7` for {sites} different 60-op "
        "programs `p`; `UseSimp` by `simp [block_cons, block_nil, Op.effect]`, `UseFrame` by the "
        "lemma `block_f7` from `frame-lemma/Frame.lean` as `block_f7 _ s`. `Base*` import only. "
        "The probes prove the first of these goals with the list restated: `UseFrameExplicit` by "
        "`exact block_f7 [<the list>] s`, `UseFrameTerm` by the term `block_f7 [<the list>] s`, "
        "`UseFrameHave` by `have h := block_f7 [<the list>] s; exact h` (the application is "
        "elaborated without the expected type, then `h`'s type is unified with the goal).\n",
        table(["module", "CPU"], rows)])


def exp_eq_def():
    """`simp [f]` vs `f.eq_def` / `unfold f` for an N-arm `match` whose equations were not
    generated upstream."""
    lean = Lean(OFFICIAL)
    d = fresh("eq-def")
    variants = ["SimpF", "EqDefSimpOnly", "EqDefRw", "Unfold"]
    setup(lean, d, [HERE / "eq-def" / f"{v}.lean" for v in variants],
          {"Ops": ops_source(400, warm=False)}, libs=())
    lean.run(d / "Ops.lean", d)
    rows = []
    for v in variants:
        cpu, _ = lean.cpu(d / f"{v}.lean", d)
        st = lean.stats(d, d / f"{v}.olean")[v]
        rows.append([f"`{v}`", secs(cpu), mb(st["bytes"]), st["eqns"], st["matchEqns"]])
    return "\n".join([
        f"Toolchain: `{lean.version}`. `Ops.lean` = `ops_source(400, warm=False)` (no equation "
        "lemmas generated upstream). Each file proves `Op.effect .o5 s = s + 5`.\n",
        table(["proof", "CPU", "olean", "equation lemmas stored", "match equations stored"], rows)])


def exp_eqns_upstream():
    """Four importers each `simp [Op.effect]`: equation lemmas generated in each of them vs once in
    the defining module."""
    lean = Lean(OFFICIAL)
    rows = []
    for warm in (False, True):
        d = fresh("eqns-upstream", "warm" if warm else "cold")
        srcs = {"Ops": ops_source(400, warm=warm)}
        for k in range(1, 5):
            srcs[f"U{k}"] = (f"import Ops\ntheorem t{k} (s : Nat) : Op.effect .o{k} s = s + {k} := by\n"
                             f"  simp [Op.effect]\n")
        setup(lean, d, sources=srcs, libs=())
        ops_cpu, _ = lean.cpu(d / "Ops.lean", d)
        us = [lean.cpu(d / f"U{k}.lean", d)[0] for k in range(1, 5)]
        st = lean.stats(d, d / "Ops.olean", *[d / f"U{k}.olean" for k in range(1, 5)])
        rows.append(["yes" if warm else "no", secs(ops_cpu), mb(st["Ops"]["bytes"]),
                     " / ".join(f"{u:.2f}" for u in us) + " s",
                     " / ".join(mb(st[f"U{k}"]["bytes"]) for k in range(1, 5)),
                     f"{ops_cpu + sum(us):.2f} s (user {ops_cpu.user + sum(u.user for u in us):.2f})"])
    out = [f"Toolchain: `{lean.version}`. N = 400; `U1`..`U4` each prove `Op.effect .oK s = s + K` "
           "by `simp [Op.effect]`.\n",
           table(["`attribute [local simp] Op.effect` in `Ops`", "`Ops` CPU", "`Ops` olean",
                  "`U1..U4` CPU", "`U1..U4` oleans", "total CPU"], rows)]
    return "\n".join(out)


def exp_listing_lemmas():
    """60 instruction-fetch lemmas over an 80-instruction listing."""
    lean = Lean(OFFICIAL)
    rows = []
    labels = {k: f"`{v}`" for k, v in PROOFS.items()} | {"none": "(no fetch lemmas)"}
    for proof in ("none", "simp", "decide", "rfl", "by-rfl"):
        d = fresh("listing-lemmas", proof)
        src = listing_source("rfl", n_lemmas=0) if proof == "none" else listing_source(proof)
        setup(lean, d, sources={"Listing": src}, libs=())
        cpu, _ = lean.cpu(d / "Listing.lean", d)
        st = lean.stats(d, d / "Listing.olean")["Listing"]
        rows.append([labels[proof], secs(cpu), mb(st["bytes"])])
    big = []
    for proof in ("rfl", "by-rfl", "decide", "decide-kernel"):
        d = fresh("listing-lemmas", "big-" + proof)
        setup(lean, d, sources={"Big": listing_source(proof, n_instr=400, indices=[390])},
              libs=())
        rc, cpu, _, o = lean.run(d / "Big.lean", d)
        err = next((l.split("error: ")[-1] for l in o.splitlines() if "error" in l), "")
        big.append([labels[proof], "ok" if rc == 0 else f"error: `{err}`", secs(cpu)])
    return "\n".join([
        f"Toolchain: `{lean.version}`. `listing_source(proof)`: an 80-instruction `prog : List "
        "Instr` and 60 lemmas `prog[k]? = some (...)` (whole module, including the definitions).\n",
        table(["proof of each fetch lemma", "module CPU", "olean"], rows),
        "\nA 400-instruction listing with one lemma for entry 390 (single run, whole module):\n",
        table(["proof", "result", "module CPU"], big)])


def exp_decide():
    """`decide` vs `decide +kernel` vs `native_decide`; List vs Array scans in the kernel;
    well-founded recursion."""
    lean = Lean(OFFICIAL)
    d = fresh("decide")
    files = ["Decide", "DecideDeep", "DecideKernel", "DecideKernelLarge", "DecideKernelHuge",
             "NativeDecide", "ListScan", "ArrayScan", "WellFounded", "WellFoundedKernel"]
    setup(lean, d, [HERE / "decide" / f"{f}.lean" for f in files])
    rows = []
    outs = []
    for f in files:
        reps = 1 if f in ("ArrayScan", "WellFounded", "DecideDeep", "DecideKernelHuge") else REPEATS
        runs = [sh(["/usr/bin/time", "-f", "maxrss %M KB", lean.bin, f"{f}.lean"], cwd=d,
                   env=dict(os.environ, LEAN_PATH=str(d))) for _ in range(reps)]
        cpu = median(r[1] for r in runs)
        o = runs[0][3]
        rss = re.search(r"maxrss (\d+) KB", o)
        o = re.sub(r"maxrss \d+ KB\n?", "", o)
        o = re.sub(r"Command exited with non-zero status \d+\n?", "", o)
        msg = " ".join(l.strip() for l in o.strip().splitlines()[:3])[:160]
        rows.append([f"`{f}`", "ok" if runs[0][0] == 0 else "error", secs(cpu),
                     f"{int(rss[1]) / 1e6:.2f} GB" if rss else "", msg.replace("|", "\\|")])
        if f == "WellFounded":
            outs.append(trim(o, 40))
    return "\n".join([f"Toolchain: `{lean.version}`.\n",
                      table(["file", "result", "CPU", "max RSS", "output (start)"], rows),
                      "\n`WellFounded.lean` output:\n", *outs])


def exp_olean_paths():
    """Linter warnings put the source path into the `.olean`."""
    rows = []
    for tc in ("leanprover/lean4:v4.29.0", "leanprover/lean4:v4.31.0",
               "leanprover/lean4:v4.33.1", OFFICIAL, "leanprover/lean4:v4.35.0"):
        try:
            lean = Lean(tc)
        except RuntimeError:
            continue
        for args, label, sub in (([], "default", "default"),
                                 (["-Dlinter.unusedVariables=false"],
                                  "`-Dlinter.unusedVariables=false`", "nolint")):
            hashes = []
            has_path = []
            for wt in ("worktree-a", "worktree-b"):
                d = fresh("olean-paths", tc.split(":")[-1], sub, wt)
                shutil.copy(HERE / "olean-paths/M.lean", d)
                lean.run(d / "M.lean", d, args=args)
                data = (d / "M.olean").read_bytes()
                hashes.append(hashlib.sha256(data).hexdigest()[:12])
                has_path.append(str(d).encode() in data)
            rows.append([tc.split(":")[-1], label, " / ".join(hashes),
                         "yes" if hashes[0] == hashes[1] else "no",
                         "yes" if any(has_path) else "no"])
    return "\n".join([
        "`olean-paths/M.lean` (one unused-variable warning) compiled as "
        "`lean -o <dir>/M.olean <dir>/M.lean` with absolute paths in two directories:\n",
        table(["Lean", "options", "olean sha256 (a / b)", "identical", "olean contains the source "
               "path"], rows)])


def write_project(d, name, lib_files, lakefile_extra=""):
    d.mkdir(parents=True, exist_ok=True)
    (d / "lean-toolchain").write_text(OFFICIAL + "\n")
    (d / "lakefile.toml").write_text(
        f'name = "{name.lower()}"\ndefaultTargets = ["{name}"]\n\n[[lean_lib]]\nname = "{name}"\n'
        + lakefile_extra)
    for rel, text in lib_files.items():
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)


def exp_lake_weak_args():
    """`weakLeanArgs` is not part of the trace: it can silence linters without rebuilding."""
    m = (HERE / "olean-paths/M.lean").read_text()
    weak = 'weakLeanArgs = ["-Dlinter.unusedVariables=false"]\n'
    rows = []
    oleans = {}
    for wt in ("a", "b"):
        d = fresh("lake-weak-args", wt)
        write_project(d, "Weak", {"Weak.lean": m})
        rc, cpu, _, o = sh(["lake", "build"], cwd=d, check=True)
        oleans[wt] = d / ".lake/build/lib/lean/Weak.olean"
    h = {k: hashlib.sha256(v.read_bytes()).hexdigest()[:12] for k, v in oleans.items()}
    rows.append(["no `weakLeanArgs`, fresh builds in `a` and `b`", f"{h['a']} / {h['b']}",
                 "yes" if h["a"] == h["b"] else "no"])
    # add weakLeanArgs to `a`: no rebuild
    da = WORK / "lake-weak-args/a"
    before = oleans["a"].stat().st_mtime_ns
    (da / "lakefile.toml").write_text((da / "lakefile.toml").read_text() + weak)
    _, _, _, o = sh(["lake", "build"], cwd=da, check=True)
    rebuilt_weak = oleans["a"].stat().st_mtime_ns != before
    # fresh builds of both with weakLeanArgs
    for wt in ("a", "b"):
        d = WORK / "lake-weak-args" / wt
        shutil.rmtree(d / ".lake")
        if weak not in (d / "lakefile.toml").read_text():
            (d / "lakefile.toml").write_text((d / "lakefile.toml").read_text() + weak)
        sh(["lake", "build"], cwd=d, check=True)
    h2 = {k: hashlib.sha256(v.read_bytes()).hexdigest()[:12] for k, v in oleans.items()}
    rows.append(["with `weakLeanArgs`, fresh builds in `a` and `b`", f"{h2['a']} / {h2['b']}",
                 "yes" if h2["a"] == h2["b"] else "no"])
    # moreLeanArgs is traced: rebuild
    before = oleans["a"].stat().st_mtime_ns
    (da / "lakefile.toml").write_text((da / "lakefile.toml").read_text().replace(
        "weakLeanArgs", "moreLeanArgs"))
    sh(["lake", "build"], cwd=da, check=True)
    rebuilt_more = oleans["a"].stat().st_mtime_ns != before
    return "\n".join([
        f"Toolchain: `{OFFICIAL}` (Lake). Project `Weak` = `olean-paths/M.lean` built with "
        "`lake build` in two directories `a` and `b`.\n",
        table(["build", "olean sha256 (a / b)", "identical"], rows),
        f"\nAdding `{weak.strip()}` to the built `a` and running `lake build` again rebuilt "
        f"`Weak`: **{'yes' if rebuilt_weak else 'no'}**. Renaming it to `moreLeanArgs` and "
        f"running `lake build` rebuilt `Weak`: **{'yes' if rebuilt_more else 'no'}**."])


def dev_lean():
    for tc in (os.environ.get("DEV_TOOLCHAIN"), "dev-fast-v4.34.0",
               "eth-act/lean4:dev-fast-v4.34.0-5"):
        if tc:
            try:
                return Lean(tc)
            except RuntimeError:
                pass
    return None


def exp_fast_lean():
    """`fast-lean build` vs `lake build` on a project with one slow proof."""
    fl = os.environ.get("FAST_LEAN") or shutil.which("fast-lean")
    if not fl:
        return "Skipped: no `fast-lean` (set FAST_LEAN or install it)."
    heavy = ("import Demo.Ops\n"
             "theorem t (s : Nat) : block [.o1, .o2] s = s + 1 + 2 := by\n"
             "  simp [block, Op.effect]\n")
    top = ("import Demo.Heavy\n"
           "theorem top (s : Nat) : block [.o1, .o2] s = s + 3 := by\n"
           "  rw [t]\n")
    axioms = "import Demo.Top\n#print axioms t\n#print axioms top\n"
    d = fresh("fast-lean", "demo")
    write_project(d, "Demo", {"Demo.lean": "import Demo.Top\n",
                              "Demo/Ops.lean": ops_source(400, warm=True),
                              "Demo/Heavy.lean": heavy, "Demo/Top.lean": top,
                              "Axioms.lean": axioms})
    rows = []

    def step(label, cmd, env_extra=None, clean=False):
        if clean:
            shutil.rmtree(d / ".lake", ignore_errors=True)
        env = dict(os.environ, **(env_extra or {}))
        rc, cpu, wall, o = sh(cmd, cwd=d, env=env)
        built = len(re.findall(r"Built ", o))
        _, _, _, ax = sh(["lake", "env", "lean", "Axioms.lean"], cwd=d)
        ax = "; ".join(l.strip() for l in ax.strip().splitlines() if "axioms" in l or "depend" in l)
        rows.append([label, "ok" if rc == 0 else f"exit {rc}", secs(cpu), built, ax])

    step("`lake build` (official), clean", ["lake", "build"], clean=True)
    step("`fast-lean build`, clean (`LEAN_DEV=proofs,sat`)", [fl, "build"], clean=True)
    step("then `lake build` (official)", ["lake", "build"])
    step("`LEAN_DEV= fast-lean build`, clean (faithful)", [fl, "build"], {"LEAN_DEV": ""},
         clean=True)
    step("`fast-lean build Demo.Top`, clean", [fl, "build", "Demo.Top"], clean=True)
    ops = []
    for tcl in (Lean(OFFICIAL), dev_lean()):
        if tcl:
            od = fresh("fast-lean", "ops-" + tcl.tc.replace("/", "-").replace(":", "-"))
            setup(tcl, od, sources={"Ops": ops_source(400, warm=True)}, libs=())
            ops.append(f"`{tcl.tc}` {secs(tcl.cpu(od / 'Ops.lean', od)[0])}")
    return "\n".join([
        f"Project `Demo` (`lean-toolchain` = `{OFFICIAL}`): `Demo.Ops` = `ops_source(400, "
        "warm=True)`, `Demo.Heavy` proves `t` by the slow `simp [block, Op.effect]`, `Demo.Top` "
        "uses `t`. After each step, `lake env lean Axioms.lean` prints the axioms of `t` and "
        "`top` (`Built` = modules and other artifacts Lake reported as built).\n",
        table(["step", "result", "CPU", "`Built` lines", "axioms"], rows),
        "\n`Demo/Ops.lean` alone with `lean` (equation generation for the 400-arm `match`): "
        + "; ".join(ops) + "."])


BUDGET_GOAL = "∀ x ∈ List.range 100, x * x % 7 ≠ 3"


def budget_source(k):
    """A search tactic in miniature: `decide` under a budget of `k` thousand heartbeats, then a
    fallback; `k = None` calls one tactic directly."""
    tac = (f"\n  first\n  | budget {k} => decide\n  | decide +kernel" if isinstance(k, int)
           else f" {k}")
    return f"import Budget\nimport HB\ncount_hb in\ntheorem t : {BUDGET_GOAL} := by{tac}\n"


def exp_budget():
    """Heartbeat budgets decide which proof a search finds, and failed alternatives cost their
    budget on every build."""
    rows = []
    lean = Lean(OFFICIAL)
    for k in (None, "decide +kernel", "decide", 100, 240, 250, 2000):
        if k is None:
            continue
        d = fresh("budget", re.sub(r"\W", "", str(k)))
        setup(lean, d, sources={"T": budget_source(k)}, libs=("HB", "Budget"))
        cpu, o = lean.cpu(d / "T.lean", d)
        tries = "; ".join(l.split(": ", 1)[1] for l in o.splitlines() if l.startswith("budget "))
        sha = hashlib.sha256((d / "T.olean").read_bytes()).hexdigest()[:12]
        label = f"`first \\| budget {k} => decide \\| decide +kernel`" if isinstance(k, int) \
            else f"`{k}` alone"
        rows.append([label, tries or "—", f"{heartbeats(o):,}k", secs(cpu), sha])
    vrows = []
    for v in ("v4.29.0", "v4.31.0", "v4.33.1", "v4.34.0", "v4.34.1", "v4.35.0"):
        try:
            lv = Lean(f"leanprover/lean4:{v}")
        except RuntimeError:
            continue
        cells = [v]
        for k in (2000, 250, 240):
            d = fresh("budget", v, str(k))
            setup(lv, d, sources={"T": budget_source(k)}, libs=("HB", "Budget"))
            o = lv.run(d / "T.lean", d)[3]
            line = next((l for l in o.splitlines() if l.startswith("budget ")), "?")
            if k == 2000:
                cells.append(re.search(r"after (\d+k)", line)[1])
            else:
                cells.append("`decide`" if "succeeded" in line else "fallback `decide +kernel`")
        vrows.append(cells)
    return "\n".join([
        f"Goal `{BUDGET_GOAL}`. `lib/Budget.lean` defines `budget K => tac` (run `tac` with its own "
        "budget of K thousand heartbeats; an overrun becomes an ordinary failure). Toolchain "
        f"`{lean.version}` for the first table. Heartbeats = whole theorem (`count_hb`), "
        "olean = sha256 of `T.olean`.\n",
        table(["proof", "budgeted attempt", "heartbeats", "CPU", "olean"], rows),
        "\nThe same source on several official toolchains: heartbeats `decide` needs (budget "
        "2000k), and which alternative wins with budgets of 250k and 240k:\n",
        table(["Lean", "`decide` needs", "winner, budget 250k", "winner, budget 240k"], vrows)])


def kernel_rfl_source(n, proof):
    v = n * (n - 1) // 2
    return (f"import KernelRfl\nimport HB\ncount_hb in\n"
            f"theorem t : (List.range {n}).foldl (· + ·) 0 = {v} := {proof}\n")


def exp_kernel_rfl():
    """Closing a closed computation `a = b`: elaborator `rfl`/`decide` vs kernel-only
    `decide +kernel`/`kernel_rfl` vs `decide_cbv`."""
    lean = Lean(OFFICIAL)
    proofs = ["rfl", "by rfl", "by decide", "by decide_cbv", "by decide +kernel", "by kernel_rfl"]
    rows = []
    for n in (100, 1000):
        for pf in proofs:
            d = fresh("kernel-rfl", str(n), re.sub(r"\W", "", pf))
            setup(lean, d, sources={"T": kernel_rfl_source(n, pf)}, libs=("HB", "KernelRfl"))
            rc, cpu, _, o = lean.run(d / "T.lean", d)
            err = next((l.split("error: ")[-1] for l in o.splitlines() if "error" in l), "")
            size = mb((d / "T.olean").stat().st_size) if rc == 0 else ""
            if rc == 0:
                cpu = lean.cpu(d / "T.lean", d)[0]
            rows.append([n, f"`{pf}`", "ok" if rc == 0 else f"error: `{err}`",
                         f"{heartbeats(o):,}k", secs(cpu), size])
    d = fresh("kernel-rfl", "false-goal")
    (d / "F.lean").write_text("import KernelRfl\n"
                              "theorem bad : (List.range 20).foldl (· + ·) 0 = 1 := by kernel_rfl\n")
    setup(lean, d, libs=("KernelRfl",))
    o = lean.run(d / "F.lean", d)[3]
    return "\n".join([
        f"Toolchain: `{lean.version}`. Goal `(List.range n).foldl (· + ·) 0 = n(n-1)/2`, one "
        "theorem per module; `kernel_rfl` from `lib/KernelRfl.lean` (`MVarId.refl` with "
        "`check := false`). Heartbeats = whole theorem incl. the kernel check (`count_hb`, "
        "synchronous); CPU = whole module.\n",
        table(["n", "proof", "result", "heartbeats", "CPU", "olean"], rows),
        "\n`kernel_rfl` on a false goal (`(List.range 20).foldl (· + ·) 0 = 1`): the kernel "
        "rejects it:\n", trim(o.replace(f"{d}/", ""), 8)])


def first_chain_source(proof, n=10):
    L = ["import HB"]
    for j in range(n):
        L.append(f"count_hb in\ntheorem t{j} : ∀ x ∈ List.range {90 + j}, x * x % 7 ≠ 3 := by\n"
                 f"  {proof}")
    return "\n".join(L) + "\n"


def exp_first_chain():
    """`first | a | b | c`: the failing alternatives are paid on every build."""
    lean = Lean(OFFICIAL)
    rows = []
    for name, pf in (("chain", "first | omega | (simp; done) | decide +kernel"),
                     ("winner", "decide +kernel")):
        d = fresh("first-chain", name)
        setup(lean, d, sources={"T": first_chain_source(pf)})
        cpu, o = lean.cpu(d / "T.lean", d)
        hb = [int(x) for x in re.findall(r"heartbeats: (\d+)k", o)]
        rows.append([f"`{pf}`".replace("|", "\\|"), f"{sum(hb):,}k", secs(cpu)])
    return "\n".join([
        f"Toolchain: `{lean.version}`. Ten theorems `∀ x ∈ List.range m, x * x % 7 ≠ 3` "
        "(m = 90..99), each proved by the given tactic; heartbeats summed over the ten.\n",
        table(["proof", "heartbeats", "module CPU"], rows)])


VERSIONS = ["v4.26.0", "v4.28.0", "v4.29.0", "v4.31.0", "v4.33.1", "v4.34.0", "v4.35.0"]


def exp_versions():
    """Version ranges: `:= rfl` tagging, `native_decide` axioms, the stuck-`match` pathology."""
    probe = ("def f (n : Nat) : Nat := n + 1\n"
             "theorem a (n : Nat) : f n = n + 1 := rfl\n"
             "theorem b (n : Nat) : f n = n + 1 := (rfl)\n"
             "theorem c (n : Nat) : f n = n + 1 := by rfl\n"
             "theorem nd : 2 + 2 = 4 := by native_decide\n"
             "#print a\n#print b\n#print c\n#print axioms nd\n")
    bad = (HERE / "stuck-match/Bad.lean").read_text().replace("import HB\n", "").replace(
        "count_hb in\n", "")
    rows = []
    for v in VERSIONS:
        try:
            lean = Lean(f"leanprover/lean4:{v}")
        except RuntimeError:
            continue
        d = fresh("versions", v)
        setup(lean, d, sources={"Probe": probe, "Ops": ops_source(100, warm=True), "Bad": bad},
              libs=())
        o = lean.run(d / "Probe.lean", d, olean=False)[3]
        tagged = [n for n in "abc" if re.search(rf"@\[defeq\] theorem {n} ", o)]
        ax = re.search(r"'nd' depends on axioms: \[(.*)\]", o)
        lean.run(d / "Ops.lean", d)
        rc = lean.run(d / "Bad.lean", d)[0]
        st = lean.stats(d, d / "Bad.olean").get("Bad", {}) if rc == 0 else {}
        rows.append([v, ", ".join({"a": "`:= rfl`", "b": "`:= (rfl)`", "c": "`:= by rfl`"}[n]
                                  for n in tagged) or "none",
                     ax[1] if ax else "?",
                     f"{st.get('matchEqns', '?')} / {st.get('splitters', '?')}"])
    return "\n".join([
        "Official toolchains. `@[defeq]` tagging of `theorem a : f n = n + 1 := rfl` (and `(rfl)`, "
        "`by rfl`) as shown by `#print`; axioms of `theorem nd : 2 + 2 = 4 := by native_decide`; "
        "`stuck-match/Bad.lean` at N = 100 (match equations / splitters stored in `Bad.olean`).\n",
        table(["Lean", "tagged `@[defeq]`", "`native_decide` axioms", "stuck match: match eqns / "
               "splitters"], rows)])


def exp_snippets():
    """The code snippets of the skills compile with the official toolchain."""
    lean = Lean(OFFICIAL)
    d = fresh("snippets")
    setup(lean, d, [HERE / "snippets/Snippets.lean"])
    rc, cpu, _, o = lean.run(d / "Snippets.lean", d)
    return "\n".join([f"Toolchain: `{lean.version}`. `lean snippets/Snippets.lean`: "
                      f"{'ok' if rc == 0 else f'exit {rc}'}, {secs(cpu)} CPU. Output:\n",
                      trim(o, 40)])


EXPERIMENTS = {
    "stuck-match": exp_stuck_match,
    "profile": exp_profile,
    "defeq-step-lemmas": exp_defeq_step_lemmas,
    "frame-lemma": exp_frame_lemma,
    "eq-def": exp_eq_def,
    "eqns-upstream": exp_eqns_upstream,
    "listing-lemmas": exp_listing_lemmas,
    "decide": exp_decide,
    "olean-paths": exp_olean_paths,
    "lake-weak-args": exp_lake_weak_args,
    "fast-lean": exp_fast_lean,
    "snippets": exp_snippets,
    "versions": exp_versions,
    "budget": exp_budget,
    "first-chain": exp_first_chain,
    "kernel-rfl": exp_kernel_rfl,
}


def main():
    names = sys.argv[1:] or list(EXPERIMENTS)
    if names == ["--list"]:
        for k, f in EXPERIMENTS.items():
            print(f"{k}: {f.__doc__.split(chr(10))[0]}")
        return
    RESULTS.mkdir(exist_ok=True)
    for name in names:
        fn = EXPERIMENTS[name]
        print(f"== {name}", flush=True)
        t0 = time.monotonic()
        body = fn()
        load = os.getloadavg()[0]
        text = (f"# {name}\n\n{fn.__doc__.strip()}\n\n"
                f"Recorded {time.strftime('%Y-%m-%d')} by `examples/run.py {name}` "
                f"({os.cpu_count()} CPUs, load {load:.0f}; CPU = user + sys seconds, user in "
                f"parentheses; median of {REPEATS} runs where repeated).\n\n{body}\n")
        (RESULTS / f"{name}.md").write_text(text)
        print(body, f"\n({time.monotonic() - t0:.0f} s)", flush=True)


if __name__ == "__main__":
    main()
