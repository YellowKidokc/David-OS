# API CALL ROUTING MANIFEST
## POF 2828 | June 30, 2026 | Compiled by Opus
## For Excel Opus — classify outputs into Excel sheets

---

## SHEET ASSIGNMENTS

### Sheet 1: "Change the Game" — Forces rewrites
- 04_writing_analysis.txt → buried claims, hidden premises, what collapses
- 12_interrogation.txt → argue against, write Lean 4, design experiment
- 06 Q3 + Q5 → structural improvements + overclaim detection

### Sheet 2: "Classify" — What is this document?
- 01_find_variables.txt → chi-variable presence and regime
- 07_TWO_manifestation.txt → where canon appears unnamed
- Station 11 (existing) → domain percentages + Ten Laws

### Sheet 3: "Quantify" — Score and measure
- 10_FOUR_chi_evaluator.txt → 10 channels × 10 pressure states
- 08_fruits_coherence.txt → nine Fruits + anti-Fruits + phase transitions
- Station 07 (existing) → Justice-Mercy + Δα extension

### Sheet 4: "Test" — Structural correspondence
- 02_isomorphic.txt → 4-level isomorphism test
- 11_universality_class_test.txt → 10-axiom model instance + Sharpe/SNR
- 03_cross_reference.txt → GTQ↔MDA dialogue
- 09_THREE_isomorphic_event_discovery.txt → event-level density scoring

### Sheet 5: "Extract" — Pull structured data
- 13_generate_claims_json.txt → claims sidecar for human review
- 05_session_notes.txt → handoff format for future sessions
- 06 Q9 → compression (1 sentence / 1 paragraph / 12 lines)

---

## OUTPUT ROUTING — Where DeepSeek results go

### → WEBSITE (JSON/HTML)
Station 11 domain bar → article header color gradient
Station 12 summaries → SEO meta tags + reading paths
Station 13 ISO HTML → isomorphism registry pages
Station 14 claims sidecar → verification overlay on articles
Station 15 isomorphism test → isomorphism panel data
Station 16 proof map → Proof Explorer connections
Station 09 glossary → glossary popup overlay

### → EXCEL (tracking/dashboards)
Everything from Sheets 1-5 above. One row per article.
Master workbook with 5 sheets.

### → BOTH
Station 08 knowledge graph → KG tab on articles + Excel connectivity scores
Station 10 final report → dashboard view + master Excel composite grade

---

## TWO MISSING STATIONS — Need to be built

### Station NEW-A: Citation Discovery
"What published papers can we cite that are structurally aligned?"

For each article, search for:
- Physics papers whose equations match our derivations
- Theology papers whose claims match our structural results
- Philosophy papers that independently reach similar conclusions
- Cross-domain papers that bridge the same gap

Output: JSON list of citable papers with:
  - title, author, year, DOI or URL
  - which claim in OUR article it supports
  - WHY we should cite it (structural alignment, not just topic overlap)
  - confidence: direct_support | structural_parallel | background

This needs web search or a citation database API (Semantic Scholar, CrossRef).
Cannot be done purely with DeepSeek — needs retrieval.

### Station NEW-B: Internal Cross-Reference
"What other parts of our OWN corpus can we cite from this article?"

For each article, search the vectorized corpus for:
- Other articles that make the same claim (evidenced_in field)
- Articles that provide the proof for something this article asserts
- Articles that extend or specialize what this article introduces
- Articles that share the same chi-variable profile

Output: JSON list of internal cross-references with:
  - source_article (this one)
  - target_article (the one we should link to)
  - relationship: proves | extends | specializes | parallels | contradicts
  - specific_claim that connects them
  - suggested_link_text for the HTML

This REQUIRES the vectorized corpus. Run after vectorization.

---

## VECTORIZATION PLAN

Vectorize the entire faiththruphysics.com corpus:
- All HTML articles → extract clean text → embed
- All markdown source → embed
- All ISO registry pages → embed
- All Lean 4 theorem descriptions → embed

Store in: ChromaDB or similar local vector DB
Query pattern: for each article, retrieve top-N most similar articles

This enables:
- Station NEW-B (internal cross-reference)
- Station 09 series continuity (currently needs retriever)
- Station 10 final report (cross-article context)
- Prompt 03 cross-reference (GTQ↔MDA requires both corpora)

---

*POF 2828 | Theophysics Research Initiative*
