"""FIS Popup v2 — Rename queue with learning feedback.

Actions: Approve, Keep Original, Wrong Domain, Wrong Subject, Skip
Editable proposed name. Rating 1-5. All corrections logged to Postgres.
"""

import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from fis.db.models import get_pending_files, get_subject_codes, search_files, update_file_status, insert_correction
from fis.db.connection import get_connection
from fis.renamer import rename_file
from fis.log import get_logger

log = get_logger("popup")


# ─── Helpers ────────────────────────────────────────────────

def log_correction(file_id, old_domain, old_subjects, old_slug,
                   new_domain, new_subjects, new_slug,
                   action, rating):
    """Write correction + feedback to Postgres."""
    try:
        insert_correction(file_id,
            {"domain": old_domain, "subjects": old_subjects, "slug": old_slug},
            {"domain": new_domain, "subjects": new_subjects, "slug": new_slug})
        # Also store the action type and rating in bil_events for richer learning
        conn = get_connection()
        with conn.cursor() as cur:
            import json
            cur.execute("""
                INSERT INTO bil_events (model_name, features, signal)
                VALUES ('file_feedback', %s, %s)
            """, (
                json.dumps({
                    "file_id": file_id,
                    "action": action,
                    "old_domain": old_domain,
                    "new_domain": new_domain,
                    "old_subjects": old_subjects,
                    "new_subjects": new_subjects,
                }),
                float(rating) / 5.0,  # normalize 1-5 to 0-1
            ))
        conn.commit()
        conn.close()
    except Exception as e:
        log.error("Correction log failed: %s", e)


# ─── Action Button Widget ───────────────────────────────────

