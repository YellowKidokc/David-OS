#Requires AutoHotkey v2.0
#SingleInstance Force

; ============================================================
; PROMPT ASSEMBLER — POF 2828
; Walks you through Layer 0→4, shows enough to decide,
; pre-assembles the final prompt, copies to clipboard.
; Hotkey: Win+P to launch
; ============================================================

PROMPT_DIR := "O:\_Theophysics_v5\David\EVALUATION_BUNDLE\MODULAR_PROMPT_SYSTEM"
SAVE_DIR   := "O:\_Theophysics_v5\David\EVALUATION_BUNDLE\SAVED_ASSEMBLIES"

; ── Block descriptions (what you see in the picker) ─────────
BLOCKS := Map(
    ; Layer 0
    "P0", "INTERPRETIVE POSTURE`nSets the lens before any domain block.`nUse for: external content (YouTube, Bible, web)`nSkip for: Theophysics papers you wrote",

    ; Layer 1 — Preamble
    "P1", "CPMR`nInterrogate first, build workflow, then execute.`nUse for: unclear scope, new projects, staged work",
    "P2", "THINKING CONTRACT`n10-point rigorous reasoning. Falsifiability required.`nUse for: adversarial testing, formal proofs, destroy-testing",
    "P3", "EVALUATOR`nDual technical + coherence assessment.`nUse for: paper evaluation, scoring, structured review",

    ; Layer 2 — Domain
    "D0", "COMPRESSED AXIOMS (~400 tokens)`n7 generators. API/pipeline use only.`nDO NOT combine with D2.",
    "D1", "TEN LAWS TAGGER`nTag every claim against L01-L10 + symmetry pairs.`nStandard for any Theophysics paper.",
    "D2", "AXIOM MAPPER (full 198)`nFull derivation chain mapping.`nHeavy — use for deep single-paper review.",
    "D3", "DIRECTION MARKER`nMark P→S / S→P / P↔S / P-only / S-only.`nStandard for cross-domain papers.",
    "D4", "SIX DOMAIN GRID`nScore across H/P/S/T/Synthesis/Agency.`nUse for broad epistemic coverage.",
    "D5", "FRUITS PRIMITIVES`n12 moral invariants as structural constraints.`nUse for theological/ethical papers.",
    "D6", "INDIGENOUS AXIOM EXTRACTOR`nFinds content's OWN bedrock — no framework imposed.`nRun FIRST on YouTube, Bible, external content. D1/D2 run after.",

    ; Layer 3 — Output
    "O1", "SEMANTIC JSON → Obsidian`nMachine-readable %%semantic{...}%% block.`nUse for: pipeline, automated batch processing.",
    "O2", "SCORECARD`nSection-by-section scoring tables.`nUse for: human review of a single paper.",
    "O3", "KILL CONDITIONS`nFalsification table + cascade analysis.`nPairs with S1_ADVERSARIAL.",
    "O4", "GAP REPORT`nMissing axioms, weak links, severity-ranked.`nPairs with S2_CONSTRUCTIVE.",
    "O5", "PAPER FINGERPRINT (5 lines)`nFastest output. Triage mode.`nPairs with S3_COMPRESSION.",

    ; Layer 4 — Style
    "S1", "ADVERSARIAL`nAttack everything. Find weakest link.`nDO NOT combine with S2.",
    "S2", "CONSTRUCTIVE`nFix everything. Suggest improvements.`nDO NOT combine with S1.",
    "S3", "COMPRESSION`nNo prose. Data only. Pipeline mode.`nDO NOT combine with S4.",
    "S4", "NARRATIVE`nPlain language. Non-specialist reader.`nDO NOT combine with S1 or S3."
)

; ── Compatibility rules ──────────────────────────────────────
; Returns warning string if conflict, else ""
CheckConflicts(selected) {
    warn := ""
    if selected.Has("D0") and selected.Has("D2")
        warn .= "⚠ D0 + D2 conflict — D0 replaces D2. Remove one.`n"
    if selected.Has("D6") and selected.Has("D2")
        warn .= "⚠ D6 must finish before D2. Run D6 first pass, D2 second.`n"
    if selected.Has("S1") and selected.Has("S2")
        warn .= "⚠ S1 + S2 conflict — opposing intent. Pick one.`n"
    if selected.Has("S3") and selected.Has("S4")
        warn .= "⚠ S3 + S4 conflict — opposing format. Pick one.`n"
    if selected.Has("S1") and selected.Has("S4")
        warn .= "⚠ S1 + S4 conflict — tone clash. Pick one.`n"
    return warn
}

