# Least-Action Prediction Engine

The trust breakthrough:

```text
Show what the user is likely to do.
Show what the system recommends.
Explain the difference.
Let the user choose.
Learn from the choice.
```

The system earns file-control trust by predicting the operator before it starts
acting for the operator.

First implementation:

- engine: `apps/api/file_intelligence_hub/intelligence/prediction_engine.py`
- API: `apps/api/file_intelligence_hub/api/routes_prediction.py`
- endpoints: `/predict/observe`, `/predict/predict`, `/predict/correct`,
  `/predict/make-permanent`, `/predict/stats`, `/predict/rules`

## Statistical Method

Use active learning, not random labeling.

Research basis:

- active learning: ask for the examples with the highest expected learning value,
- human-in-the-loop ML: keep the operator in the correction loop,
- personal information management: preserve meaningful folder structures,
- user-action prediction: learn from move, rename, copy, and reject sequences,
- programming by demonstration: turn repeated user actions into proposed rules.

For a folder with many files, the system should ask for labels/actions on the
few examples that are most useful:

1. Representative examples from dense clusters.
2. Uncertain examples near decision boundaries.
3. Disagreement examples where engines differ.
4. High-risk examples where mistakes cost more.
5. Boundary examples that separate two possible folders/actions.

Do not ask the user to label 200 files. Ask them to decide the 10 to 20 examples
that will classify the other 180 safely.

## Start Predictions By Question 2

The 20 scanner questions are not a long survey before intelligence begins.

```text
Q1 gives inventory.
Q2 starts prediction.
```

After extension spread and version/name signals are known, the system can start
showing provisional predictions:

```text
Your likely action: move to Research
System recommendation: move to Research/Physics/2026Q1
Why: same extension/domain/semantic cluster as 18 existing files
Confidence: 0.71
Needs review: yes
```

Each later question refines the prediction.

## Prediction Targets

Predict these separately:

| Prediction | Output |
| --- | --- |
| folder role | inbox, archive, program_root, research, media_dump, backup |
| file classification | kind, domain, semantic vector, status |
| rename | best name candidates |
| destination | likely folder or proposed new cluster |
| action | keep, rename, move, copy, archive, protect, quarantine |
| risk | auto_allowed, proposal, review_required, blocked |
| batch rule | "apply this to 37 similar files?" |

## Least-Action Loop

```text
scan
  -> cluster files
  -> predict user action
  -> predict system action
  -> ask for the most informative examples
  -> learn from accept/edit/reject
  -> propose batch rule
  -> review gate
  -> execute only approved jobs
```

## Query Score

Rank files for user decision with a combined score:

```text
query_score =
  uncertainty
  + committee_disagreement
  + representativeness
  + risk_weight
  + batch_impact
  - redundancy
```

Where:

- uncertainty: model is unsure between labels/actions,
- committee_disagreement: rules, semantic scorer, folder history, and user model disagree,
- representativeness: file sits near the center of a large cluster,
- risk_weight: mistake would be expensive,
- batch_impact: one decision can label many similar files,
- redundancy: already asked about a near-duplicate.

## The First 20 Actions

The system should learn fastest by asking/observing in this order:

1. Protect roots: what must never be touched?
2. Identify folder role for the top-level folders.
3. Ask about one representative file from each major cluster.
4. Ask about uncertain boundary files between clusters.
5. Ask about highest-risk anomalies.
6. Observe real user moves/renames.
7. Predict the next action before the user acts.
8. Offer "apply to similar" only after one accepted decision.

## Trust Score

Automation can increase only when predictions match user behavior.

Track per folder/profile:

```text
prediction_matches
accepted_suggestions
edited_suggestions
rejected_suggestions
undos
blocked_by_review_gate
```

Low-risk automation can be proposed after repeated success in the same scope.

Never automate:

```text
delete
program roots
secrets
unknown extensions
cross-drive moves
bulk restructures
low-confidence actions
```

## GUI

The Prediction Board should show:

```text
File/folder
Your likely action
System recommended action
Why
Confidence
Risk gate
Accept
Edit
Reject
Apply to similar
Protect
```

The user learns the system by seeing the prediction.
The system learns the user by recording the correction.
