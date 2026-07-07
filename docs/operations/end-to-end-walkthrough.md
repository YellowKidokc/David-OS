# TOP AI FIS End-to-End Walkthrough

This is the plain-language path from install to daily use. The goal is to explain what a person experiences, what the system is doing behind the curtain, and why this is different from a normal file organizer, clipboard tool, or chatbot frontend.

## What The User Installs

TOP AI FIS is one system with several small parts:

1. **Hub API**
   The local brain. It receives events, stores history, checks permissions, runs jobs, and tells other parts what to do.

2. **SQLite databases**
   The fast local memory. They index files, folders, API calls, clipboard items, labels, vectors, and action history.

3. **Folder memory buckets**
   The human-readable storage. Real notes, captures, and memory files live in folders so they are easy to back up and inspect.

4. **Watchers and scanners**
   Small workers that notice folder changes, scan files, detect duplicates, classify content, and propose labels.

5. **NLP and CHI labelers**
   The meaning layer. spaCy can extract language features, and CHI decides domain, coherence, category, and system meaning.

6. **React cockpit**
   The control panel. This is where the user sees agents, messages, clipboard history, folders, API calls, memory, and approvals.

7. **AutoHotkey bridge**
   The desktop hand. It pastes, sends, captures selected text, follows windows, and lets normal desktop apps talk to the hub.

8. **Optional Synology / desktop / laptop nodes**
   Multiple machines can run watchers and report to the same hub or keep redundant backups.

## First Install Experience

A normal install should feel like this:

1. User installs or starts the hub.
2. User chooses where memory and databases live.
3. User opens the React cockpit.
4. User adds one or more watched folders.
5. User enables clipboard capture if they want it.
6. User connects optional bridges: AutoHotkey, Syncthing, Synology, Cloudflare/R2 later.
7. User runs the first scan.
8. System reports what it found before changing anything.
9. User approves or rejects proposed labels, renames, moves, conversions, or archives.
10. The hub records every decision so the next scan gets smarter.

The first run should be cautious. It should diagnose, label, and propose. It should not start moving or deleting files without approval.

## Beginning-To-End Example

### Step 1: A File Arrives

The user drops this file into a watched folder:

```text
D:\DONT TOUCH BOOT UP\PICS\new folder\scan0007.pdf
```

The file name is bad, but the file might be important.

### Step 2: Watcher Reports The Event

The local watcher sees the new file and sends an event to the hub:

```text
event_type: file_created
path: D:\DONT TOUCH BOOT UP\PICS\new folder\scan0007.pdf
node: desktop
```

The watcher does not decide what to do. It reports.

### Step 3: Hub Creates A Job

The hub stores the event in SQLite and creates a scan/classify job:

```text
file_events -> folder_scans -> dispatch_jobs
```

Now the system has an audit trail before any action happens.

### Step 4: Reader Extracts What It Can

The reader engine checks the file:

```text
extension: .pdf
signature: PDF
metadata: title/author/pages if available
text: extracted if possible
```

If the PDF is image-only, the reader marks it as needing OCR instead of pretending it understands it.

### Step 5: NLP And CHI Classify Meaning

If text is available:

```text
spaCy -> tokens, lemmas, entities, noun chunks, sentence structure
CHI -> domain, profile, meaning, category, confidence
```

Example output:

```text
domain: legal
category: lease_document
confidence: 0.82
suggested_project: Legal
needs_review: true
```

### Step 6: Sidecar Is Written

The system writes metadata beside the file using protected weird extensions:

```text
scan0007.pdf
scan0007.pdf.fmeta
scan0007.pdf.chi
```

These sidecars are not random junk. They are protected system memory. Before any cleanup/delete job runs, those extensions are recognized and indexed into SQLite.

### Step 7: SQLite Index Updates

The hub indexes:

```text
file path
hash
size
dates
detected type
labels
tags
sidecars
confidence
recommended action
```

Now search is fast even if the folder is huge.

### Step 8: User Sees A Proposal

In the React cockpit, the user sees:

```text
New file found:
scan0007.pdf

Likely type:
Legal / lease document

Suggested rename:
2026-07-03_lease_document_scan0007.pdf

Suggested folder:
20_Projects/Legal/Needs_Review

Action:
Approve / Edit / Reject / Archive / Ask AI
```

Nothing has been moved yet.

### Step 9: User Approves

If approved, the organizer performs the action and logs it:

```text
old_path
new_path
who approved
when approved
why suggested
```

If rejected, that is also stored. Rejections are training data for the preference engine.

### Step 10: Memory And Knowledge Update

If the user chooses **Save as Memory**, the system creates a Markdown memory item:

```text
TopOfMind_Memory/20_Projects/Legal/2026-07-03_lease-document-note.md
```

The SQLite index links that memory to the original file and sidecars.

If vectorization is enabled, the text is chunked and indexed for similarity search.

## Clipboard Example

The user copies text from a browser, PDF, chat, or command line.

AutoHotkey posts it to:

```text
POST /clipboard/save
```

The hub stores:

```text
clipboard text
source window
timestamp
agent target if selected
tags if provided
```

From the React cockpit, the user can:

```text
copy it back out
send it to Claude/Gemini/Codex/Kimi/GPT
save it as memory
attach it to a project
turn it into a command/API call
```

This makes clipboard history part of the same intelligence system instead of a separate throwaway tool.

## Agent Message Example

The user sends a message to Claude from the cockpit.

The hub records:

```text
agent: claude
message
route
priority
conversation id
created time
```

The AHK bridge or API bridge sends the text to the real app. When a response is captured, it comes back through the hub and can be:

```text
stored in message history
saved to clipboard history
saved as memory
searched later
routed to another agent
attached to a project
```

That is how multiple AIs can work together without losing the conversation trail.

## Why This Is Different

Normal file organizers move files. TOP AI FIS builds a memory and decision system around files.

Normal clipboard tools save copied text. TOP AI FIS can route clipboard items to agents, memory, files, and API calls.

Normal chatbot frontends send messages. TOP AI FIS treats messages as durable project data that can be searched, tagged, approved, shared, or kept private.

Normal vector databases hide everything in embeddings. TOP AI FIS keeps human-readable folders first, then uses SQLite and vectors as indexes.

Normal automations do actions. TOP AI FIS records evidence, proposes actions, and learns from approvals and rejections.

## Core Rule

```text
Folders store the memory.
SQLite indexes the memory.
The Hub API enforces permissions.
Workers propose actions.
The user approves risky changes.
```

That is the backbone.

## What The User Should Expect

On day one:

```text
safe scanning
clipboard saving
folder inventory
basic labels
searchable history
manual approvals
```

After setup:

```text
faster folder startup from SQLite cache
better naming suggestions
agent-routed memory
knowledge banks
duplicate detection
conversion suggestions
Synology/laptop/desktop redundancy
```

Later:

```text
Cloudflare/R2 publishing
MCP tools
agent-to-agent routing
Markov/prediction engines
stronger NLP
approval-trained preferences
```

## What Must Stay Safe

The system should never silently delete or move important files just because it guessed.

High-risk actions need approval:

```text
delete
move across major folders
archive
rename large batches
overwrite
convert and replace original
share private memory with another agent
run command-line actions
```

Low-risk actions can be automatic:

```text
scan
hash
index
write sidecar
create proposal
record clipboard
update SQLite cache
generate report
```

## Short Pitch

TOP AI FIS is a local-first intelligence hub for files, folders, clipboard, agents, commands, and memory.

It watches what changes, understands what it can, asks for help when it cannot, proposes safe actions, remembers decisions, and lets multiple AIs work from the same permissioned memory system.

