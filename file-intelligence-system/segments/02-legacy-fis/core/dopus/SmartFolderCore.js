// SmartFolderCore.js — Directory Opus Script Add-in
// File History Tracker + Folder Content Preview
// (c) 2026 David Lowe / Theophysics Research Initiative
//
// INSTALL: Drag this file into DOpus > Settings > Preferences > Toolbars > Scripts
//          Or: Settings > Script Add-ins > drag file onto list
//
// COLUMNS ADDED:
//   "SF: History"    — Last recorded action + timestamp for files
//   "SF: Contents"   — File/folder count + top filenames for folders
//   "SF: Age"        — How old the file is in human-readable form
//   "SF: Origin"     — Where the file came from (if tracked)

var STREAM_NAME = "smartfolder";

// ============================================================
// INIT — Register everything
// ============================================================

function OnInit(initData) {
    initData.name = "SmartFolder Core";
    initData.version = "1.0";
    initData.desc = "File history tracking, folder content preview, and smart metadata columns.";
    initData.copyright = "(c) 2026 David Lowe";
    initData.default_enable = true;
    initData.min_version = "13.0";

    // --- Config ---
    initData.config.USE_ADS          = true;
    initData.config.USE_SIDECAR      = false;
    initData.config.SIDECAR_EXT      = ".fmeta";
    initData.config.MAX_PREVIEW      = 15;
    initData.config.TRACK_COPIES     = true;
    initData.config.TRACK_MOVES      = true;
    initData.config.TRACK_RENAMES    = true;
    initData.config.TRACK_DELETES    = true;
    initData.config.SHOW_EXTENSIONS  = true;

    initData.config_desc = DOpus.Create.Map();
    initData.config_desc("USE_ADS")         = "Store history in NTFS Alternate Data Streams (invisible metadata)";
    initData.config_desc("USE_SIDECAR")     = "Store history in .fmeta sidecar files (portable but visible)";
    initData.config_desc("SIDECAR_EXT")     = "Extension for sidecar files";
    initData.config_desc("MAX_PREVIEW")     = "Max files to list in folder content preview";
    initData.config_desc("TRACK_COPIES")    = "Track file copy operations";
    initData.config_desc("TRACK_MOVES")     = "Track file move operations";
    initData.config_desc("TRACK_RENAMES")   = "Track file rename operations";
    initData.config_desc("TRACK_DELETES")   = "Track file delete operations";
    initData.config_desc("SHOW_EXTENSIONS") = "Show file extensions in folder preview";

    // --- Columns ---
    var col;

    col = initData.AddColumn();
    col.name        = "SFHistory";
    col.method      = "OnColHistory";
    col.label       = "SF: History";
    col.justify     = "left";
    col.autogroup   = true;
    col.autorefresh = true;
    col.type        = "string";

    col = initData.AddColumn();
    col.name        = "SFContents";
    col.method      = "OnColContents";
    col.label       = "SF: Contents";
    col.justify     = "left";
    col.autogroup   = false;
    col.autorefresh = true;
    col.type        = "string";

    col = initData.AddColumn();
    col.name        = "SFAge";
    col.method      = "OnColAge";
    col.label       = "SF: Age";
    col.justify     = "right";
    col.autogroup   = true;
    col.autorefresh = true;
    col.type        = "string";

    col = initData.AddColumn();
    col.name        = "SFOrigin";
    col.method      = "OnColOrigin";
    col.label       = "SF: Origin";
    col.justify     = "left";
    col.autogroup   = true;
    col.autorefresh = true;
    col.type        = "string";

    // --- Commands ---
    var cmd;

    cmd = initData.AddCommand();
    cmd.name   = "SmartFolderShowHistory";
    cmd.method = "OnCmdShowHistory";
    cmd.desc   = "Show full history for selected file(s)";
    cmd.label  = "Show File History";

    cmd = initData.AddCommand();
    cmd.name   = "SmartFolderClearHistory";
    cmd.method = "OnCmdClearHistory";
    cmd.desc   = "Clear history for selected file(s)";
    cmd.label  = "Clear File History";

    cmd = initData.AddCommand();
    cmd.name   = "SmartFolderSnapshot";
    cmd.method = "OnCmdSnapshot";
    cmd.desc   = "Snapshot current folder state to history";
    cmd.label  = "Snapshot Folder";
}

// ============================================================
// HISTORY STORAGE — ADS + Sidecar
// ============================================================

function _shell() { return new ActiveXObject("WScript.Shell"); }
function _fso() { return new ActiveXObject("Scripting.FileSystemObject"); }