; ── Preset assemblies ────────────────────────────────────────
PRESETS := Map(
    "01 TRIAGE-FAST",        ["P3","D1","O5","S3"],
    "02 TRIAGE-DEEP",        ["P2","D1","D2","D3","O5","S3"],
    "03 PAPER-REVIEW",       ["P3","D1","D3","D5","O2","S2"],
    "04 PAPER-DESTROY",      ["P2","D1","D2","D3","O3","S1"],
    "05 PAPER-STRENGTHEN",   ["P3","D2","D3","O4","S2"],
    "06 PIPELINE-AUTO",      ["P3","D1","D2","D3","D4","D5","O1","S3"],
    "07 EXPLAIN-HUMAN",      ["P3","D1","O5","S4"],
    "08 GAP-FILL",           ["P3","D2","D3","O4","S2"],
    "09 EXTERNAL-TRIAGE",    ["P0","P2","D6","O5","S3"],
    "10 YOUTUBE-AXIOM",      ["P0","P2","D6","O3","S1"],
    "11 BIBLE-VALIDATE",     ["P0","P2","D6","D2","O3"],
    "12 CHANNEL-COMPARE",    ["P0","P2","D6","D1","O4"],
    "13 FULL-FRAMEWORK",     ["P2","D1","D2","D3","D4","D5","O2","S2"]
)

; ── Read a block file and return its content ─────────────────
ReadBlock(code) {
    ; Map code to filename
    fileMap := Map(
        "P0","LAYER_0_POSTURE\P0_INTERPRETIVE_POSTURE.md",
        "P1","LAYER_1_PREAMBLE\P1_CPMR.md",
        "P2","LAYER_1_PREAMBLE\P2_THINKING_CONTRACT.md",
        "P3","LAYER_1_PREAMBLE\P3_EVALUATOR.md",
        "D0","LAYER_2_DOMAIN\D0_COMPRESSED_AXIOMS.md",
        "D1","LAYER_2_DOMAIN\D1_TEN_LAWS.md",
        "D2","LAYER_2_DOMAIN\D2_AXIOM_MAPPER.md",
        "D3","LAYER_2_DOMAIN\D3_DIRECTION_MARKER.md",
        "D4","LAYER_2_DOMAIN\D4_SIX_DOMAIN_GRID.md",
        "D5","LAYER_2_DOMAIN\D5_FRUITS_PRIMITIVES.md",
        "D6","LAYER_2_DOMAIN\D6_INDIGENOUS_AXIOM_EXTRACTOR.md",
        "O1","LAYER_3_OUTPUT\O1_SEMANTIC_JSON.md",
        "O2","LAYER_3_OUTPUT\O2_SCORECARD.md",
        "O3","LAYER_3_OUTPUT\O3_KILL_CONDITIONS.md",
        "O4","LAYER_3_OUTPUT\O4_GAP_REPORT.md",
        "O5","LAYER_3_OUTPUT\O5_PAPER_FINGERPRINT.md",
        "S1","LAYER_4_STYLE\S1_ADVERSARIAL.md",
        "S2","LAYER_4_STYLE\S2_CONSTRUCTIVE.md",
        "S3","LAYER_4_STYLE\S3_COMPRESSION.md",
        "S4","LAYER_4_STYLE\S4_NARRATIVE.md"
    )
    if !fileMap.Has(code)
        return "; [Block file not found for: " code "]`n"
    path := PROMPT_DIR "\" fileMap[code]
    if !FileExist(path)
        return "; [File missing: " path "]`n"
    return FileRead(path) "`n`n---`n`n"
}

; ── Assemble final prompt from selected codes ────────────────
AssemblePrompt(selected) {
    ; Order: Layer 0 first, then P, then D (sorted), then O, then S
    order := ["P0","P1","P2","P3","D0","D1","D2","D3","D4","D5","D6",
              "O1","O2","O3","O4","O5","S1","S2","S3","S4"]
    out := ""
    for code in order {
        if selected.Has(code)
            out .= ReadBlock(code)
    }
    return out
}

