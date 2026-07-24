"""Activity Log Panel for S3 Manager Pro v5.0."""

import threading
from datetime import datetime
from tkinter import filedialog

import customtkinter as ctk

from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME
from s3_manager_pro_v5.utils.formatting import format_size


class ActivityLogger:
    """Singleton logger for tracking in-app activity."""

    _instance: "ActivityLogger | None" = None
    _lock = threading.Lock()

    def __new__(cls) -> "ActivityLogger":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._logs: list[tuple[str, str, str]] = []
                cls._instance._listeners: list = []
        return cls._instance

    def log(self, message: str, level: str = "info") -> None:
        """Log a message with timestamp and level.

        Args:
            message: The log message.
            level: One of 'info', 'success', 'warning', 'error'.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = (timestamp, level, message)
        self._logs.append(entry)
        self._notify_listeners(entry)

    def get_logs(self) -> list[tuple[str, str, str]]:
        """Return all log entries as list of (timestamp, level, message)."""
        return list(self._logs)

    def clear(self) -> None:
        """Clear all logs."""
        self._logs.clear()

    def add_listener(self, callback) -> None:
        """Register a callback to be notified on new log entries."""
        self._listeners.append(callback)

    def remove_listener(self, callback) -> None:
        """Remove a registered listener."""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self, entry: tuple[str, str, str]) -> None:
        """Notify all registered listeners of a new entry."""
        for listener in self._listeners:
            try:
                listener(entry)
            except Exception:
                pass


# Color mapping for log levels
LOG_LEVEL_COLORS = {
    "info": "#FFFFFF",
    "success": "#4CAF50",
    "warning": "#FF9800",
    "error": "#F44336",
}

LOG_LEVEL_ICONS = {
    "info": "ℹ️",
    "success": "✅",
    "warning": "⚠️",
    "error": "❌",
}


class ActivityLogPanel(ctk.CTkFrame):
    """Scrollable panel displaying activity log entries with color coding."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.logger = ActivityLogger()

        self._build_ui()
        self._load_existing_logs()
        self.logger.add_listener(self._on_new_log)

    def _build_ui(self):
        """Build the panel UI."""
        # Header with buttons
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=5, pady=(5, 0))

        ctk.CTkLabel(
            header,
            text="📋 Activity Log",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            header,
            text="Export",
            width=70,
            command=self._export_logs,
        ).pack(side="right", padx=5)

        ctk.CTkButton(
            header,
            text="Clear",
            width=70,
            command=self._clear_logs,
        ).pack(side="right", padx=5)

        # Scrollable log area
        self.log_textbox = ctk.CTkTextbox(
            self,
            state="disabled",
            font=ctk.CTkFont(family="Consolas", size=11),
        )
        self.log_textbox.pack(fill="both", expand=True, padx=5, pady=5)

        # Configure tags for color coding
        self.log_textbox._textbox.tag_configure("info", foreground="#FFFFFF")
        self.log_textbox._textbox.tag_configure("success", foreground="#4CAF50")
        self.log_textbox._textbox.tag_configure("warning", foreground="#FF9800")
        self.log_textbox._textbox.tag_configure("error", foreground="#F44336")

    def _load_existing_logs(self):
        """Load any existing logs into the display."""
        for entry in self.logger.get_logs():
            self._append_entry(entry)

    def _on_new_log(self, entry: tuple[str, str, str]):
        """Callback when a new log entry is added."""
        # Schedule UI update on main thread
        self.after(0, lambda: self._append_entry(entry))

    def _append_entry(self, entry: tuple[str, str, str]):
        """Append a log entry to the textbox with color coding."""
        timestamp, level, message = entry
        icon = LOG_LEVEL_ICONS.get(level, "")
        line = f"[{timestamp}] {icon} {message}\n"

        self.log_textbox.configure(state="normal")
        self.log_textbox._textbox.insert("end", line, level)
        self.log_textbox.configure(state="disabled")
        self.log_textbox.see("end")

    def _clear_logs(self):
        """Clear all displayed logs."""
        self.logger.clear()
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")

    def _export_logs(self):
        """Export logs to a text file."""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            title="Export Activity Log",
        )

        if not filepath:
            return

        try:
            logs = self.logger.get_logs()
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("S3 Manager Pro - Activity Log\n")
                f.write("=" * 60 + "\n\n")
                for timestamp, level, message in logs:
                    f.write(f"[{timestamp}] [{level.upper()}] {message}\n")

            self.logger.log(f"Logs exported to: {filepath}", level="success")
        except Exception as e:
            self.logger.log(f"Failed to export logs: {e}", level="error")

    def destroy(self):
        """Clean up listener on destroy."""
        self.logger.remove_listener(self._on_new_log)
        super().destroy()