function ReadHistoryADS(filePath) {
    try {
        var shell = _shell();
        var cmd = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "' +
            "Get-Content -Path '" + filePath.replace(/'/g, "''") +
            "' -Stream '" + STREAM_NAME + "' -ErrorAction SilentlyContinue" + '"';
        var exec = shell.Exec(cmd);
        var out = "";
        while (!exec.StdOut.AtEndOfStream) out += exec.StdOut.ReadLine() + "\n";
        out = out.replace(/^\s+|\s+$/g, "");
        if (!out || out.length < 2) return null;
        return JSON.parse(out);
    } catch (e) { return null; }
}

function WriteHistoryADS(filePath, histObj) {
    try {
        var json = JSON.stringify(histObj);
        var escaped = json.replace(/'/g, "''").replace(/"/g, '\\"');
        var shell = _shell();
        var cmd = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "' +
            "Set-Content -Path '" + filePath.replace(/'/g, "''") +
            "' -Stream '" + STREAM_NAME + "' -Value '" + escaped + "'" + '"';
        shell.Run(cmd, 0, true);
    } catch (e) {
        DOpus.Output("SmartFolder: ADS write error: " + e.message);
    }
}

function ReadHistorySidecar(filePath, ext) {
    try {
        var fso = _fso();
        var metaPath = filePath + ext;
        if (!fso.FileExists(metaPath)) return null;
        var f = fso.OpenTextFile(metaPath, 1, false, -1);
        var json = f.ReadAll();
        f.Close();
        return JSON.parse(json);
    } catch (e) { return null; }
}

function WriteHistorySidecar(filePath, ext, histObj) {
    try {
        var fso = _fso();
        var metaPath = filePath + ext;
        var f = fso.CreateTextFile(metaPath, true, true);
        f.Write(JSON.stringify(histObj, null, 2));
        f.Close();
        try { var file = fso.GetFile(metaPath); file.Attributes = file.Attributes | 2; } catch (e2) {}
    } catch (e) {
        DOpus.Output("SmartFolder: Sidecar write error: " + e.message);
    }
}

function ReadHistory(filePath) {
    var hist = null;
    if (Script.config.USE_ADS) hist = ReadHistoryADS(filePath);
    if (!hist && Script.config.USE_SIDECAR) hist = ReadHistorySidecar(filePath, Script.config.SIDECAR_EXT);
    return hist || { events: [], origin: "" };
}

function WriteHistory(filePath, histObj) {
    if (Script.config.USE_ADS) WriteHistoryADS(filePath, histObj);
    if (Script.config.USE_SIDECAR) WriteHistorySidecar(filePath, Script.config.SIDECAR_EXT, histObj);
}

function AppendEvent(filePath, action, details) {
    var hist = ReadHistory(filePath);
    hist.events.push({
        action: action,
        timestamp: new Date().toISOString(),
        details: details || ""
    });
    if (hist.events.length > 100) hist.events = hist.events.slice(hist.events.length - 100);
    WriteHistory(filePath, hist);
}

// ============================================================
// COLUMN HANDLERS
// ============================================================

function OnColHistory(scriptColData) {
    var item = scriptColData.item;
    if (item.is_dir) { scriptColData.value = ""; return; }
    var hist = ReadHistory(String(item.realpath));
    if (!hist.events || hist.events.length === 0) {
        scriptColData.value = "(no history)";
        scriptColData.sort = 0;
        return;
    }
    var last = hist.events[hist.events.length - 1];
    var ts = last.timestamp.substring(0, 16).replace("T", " ");
    scriptColData.value = last.action + " — " + ts;
    if (last.details) scriptColData.value += " [" + last.details + "]";
    scriptColData.sort = hist.events.length;
}

function OnColContents(scriptColData) {
    var item = scriptColData.item;
    if (!item.is_dir) { scriptColData.value = ""; return; }
    try {
        var folderEnum = DOpus.FSUtil.ReadDir(item.realpath, false);
        var files = 0, dirs = 0, names = [];
        var maxPreview = Script.config.MAX_PREVIEW || 15;
        var showExt = Script.config.SHOW_EXTENSIONS;

        while (!folderEnum.complete) {
            var entry = folderEnum.Next();
            if (entry.is_dir) {
                dirs++;
                if (names.length < maxPreview) names.push("[" + entry.name + "]");
            } else {
                files++;
                if (names.length < maxPreview) names.push(showExt ? entry.name : entry.name_stem);
            }
        }

        var summary = "";
        if (dirs > 0) summary += dirs + " folder" + (dirs > 1 ? "s" : "");
        if (dirs > 0 && files > 0) summary += ", ";
        if (files > 0) summary += files + " file" + (files > 1 ? "s" : "");
        if (dirs === 0 && files === 0) summary = "(empty)";

        if (names.length > 0) summary += "\n" + names.join("\n");
        var total = dirs + files;
        if (total > maxPreview) summary += "\n...+" + (total - maxPreview) + " more";
        scriptColData.value = summary;
        scriptColData.sort  = total;
    } catch (e) { scriptColData.value = "(error)"; }
}

function OnColAge(scriptColData) {
    var item = scriptColData.item;
    if (item.is_dir) { scriptColData.value = ""; return; }
    var now = new Date();
    var mod = new Date(item.modify);
    var diffMin = Math.floor((now - mod) / 60000);
    if (diffMin < 1)           scriptColData.value = "just now";
    else if (diffMin < 60)     scriptColData.value = diffMin + "m";
    else if (diffMin < 1440)   scriptColData.value = Math.floor(diffMin / 60) + "h";
    else if (diffMin < 43200)  scriptColData.value = Math.floor(diffMin / 1440) + "d";
    else if (diffMin < 525600) scriptColData.value = Math.floor(diffMin / 43200) + "mo";
    else                       scriptColData.value = Math.floor(diffMin / 525600) + "y";
    scriptColData.sort = diffMin;
}

function OnColOrigin(scriptColData) {
    var item = scriptColData.item;
    if (item.is_dir) { scriptColData.value = ""; return; }
    var hist = ReadHistory(String(item.realpath));
    scriptColData.value = hist.origin || "";
}

// ============================================================
// FILE OPERATION TRACKING
// ============================================================

function OnFileOperationComplete(completeData) {
    if (completeData.query) return;
    var action = String(completeData.action);
    if (action === "copy" && !Script.config.TRACK_COPIES) return;
    if (action === "move" && !Script.config.TRACK_MOVES) return;
    if (action === "rename" && !Script.config.TRACK_RENAMES) return;
    if (action === "delete" && !Script.config.TRACK_DELETES) return;

    try {
        if (completeData.dest) {
            var enumFiles = new Enumerator(completeData.dest);
            while (!enumFiles.atEnd()) {
                var destItem = enumFiles.item();
                var fullPath = String(destItem.realpath);
                if (action === "copy") {
                    var hist = ReadHistory(fullPath);
                    hist.origin = String(completeData.source || "unknown");
                    hist.events.push({
                        action: "copied",
                        timestamp: new Date().toISOString(),
                        details: "from " + String(completeData.source || "?")
                    });
                    WriteHistory(fullPath, hist);
                } else if (action === "move") {
                    AppendEvent(fullPath, "moved", "from " + String(completeData.source || "?"));
                } else if (action === "rename") {
                    AppendEvent(fullPath, "renamed", "");
                }
                enumFiles.moveNext();
            }
        }
    } catch (e) {
        DOpus.Output("SmartFolder: Track error: " + e.message);
    }
}

// ============================================================
// CUSTOM COMMANDS
// ============================================================

function OnCmdShowHistory(scriptCmdData) {
    var tab = scriptCmdData.func.sourcetab;
    var selected = tab.selected;
    if (selected.count === 0) {
        var dlg = scriptCmdData.func.Dlg;
        dlg.message = "No files selected.";
        dlg.title = "SmartFolder";
        dlg.buttons = "OK";
        dlg.Show();
        return;
    }
    var enumSel = new Enumerator(selected);
    var report = "";
    while (!enumSel.atEnd()) {
        var item = enumSel.item();
        var hist = ReadHistory(String(item.realpath));
        report += "=== " + item.name + " ===\n";
        if (hist.origin) report += "Origin: " + hist.origin + "\n";
        if (hist.events.length === 0) {
            report += "(no recorded history)\n";
        } else {
            for (var i = 0; i < hist.events.length; i++) {
                var ev = hist.events[i];
                var ts = ev.timestamp.substring(0, 16).replace("T", " ");
                report += "  " + ts + "  " + ev.action;
                if (ev.details) report += "  " + ev.details;
                report += "\n";
            }
        }
        report += "\n";
        enumSel.moveNext();
    }
    var dlg = scriptCmdData.func.Dlg;
    dlg.message = report;
    dlg.title = "SmartFolder — File History";
    dlg.buttons = "OK";
    dlg.Show();
}

function OnCmdClearHistory(scriptCmdData) {
    var tab = scriptCmdData.func.sourcetab;
    var selected = tab.selected;
    if (selected.count === 0) return;
    var dlg = scriptCmdData.func.Dlg;
    dlg.message = "Clear history for " + selected.count + " file(s)?";
    dlg.title = "SmartFolder";
    dlg.buttons = "Yes|No";
    if (dlg.Show() !== 1) return;
    var enumSel = new Enumerator(selected);
    while (!enumSel.atEnd()) {
        var item = enumSel.item();
        WriteHistory(String(item.realpath), { events: [], origin: "" });
        enumSel.moveNext();
    }
}

function OnCmdSnapshot(scriptCmdData) {
    var tab = scriptCmdData.func.sourcetab;
    var path = String(tab.path);
    var folderEnum = DOpus.FSUtil.ReadDir(path, false);
    var count = 0;
    while (!folderEnum.complete) {
        var entry = folderEnum.Next();
        if (!entry.is_dir) {
            AppendEvent(String(entry.realpath), "snapshot", "folder state captured");
            count++;
        }
    }
    DOpus.Output("SmartFolder: Snapshot captured for " + count + " files in " + path);
}