; ── Save assembly to disk ────────────────────────────────────
SaveAssembly(name, selected, assembled) {
    if !DirExist(SAVE_DIR)
        DirCreate(SAVE_DIR)
    ts := FormatTime(, "yyyyMMdd_HHmmss")
    safeName := RegExReplace(name, "[^\w\-]", "_")
    path := SAVE_DIR "\" ts "_" safeName ".md"
    
    header := "---`nassembly_name: " name "`ncreated: " ts "`nblocks: "
    codes := []
    for code in selected
        codes.Push(code)
    header .= "[" StrJoin(codes, ", ") "]`n---`n`n"
    
    FileAppend(header . assembled, path)
    return path
}

StrJoin(arr, sep) {
    out := ""
    for i, v in arr
        out .= (i > 1 ? sep : "") v
    return out
}

; ============================================================
; MAIN GUI
; ============================================================

ShowAssembler(*) {
    selected := Map()  ; code → true
    
    ; ── Build main window ───────────────────────────────────
    main := Gui("+Resize", "⚙ Prompt Assembler — POF 2828")
    main.SetFont("s10", "Segoe UI")
    main.BackColor := "1a1a2e"
    
    ; Header
    main.SetFont("s13 bold", "Segoe UI")
    main.AddText("cWhite x10 y10 w700", "PROMPT ASSEMBLER")
    main.SetFont("s9", "Segoe UI")
    main.AddText("c808080 x10 y35 w700", "Pick blocks layer by layer. Conflicts flagged. Assemble and copy.")
    
    ; ── Layer 0 ─────────────────────────────────────────────
    main.SetFont("s10 bold", "Segoe UI")
    main.AddText("cFFD700 x10 y65 w700", "LAYER 0 — INTERPRETIVE POSTURE  (optional — use for external content)")
    main.SetFont("s9", "Segoe UI")
    
    cb_P0 := main.AddCheckBox("c90EE90 x10 y85 w700 vP0", "P0 — INTERPRETIVE POSTURE  |  Sets lens before domain blocks. Use: YouTube, Bible, web content.")
    
    ; ── Layer 1 ─────────────────────────────────────────────
    main.SetFont("s10 bold", "Segoe UI")
    main.AddText("cFFD700 x10 y115 w700", "LAYER 1 — PREAMBLE  (pick exactly one)")
    main.SetFont("s9", "Segoe UI")
    
    cb_P1 := main.AddRadio("c90EE90 x10 y135 w700 Group vPreamble", "P1 — CPMR  |  Interrogate → Workflow → Execute. Use: unclear scope, staged work.")
    cb_P2 := main.AddRadio("c90EE90 x10 y155 w700", "P2 — THINKING CONTRACT  |  10-point rigor, falsifiability required. Use: destroy-testing, proofs.")
    cb_P3 := main.AddRadio("c90EE90 x10 y175 w700", "P3 — EVALUATOR  |  Dual technical + coherence. Use: paper evaluation, scoring.")
    cb_P3.Value := 1  ; default
    
    ; ── Layer 2 ─────────────────────────────────────────────
    main.SetFont("s10 bold", "Segoe UI")
    main.AddText("cFFD700 x10 y205 w700", "LAYER 2 — DOMAIN  (pick one or more — watch conflicts)")
    main.SetFont("s9", "Segoe UI")
    
    cb_D0 := main.AddCheckBox("cADD8E6 x10 y225 w700 vD0", "D0 — COMPRESSED AXIOMS (~400 tok)  |  7 generators. API/pipeline only. ⚠ NOT with D2.")
    cb_D1 := main.AddCheckBox("cADD8E6 x10 y245 w700 vD1", "D1 — TEN LAWS TAGGER  |  Tag claims vs L01-L10. Standard Theophysics paper.")
    cb_D2 := main.AddCheckBox("cADD8E6 x10 y265 w700 vD2", "D2 — AXIOM MAPPER (198)  |  Full chain mapping. Heavy — single deep paper. ⚠ NOT with D0.")
    cb_D3 := main.AddCheckBox("cADD8E6 x10 y285 w700 vD3", "D3 — DIRECTION MARKER  |  P→S / S→P / P↔S coding. Standard cross-domain.")
    cb_D4 := main.AddCheckBox("cADD8E6 x10 y305 w700 vD4", "D4 — SIX DOMAIN GRID  |  H/P/S/T/Synthesis/Agency scoring. Broad coverage.")
    cb_D5 := main.AddCheckBox("cADD8E6 x10 y325 w700 vD5", "D5 — FRUITS PRIMITIVES  |  12 moral invariants. Theological / ethical papers.")
    cb_D6 := main.AddCheckBox("cADD8E6 x10 y345 w700 vD6", "D6 — INDIGENOUS AXIOM EXTRACTOR  |  Content's OWN bedrock. Run FIRST on external. D1/D2 after.")
    
    ; ── Layer 3 ─────────────────────────────────────────────
    main.SetFont("s10 bold", "Segoe UI")
    main.AddText("cFFD700 x10 y375 w700", "LAYER 3 — OUTPUT  (pick exactly one)")
    main.SetFont("s9", "Segoe UI")
    
    cb_O1 := main.AddRadio("cFFA07A x10 y395 w700 Group vOutput", "O1 — SEMANTIC JSON → Obsidian  |  Machine-readable. Pipeline / batch processing.")
    cb_O2 := main.AddRadio("cFFA07A x10 y415 w700", "O2 — SCORECARD  |  Section scoring tables. Human review of single paper.")
    cb_O3 := main.AddRadio("cFFA07A x10 y435 w700", "O3 — KILL CONDITIONS  |  Falsification + cascade. Pairs with S1 Adversarial.")
    cb_O4 := main.AddRadio("cFFA07A x10 y455 w700", "O4 — GAP REPORT  |  Missing axioms, severity-ranked. Pairs with S2 Constructive.")
    cb_O5 := main.AddRadio("cFFA07A x10 y475 w700", "O5 — PAPER FINGERPRINT (5 lines)  |  Fastest. Triage mode. Pairs with S3 Compression.")
    cb_O5.Value := 1  ; default
    
    ; ── Layer 4 ─────────────────────────────────────────────
    main.SetFont("s10 bold", "Segoe UI")
    main.AddText("cFFD700 x10 y505 w700", "LAYER 4 — STYLE  (optional — pick zero or one)")
    main.SetFont("s9", "Segoe UI")
    
    cb_S0 := main.AddRadio("cDDA0DD x10 y525 w700 Group vStyle", "None (no style modifier)")
    cb_S1 := main.AddRadio("cDDA0DD x10 y545 w700", "S1 — ADVERSARIAL  |  Attack everything. Find weakest link. ⚠ NOT with S2 or S4.")
    cb_S2 := main.AddRadio("cDDA0DD x10 y565 w700", "S2 — CONSTRUCTIVE  |  Fix everything. Suggest improvements. ⚠ NOT with S1.")
    cb_S3 := main.AddRadio("cDDA0DD x10 y585 w700", "S3 — COMPRESSION  |  No prose, data only. Pipeline. ⚠ NOT with S4.")
    cb_S4 := main.AddRadio("cDDA0DD x10 y605 w700", "S4 — NARRATIVE  |  Plain language, non-specialist reader. ⚠ NOT with S1 or S3.")
    cb_S0.Value := 1  ; default
    
    ; ── Presets ─────────────────────────────────────────────
    main.SetFont("s10 bold", "Segoe UI")
    main.AddText("cFFD700 x10 y635 w120", "PRESETS:")
    main.SetFont("s9", "Segoe UI")
    
    presetList := []
    for name, _ in PRESETS
        presetList.Push(name)
    
    ddl := main.AddDropDownList("x135 y632 w300 vPresetChoice", presetList)
    
    btnLoadPreset := main.AddButton("x445 y630 w120", "Load Preset")
    btnLoadPreset.OnEvent("Click", LoadPreset.Bind(main, ddl,
        cb_P0, cb_P1, cb_P2, cb_P3,
        cb_D0, cb_D1, cb_D2, cb_D3, cb_D4, cb_D5, cb_D6,
        cb_O1, cb_O2, cb_O3, cb_O4, cb_O5,
        cb_S0, cb_S1, cb_S2, cb_S3, cb_S4))
    
    ; ── Conflict display ────────────────────────────────────
    conflictText := main.AddText("cFF6B6B x10 y665 w700 h40 vConflictDisplay", "")
    
    ; ── Action buttons ──────────────────────────────────────
    btnAssemble := main.AddButton("x10 y715 w150 h35", "🔧 ASSEMBLE + COPY")
    btnSave     := main.AddButton("x170 y715 w150 h35", "💾 SAVE ASSEMBLY")
    btnPreview  := main.AddButton("x330 y715 w150 h35", "👁 PREVIEW NAMES")
    btnClose    := main.AddButton("x490 y715 w100 h35", "Close")
    
    btnAssemble.OnEvent("Click", DoAssemble.Bind(main,
        cb_P0, cb_P1, cb_P2, cb_P3,
        cb_D0, cb_D1, cb_D2, cb_D3, cb_D4, cb_D5, cb_D6,
        cb_O1, cb_O2, cb_O3, cb_O4, cb_O5,
        cb_S0, cb_S1, cb_S2, cb_S3, cb_S4,
        conflictText, false))
    
    btnSave.OnEvent("Click", DoAssemble.Bind(main,
        cb_P0, cb_P1, cb_P2, cb_P3,
        cb_D0, cb_D1, cb_D2, cb_D3, cb_D4, cb_D5, cb_D6,
        cb_O1, cb_O2, cb_O3, cb_O4, cb_O5,
        cb_S0, cb_S1, cb_S2, cb_S3, cb_S4,
        conflictText, true))
    
    btnPreview.OnEvent("Click", DoPreview.Bind(main,
        cb_P0, cb_P1, cb_P2, cb_P3,
        cb_D0, cb_D1, cb_D2, cb_D3, cb_D4, cb_D5, cb_D6,
        cb_O1, cb_O2, cb_O3, cb_O4, cb_O5,
        cb_S0, cb_S1, cb_S2, cb_S3, cb_S4,
        conflictText))
    
    btnClose.OnEvent("Click", (*) => main.Destroy())
    
    main.Show("w730 h765")
}

