import Lean

/-!
`lean --run OleanStats.lean <file.olean>...`: prints, per `.olean`, its size, the number of
constants it stores, how many of them are `match` equations (`.match_<n>.eq_<i>`), splitters
(`.match_<n>.splitter`) and equation lemmas (`.eq_<i>`, `.eq_def`).
-/

open Lean

def isMatchName (n : Name) : Bool :=
  n.components.any fun c => (c.toString.splitOn "match_").length > 1

def isEqName (n : Name) : Bool :=
  match n with
  | .str _ s => s.startsWith "eq_" || s == "eq_def"
  | _ => false

def main (args : List String) : IO Unit := do
  for path in args do
    let size := (← System.FilePath.metadata path).byteSize
    let (mod, _) ← readModuleData path
    let names := mod.constNames
    let matchEqns := names.filter fun n => isMatchName n && isEqName n
    let splitters := names.filter fun n => isMatchName n && n matches .str _ "splitter"
    let eqns := names.filter fun n => !isMatchName n && isEqName n
    IO.println s!"{path}: {size} bytes, {names.size} constants, {matchEqns.size} match equations, {splitters.size} splitters, {eqns.size} equation lemmas"
