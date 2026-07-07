# SEMANTIC ADDRESSING SYSTEM — STRESS TEST (HARD MODE)
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
Do **NOT** score based on the subject matter alone if that would conflict with the document's own structure.
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
HASH: [3-level vars] · [2-level vars] · [1-level vars] — magnitude, state
PREDICT: [one sentence predicting what this document contains]
```
### Rules (STRICT)
1. Do NOT explain your reasoning
2. Do NOT add caveats or disclaimers
3. Do NOT say "it depends" — commit to scores
4. If you are unsure, that uncertainty IS the E score rising
5. Magnitude: 1=fragment/sketch, 2=substantial, 3=comprehensive
6. State: D=draft, W=working, F=final/published
7. Hash format: [all vars scoring 3] · [all vars scoring 2] · [all vars scoring 1] — magnitude, state
8. The PREDICT sentence must follow ONLY from the scores, not from your knowledge of the document
9. Score the document as the artifact it is, not merely the topic it discusses
10. Variables scoring 0 never appear in the hash
---
## CLASSIFY THESE DOCUMENTS

1. A suicide note left on a kitchen table (handwritten, 3 paragraphs)
2. The Rosetta Stone (the physical artifact, not a photo of it)
3. A redacted FBI document with 60% blacked out
4. The Nicene Creed (325 AD, original Greek)
5. A live-updating stock ticker showing AAPL price
6. Kafka's "The Metamorphosis" (complete novella)
7. A DNA sequence file (.fasta format, 3 billion base pairs)
8. The Treaty of Versailles (1919, full text)
9. A child's crayon drawing of their family
10. Wittgenstein's Tractatus Logico-Philosophicus
11. An autopsy report (standard medical examiner format)
12. The Book of Revelation (KJV)
13. A CAPTCHA image showing distorted text "xR7pQ2"
14. Gandhi's letter to Hitler (July 23, 1939)
15. A functioning analog clock (the object itself)
16. Nietzsche's "Thus Spoke Zarathustra"
17. A spreadsheet of 10,000 rows — all cells contain "ERROR"
18. The Voyager Golden Record (the physical disc)
19. A cease-and-desist letter from a law firm
20. John Cage's 4'33" (the musical score)