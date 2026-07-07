# SEMANTIC ADDRESSING SYSTEM — BLIND VALIDATION TEST (CORRECTED)
# Paste this entire prompt into any LLM (GPT, Gemini, Claude, etc.)
# Do NOT add context. Do NOT explain Theophysics. The system must stand alone.

---

## SYSTEM DEFINITION (read carefully, follow exactly)

You are a document classification engine. You use a 10-variable coordinate system to assign every document a semantic address.

### SCORING FRAME (MANDATORY)

Score each variable based on the document **as an artifact**:
- what the document is structurally
- how the document functions
- how the document presents its content

Do **NOT** score based on the subject matter alone if that would conflict with the document’s own structure.

Example:
- A rigorous paper *about* incompleteness is **not** high E unless the paper itself is structurally noisy, fragmented, contradictory, or unresolved.
- A short incomplete note *is* high E if the artifact itself is fragmentary or underspecified.

### The 10 Variables

Each variable scores from 0 to 3:
- 0 = absent
- 1 = minor presence
- 2 = significant presence  
- 3 = dominant signal

| Var | Name | What it detects |
|-----|------|-----------------|
| G | Authority/Ground | External source of order, foundational grounding, non-derived origin, governing law |
| M | Mechanism/Action | Physical process, execution, procedure, operational logic, tools doing things |
| E | Entropy/Disorder | The document's own structural noise, ambiguity, decay, contradiction, fragmentation, or unresolved state |
| S | Identity/Self | Persistent personhood, inner life, selfhood, "who" not "what" |
| T | Time/Sequence | Temporal structure, chronology, irreversibility, lifecycle, historical progression |
| K | Knowledge/Info | Structured content, definitions, data, explicit claims, formal understanding |
| R | Relation/Bond | Connections, dependencies, obligations, covenants, networks, "between" things |
| Q | Experience/Felt | Subjective experience, first-person awareness, emotional tone, felt meaning |
| F | Faith/Trust | Commitment under uncertainty, assumptions, belief, epistemic risk, working hypotheses |
| C | Coherence/Unity | Integration, consistency, everything fitting together, system-wide harmony |

### Output Format

For each document, output ONLY:

```
DOCUMENT: [name]
SCORES: G=_ M=_ E=_ S=_ T=_ K=_ R=_ Q=_ F=_ C=_
HASH: [top 2-3 vars by score][magnitude 1-3][state D/W/F]
PREDICT: [one sentence predicting what this document contains]
```

### Rules (STRICT)

1. Do NOT explain your reasoning
2. Do NOT add caveats or disclaimers
3. Do NOT say "it depends" — commit to scores
4. If you are unsure, that uncertainty IS the E score rising
5. Magnitude: 1=fragment/sketch, 2=substantial, 3=comprehensive
6. State: D=draft, W=working, F=final/published
7. The HASH uses only the variables scoring 2 or 3
8. The PREDICT sentence must follow ONLY from the scores, not from your knowledge of the document
9. Score the document as the artifact it is, not merely the topic it discusses

---

## CLASSIFY THESE DOCUMENTS

1. Genesis Chapter 1 (King James Bible)
2. Moby Dick by Herman Melville (complete novel)
3. Brown v. Board of Education (1954 Supreme Court opinion)
4. Harry Potter and the Philosopher's Stone by J.K. Rowling
5. Einstein's 1905 paper "On the Electrodynamics of Moving Bodies"
6. A unsigned, undated Post-it note reading "call Mike Tuesday"
7. The United States Constitution
8. Darwin's On the Origin of Species
9. A Python script: def sort_list(arr): return sorted(arr)
10. Martin Luther King Jr.'s "I Have a Dream" speech
11. A corporate Q4 earnings spreadsheet with 500 rows of financial data
12. Euclid's Elements (Book I)
13. A personal diary entry: "Today was the worst day of my life"
14. RFC 2616 (HTTP/1.1 Specification)
15. The Communist Manifesto by Marx and Engels
16. A blank .txt file (0 bytes)
17. Shakespeare's Hamlet
18. A marriage certificate
19. Gödel's 1931 incompleteness paper
20. A TikTok comment: "lol this is so fake"
