# 28POF Workbook Integration

Source workbook:

```text
\\192.168.2.50\h_hp\Desktop\28pof_hub_architecture_with_templates.xlsx
```

This workbook is a concrete architecture template for the hub. It confirms the control-plane rule:

```text
folders do not host active scripts
watchers and API calls create jobs
hub policy decides
workers execute
GUI approves risky actions
SQLite remembers
```

## Imported Contract Sheets

The extractor is:

```text
D:\GitHub\TOP AI FIS\scripts\bootstrap\extract_28pof_workbook.py
```

It writes scanner-readable JSON under:

```text
D:\GitHub\TOP AI FIS\config\rules
```

Generated files:

```text
symptom_registry.28pof.v1.json
detection_functions.28pof.v1.json
severity_scale.28pof.v1.json
folder_profiles.28pof.v1.json
review_gates.28pof.v1.json
build_order.28pof.v1.json
28pof_workbook_import_summary.json
```

## How It Fits The First Install

The onboarding questions create the user safety profile.

The 28POF symptom registry tells the scanner what to detect.

The 28POF detection functions give stable function names for scanner implementation.

The 28POF folder profiles tell the hub how different roots should behave.

The 28POF review gates tell the hub when to stop and ask the user.

The 28POF build order tells us which implementation pieces should be built first.

## Scanner Contract

The scanner should load:

```text
config\rules\onboarding_questions.v1.json
config\rules\folder_marker_contract.v1.json
config\rules\symptom_registry.28pof.v1.json
config\rules\detection_functions.28pof.v1.json
config\rules\review_gates.28pof.v1.json
```

Then it should:

```text
1. read user profile
2. scan only approved roots
3. detect symptoms
4. write marker files where allowed
5. create jobs/proposals
6. route risky actions to review
```

