# Local NLP Synthesis Pipeline Prompt

## Job

Build a local, non-destructive Theophysics vault synthesis pipeline using the existing David OS tagger and the local NLP model folders.

The goal is not to rewrite the whole vault. The goal is to extract clean chunks, group them by topic, detect contradictions and definition drift, audit math, and produce synthesis reports that point back to source files and paragraph numbers.

## Existing Model Roots

Model root:

```text
\\192.168.2.50\brain\05_MODELS
```

Station root:

```text
\\192.168.2.50\brain\04_STATIONS\NLP_file-intelligence-system-master\file-intelligence-system-master
```

Useful model roles:

- `M01_summarizer`, `M13_bart_summarizer`, `M23_08_SUMMARIZER`: summarization
- `M02_embedder`, `M19_03_EMBEDDINGS_FAST`, `sbert_minilm`: embeddings
- `M03_contradiction`, `M08_contradiction_deep`, `M17_01_CONTRADICTION_PRIMARY`, `M18_02_CONTRADICTION_FAST`, `M27_14_CONTRADICTION_TINY`, `M28_15_CONTRADICTION_ENSEMBLE_LONG`, `deberta_nli`: contradiction / NLI
- `M07_fact_verify`, `M20_05_SCIENTIFIC_CLAIM_VERIFY`: fact or scientific-claim verification
- `M09_claim_extract`: claim extraction
- `M10_timeline`: timeline extraction
- `M11_math_verify`: math verification
- `M12_paper_review`: paper review
- `M21_06_NER_GENERAL`, `M29_16_NER_ENHANCED`: NER
- `M22_07_ZERO_SHOT_CLASSIFIER`: zero-shot classification
- `M24_09_RERANKER`: reranking
- `M30_18_QA_EXTRACTOR`: QA extraction
- `M06_llm`, `M15_mistral_7b`: local LLM layer if usable

## Do Not

- Do not mutate the original vault.
- Do not move original papers.
- Do not start with vectorization before clean chunk extraction.
- Do not summarize whole papers first and lose source structure.
- Do not treat every tag match as equally meaningful.
- Do not sentence-slice by default.

## Build Order

### 1. Inventory

Scan Markdown/text files and record:

- file path
- title
- headings
- paragraph count
- word count
- detected tags
- detected equations
- detected definitions
- detected claims

### 2. Chunking

Create stable chunk records:

- source file
- heading path
- paragraph index
- text
- hash
- nearby context

Default chunk policy:

- paragraph-only for clean excerpts
- paragraph `1-1` window for synthesis
- section-level chunks for final reconstruction

### 3. Topic Aggregation

Create topic views containing excerpts, not copied source files.

Priority topics:

- Resurrection
- Grace
- Atonement
- Justice/Mercy
- Record Preservation
- Q Gate
- Coherence
- Sin Operator
- ResurrectionAsVacuumConfirm
- Coupling Architecture
- Vacuum Stabilization

### 4. Embeddings

Only after chunk extraction, embed cleaned chunks using the fastest working local embedder:

- `M02_embedder`
- `M19_03_EMBEDDINGS_FAST`
- `sbert_minilm`

Persist embeddings in a local database or vector index.

### 5. Clustering

For each topic, cluster related chunks.

Example Resurrection clusters:

- historical resurrection
- resurrection as proof
- resurrection as phase transition
- resurrection as vacuum confirmation
- resurrection and record preservation
- resurrection and glorification
- resurrection and final judgment

### 6. Claim Extraction

Run claim extraction over each cluster.

Output:

- claim text
- source chunk ids
- confidence
- claim type: theological, mathematical, historical, metaphorical, model-internal, empirical, speculative

### 7. Definition Audit

Extract definition-like statements and group by term.

Detect:

- same term with multiple definitions
- different terms used for the same idea
- undefined core terms
- circular definitions

Priority terms:

- Grace
- Justice
- Mercy
- Sin
- Coherence
- Resurrection
- Q Gate
- Record
- Operator
- Faith
- Repentance
- Atonement
- Vacuum
- Entropy
- Chi
- Master Equation

### 8. Math Audit

Extract equations and math-like expressions.

Check:

- variable reuse
- missing definitions
- inconsistent notation
- impossible algebra
- unsupported formal leap
- metaphor written as math

Output labels:

- valid
- probably valid
- notation unclear
- unsupported
- contradiction
- needs human review

### 9. Contradiction / NLI Pass

Compare claims within each topic.

Output:

- supported pairs
- duplicate claims
- tension pairs
- direct contradictions
- same words / different meaning candidates

### 10. Synthesis

For each topic report, produce:

- canonical definition
- strongest claims
- repeated claims
- weak or unsupported claims
- contradictions and tensions
- best source excerpts
- recommended paper section
- parking lot

## Output Layout

```text
theophysics_synthesis/
  SUMMARY.md
  topics/
    Resurrection.md
    Grace.md
    Atonement.md
    Justice_Mercy.md
  audits/
    definition_audit.md
    math_audit.md
    contradiction_audit.md
    claim_inventory.md
  data/
    chunks.jsonl
    claims.jsonl
    definitions.jsonl
    math_items.jsonl
    embeddings.index
```

## First Test

Run only on Resurrection first.

Use:

- 20-40 source files, or
- top 100 resurrection-related chunks

Do not run the whole vault until the Resurrection test proves the chunk size, clustering, and synthesis format are useful.

The Resurrection report should answer:

- What are all the resurrection claims in the vault?
- Which claims repeat?
- Which are strongest?
- Which are unclear?
- Which are theological vs. mathematical vs. metaphorical?
- Which definitions and equations are involved?
- What should be kept for a final paper?
- What should be discarded or parked?

## Core Rule

Extraction first. Embeddings second. Contradiction third. Synthesis last.

Every summary, claim, contradiction, equation, and canonical definition must point back to the original file and paragraph/section.