; ── Collect selected codes from GUI ─────────────────────────
CollectSelected(cb_P0, cb_P1, cb_P2, cb_P3,
                cb_D0, cb_D1, cb_D2, cb_D3, cb_D4, cb_D5, cb_D6,
                cb_O1, cb_O2, cb_O3, cb_O4, cb_O5,
                cb_S0, cb_S1, cb_S2, cb_S3, cb_S4) {
    selected := Map()
    if cb_P0.Value  selected["P0"] := true
    if cb_P1.Value  selected["P1"] := true
    if cb_P2.Value  selected["P2"] := true
    if cb_P3.Value  selected["P3"] := true
    if cb_D0.Value  selected["D0"] := true
    if cb_D1.Value  selected["D1"] := true
    if cb_D2.Value  selected["D2"] := true
    if cb_D3.Value  selected["D3"] := true
    if cb_D4.Value  selected["D4"] := true
    if cb_D5.Value  selected["D5"] := true
    if cb_D6.Value  selected["D6"] := true
    if cb_O1.Value  selected["O1"] := true
    if cb_O2.Value  selected["O2"] := true
    if cb_O3.Value  selected["O3"] := true
    if cb_O4.Value  selected["O4"] := true
    if cb_O5.Value  selected["O5"] := true
    if cb_S1.Value  selected["S1"] := true
    if cb_S2.Value  selected["S2"] := true
    if cb_S3.Value  selected["S3"] := true
    if cb_S4.Value  selected["S4"] := true
    return selected
}

