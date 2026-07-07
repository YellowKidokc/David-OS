# Label Enforcement

Labels in TOP AI FIS are operational rules, not just tags.

If a folder is labeled `program_root`, `protected`, `do_not_delete`, or
`quarantine`, every watcher, scanner, worker, and review gate must obey that
label before creating or executing a job.

## Where Labels Live

Labels are stored in three places, each with a different job:

| Layer | Purpose |
| --- | --- |
| SQLite | Enforcement source of truth. The hub checks this before jobs run. |
| Folder markers | Portable memory that travels with folders where allowed. |
| File sidecars | Portable memory that travels with files where allowed. |

SQLite wins for enforcement. Marker files help rebuild SQLite if a machine is
offline or a folder moves.

## Folder Labels

Important folder labels:

```text
protected
program_root
do_not_delete
do_not_move
quarantine
inbox
archive
```

Examples:

```text
program_root -> implies protected -> blocks rename/move/archive/delete
do_not_delete -> blocks soft delete and cleanup jobs
quarantine -> blocks sharing/publishing/deleting until reviewed
inbox -> allows suggestions, but actions are review-first
```

## File Labels

Important file labels:

```text
protected
canonical
duplicate_candidate
unknown_extension
secret_candidate
sidecar_protected
delete_candidate
```

Examples:

```text
canonical + duplicate_candidate -> canonical wins; do not archive/delete
unknown_extension + delete_candidate -> quarantine wins; review first
sidecar_protected -> import/check before any cleanup
```

## Most Restrictive Wins

When labels conflict, the most restrictive label wins.

```text
blocked > manual_only > review_required > proposal_allowed > auto_allowed
```

So if one detector says "media dump, can organize" and another says
"program root, do not touch," the program-root label wins.

## Enforcement Flow

```text
watcher event
  -> read folder marker and SQLite labels
  -> scanner adds symptom labels
  -> worker proposes a job
  -> review gate checks labels
  -> blocked/review/queued decision
  -> approved worker executes only if ledger is ready
```

## Rule For Deletes

No permanent delete in v1.

Deletes are only:

```text
soft_delete proposal -> review -> .trash/<date>/ move -> ledger entry
```

Protected sidecar extensions are never treated as junk:

```text
.fmeta
.chi
.fisnote
.fistag
.fisdead
```

Before any cleanup touches those, the hub must import/check them and create a
ledger entry.

## Rule For Program Roots

If a folder contains project markers like:

```text
.git
package.json
pyproject.toml
requirements.txt
node_modules
venv
.venv
Cargo.toml
```

then it gets:

```text
program_root
protected
do_not_move
do_not_delete
```

The scanner can still read/index/classify it, but no automatic organizing.

## Implementation Contract

Every job that could touch files must check:

```text
config/rules/label_enforcement.v1.json
```

before it is queued for execution.

If the label state is missing or stale, the safe answer is:

```text
review_required
```

not "go ahead."
