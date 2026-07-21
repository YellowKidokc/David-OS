"""File watcher — monitors folders and triggers the FIS pipeline.

Routes .md files with YAML frontmatter to the recon ingest pipeline.
All other files go through the standard NLP pipeline.
"""

import sys
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from fis.db.connection import get_config
from fis.log import get_logger
from fis.pipeline import FISPipeline
from fis.renamer import rename_file
from fis.fmeta import evacuate_to_graveyard, fmeta_path_for

log = get_logger("watcher")


class FISHandler(FileSystemEventHandler):
    """Handles file creation/modification events.

    Routes .md files with YAML frontmatter to recon ingest.
    All other files go through the standard pipeline.
    """

    def __init__(self, pipeline: FISPipeline, config):
        self.pipeline = pipeline
        self.debounce = int(config.get("watcher", "debounce_seconds", fallback="3"))
        self.ignore_ext = [
            ext.strip()
            for ext in config.get("watcher", "ignore_extensions", fallback="").split(",")
        ]
        self.recon_enabled = config.get("recon", "enabled", fallback="true").lower() == "true"
        self._pending = {}

    def on_deleted(self, event):
        """When a file is deleted, check if its .fmeta is now orphaned."""
        if event.is_directory:
            return
        path = Path(event.src_path)
        # Skip .fmeta files themselves being deleted
        if path.suffix.lower() == ".fmeta":
            return
        # Check if there's a .fmeta sidecar that's now orphaned
        fmeta = fmeta_path_for(event.src_path)
        if fmeta.exists():
            try:
                dest = evacuate_to_graveyard(fmeta)
                if dest:
                    log.info("EVACUATED %s -> graveyard (parent deleted)", fmeta.name)
            except Exception as e:
                log.warning("Could not evacuate %s: %s", fmeta.name, e)

    def on_moved(self, event):
        """When a file is moved/renamed, move its .fmeta AND learn from it."""
        if event.is_directory:
            return
        from fis.fmeta import move_fmeta_with_file
        try:
            move_fmeta_with_file(event.src_path, event.dest_path)
        except Exception as e:
            log.debug("fmeta move failed for %s: %s", event.src_path, e)

        # LEARN FROM MANUAL MOVES AND RENAMES
        # If David moves or renames a file himself (not through FIS),
        # that's a strong preference signal. Feed it to River.
        try:
            src = Path(event.src_path)
            dest = Path(event.dest_path)

            # Skip FIS's own renames (those go through /approve)
            # FIS renames have the coord_hash pattern: ABC1X_slug_XX.XX_000000.ext
            import re
            fis_pattern = re.compile(r'^[A-Z]{1,5}\d[DWFX]_')
            if fis_pattern.match(dest.name):
                return  # FIS did this rename, already learned via /approve

            # Skip .fmeta, .orgledger, system files
            if dest.suffix.lower() in {'.fmeta', '.orgledger', '.tmp', '.lock'}:
                return

            from fis.naming_learner import NamingLearner
            learner = NamingLearner()

            # Was this a RENAME (same folder) or a MOVE (different folder)?
            if src.parent == dest.parent:
                # RENAME — David chose this name. Very strong signal.
                features = learner.extract_features(
                    original_name=src.name,
                    extension=dest.suffix,
                    file_path=str(dest.resolve()),
                )
                learner.learn_approve(features, dest.name, original_name=src.name)
                log.info("LEARN_RENAME %s -> %s (manual rename = strong signal)",
                         src.name, dest.name)
            else:
                # MOVE — David chose this destination. Routing signal.
                features = learner.extract_features(
                    original_name=src.name,
                    extension=dest.suffix,
                    file_path=str(dest.resolve()),
                )
                # Learn with the destination folder as context
                learner.learn_approve(features, dest.name)
                log.info("LEARN_MOVE %s -> %s (manual move = routing signal)",
                         src.name, dest.parent.name)
        except Exception as e:
            log.debug("Learn from move failed: %s", e)

    def on_created(self, event):
        if event.is_directory:
            return
        self._handle(event.src_path)

    def on_modified(self, event):
        if event.is_directory:
            return
        self._handle(event.src_path)

    # Folders to never process (normalized lowercase for comparison)
    IGNORE_FOLDERS = {
        'node_modules', '.git', '__pycache__', '.venv', 'venv',
        '.wrangler', 'dist', 'build', '.next', '.nuxt',
        'target', 'bin', 'obj',  # Rust/C# build dirs
        '$recycle.bin', '$recycle',  # Windows Recycle Bin
        '_canonical_backups', '_rejected',  # Canonical gate control dirs
    }

    WEBSITE_NO_RENAME_ROOTS = (
        r"\\dlowenas\HPWorkstation\Desktop\Master HTMl\K-Production-Ready",
        r"\\dlowenas\HPWorkstation\Desktop\Master HTMl\_staging",
    )

    # Never process files inside FIS's own repo
    _SELF_DIR = str(Path(__file__).parent.parent.resolve()).lower()

    @classmethod
    def _is_website_watch_path(cls, path: Path) -> bool:
        path_text = str(path).replace("/", "\\").lower().rstrip("\\")
        for root in cls.WEBSITE_NO_RENAME_ROOTS:
            root_text = root.replace("/", "\\").lower().rstrip("\\")
            if path_text == root_text or path_text.startswith(root_text + "\\"):
                return True
        return False

    def _handle(self, file_path: str):
        path = Path(file_path)
        path_lower = str(path).lower()

        # RULE 1: Never touch our own repo
        if path_lower.startswith(self._SELF_DIR):
            return

        # RULE 2: Skip anything inside node_modules, .git, __pycache__, etc.
        parts_lower = [p.lower() for p in path.parts]
        if any(part in self.IGNORE_FOLDERS for part in parts_lower):
            return

        # RULE 3: Skip binary files that can't be text-extracted
        if path.suffix.lower() in {'.exe', '.dll', '.msi', '.so', '.dylib',
                                     '.pdb', '.obj', '.o', '.a', '.lib',
                                     '.whl', '.egg', '.zip', '.tar', '.gz',
                                     '.7z', '.rar', '.iso', '.img',
                                     '.ttf', '.otf', '.woff', '.woff2'}:
            return

        # RULE 4: Skip log/pid/lock files (feedback loop prevention)
        if path.suffix.lower() in {'.log', '.pid', '.lock', '.lck'}:
            return

        # Skip ignored extensions from config
        if path.suffix.lower() in self.ignore_ext:
            return

        # Skip hidden files, FIS metadata, and .fmeta sidecars
        if path.name.startswith(".") or path.name == ".fis_meta.json":
            return
        if path.suffix.lower() == ".fmeta":
            return

        # Skip files being written (debounce)
        import threading

        if file_path in self._pending:
            self._pending[file_path].cancel()

        timer = threading.Timer(self.debounce, self._process, [file_path])
        self._pending[file_path] = timer
        timer.start()

    def _process(self, file_path: str):
        self._pending.pop(file_path, None)
        try:
            # Route .md files with frontmatter to recon ingest
            path = Path(file_path)
            if (self.recon_enabled
                    and path.suffix.lower() == ".md"
                    and self._has_frontmatter(file_path)):
                from fis.recon.recon_ingest import ingest
                result = ingest(file_path)
            else:
                result = self.pipeline.process(file_path)

            if result.get("status") == "auto":
                if self._is_website_watch_path(path):
                    log.info("WEBSITE_QUEUE_NO_RENAME %s -> %s (confidence: %.0f)",
                             result['original_name'], result['proposed_name'],
                             result.get('confidence', 0))
                    return
                # Auto-rename high confidence files
                rename_file(
                    file_path,
                    result["proposed_name"],
                    result["file_id"],
                )
                log.info("AUTO %s -> %s", result['original_name'], result['proposed_name'])
            elif result.get("status") == "pending":
                log.info("QUEUE %s -> %s (confidence: %.0f)",
                         result['original_name'], result['proposed_name'], result['confidence'])
            elif result.get("status") == "kickout":
                log.info("KICKOUT %s (confidence: %.0f)",
                         result['original_name'], result.get('confidence', 0))
            elif result.get("status") == "duplicate":
                log.info("SKIP %s is duplicate of %s",
                         Path(file_path).name, result['existing_id'])
        except Exception as e:
            log.error("%s: %s", file_path, e)

    @staticmethod
    def _has_frontmatter(file_path: str) -> bool:
        """Quick check: does this file start with YAML frontmatter (---)."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                first_line = f.readline().strip()
                return first_line == "---"
        except (OSError, UnicodeDecodeError):
            return False


def start_watcher():
    """Start the file watcher service."""
    config = get_config()
    pipeline = FISPipeline()

    folders_raw = config.get("watcher", "watch_folders", fallback="")
    folders = [f.strip() for f in folders_raw.split(",") if f.strip()]

    if not folders:
        log.error("No watch folders configured in settings.ini")
        sys.exit(1)

    handler = FISHandler(pipeline, config)
    observer = Observer()

    for folder in folders:
        if Path(folder).exists():
            observer.schedule(handler, folder, recursive=True)
            log.info("Watching: %s", folder)
        else:
            log.warning("Folder not found, skipping: %s", folder)

    observer.start()
    log.info("FIS Watcher running. Monitoring %d folders.", len(folders))

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        log.info("FIS Watcher stopped.")

    observer.join()


if __name__ == "__main__":
    start_watcher()
