"""Transfer Queue — shows active, completed, and failed transfers."""
import time
from datetime import datetime
from dataclasses import dataclass, field
import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME
from s3_manager_pro_v5.utils.formatting import format_size, format_duration


@dataclass
class TransferRecord:
    """A record of a transfer operation."""
    id: str
    operation: str  # "download" or "upload"
    filename: str
    size: int
    status: str  # "active", "completed", "failed", "cancelled"
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime = None
    error: str = ""
    speed: float = 0.0


class TransferHistory:
    """Manages transfer history records."""

    def __init__(self):
        self._records: list = []
        self._counter = 0

    def add_record(self, operation: str, filename: str, size: int, status: str = "active") -> str:
        """Add a new transfer record. Returns record ID."""
        self._counter += 1
        record_id = f"t_{self._counter}"
        record = TransferRecord(
            id=record_id,
            operation=operation,
            filename=filename,
            size=size,
            status=status,
        )
        self._records.insert(0, record)  # Most recent first

        # Keep max 200 records
        if len(self._records) > 200:
            self._records = self._records[:200]

        return record_id

    def update_record(self, record_id: str, status: str, error: str = "", speed: float = 0.0):
        """Update a record's status."""
        for record in self._records:
            if record.id == record_id:
                record.status = status
                record.error = error
                record.speed = speed
                if status in ("completed", "failed", "cancelled"):
                    record.completed_at = datetime.now()
                break

    def add_batch(self, operation: str, filenames: list, sizes: list, status: str):
        """Add multiple records at once (for bulk operations)."""
        for fname, size in zip(filenames, sizes):
            self.add_record(operation, fname, size, status)

    @property
    def records(self) -> list:
        return self._records

    @property
    def active_count(self) -> int:
        return sum(1 for r in self._records if r.status == "active")

    @property
    def completed_count(self) -> int:
        return sum(1 for r in self._records if r.status == "completed")

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self._records if r.status == "failed")

    def clear(self):
        """Clear all history."""
        self._records.clear()


class TransferQueueDialog:
    """Dialog showing transfer history."""

    def __init__(self, parent, app, history: TransferHistory):
        self.app = app
        self.history = history

        colors = DARK_THEME if app.is_dark else LIGHT_THEME

        self.win = ctk.CTkToplevel(parent)
        self.win.title("📋 Transfer Queue & History")
        self.win.geometry("700x500")
        self.win.transient(parent)
        self.win.grab_set()
        self.win.resizable(True, True)
        self.win.configure(fg_color=colors["bg"])

        # Title + summary
        header = ctk.CTkFrame(self.win, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(15, 5))

        ctk.CTkLabel(header, text="📋 Transfer Queue",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=colors["text_primary"]).pack(side="left")

        # Summary badges
        badge_frame = ctk.CTkFrame(header, fg_color="transparent")
        badge_frame.pack(side="right")

        active = history.active_count
        completed = history.completed_count
        failed = history.failed_count

        if active > 0:
            self._badge(badge_frame, f"⏳ {active} Active", colors["warning"])
        self._badge(badge_frame, f"✅ {completed} Done", colors["success"])
        if failed > 0:
            self._badge(badge_frame, f"❌ {failed} Failed", colors["danger"])

        # Filter tabs
        tab_frame = ctk.CTkFrame(self.win, fg_color="transparent")
        tab_frame.pack(fill="x", padx=15, pady=5)

        self.filter_var = ctk.StringVar(value="all")
        for label, value in [("All", "all"), ("Active", "active"), ("Completed", "completed"), ("Failed", "failed")]:
            ctk.CTkRadioButton(tab_frame, text=label, variable=self.filter_var, value=value,
                               text_color=colors["text_primary"],
                               command=self._refresh_list).pack(side="left", padx=(0, 12))

        # Table
        tree_frame = ctk.CTkFrame(self.win, fg_color="transparent")
        tree_frame.pack(fill="both", expand=True, padx=15, pady=(5, 5))

        columns = ("status", "operation", "filename", "size", "time")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=12)
        self.tree.heading("status", text="Status")
        self.tree.heading("operation", text="Type")
        self.tree.heading("filename", text="File")
        self.tree.heading("size", text="Size")
        self.tree.heading("time", text="Time")

        self.tree.column("status", width=80, anchor="center")
        self.tree.column("operation", width=70, anchor="center")
        self.tree.column("filename", width=280, anchor="w")
        self.tree.column("size", width=90, anchor="e")
        self.tree.column("time", width=130, anchor="center")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Style
        style = ttk.Style()
        style.configure("Treeview",
                        background=colors["bg"],
                        foreground=colors["text_primary"],
                        fieldbackground=colors["bg"])
        style.configure("Treeview.Heading",
                        background=colors["surface"],
                        foreground=colors["text_primary"])

        # Bottom buttons
        btn_frame = ctk.CTkFrame(self.win, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=(5, 15))

        ctk.CTkButton(btn_frame, text="🗑 Clear History", width=120, height=32,
                      corner_radius=6, fg_color=colors["danger"], hover_color=colors["danger_hover"],
                      command=self._clear_history).pack(side="left", padx=(0, 10))

        ctk.CTkButton(btn_frame, text="Close", width=70, height=32,
                      corner_radius=6, fg_color=colors["badge_bg"],
                      hover_color=colors["surface_hover"],
                      text_color=colors["text_primary"],
                      command=self.win.destroy).pack(side="right")

        # Populate
        self._refresh_list()

    def _badge(self, parent, text, color):
        """Create a small badge label."""
        ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(size=11),
                     text_color=color).pack(side="left", padx=(10, 0))

    def _refresh_list(self):
        """Refresh the transfer list based on current filter."""
        self.tree.delete(*self.tree.get_children())
        filter_val = self.filter_var.get()

        for record in self.history.records:
            if filter_val != "all" and record.status != filter_val:
                continue

            status_icon = {
                "active": "⏳",
                "completed": "✅",
                "failed": "❌",
                "cancelled": "⛔",
            }.get(record.status, "❓")

            op_icon = "⬇" if record.operation == "download" else "⬆"
            time_str = record.started_at.strftime("%H:%M:%S")

            if record.completed_at:
                duration = (record.completed_at - record.started_at).total_seconds()
                time_str = f"{time_str} ({format_duration(duration)})"

            self.tree.insert("", "end", values=(
                status_icon,
                f"{op_icon} {record.operation.capitalize()}",
                record.filename,
                format_size(record.size),
                time_str,
            ))

    def _clear_history(self):
        """Clear all transfer history."""
        from tkinter import messagebox
        if messagebox.askyesno("Clear History", "Clear all transfer history?", parent=self.win):
            self.history.clear()
            self._refresh_list()