class ActionButtons(QWidget):
    """Row of action buttons for a single file."""

    def __init__(self, file_data, parent_tab):
        super().__init__()
        self.file_data = file_data
        self.parent_tab = parent_tab
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(3)

        # Approve — use proposed (or edited) name
        btn_approve = QPushButton("Approve")
        btn_approve.setStyleSheet("background:#2E7D32; color:white; padding:4px 8px; font-size:11px;")
        btn_approve.setToolTip("Rename file to proposed name")
        btn_approve.clicked.connect(lambda: self._action("approve"))
        layout.addWidget(btn_approve)

        # Keep Original — add domain/subject/ID suffix only
        btn_keep = QPushButton("Keep")
        btn_keep.setStyleSheet("background:#1565C0; color:white; padding:4px 8px; font-size:11px;")
        btn_keep.setToolTip("Keep original name, add classification suffix")
        btn_keep.clicked.connect(lambda: self._action("keep_original"))
        layout.addWidget(btn_keep)

        # Wrong Domain
        btn_domain = QPushButton("Domain")
        btn_domain.setStyleSheet("background:#E65100; color:white; padding:4px 8px; font-size:11px;")
        btn_domain.setToolTip("Domain is wrong — will prompt for correct domain")
        btn_domain.clicked.connect(lambda: self._action("wrong_domain"))
        layout.addWidget(btn_domain)

        # Wrong Subject
        btn_subject = QPushButton("Subject")
        btn_subject.setStyleSheet("background:#F57F17; color:white; padding:4px 8px; font-size:11px;")
        btn_subject.setToolTip("Subjects are wrong — will prompt for correction")
        btn_subject.clicked.connect(lambda: self._action("wrong_subject"))
        layout.addWidget(btn_subject)

        # Skip — don't rename, don't learn
        btn_skip = QPushButton("Skip")
        btn_skip.setStyleSheet("background:#585B70; color:#CDD6F4; padding:4px 8px; font-size:11px;")
        btn_skip.setToolTip("Skip this file entirely")
        btn_skip.clicked.connect(lambda: self._action("skip"))
        layout.addWidget(btn_skip)

    def _action(self, action_type):
        f = self.file_data
        file_id = f["file_id"]
        file_path = f["file_path"]
        original = f["original_name"]
        proposed = f["proposed_name"] or ""
        domain = f["domain"] or ""
        subjects = f["subject_codes"] or []
        slug = f["slug"] or ""
        import os

        # Get the edited proposed name from the table (user may have changed it)
        row = self.parent_tab.get_row_for_file(file_id)
        edited_name = proposed
        rating = 3  # default
        if row is not None:
            name_item = self.parent_tab.table.item(row, 1)
            if name_item:
                edited_name = name_item.text()
            rating_widget = self.parent_tab.table.cellWidget(row, 5)
            if rating_widget and hasattr(rating_widget, 'value'):
                rating = rating_widget.value()

        if action_type == "approve":
            # Use edited name (user may have corrected the slug)
            if edited_name and edited_name != proposed:
                # User edited — log correction
                log_correction(file_id, domain, subjects, slug,
                              domain, subjects, edited_name.split("_")[0],
                              "approve_edited", rating)
            else:
                log_correction(file_id, domain, subjects, slug,
                              domain, subjects, slug,
                              "approve", rating)
            if edited_name:
                rename_file(file_path, edited_name, file_id)

        elif action_type == "keep_original":
            # Keep original filename, just add domain.subject_seqid suffix
            stem, ext = os.path.splitext(original)
            seq = f.get("sequence_id", "000000")
            subj_str = "-".join(subjects[:3]) if subjects else "GN"
            keep_name = f"{stem}_{domain}.{subj_str}_{seq}{ext}"
            log_correction(file_id, domain, subjects, slug,
                          domain, subjects, stem,
                          "keep_original", rating)
            rename_file(file_path, keep_name, file_id)

        elif action_type == "wrong_domain":
            # Let user pick correct domain from dropdown
            from fis.db.codes import list_domains
            domains = list_domains()
            domain_codes = [d["code"] for d in domains]
            domain_labels = [f"{d['code']} — {d['label']}" for d in domains]

            from PySide6.QtWidgets import QInputDialog
            choice, ok = QInputDialog.getItem(
                self, "Correct Domain",
                f"Original: {original}\nCurrent domain: {domain}\n\nSelect correct domain:",
                domain_labels, 0, False)
            if ok and choice:
                new_domain = choice.split(" — ")[0]
                log_correction(file_id, domain, subjects, slug,
                              new_domain, subjects, slug,
                              "wrong_domain", 1)  # rating 1 = bad miss
                # Rebuild proposed name with corrected domain
                seq = f.get("sequence_id", "000000")
                subj_str = "-".join(subjects[:3]) if subjects else "GN"
                ext = os.path.splitext(original)[1]
                new_name = f"{slug}_{new_domain}.{subj_str}_{seq}{ext}"
                rename_file(file_path, new_name, file_id)

        elif action_type == "wrong_subject":
            from PySide6.QtWidgets import QInputDialog
            current = ", ".join(subjects)
            new_subj, ok = QInputDialog.getText(
                self, "Correct Subjects",
                f"Original: {original}\nCurrent subjects: {current}\n\n"
                "Enter correct subject codes (comma-separated, e.g. MQ, CS):")
            if ok and new_subj:
                new_subjects = [s.strip() for s in new_subj.split(",")]
                log_correction(file_id, domain, subjects, slug,
                              domain, new_subjects, slug,
                              "wrong_subject", 2)  # rating 2 = partial miss
                # Rebuild proposed name with corrected subjects
                seq = f.get("sequence_id", "000000")
                subj_str = "-".join(new_subjects[:3])
                ext = os.path.splitext(original)[1]
                new_name = f"{slug}_{domain}.{subj_str}_{seq}{ext}"
                rename_file(file_path, new_name, file_id)

        elif action_type == "skip":
            log_correction(file_id, domain, subjects, slug,
                          domain, subjects, slug,
                          "skip", rating)
            update_file_status(file_id, "skipped")

        self.parent_tab.load_pending()


# ─── Rating Widget ──────────────────────────────────────────

class RatingWidget(QWidget):
    """1-5 star rating with clickable buttons."""

    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(1)
        self._rating = 3
        self._buttons = []
        for i in range(1, 6):
            btn = QPushButton(str(i))
            btn.setFixedSize(22, 22)
            btn.setStyleSheet(self._style(i, self._rating))
            btn.clicked.connect(lambda checked, val=i: self._set(val))
            layout.addWidget(btn)
            self._buttons.append(btn)

    def _style(self, val, current):
        if val <= current:
            return "background:#F59E0B; color:#1E1E2E; border:none; border-radius:3px; font-size:10px; font-weight:bold;"
        return "background:#45475A; color:#585B70; border:none; border-radius:3px; font-size:10px;"

    def _set(self, val):
        self._rating = val
        for i, btn in enumerate(self._buttons):
            btn.setStyleSheet(self._style(i + 1, val))

    def value(self):
        return self._rating


