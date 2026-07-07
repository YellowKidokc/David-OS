"""FMeta — persistent per-file metadata sidecar system.

Every classified file gets a .fmeta companion that tracks:
  - Nabla semantic address (D/N/V/A/U/R :: VECTOR :: HASH)
  - 10-variable vector and DQM tier
  - Full rename/move/delete history
  - Classification confidence and model provenance

The .fmeta file is designed to be immortal:
  - Set hidden+system attributes on Windows (casual deletion resistant)
  - Graveyard evacuation: if parent file vanishes, .fmeta is rescued
  - Plain text, opens in any editor, human-readable

Extension: .fmeta
Format: key-value header + chronological history log
"""

import ctypes
import json
import os
import platform
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fis.log import get_logger

log = get_logger("fmeta")

# Graveyard location — all orphaned .fmeta files go here
GRAVEYARD_DIR = Path("D:/FIS/graveyard")

# Windows file attributes
FILE_ATTRIBUTE_HIDDEN = 0x02
FILE_ATTRIBUTE_SYSTEM = 0x04


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _set_hidden_system(path: Path):
    """Set hidden + system attributes on Windows. No-op on other platforms."""
    if platform.system() != "Windows":
        return
    try:
        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
        if attrs == -1:
            attrs = 0
        new_attrs = attrs | FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM
        ctypes.windll.kernel32.SetFileAttributesW(str(path), new_attrs)
        log.debug("Set hidden+system on %s", path)
    except Exception as e:
        log.warning("Could not set attributes on %s: %s", path, e)


def fmeta_path_for(file_path: str | Path) -> Path:
    """Get the .fmeta sidecar path for a given file.

    report.pdf -> report.pdf.fmeta
    """
    return Path(str(file_path) + ".fmeta")


def create_fmeta(
    file_path: str | Path,
    *,
    nabla_address: str = "",
    vector: list[float] | None = None,
    vector_hash: str = "",
    dqm_tier: str = "",
    dqm_confidence: int = 0,
    dqm_flags: list[str] | None = None,
    domain: str = "",
    subjects: list[str] | None = None,
    slug: str = "",
    fis_confidence: float = 0.0,
    sequence_id: int = 0,
    proposed_name: str = "",
    classification_source: str = "fis_pipeline",
    extra: dict | None = None,
) -> Path:
    """Create a .fmeta sidecar for a file.

    If one already exists, appends a RECLASSIFIED event to history.
    """
    file_path = Path(file_path)
    meta_path = fmeta_path_for(file_path)
    now = _now()

    var_names = ["G", "M", "E", "S", "T", "K", "R", "Q", "F", "C"]
    vec = vector or [0.0] * 10
    vector_str = "".join(f"{var_names[i]}{int(vec[i])}" for i in range(10))

    subjects = subjects or []
    dqm_flags = dqm_flags or []

    lines = []
    lines.append(f"FMETA_VERSION: 1")
    lines.append(f"ORIGINAL_NAME: {file_path.name}")
    lines.append(f"ORIGINAL_PATH: {file_path.resolve()}")
    lines.append(f"CREATED: {now}")
    lines.append(f"")
    lines.append(f"# --- NABLA SEMANTIC ADDRESS ---")
    lines.append(f"NABLA: {nabla_address}")
    lines.append(f"VECTOR: {vector_str}")
    lines.append(f"HASH: {vector_hash}")
    lines.append(f"DQM: {dqm_tier}({dqm_confidence}){('[' + ','.join(dqm_flags) + ']') if dqm_flags else ''}")
    lines.append(f"")
    lines.append(f"# --- FIS CLASSIFICATION ---")
    lines.append(f"DOMAIN: {domain}")
    lines.append(f"SUBJECTS: {','.join(subjects)}")
    lines.append(f"SLUG: {slug}")
    lines.append(f"FIS_CONFIDENCE: {fis_confidence:.1f}")
    lines.append(f"SEQUENCE_ID: {sequence_id:06d}")
    lines.append(f"PROPOSED_NAME: {proposed_name}")
    lines.append(f"SOURCE: {classification_source}")

    if extra:
        lines.append(f"")
        lines.append(f"# --- EXTRA ---")
        for k, v in extra.items():
            lines.append(f"{k.upper()}: {v}")

    lines.append(f"")
    lines.append(f"# --- HISTORY ---")
    lines.append(f"# Each line: ISO-timestamp ACTION details")

    if meta_path.exists():
        # Preserve existing history, update header
        existing = meta_path.read_text(encoding="utf-8")
        history_marker = "# --- HISTORY ---"
        if history_marker in existing:
            history_section = existing[existing.index(history_marker):]
            # Append reclassification event
            lines_text = "\n".join(lines[:lines.index("# --- HISTORY ---")])
            history_section += f"\n{now} RECLASSIFIED domain={domain} conf={fis_confidence:.1f}"
            content = lines_text + "\n" + history_section
        else:
            content = "\n".join(lines) + f"\n{now} CLASSIFIED domain={domain} subjects={','.join(subjects)} conf={fis_confidence:.1f}"
    else:
        content = "\n".join(lines) + f"\n{now} CLASSIFIED domain={domain} subjects={','.join(subjects)} conf={fis_confidence:.1f}"

    meta_path.write_text(content, encoding="utf-8")
    _set_hidden_system(meta_path)
    log.info("Created .fmeta for %s", file_path.name)
    return meta_path


