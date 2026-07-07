# Onboarding Questions and GUI Flow

This is the first user-trust layer for the File Intelligence System.

The 20 questions are not a survey. Each question must produce a concrete axiom
that changes scanner behavior, predictions, naming suggestions, folder plans, or
review gates.

```text
question -> axiom -> scanner weighting -> prediction -> GUI proposal -> review gate
```

If a question does not change behavior, remove it.

## Operating Order

1. Start the background scan.
2. Ask the 20 onboarding questions.
3. Begin provisional predictions by question 2.
4. Cache naming suggestions and folder-role predictions in SQLite during scan.
5. Show the first report as a prediction board, not a static report.
6. Let the user accept, edit, reject, protect, or apply-to-similar.

The scanner should not wait for onboarding to finish. It should build facts while
the user answers. The answers then become weights and rules over the facts.

## Main GUIs

### 1. Onboarding Constitution

Purpose: collect the 20 answers and convert them into axioms.

Outputs:

- `primary_navigation_axis`
- `separate_business_personal`
- `folder_depth_limit`
- `rename_schema_default`
- `automation_level`
- `delete_policy`
- `protected_domains`
- `archive_policy`
- `sync_priority`
- `review_thresholds`

### 2. Prediction Board

Purpose: show the trust breakthrough.

```text
File/folder
Your likely action
System recommended action
Why
Confidence
Risk gate
Accept / Edit / Reject / Protect / Apply to Similar
```

This is where the system earns permission by showing it understands the user.

### 3. Rename Studio

Purpose: show multiple deterministic names before touching anything.

The first four schemas:

| Schema | Example |
| --- | --- |
| `clean_snake` | `quarterly_report_2026_07.pdf` |
| `clean_title` | `Quarterly Report 2026 07.pdf` |
| `date_project_slug` | `2026-07-03_finance_quarterly_report.pdf` |
| `domain_date_type` | `finance_2026-07-03_receipt_walmart.pdf` |

Scanner cache should precompute:

```text
original_name
extension
detected_domain
detected_type
clean_snake
clean_title
date_project_slug
domain_date_type
spelling_flags
collision_warning
confidence
```

### 4. Folder System Builder

Purpose: solve messy folder piles, not merely rename files.

It should classify folder roles:

```text
inbox
project
business
personal
finance
legal
research
media_dump
archive
program_root
backup
do_not_touch
```

Then propose adaptable structures:

```text
Personal-first
Business-first
Project-first
Domain-first
Date/archive-first
Hybrid
```

### 5. Automation Rules

Purpose: convert repeated accepted predictions into explicit rules.

Examples:

```text
Always move invoice PDFs from Downloads to Business/Finance/Invoices/YYYY.
Always rename screenshots with date_project_slug.
Never move program roots.
Always review cross-drive moves.
```

### 6. Review Gate Queue

Purpose: keep the brakes visible.

Always review:

```text
delete
bulk move
cross-drive move
program_root
credentials
unknown extension
low confidence
folder with protected labels
```

## How It Programs Later

### SQLite Tables

The API should eventually persist:

```text
onboarding_answers
preference_axioms
scan_sessions
file_name_suggestions
folder_role_predictions
action_predictions
accepted_predictions
automation_rules
review_gate_decisions
```

### API Flow

```text
POST /onboarding/session
GET  /onboarding/questions
POST /onboarding/answer
GET  /onboarding/axioms

POST /folders/scan
GET  /folders/{id}/predictions
GET  /files/{id}/name-suggestions

POST /predict/observe
POST /predict/predict
POST /predict/correct
POST /predict/make-permanent

POST /automation/rules
GET  /reviews
POST /reviews/{id}/decision
```

### Scanner Behavior

During scan, compute deterministic facts first:

```text
extension histogram
file count
size totals
age distribution
top filename tokens
top domains
duplicates
program-root indicators
archive indicators
media-dump indicators
protected labels
```

Then generate predictions:

```text
folder role
file domain
file type
rename suggestions
likely destination
system recommended destination
risk gate
```

The GUI reads predictions from SQLite instead of recomputing them live.

## Non-Negotiable Design Rule

The system should never say only:

```text
I recommend this.
```

It should say:

```text
You usually do this.
I recommend this.
Here is why they differ.
Choose what wins.
```

