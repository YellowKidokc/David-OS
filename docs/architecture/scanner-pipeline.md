# Scanner Pipeline

Source reviewed:

```text
\\192.168.2.50\h_hp\Desktop\scanner_pipeline_explained.html
```

This document converts that HTML explanation into the working TOP AI FIS
scanner contract.

## Core Principle

The scanner does not organize files directly.

```text
detection -> labels -> diagnosis -> treatment plan -> jobs -> review gates -> actions
```

The scanner is allowed to observe, label, score, and propose. It does not rename,
move, archive, or delete files by itself.

## The 20 Questions

The "20 questions" are the scanner's first-pass learning model. They are not
chat questions to the user. They are repeatable checks the scanner asks of every
folder.

| Q | Learns | Primary symptom(s) | Operational meaning |
| --- | --- | --- | --- |
| 1 | File type spread | `S01` | Too many unrelated extensions means the folder may be a dump. |
| 2 | Duplicate/version naming | `S02`, `N01` | Many `final`, `copy`, or `(1)` names mean current truth is unclear. |
| 3 | Tree depth | `S03`, `N04` | Deep sparse folders may need flattening or path shortening. |
| 4 | Directory width | `S04` | Hundreds/thousands of files in one folder create scroll paralysis. |
| 5 | Orphan sidecars | `S05` | `.chi`, `.fmeta`, `.fisnote`, `.srt`, or metadata files lost their parent. |
| 6 | Name collisions | `S06` | Case or near-name collisions can cause wrong-file usage. |
| 7 | Project scatter | `S07` | Same project appears across distant folders/drives. |
| 8 | Broken references | `S08` | Markdown/HTML links point to missing targets. |
| 9 | Exact duplicates | `C01` | Same bytes appear in multiple places. |
| 10 | Format redundancy | `C02` | Same stem/content exists as `.md`, `.html`, `.pdf`, `.docx`, etc. |
| 11 | Abandoned drafts | `C03` | Drafts and WIP files have aged into clutter. |
| 12 | Mixed documents | `C04` | PDFs, docs, sheets, and decks are mixed without grouping. |
| 13 | Auto-named media | `C05`, `N01` | Photos/screenshots/videos need date/source naming proposals. |
| 14 | Unknown file types | `C06` | Unknown extensions must be quarantined/reviewed, not deleted. |
| 15 | Age/activity mismatch | `T01`, `T02`, `T04` | Stale files in active folders or burst imports need review. |
| 16 | Program-root markers | `I01`, `I05` | Code/app roots become protected zones. |
| 17 | Credentials/secrets | `I03` | Critical alert; never auto-fix. |
| 18 | Sync conflicts | `I04`, `I06` | Conflicted copies or mirror drift require careful reconciliation. |
| 19 | Missing research tags | `R01`, `R06` | Canonical/research files need `.chi` or SQLite semantic classification. |
| 20 | Semantic identity | semantic score | Run the 10D scorer and produce coordinate hash/meta classification. |

## Label Shape

Each symptom found by `agents/scanners/folder_scanner.py` should be normalized to:

```json
{
  "symptom_id": "S04",
  "category": "Structural",
  "severity": "medium",
  "name": "Flat overload",
  "count": 1,
  "auto_fixable": false,
  "priority_code": 40003,
  "affected_paths": ["D:/Downloads"],
  "recommended_action": "classify + split by domain/date"
}
```

This label can then be stored in SQLite, shown in React, routed as a Top of Mind
message, or converted into a job proposal.

## Severity Semantics

| Severity | Meaning | Default behavior |
| --- | --- | --- |
| low | Cosmetic/noise, low data-loss risk | May propose batch cleanup; still reversible. |
| medium | Functional clutter or confusion | Proposal only; human approval before action. |
| high | Structural/data-loss risk | Requires planning and review. |
| critical | Security/integrity danger | Alert and block automation. |

## File Actions

Actions are the output of approved jobs, not raw scanner decisions.

