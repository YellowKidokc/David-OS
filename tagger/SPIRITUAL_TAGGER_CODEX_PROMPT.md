# Spiritual Tagger Build Prompt

## Goal

Build and run the David OS spiritual tagger over the full Theophysics corpus without destroying or moving originals.

The first pass is document-level and paragraph-level only. Do not slice to sentence level in Phase 1.

## Source Registry

- Tag source: `tagger/Master Spiritual tagger.md`
- Generated registry: `tagger/spiritual_tag_registry.csv`
- Runner: `tagger/spiritual_paragraph_tagger.py`

## Operating Principle

If a paper hits a tag, the tagger should create a matching folder route and, when explicitly requested, copy the original paper into that tag folder.

One paper may appear in many tag folders. That is intentional. The tag folders are a discovery/index layer, not the canonical source of truth.

## Phase 1: Folder Routing

Run read-only first:

```powershell
python D:\GitHub\David-OS\tagger\spiritual_paragraph_tagger.py `
  --source O:\_Theophysics_v5 `
  --output C:\Theophysics_Tagger\02_INDEX `
  --tagged C:\Theophysics_Tagger\03_TAGGED `
  --limit 1000
```

Review:

- `*_document_tags.csv`
- `*_paragraph_tags.csv`
- `*_folder_routes.csv`
- `*_summary.json`

Then copy by primary tag if the routes look sane:

```powershell
python D:\GitHub\David-OS\tagger\spiritual_paragraph_tagger.py `
  --source O:\_Theophysics_v5 `
  --output C:\Theophysics_Tagger\02_INDEX `
  --tagged C:\Theophysics_Tagger\03_TAGGED `
  --copy-mode primary
```

For the full “copy copy copy into every matching tag folder” behavior:

```powershell
python D:\GitHub\David-OS\tagger\spiritual_paragraph_tagger.py `
  --source O:\_Theophysics_v5 `
  --output C:\Theophysics_Tagger\02_INDEX `
  --tagged C:\Theophysics_Tagger\03_TAGGED `
  --copy-mode all-tags
```

## Phase 2: Paragraph Slicing

Only after Phase 1 routes look useful:

```powershell
python D:\GitHub\David-OS\tagger\spiritual_paragraph_tagger.py `
  --source O:\_Theophysics_v5 `
  --output C:\Theophysics_Tagger\02_INDEX `
  --tagged C:\Theophysics_Tagger\03_TAGGED `
  --slices C:\Theophysics_Tagger\04_EXPORTS\paragraph_slices `
  --slice-paragraphs
```

This writes paragraph artifacts with source path, paragraph number, and tags.

## Resurrection Pilot

Before slicing the whole vault, run a focused resurrection pilot:

1. Scan `O:\_Theophysics_v5` for `Resurrection`, `Incarnation`, `Cross`, `Pentecost`, `VacuumStabilization`, `CouplingArchitecture`, and `ResurrectionAsVacuumConfirm`.
2. Select the top 20-40 papers by paragraph-hit count.
3. Extract paragraph windows, not sentences.
4. Start with a `1-1` window: one paragraph before, the hit paragraph, and one paragraph after.
5. Compare against `0-0` hit paragraph only and `2-2` two before/two after.

Default recommendation: `1-1` is the best first-pass unit because it preserves setup and caveat without dragging in the whole paper.

## Rules

- Do not move originals.
- Do not delete originals.
- Do not sentence-slice in Phase 1.
- Keep paragraph text attached to source path and paragraph number.
- Treat folders as index copies, not canonical storage.
- Prefer C drive for generated indexes and copied tag folders.
- Leave `O:\_Theophysics_v5` as the source-of-truth vault.

## Why Paragraphs First

Paragraphs preserve enough context for theological and formal claims. Sentences are too brittle for this corpus because claims often depend on the paragraph-level setup, caveat, or open-problem label.