# ─── Rename Queue Tab (v2) ──────────────────────────────────

class RenameQueueTab(QWidget):
    """Pending files with editable names, action buttons, and ratings."""

    def __init__(self):
        super().__init__()
        self._file_map = {}  # file_id -> row index
        layout = QVBoxLayout(self)

        # Header
        header = QHBoxLayout()
        self.count_label = QLabel("Pending: 0")
        self.count_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        header.addWidget(self.count_label)

        self.sort_label = QLabel("Sort:")
        self.sort_label.setFont(QFont("Segoe UI", 10))
        header.addWidget(self.sort_label)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Confidence ↓", "Confidence ↑", "Newest", "Oldest"])
        self.sort_combo.currentIndexChanged.connect(self.load_pending)
        self.sort_combo.setStyleSheet("background:#313244; color:#CDD6F4; padding:4px;")
        header.addWidget(self.sort_combo)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_pending)
        header.addWidget(refresh_btn)

        layout.addLayout(header)

        # Table — 7 columns: Original, Proposed (editable), Domain, Subjects, Confidence, Rating, Actions
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Original", "Proposed (editable)", "Domain", "Subjects", "Conf", "Rating", "Actions"
        ])
        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header_view.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 200)
        self.table.setColumnWidth(3, 120)
        self.table.setColumnWidth(6, 320)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setDefaultSectionSize(36)
        layout.addWidget(self.table)

        self.load_pending()

    def get_row_for_file(self, file_id):
        return self._file_map.get(file_id)

    def load_pending(self):
        files = get_pending_files(limit=100)

        # Sort based on combo selection
        sort_mode = self.sort_combo.currentText() if hasattr(self, 'sort_combo') else "Confidence ↓"
        if sort_mode == "Confidence ↓":
            files.sort(key=lambda f: f.get("confidence") or 0, reverse=True)
        elif sort_mode == "Confidence ↑":
            files.sort(key=lambda f: f.get("confidence") or 0)
        elif sort_mode == "Newest":
            files.sort(key=lambda f: f.get("created_at") or "", reverse=True)
        elif sort_mode == "Oldest":
            files.sort(key=lambda f: f.get("created_at") or "")

        self.table.setRowCount(len(files))
        self._file_map.clear()
        self.count_label.setText(f"Pending: {len(files)}")

        for row, f in enumerate(files):
            self._file_map[f["file_id"]] = row

            # Col 0: Original name (read-only)
            orig_item = QTableWidgetItem(f["original_name"])
            orig_item.setFlags(orig_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, orig_item)

            # Col 1: Proposed name (EDITABLE — this is the key change)
            proposed_item = QTableWidgetItem(f["proposed_name"] or "")
            self.table.setItem(row, 1, proposed_item)

            # Col 2: Domain (read-only)
            domain_item = QTableWidgetItem(f["domain"] or "")
            domain_item.setFlags(domain_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 2, domain_item)

            # Col 3: Subjects (read-only)
            subj_text = ", ".join(f["subject_codes"]) if f["subject_codes"] else ""
            subj_item = QTableWidgetItem(subj_text)
            subj_item.setFlags(subj_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 3, subj_item)

            # Col 4: Confidence (color coded)
            conf = f["confidence"] or 0
            conf_item = QTableWidgetItem(f"{conf:.0f}%")
            conf_item.setFlags(conf_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if conf >= 80:
                conf_item.setForeground(QColor("#2E7D32"))
            elif conf >= 50:
                conf_item.setForeground(QColor("#F57F17"))
            else:
                conf_item.setForeground(QColor("#C62828"))
            self.table.setItem(row, 4, conf_item)

            # Col 5: Rating (1-5 clickable)
            rating = RatingWidget()
            self.table.setCellWidget(row, 5, rating)

            # Col 6: Action buttons
            actions = ActionButtons(f, self)
            self.table.setCellWidget(row, 6, actions)


# ─── Code Search Tab ────────────────────────────────────────

class CodeSearchTab(QWidget):
    """Search subject codes and classified files by concept."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type a concept... (consciousness, master equation, entropy)")
        self.search_input.setFont(QFont("Segoe UI", 12))
        self.search_input.textChanged.connect(self._on_search)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        self.code_label = QLabel("Matching Codes:")
        self.code_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(self.code_label)

        self.code_table = QTableWidget()
        self.code_table.setColumnCount(4)
        self.code_table.setHorizontalHeaderLabels(["Code", "Label", "Domain", "Aliases"])
        self.code_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.code_table.setMaximumHeight(200)
        layout.addWidget(self.code_table)

        self.file_label = QLabel("Matching Files:")
        self.file_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(self.file_label)

        self.file_table = QTableWidget()
        self.file_table.setColumnCount(5)
        self.file_table.setHorizontalHeaderLabels(["Name", "Domain", "Subjects", "Tags", "Path"])
        self.file_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.file_table)

    def _on_search(self, text):
        if len(text) < 2:
            return
        try:
            codes = get_subject_codes()
            matching = [c for c in codes if text.lower() in (
                (c["label"] or "").lower() + " " +
                " ".join(c.get("aliases") or []).lower() + " " +
                (c.get("description") or "").lower()
            )]
            self.code_table.setRowCount(len(matching))
            for row, c in enumerate(matching):
                self.code_table.setItem(row, 0, QTableWidgetItem(c["code"]))
                self.code_table.setItem(row, 1, QTableWidgetItem(c["label"]))
                self.code_table.setItem(row, 2, QTableWidgetItem(c["domain"]))
                self.code_table.setItem(row, 3, QTableWidgetItem(", ".join(c.get("aliases") or [])))
        except Exception:
            pass
        try:
            files = search_files(text, limit=20)
            self.file_table.setRowCount(len(files))
            for row, f in enumerate(files):
                self.file_table.setItem(row, 0, QTableWidgetItem(
                    f.get("final_name") or f.get("proposed_name") or f["original_name"]))
                self.file_table.setItem(row, 1, QTableWidgetItem(f.get("domain") or ""))
                self.file_table.setItem(row, 2, QTableWidgetItem(", ".join(f.get("subject_codes") or [])))
                self.file_table.setItem(row, 3, QTableWidgetItem(", ".join(f.get("tags") or [])))
                self.file_table.setItem(row, 4, QTableWidgetItem(f.get("file_path") or ""))
        except Exception:
            pass


# ─── Main Window ────────────────────────────────────────────

class FISPopup(QMainWindow):
    """FIS popup — Ctrl+Alt+F to open."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("FIS — File Intelligence System")
        self.setMinimumSize(1100, 650)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)

        self.setStyleSheet("""
            QMainWindow { background-color: #1E1E2E; }
            QWidget { background-color: #1E1E2E; color: #CDD6F4; }
            QTableWidget { background-color: #313244; alternate-background-color: #45475A;
                          gridline-color: #585B70; border: none; }
            QHeaderView::section { background-color: #585B70; color: #CDD6F4;
                                  padding: 6px; border: none; font-weight: bold; }
            QLineEdit { background-color: #313244; border: 2px solid #585B70;
                       border-radius: 8px; padding: 8px; color: #CDD6F4; font-size: 14px; }
            QLineEdit:focus { border-color: #89B4FA; }
            QPushButton { background-color: #89B4FA; color: #1E1E2E; border: none;
                         border-radius: 6px; padding: 6px 16px; font-weight: bold; }
            QPushButton:hover { background-color: #B4D0FB; }
            QTabWidget::pane { border: none; }
            QTabBar::tab { background-color: #313244; color: #CDD6F4; padding: 8px 20px;
                          border: none; margin-right: 2px; }
            QTabBar::tab:selected { background-color: #585B70; }
            QComboBox { background-color: #313244; color: #CDD6F4; padding: 4px;
                       border: 1px solid #585B70; border-radius: 4px; }
            QComboBox::drop-down { border: none; }
        """)

        tabs = QTabWidget()
        tabs.addTab(RenameQueueTab(), "Rename Queue")
        tabs.addTab(CodeSearchTab(), "Code Search")
        self.setCentralWidget(tabs)

        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, self.close)


def launch_popup():
    app = QApplication.instance() or QApplication(sys.argv)
    window = FISPopup()
    window.show()
    app.exec()


if __name__ == "__main__":
    launch_popup()
