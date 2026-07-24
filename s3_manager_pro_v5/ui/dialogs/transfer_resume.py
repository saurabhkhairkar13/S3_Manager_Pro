"""Transfer Resume - Persist and resume partial S3 downloads."""

import json
import os
import time
from pathlib import Path
from typing import Any

import customtkinter as ctk

from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME
from s3_manager_pro_v5.utils.formatting import format_size

# Default state file location
STATE_FILE = "s3_transfer_state.json"


class TransferStateManager:
    """Manages persistence of partial download state to a JSON file.

    Tracks incomplete transfers so they can be resumed after application restart.
    """

    def __init__(self, state_file: str | None = None):
        """Initialize the transfer state manager.

        Args:
            state_file: Path to the JSON state file. Defaults to s3_transfer_state.json
                       in the user's home directory.
        """
        if state_file is None:
            home = Path.home()
            self.state_file = home / ".s3_manager_pro" / STATE_FILE
        else:
            self.state_file = Path(state_file)

        # Ensure directory exists
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

    def _load_state(self) -> dict[str, Any]:
        """Load the current state from disk.

        Returns:
            Dictionary of transfer states keyed by S3 key.
        """
        if not self.state_file.exists():
            return {}

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_to_disk(self, state: dict[str, Any]):
        """Write the state dictionary to disk.

        Args:
            state: The full state dictionary to persist.
        """
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, default=str)

    def save_state(
        self, key: str, local_path: str, bytes_downloaded: int, total_size: int
    ):
        """Save or update the state of a partial download.

        Args:
            key: The S3 object key being downloaded.
            local_path: Local file path where download is being saved.
            bytes_downloaded: Number of bytes successfully downloaded so far.
            total_size: Total size of the object in bytes.
        """
        state = self._load_state()
        state[key] = {
            "key": key,
            "local_path": local_path,
            "bytes_downloaded": bytes_downloaded,
            "total_size": total_size,
            "last_updated": time.time(),
            "percent_complete": round(
                (bytes_downloaded / total_size * 100) if total_size > 0 else 0, 2
            ),
        }
        self._save_to_disk(state)

    def get_pending_transfers(self) -> list[dict[str, Any]]:
        """Get all pending (incomplete) transfers.

        Returns:
            List of transfer state dictionaries for incomplete downloads.
        """
        state = self._load_state()
        pending = []
        for entry in state.values():
            if entry.get("bytes_downloaded", 0) < entry.get("total_size", 0):
                pending.append(entry)
        return pending

    def remove_state(self, key: str):
        """Remove a transfer entry (e.g., after successful completion).

        Args:
            key: The S3 object key to remove from state tracking.
        """
        state = self._load_state()
        if key in state:
            del state[key]
            self._save_to_disk(state)

    def clear_all(self):
        """Remove all transfer state entries."""
        self._save_to_disk({})


