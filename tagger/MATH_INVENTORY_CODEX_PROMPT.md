# Theophysics Math Inventory Prompt

## Goal

Build a source-backed inventory of the current Theophysics math before judging whether the math is true.

Do not scan the million-document pile first. Start with the newest or most canonical Theophysics vault, extract the math, group it, map symbols to definitions, and only then compare older vaults.

## Source Of Truth

Default canonical source:

```text
O:\_Theophysics_v5
```

Useful first-pass folders:

```text
O:\_Theophysics_v5\MASTER_EQUATION
O:\_Theophysics_v5\00_Canonical
O:\_Theophysics_v5\99_MATH_APPENDIX
O:\_Theophysics_v5\04_THEOPYHISCS
O:\_Theophysics_v5\Cross
O:\_Theophysics_v5\__John Templeton
```

## Tool

```text
tagger\theophysics_math_inventory.py
```

## First Pass

Run read-only:

```powershell
python D:\GitHub\David-OS\tagger\theophysics_math_inventory.py `
  --source O:\_Theophysics_v5\MASTER_EQUATION `
  --source O:\_Theophysics_v5\00_Canonical `
  --source O:\_Theophysics_v5\99_MATH_APPENDIX `
  --source O:\_Theophysics_v5\04_THEOPYHISCS `
  --source O:\_Theophysics_v5\Cross `
  --source "O:\_Theophysics_v5\__John Templeton" `
  --output C:\Theophysics_Tagger\05_MATH_AUDIT
```

## Extract

Scan for:

```text
$...$
$$...$$
fenced math blocks
χ =
dχ/dt =
L =
G·M·E·S·T·K·R·Q·F·C
Noether
Lagrangian
Hamiltonian
entropy
operator
tensor
field
phase transition
boundary theorem
```

## Reports

Produce:

```text
math_inventory.md
symbol_dictionary.md
math_conflicts.md
canonical_math_candidate.md
```

Also keep CSV sidecars for machine review:

```text
math_inventory.csv
symbol_definitions.csv
math_conflicts.csv
summary.json
```

## Audit Questions

Do not start with:

```text
Is all the math true?
```

Start with:

```text
What math do we actually have?
Where is it?
What symbols are used?
Are they defined consistently?
Which version appears most mature?
Which equations are repeated across final-looking documents?
```

## Rules

- Do not mutate the vault.
- Do not move files.
- Do not compare old vaults until the canonical scan has a clean inventory.
- Keep every math item attached to source file and paragraph number.
- Treat `math_conflicts.md` as a cleanup map, not a final verdict.
- Treat `canonical_math_candidate.md` as a candidate spine for human review.
