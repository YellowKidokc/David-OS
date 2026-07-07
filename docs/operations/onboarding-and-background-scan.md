# Onboarding And Background Scan

The first install should do two things at the same time:

1. Ask the user enough questions to become safe.
2. Start a read-first background scan so the app can ask smarter follow-ups.

The system should not wait until every question is answered before learning the shape of the machine. It also should not take action before it understands the user's safety boundaries.

## First-Run Flow

```text
Install
  -> choose storage location
  -> start Hub API
  -> open React cockpit
  -> begin Step 0 scope interview
  -> start scanner in observe/index/profile mode
  -> build user file profile
  -> write folder markers only inside approved roots
  -> create proposals, not actions
  -> user approves next step
```

## The First 20 Questions

The canonical machine-readable questions live in:

```text
D:\GitHub\TOP AI FIS\config\rules\onboarding_questions.v1.json
```

The first five are mandatory:

```text
1. Is this personal, business, research, or mixed?
2. What folders are we allowed to inspect first?
3. What folders or file types should I never touch?
4. What files are most important not to lose?
5. What is the goal today: clean, organize, rename, dedupe, archive, or understand?
```

The rest collect:

```text
daily working folders
primary domains
sensitive file classes
active projects/program roots
backup and mirror locations
source-of-truth rules
duplicate keeper preference
rename style
date policy
AI export grouping
media categories
business lanes
retention rules
public/private boundaries
automation comfort level
```

## What The Scanner Does During Questions

During onboarding, the scanner runs in this mode:

```text
observe_index_and_profile_only
```

Allowed:

```text
scan
hash
inventory
classify
write sidecars inside approved roots
write folder markers inside approved roots
create proposals
```

Blocked:

```text
delete
move
rename
archive
overwrite
publish
share private memory
run command-line actions
```

## Marker Files

The canonical marker contract lives in:

```text
D:\GitHub\TOP AI FIS\config\rules\folder_marker_contract.v1.json
```

Every approved scanned folder can receive three folder marker files:

```text
.folder.fmeta
FIS_FOLDER_INDEX.fisnote
FIS_FOLDER_DIAGNOSIS.chi
```

Their jobs:

```text
.folder.fmeta
  machine-readable folder profile

FIS_FOLDER_INDEX.fisnote
  human-readable inventory of files and families

FIS_FOLDER_DIAGNOSIS.chi
  symptom diagnosis, risk, confidence, and proposed plan
```

File-level sidecars use protected weird extensions:

```text
example.pdf.fmeta
example.pdf.chi
example.pdf.fisnote
example.pdf.fisdead
```

The scanner must recognize these every time. A delete/archive job must import and review these before removing anything.

## Folder Safety Zones

The onboarding profile divides the machine into zones:

```text
DO NOT TOUCH
  system folders, program roots, hidden config, active dependencies

PROTECTED
  critical personal, legal, tax, medical, client, research, family, credential, source code

WORKING
  user-approved folders such as Documents, Desktop, Downloads, Pictures, project folders

DISPOSABLE / REVIEW
  duplicate candidates, old downloads, temp exports, empty folders, generated junk
```

Default rule:

```text
Only work inside user-selected folders. Never assume whole-drive authority.
```

## Why The Questions Matter

The scan can tell what exists. The questions tell what matters.

For example, two folders can both contain PDFs and spreadsheets:

```text
Folder A: tax/legal records
Folder B: random downloads
```

The file types look similar, but the safety policy is completely different.

The questionnaire creates the user's file profile:

```text
environment type
allowed roots
do-not-touch roots
protected roots
important files
backup locations
source-of-truth rules
rename preferences
automation comfort
```

That profile becomes the scanner's conscience.

## Evidence-Based Follow-Ups

After the first scan, the app should ask questions based on what it actually found:

```text
I found a lot of Excel files. Are these accounting, trading, inventory, research, or client records?

I found project folders with code dependencies. Should I protect those from rename and move?

I found AI conversation exports. Do you want those grouped by model, project, or date?

I found images. Are these family photos, screenshots, site assets, generated images, reference images, or mixed?

I found duplicates. Should I prefer newest, oldest, largest, source-of-truth folder, or manual review?
```

This is the difference between a file sorter and a file consultant.

## Operating Principle

Every proposed action must answer:

```text
What did we find?
Why do we think that?
What do we propose?
What could break if we are wrong?
```

That is the trust layer.