; ── Preview selected block names ────────────────────────────
DoPreview(main, cb_P0, cb_P1, cb_P2, cb_P3,
          cb_D0, cb_D1, cb_D2, cb_D3, cb_D4, cb_D5, cb_D6,
          cb_O1, cb_O2, cb_O3, cb_O4, cb_O5,
          cb_S0, cb_S1, cb_S2, cb_S3, cb_S4,
          conflictText, *) {
    
    selected := CollectSelected(cb_P0, cb_P1, cb_P2, cb_P3,
        cb_D0, cb_D1, cb_D2, cb_D3, cb_D4, cb_D5, cb_D6,
        cb_O1, cb_O2, cb_O3, cb_O4, cb_O5,
        cb_S0, cb_S1, cb_S2, cb_S3, cb_S4)
    
    warn := CheckConflicts(selected)
    conflictText.Text := warn ? warn : ""
    
    ; Build preview string
    order := ["P0","P1","P2","P3","D0","D1","D2","D3","D4","D5","D6",
              "O1","O2","O3","O4","O5","S1","S2","S3","S4"]
    preview := "ASSEMBLY PREVIEW:`n`n"
    for code in order {
        if selected.Has(code) {
            desc := BLOCKS.Has(code) ? BLOCKS[code] : code
            firstLine := StrSplit(desc, "`n")[1]
            preview .= "  [" code "] " firstLine "`n"
        }
    }
    
    if warn
        preview .= "`n⚠ CONFLICTS DETECTED — fix before assembling`n" warn
    
    MsgBox(preview, "Assembly Preview — POF 2828", "OK")
}