def append_history(file_path: str | Path, action: str, details: str = ""):
    """Append a history event to a file's .fmeta sidecar.

    Actions: MOVED, RENAMED, DELETED, APPROVED, REJECTED, RECLASSIFIED,
             EVACUATED, RESTORED, TAGGED, OPENED, ACCESSED
    """
    meta_path = fmeta_path_for(file_path)
    if not meta_path.exists():
        log.warning("No .fmeta for %s — creating stub", file_path)
        create_fmeta(file_path, classification_source="stub")

    now = _now()
    line = f"{now} {action} {details}".rstrip()

    with open(meta_path, "a", encoding="utf-8") as f:
        f.write(f"\n{line}")

    log.debug("Appended %s to %s", action, meta_path.name)


def evacuate_to_graveyard(fmeta_path: str | Path) -> Optional[Path]:
    """Move an orphaned .fmeta to the graveyard.

    Called when the parent file has been deleted but the .fmeta survives.
    Appends EVACUATED event before moving.
    """
    fmeta_path = Path(fmeta_path)
    if not fmeta_path.exists():
        return None

    GRAVEYARD_DIR.mkdir(parents=True, exist_ok=True)

    # Append evacuation notice
    now = _now()
    original_location = str(fmeta_path.resolve())
    with open(fmeta_path, "a", encoding="utf-8") as f:
        f.write(f"\n{now} PARENT_DELETED original_location={original_location}")
        f.write(f"\n{now} EVACUATED destination={GRAVEYARD_DIR}")

    # Move to graveyard with timestamp prefix to avoid collisions
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest_name = f"{ts}_{fmeta_path.name}"
    dest = GRAVEYARD_DIR / dest_name

    shutil.move(str(fmeta_path), str(dest))
    log.info("Evacuated %s -> %s", fmeta_path.name, dest)
    return dest


def move_fmeta_with_file(old_path: str | Path, new_path: str | Path):
    """When a file moves, move its .fmeta too and log the move."""
    old_meta = fmeta_path_for(old_path)
    new_meta = fmeta_path_for(new_path)

    if old_meta.exists():
        now = _now()
        with open(old_meta, "a", encoding="utf-8") as f:
            f.write(f"\n{now} MOVED {old_path} -> {new_path}")

        if old_meta != new_meta:
            shutil.move(str(old_meta), str(new_meta))
            _set_hidden_system(new_meta)
            log.info("Moved .fmeta: %s -> %s", old_meta.name, new_meta.name)


def rename_fmeta_with_file(old_path: str | Path, new_name: str):
    """When a file is renamed, rename its .fmeta and log it."""
    old_path = Path(old_path)
    new_path = old_path.parent / new_name
    old_meta = fmeta_path_for(old_path)
    new_meta = fmeta_path_for(new_path)

    if old_meta.exists():
        now = _now()
        with open(old_meta, "a", encoding="utf-8") as f:
            f.write(f"\n{now} RENAMED {old_path.name} -> {new_name}")

        if old_meta != new_meta:
            shutil.move(str(old_meta), str(new_meta))
            _set_hidden_system(new_meta)
            log.info("Renamed .fmeta: %s -> %s", old_meta.name, new_meta.name)


def read_fmeta(file_path: str | Path) -> dict:
    """Read and parse a .fmeta file into a dict.

    Returns: {header fields as key:value, history: [list of event lines]}
    """
    meta_path = fmeta_path_for(file_path)
    if not meta_path.exists():
        return {}

    content = meta_path.read_text(encoding="utf-8")
    result = {"history": []}
    in_history = False

    for line in content.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            if "HISTORY" in line:
                in_history = True
            continue

        if in_history:
            # History lines start with ISO timestamp
            if len(line) > 20 and line[4] == "-" and line[10] == "T":
                result["history"].append(line)
        else:
            if ":" in line:
                key, _, val = line.partition(":")
                result[key.strip()] = val.strip()

    return result


def scan_for_orphans(directory: str | Path):
    """Scan a directory for .fmeta files whose parent file is gone.

    Evacuates orphans to the graveyard.
    """
    directory = Path(directory)
    orphans = []

    for fmeta in directory.rglob("*.fmeta"):
        # Parent file is the fmeta path minus the .fmeta extension
        parent_file = Path(str(fmeta)[:-6])  # strip ".fmeta"
        if not parent_file.exists():
            log.info("Orphan found: %s (parent: %s)", fmeta.name, parent_file.name)
            dest = evacuate_to_graveyard(fmeta)
            if dest:
                orphans.append(str(dest))

    return orphans