| Action | Meaning | Safety rule |
| --- | --- | --- |
| classify | Run deterministic/semantic scoring and store labels | Read-only; safe. |
| write_sidecar | Write `.chi`, `.fmeta`, `.fisnote`, or `.fisdead` | Allowed only where folder policy permits marker files. |
| rename | Change filename, keep extension | Suggest first; ledger must record old/new. |
| move | Move file and sidecars together | Proposal first unless explicitly safe. |
| archive | Move to reversible `.archive/<date>/` | Proposal first for user files. |
| soft_delete | Move to reversible `.trash/<date>/` | Always approval-required in v1. |
| protect | Mark folder/file as never-touch | Automatic for program roots/secrets zones. |
| convert | Create optimized copy, preserve original | Proposal or safe-copy only; never overwrite source. |

## 10,000-File Folder Strategy

A huge folder is not read all at once. It is triaged.

### Phase 1: Discovery

Count files, directories, extensions, total size, top-level width, depth, and
dangerous markers.

Immediate labels usually include:

```text
S04 flat overload
S01 extension swamp
C01 duplicate pressure
C05 media dump
C06 unknown blobs
I01 program-root danger, if markers exist
```

### Phase 2: Sampling

For very large folders, use a deterministic sample:

- first 50 files alphabetically,
- last 50 files alphabetically,
- 50 deterministic middle/sample files,
- all files in the top 5 percent by size,
- all files with dangerous/protected extensions,
- all program-root marker files,
- all sidecar/marker files.

This keeps startup fast while still catching the dangerous stuff.

### Phase 3: Classification

Files move through four layers:

```text
physical -> semantic -> meta -> relational
```

- physical: extension, size, dates, path, hash
- semantic: 10D vector, dominant variables, coordinate hash
- meta: CONTEXT / DOMAIN / FUNCTION / STATE
- relational: project, source, owner, sidecar links, references

### Phase 4: Cluster Naming

Do not name a 10,000-file folder as one thing. Name the clusters inside it.

Cluster proposal pattern:

```text
{category}_{domain}_{date_range}
```

Examples:

```text
research_physics_2025Q4
research_theology_2026Q1
code_theophysics
finance_personal_2025
media_photos_2025Q4
media_screenshots_2026Q1
installers_software
_unknown
_duplicates
_protected
```

The original folder becomes a reviewed reorganization proposal. No bulk move
happens without review.

## What Gets Stored

### Per File

- stable file id
- current path and original path
- quick hash and full hash where available
- extension/kind/parser status
- 10D semantic vector and coordinate hash
- meta classification
- symptom ids affecting the file
- proposed actions, if any

### Per Folder

- folder role/profile
- file count, directory count, total size
- health grade and score
- symptom counts
- dominant semantic variables
- proposed cluster/subfolder structure
- last scanned timestamp
- score delta from previous scan

### In Shared Memory

Use concise facts agents can query:

```text
scan_Downloads_20260703 -> Grade D, 14 symptoms, 340 duplicate clusters
folder_role_Downloads -> intake_hub
chi_dominant_Downloads -> Q, E, S
```

## Learning Loop

Every human decision feeds preference learning, scoped by folder profile:

- accepted rename reinforces naming pattern,
- edited rename records what changed,
- rejected rename suppresses that pattern,
- manual move teaches routing preference,
- ignored symptom lowers alert frequency but keeps diagnosis,
- fixed symptom improves next scan score and records the successful treatment.

Learning is local first. A correction in Downloads must not become a global rule
without explicit approval.

## Next Implementation Target

Create a scanner-to-jobs bridge:

```text
ScanReport -> normalized labels -> treatment plan -> jobs/review_items
```

That bridge should read:

- `config/rules/scanner_pipeline.v1.json`
- `config/rules/symptom_registry.28pof.v1.json`
- `config/rules/review_gates.28pof.v1.json`
- folder profile rules

Then it should create proposals, not perform actions.