; ── Assemble + copy (or save) ────────────────────────────────
DoAssemble(main, cb_P0, cb_P1, cb_P2, cb_P3,
           cb_D0, cb_D1, cb_D2, cb_D3, cb_D4, cb_D5, cb_D6,
           cb_O1, cb_O2, cb_O3, cb_O4, cb_O5,
           cb_S0, cb_S1, cb_S2, cb_S3, cb_S4,
           conflictText, doSave, *) {
    
    selected := CollectSelected(cb_P0, cb_P1, cb_P2, cb_P3,
        cb_D0, cb_D1, cb_D2, cb_D3, cb_D4, cb_D5, cb_D6,
        cb_O1, cb_O2, cb_O3, cb_O4, cb_O5,
        cb_S0, cb_S1, cb_S2, cb_S3, cb_S4)
    
    warn := CheckConflicts(selected)
    conflictText.Text := warn ? warn : ""
    
    if warn {
        MsgBox("Fix conflicts before assembling:`n`n" warn, "Conflict — Aborted", "OK Icon!")
        return
    }
    
    if selected.Count = 0 {
        MsgBox("No blocks selected.", "Nothing to assemble", "OK")
        return
    }
    
    assembled := AssemblePrompt(selected)
    A_Clipboard := assembled
    
    if doSave {
        ; Ask for assembly name
        name := InputBox("Name this assembly (for saving):", "Save Assembly", "w400 h120").Value
        if name = ""
            name := "unnamed_" FormatTime(, "HHmmss")
        path := SaveAssembly(name, selected, assembled)
        MsgBox("Saved to:`n" path "`n`nAlso copied to clipboard.", "Saved ✓", "OK")
    } else {
        ; Count blocks
        count := selected.Count
        MsgBox(count " blocks assembled and copied to clipboard.`n`nPaste into any AI chat.", "Copied ✓", "OK")
    }
}

; ── Load a preset into checkboxes ────────────────────────────
LoadPreset(main, ddl, cb_P0, cb_P1, cb_P2, cb_P3,
           cb_D0, cb_D1, cb_D2, cb_D3, cb_D4, cb_D5, cb_D6,
           cb_O1, cb_O2, cb_O3, cb_O4, cb_O5,
           cb_S0, cb_S1, cb_S2, cb_S3, cb_S4, *) {
    
    choice := ddl.Text
    if !PRESETS.Has(choice)
        return
    
    codes := PRESETS[choice]
    
    ; Reset all
    for cb in [cb_P0, cb_D0, cb_D1, cb_D2, cb_D3, cb_D4, cb_D5, cb_D6]
        cb.Value := 0
    cb_P3.Value := 1  ; default preamble
    cb_O5.Value := 1  ; default output
    cb_S0.Value := 1  ; default style (none)
    
    cbMap := Map(
        "P0", cb_P0, "P1", cb_P1, "P2", cb_P2, "P3", cb_P3,
        "D0", cb_D0, "D1", cb_D1, "D2", cb_D2, "D3", cb_D3,
        "D4", cb_D4, "D5", cb_D5, "D6", cb_D6,
        "O1", cb_O1, "O2", cb_O2, "O3", cb_O3, "O4", cb_O4, "O5", cb_O5,
        "S1", cb_S1, "S2", cb_S2, "S3", cb_S3, "S4", cb_S4
    )
    
    for code in codes {
        if cbMap.Has(code)
            cbMap[code].Value := 1
    }
    
    MsgBox("Preset loaded: " choice, "Preset ✓", "OK T2")
}

; ============================================================
; HOTKEY
; ============================================================

#p::ShowAssembler()   ; Win+P to open