class ResumeTransfersDialog(ctk.CTkToplevel):
    """Dialog showing pending incomplete downloads with option to resume them."""

    def __init__(self, parent, app, state_manager: TransferStateManager | None = None):
        """Initialize the resume transfers dialog.

        Args:
            parent: Parent widget.
            app: Application instance with download resume capability.
            state_manager: Optional TransferStateManager instance. Creates one if None.
        """
        super().__init__(parent)
        self.app = app
        self.state_manager = state_manager or TransferStateManager()

        self.title("Resume Incomplete Transfers")
        self.geometry("700x450")
        self.resizable(True, True)

        # Center on parent
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._load_transfers()

    def _build_ui(self):
        """Build the dialog UI."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        header = ctk.CTkLabel(
            self,
            text="Incomplete Transfers",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        header.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="w")

        # Scrollable frame for transfer list
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.grid(row=1, column=0, padx=16, pady=8, sticky="nsew")
        self.scroll_frame.grid_columnconfigure(0, weight=1)

        # Bottom buttons
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=2, column=0, padx=16, pady=(8, 16), sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)

        self.resume_all_btn = ctk.CTkButton(
            button_frame,
            text="Resume All",
            command=self._resume_all,
        )
        self.resume_all_btn.grid(row=0, column=1, padx=4)

        self.clear_all_btn = ctk.CTkButton(
            button_frame,
            text="Clear All",
            fg_color="red",
            hover_color="darkred",
            command=self._clear_all,
        )
        self.clear_all_btn.grid(row=0, column=2, padx=4)

        self.close_btn = ctk.CTkButton(
            button_frame,
            text="Close",
            command=self.destroy,
        )
        self.close_btn.grid(row=0, column=3, padx=4)

    def _load_transfers(self):
        """Load and display pending transfers."""
        # Clear existing entries
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        transfers = self.state_manager.get_pending_transfers()

        if not transfers:
            empty_label = ctk.CTkLabel(
                self.scroll_frame,
                text="No incomplete transfers found.",
                font=ctk.CTkFont(size=13),
            )
            empty_label.grid(row=0, column=0, padx=16, pady=32)
            self.resume_all_btn.configure(state="disabled")
            self.clear_all_btn.configure(state="disabled")
            return

        for idx, transfer in enumerate(transfers):
            self._create_transfer_row(idx, transfer)

    def _create_transfer_row(self, idx: int, transfer: dict[str, Any]):
        """Create a row widget for a single transfer entry.

        Args:
            idx: Row index.
            transfer: Transfer state dictionary.
        """
        row_frame = ctk.CTkFrame(self.scroll_frame)
        row_frame.grid(row=idx, column=0, padx=4, pady=4, sticky="ew")
        row_frame.grid_columnconfigure(1, weight=1)

        # File info
        key = transfer.get("key", "Unknown")
        filename = key.split("/")[-1] if "/" in key else key
        bytes_done = transfer.get("bytes_downloaded", 0)
        total = transfer.get("total_size", 0)
        percent = transfer.get("percent_complete", 0)

        name_label = ctk.CTkLabel(
            row_frame,
            text=filename,
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        )
        name_label.grid(row=0, column=0, columnspan=3, padx=8, pady=(6, 2), sticky="w")

        progress_text = f"{format_size(bytes_done)} / {format_size(total)} ({percent}%)"
        progress_label = ctk.CTkLabel(
            row_frame,
            text=progress_text,
            font=ctk.CTkFont(size=11),
            anchor="w",
        )
        progress_label.grid(row=1, column=0, padx=8, pady=(0, 6), sticky="w")

        # Progress bar
        progress_bar = ctk.CTkProgressBar(row_frame, width=200)
        progress_bar.set(percent / 100.0 if total > 0 else 0)
        progress_bar.grid(row=1, column=1, padx=8, pady=(0, 6), sticky="ew")

        # Resume button
        resume_btn = ctk.CTkButton(
            row_frame,
            text="Resume",
            width=70,
            command=lambda k=key, lp=transfer.get("local_path", ""): self._resume_one(
                k, lp
            ),
        )
        resume_btn.grid(row=0, column=3, rowspan=2, padx=(4, 4), pady=6)

        # Remove button
        remove_btn = ctk.CTkButton(
            row_frame,
            text="✕",
            width=30,
            fg_color="red",
            hover_color="darkred",
            command=lambda k=key: self._remove_one(k),
        )
        remove_btn.grid(row=0, column=4, rowspan=2, padx=(0, 8), pady=6)

    def _resume_one(self, key: str, local_path: str):
        """Resume a single transfer.

        Args:
            key: S3 object key to resume downloading.
            local_path: Local path to save/resume the file.
        """
        if hasattr(self.app, "resume_download"):
            self.app.resume_download(key, local_path)

    def _resume_all(self):
        """Resume all pending transfers."""
        transfers = self.state_manager.get_pending_transfers()
        for transfer in transfers:
            key = transfer.get("key", "")
            local_path = transfer.get("local_path", "")
            if key and hasattr(self.app, "resume_download"):
                self.app.resume_download(key, local_path)

    def _remove_one(self, key: str):
        """Remove a single transfer from tracking.

        Args:
            key: S3 object key to remove.
        """
        self.state_manager.remove_state(key)
        self._load_transfers()

    def _clear_all(self):
        """Clear all transfer state entries."""
        self.state_manager.clear_all()
        self._load_transfers()
