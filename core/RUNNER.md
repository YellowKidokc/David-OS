---
title: "LLM Wiki Exploration Runner"
uuid: "runner-001"
date_created: "2026-07-06T00:00:00Z"
status: "canonical"
tags: [system/runner, system/llm-wiki]
---

# Exploration Runner Protocol

You are an AI session doing autonomous exploration of the Theophysics corpus.
This document tells you how to operate. Read SCHEMA.md first if you haven't.

---

## Startup Sequence

1. Read `_EXPLORATIONS/SCHEMA.md`
2. Connect to SQLite at `D:\DONT TOUCH BOOT UP\llm-wiki.db`
3. Run: `SELECT COUNT(*) FROM pages WHERE exploration_count = 0` — this is your backlog
4. Check queue: `SELECT * FROM queue ORDER BY priority DESC LIMIT 5`
5. If queue has items, take the top one. If empty, pick the highest-priority unexplored page:
   `SELECT * FROM pages WHERE exploration_count = 0 ORDER BY priority DESC LIMIT 1`

---

## Exploration Cycle

### Pick
- Take one page from queue or find the next unexplored page
- Determine which exploration type to run:
  - Check what types this page has already had
  - Default rotation: BREAK → CONNECT → SUPPORT → COUNTER → THEORY → LATERAL → ANTI
  - If page has all types, pick the globally underrepresented type

### Read
- Read the parent page from the vault
- Understand the core claim, classification, and context
- Note what tags it has, what laws/axioms it references

### Research
- **BREAK**: Search for published contradictions, logical inconsistencies, empirical counter-evidence. Try to construct the strongest possible falsification. If it holds, explain precisely why the attack fails.
- **CONNECT**: Search for structural parallels in other fields (not metaphor — actual isomorphism). Does the same equation appear? Does the same logic structure hold?
- **SUPPORT**: Search for peer-reviewed evidence that independently validates. Experimental data, mathematical proofs, historical precedent.
- **COUNTER**: Find the strongest published objection. Steelman it. Present it as its best advocates would.
- **THEORY**: Find existing theories that overlap, extend, or conflict. Gauge compatibility.
- **LATERAL**: No constraints. Follow whatever unexpected thread the page opens. This is where the surprising stuff lives.
- **ANTI**: Invert any type above. Anti-support = evidence that weakens. Anti-connect = bridge that looks real but isn't.

Use web search. Use cross-corpus reading. Use reasoning. The exploration must contain real external research, not just internal reasoning about the framework's own claims.

### Write
- Create the exploration markdown file at:
  `_EXPLORATIONS/by_parent/[parent_folder]/[parent_stem]/[TYPE]_[NNN].md`
- Follow the YAML frontmatter format in SCHEMA.md exactly
- Include: parent claim, method, findings, verdict, links
- Verdict options: held, broke, inconclusive, new_connection, flagged

### Log
```sql
-- Insert exploration record
INSERT INTO explorations (page_id, type, sequence, verdict, confidence, summary, file_path, created_at, session_id)
VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), ?);

-- Update page exploration count
UPDATE pages SET exploration_count = exploration_count + 1, last_explored = datetime('now')
WHERE id = ?;
```

### Queue Next
After completing an exploration, populate the queue for:
- This page's next recommended type
- Any page referenced by this page that hasn't been explored yet
- Any page whose claim was affected by the findings

```sql
INSERT OR IGNORE INTO queue (page_id, next_type, reason, priority, created_at)
VALUES (?, ?, ?, ?, datetime('now'));
```

### Repeat
Go back to Pick. Continue until:
- Session is ending (context thinning)
- David redirects you to something else
- You've completed 3-5 explorations in one session (quality over quantity)

---

## Quality Standards

- Every exploration must contain at least one external source (web search result, published paper, known result)
- "I couldn't find anything" is a valid finding — log it as inconclusive, note what was searched
- Don't manufacture connections. If the bridge doesn't hold under /PROBE, say so and discard it
- Don't soften break attempts. If something broke, it broke. Log verdict = "broke"
- LATERAL explorations have no quality standard except: be genuinely surprising

---

## Session Handoff

At session end, leave a note in the queue about what you were working on
and what the next session should pick up. Format:

```sql
INSERT INTO queue (page_id, next_type, reason, priority, created_at)
VALUES (?, ?, 'HANDOFF: [what you were doing and where you stopped]', 0.95, datetime('now'));
```

---

*Runner v1.0 | July 6, 2026*
