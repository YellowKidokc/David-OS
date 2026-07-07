"""
gui.py

Main GUI application for the File Integrity Monitor, built with Tkinter.

Features:
- Pick a folder to monitor
- Create/refresh a baseline (hashes every file, backs up critical files)
- Run a one-time scan against the baseline
- Start/stop live, real-time monitoring
- Color-coded, timestamped, icon-tagged event feed with scan dividers
- View the running log
- Export a summary report
- Restore a critical file from its last known-good backup
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
from datetime import datetime

from integrity_engine import (
    scan_directory,
    save_baseline,
    load_baseline,
    compare_to_baseline,
)
from backup_manager import backup_all_critical, restore_file, has_backup
from monitor import LiveMonitor
from logger import log_event, read_log, export_report


class FileIntegrityMonitorApp:

    EVENT_ICONS = {
        "BASELINE": "🛡",
        "MODIFIED": "⚠",
        "DELETED": "✖",
        "NEW": "➕",
        "RESTORED": "✔",
    }

    def __init__(self, root):
        self.root = root
        self.root.title("File Integrity Monitor")
        self.root.geometry("780x560")
        self.root.minsize(700, 500)

        self.monitored_path = None
        self.baseline = None
        self.live_monitor = None

        self._build_ui()
        self._refresh_status("No folder selected", "gray")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- UI construction ----------

    def _build_ui(self):
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill="x")

        ttk.Button(top_frame, text="Select Folder", command=self._select_folder).pack(side="left")
        self.folder_label = ttk.Label(top_frame, text="No folder selected", foreground="gray")
        self.folder_label.pack(side="left", padx=10)

        action_frame = ttk.Frame(self.root, padding=(10, 0))
        action_frame.pack(fill="x")

        ttk.Button(action_frame, text="Create / Refresh Baseline",
                   command=self._create_baseline).pack(side="left", padx=2)
        ttk.Button(action_frame, text="Scan Now",
                   command=self._scan_now).pack(side="left", padx=2)
        self.start_button = ttk.Button(action_frame, text="Start Live Monitoring",
                                        command=self._start_monitoring)
        self.start_button.pack(side="left", padx=2)
        self.stop_button = ttk.Button(action_frame, text="Stop Monitoring",
                                       command=self._stop_monitoring, state="disabled")
        self.stop_button.pack(side="left", padx=2)
        ttk.Button(action_frame, text="Export Report",
                   command=self._export_report).pack(side="left", padx=2)
        ttk.Button(action_frame, text="Restore File",
                   command=self._restore_file_dialog).pack(side="left", padx=2)

        status_frame = ttk.Frame(self.root, padding=10)
        status_frame.pack(fill="x")
        ttk.Label(status_frame, text="Status:").pack(side="left")
        self.status_label = ttk.Label(status_frame, text="Idle", foreground="gray",
                                       font=("Segoe UI", 10, "bold"))
        self.status_label.pack(side="left", padx=5)

        feed_frame = ttk.LabelFrame(self.root, text="Live Event Feed", padding=5)
        feed_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.event_list = tk.Listbox(feed_frame, font=("Consolas", 9))
        scrollbar = ttk.Scrollbar(feed_frame, orient="vertical", command=self.event_list.yview)
        self.event_list.configure(yscrollcommand=scrollbar.set)
        self.event_list.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        last_scan_frame = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        last_scan_frame.pack(fill="x")
        self.summary_label = ttk.Label(last_scan_frame, text="No scans run yet.", foreground="gray")
        self.summary_label.pack(side="left")

    # ---------- Helpers ----------

    def _refresh_status(self, text, color):
        self.status_label.config(text=text, foreground=color)
        self.folder_label.config(
            text=self.monitored_path if self.monitored_path else "No folder selected"
        )

    def _add_event_to_feed(self, text, critical=False, event_type=None):
        """
        Add one line to the live event feed, newest on top, with a
        timestamp, an icon, and the event type spelled out as text.
        Critical events are shown in red so they stand out from
        routine changes.
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        icon = self.EVENT_ICONS.get(event_type, "•")
        label = event_type if event_type else "EVENT"
        formatted = f"[{timestamp}] {icon} {label:<9} {text}"

        self.event_list.insert(0, formatted)
        self.event_list.itemconfig(
            0,
            foreground="red" if critical else "black",
            selectforeground="red" if critical else "black",
        )

    def _add_scan_divider(self):
        """Insert a gray divider line marking the start of a new scan's results."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        divider = f"────────── Scan at {timestamp} ──────────"
        self.event_list.insert(0, divider)
        self.event_list.itemconfig(0, foreground="gray")

    # ---------- Button actions ----------

    def _select_folder(self):
        folder = filedialog.askdirectory(title="Select a folder to monitor")
        if folder:
            self.monitored_path = folder
            self.baseline = load_baseline()
            if self.baseline and self.baseline.get("root_path") != folder:
                self.baseline = None  # baseline was for a different folder, ignore it
            self._refresh_status("Folder selected — create a baseline to begin", "blue")

    def _create_baseline(self):
        if not self.monitored_path:
            messagebox.showwarning("No folder", "Please select a folder first.")
            return

        self._refresh_status("Creating baseline...", "blue")
        self.root.update_idletasks()

        snapshot = scan_directory(self.monitored_path)
        save_baseline(snapshot, self.monitored_path)
        self.baseline = load_baseline()

        backed_up = backup_all_critical(self.monitored_path, snapshot)

        log_event("BASELINE_CREATED", self.monitored_path,
                   details=f"{len(snapshot)} files, {len(backed_up)} critical files backed up")
        self._add_event_to_feed(
            f"Created baseline for {len(snapshot)} files "
            f"({len(backed_up)} critical files backed up)",
            event_type="BASELINE",
        )
        self._refresh_status(f"Baseline ready ({len(snapshot)} files)", "green")

    def _scan_now(self):
        if not self.baseline:
            messagebox.showwarning("No baseline", "Please create a baseline first.")
            return

        result = compare_to_baseline(self.monitored_path, self.baseline)
        modified, deleted, new = result["modified"], result["deleted"], result["new"]

        self._add_scan_divider()

        for item in modified:
            log_event("MODIFIED", item["path"], critical=item["critical"])
            self._add_event_to_feed(item["path"], critical=item["critical"], event_type="MODIFIED")

        for item in deleted:
            log_event("DELETED", item["path"], critical=item["critical"])
            self._add_event_to_feed(item["path"], critical=item["critical"], event_type="DELETED")

        for item in new:
            log_event("NEW", item["path"], critical=item["critical"])
            self._add_event_to_feed(item["path"], critical=item["critical"], event_type="NEW")

        self.last_scan_result = result
        self.summary_label.config(
            text=f"Last scan: {len(modified)} modified, {len(deleted)} deleted, {len(new)} new "
                 f"({datetime.now().strftime('%H:%M:%S')})"
        )
        self._refresh_status("Scan complete", "green")

    def _start_monitoring(self):
        if not self.baseline:
            messagebox.showwarning("No baseline", "Please create a baseline first.")
            return

        def process_live_event(event_type, rel_path, critical, new_hash):
            log_event(event_type, rel_path, critical=critical)
            self._add_event_to_feed(rel_path, critical=critical, event_type=event_type)
            # Update the in-memory baseline so we don't re-alert on the same change repeatedly
            if event_type in ("MODIFIED", "NEW") and new_hash:
                self.baseline["files"][rel_path] = {
                    "hash": new_hash,
                    "size": None,
                    "critical": critical,
                    "last_seen": datetime.now().isoformat(),
                }
            elif event_type == "DELETED" and rel_path in self.baseline["files"]:
                del self.baseline["files"][rel_path]

        def handle_live_event(event_type, rel_path, critical, new_hash):
            self.root.after(0, process_live_event, event_type, rel_path, critical, new_hash)

        self.live_monitor = LiveMonitor(self.monitored_path, handle_live_event)
        self.live_monitor.start()

        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self._refresh_status("Monitoring live...", "orange")

    def _stop_monitoring(self):
        if self.live_monitor:
            self.live_monitor.stop()
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self._refresh_status("Monitoring stopped", "gray")

    def _export_report(self):
        if not hasattr(self, "last_scan_result"):
            messagebox.showwarning("No scan yet", "Run a scan before exporting a report.")
            return
        output_path = export_report(self.last_scan_result)
        messagebox.showinfo("Report exported", f"Report saved to:\n{os.path.abspath(output_path)}")

    def _restore_file_dialog(self):
        if not self.monitored_path:
            messagebox.showwarning("No folder", "Please select a folder first.")
            return

        rel_path = simpledialog.askstring(
            "Restore File", "Enter the relative path of the file to restore:"
        )
        if not rel_path:
            return

        if not has_backup(rel_path):
            messagebox.showerror("No backup found", f"No backup exists for: {rel_path}")
            return

        success = restore_file(self.monitored_path, rel_path)
        if success:
            log_event("RESTORED", rel_path, details="Restored from backup")
            self._add_event_to_feed(rel_path, event_type="RESTORED")
            messagebox.showinfo("Restored", f"Successfully restored: {rel_path}")
        else:
            messagebox.showerror("Restore failed", f"Could not restore: {rel_path}")

    def _on_close(self):
        if self.live_monitor and self.live_monitor.is_running():
            self.live_monitor.stop()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = FileIntegrityMonitorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
