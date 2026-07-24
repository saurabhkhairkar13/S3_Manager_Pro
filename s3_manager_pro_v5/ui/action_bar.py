"""Action bar (buttons) + Progress bar (transfer status)."""
import customtkinter as ctk
from s3_manager_pro_v5.utils.formatting import format_size, format_duration


class ActionBar(ctk.CTkFrame):
    """Bottom action bar with operation buttons."""

    def __init__(self, parent, app):
        super().__init__(parent, height=44, corner_radius=0)
        self.app = app
        self.pack_propagate(False)

        # Buttons container
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(side="left", padx=10, pady=6)

        from s3_manager_pro_v5.ui.tooltip import Tooltip

        # Download
        self.download_btn = ctk.CTkButton(
            self.btn_frame, text="⬇ Download", width=100, height=30,
            corner_radius=6, font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#28a745", hover_color="#218838",
            command=app.download_selected,
        )
        self.download_btn.pack(side="left", padx=(0, 4))
        Tooltip(self.download_btn, "Download selected files to local folder (Ctrl+D)")

        # Upload
        self.upload_btn = ctk.CTkButton(
            self.btn_frame, text="⬆ Upload", width=85, height=30,
            corner_radius=6, font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#0984e3", hover_color="#0773c5",
            command=app.upload_files,
        )
        self.upload_btn.pack(side="left", padx=(0, 4))
        Tooltip(self.upload_btn, "Upload files or folder to current S3 location (Ctrl+U)")

        # Restore (Glacier)
        self.restore_btn = ctk.CTkButton(
            self.btn_frame, text="🔄 Restore", width=85, height=30,
            corner_radius=6, font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#6f42c1", hover_color="#5a32a3",
            command=app.restore_glacier,
        )
        self.restore_btn.pack(side="left", padx=(0, 4))
        Tooltip(self.restore_btn, "Restore Glacier/Deep Archive files with cost estimation")

        # Share URL
        self.share_btn = ctk.CTkButton(
            self.btn_frame, text="🔗 Share", width=75, height=30,
            corner_radius=6, font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#00b894", hover_color="#00a381",
            command=app.copy_presigned_url,
        )
        self.share_btn.pack(side="left", padx=(0, 4))
        Tooltip(self.share_btn, "Generate a shareable presigned URL (1hr-7day expiry)")

        # Sync
        self.sync_btn = ctk.CTkButton(
            self.btn_frame, text="📋 Sync", width=75, height=30,
            corner_radius=6, font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#fdcb6e", hover_color="#e0b035", text_color="#2d3436",
            command=app.open_sync_dialog,
        )
        self.sync_btn.pack(side="left", padx=(0, 4))
        Tooltip(self.sync_btn, "Sync local folder ↔ S3 with dry-run preview")

        # Delete (separated, right-aligned within buttons)
        self.delete_btn = ctk.CTkButton(
            self.btn_frame, text="🗑", width=35, height=30,
            corner_radius=6, font=ctk.CTkFont(size=14),
            fg_color="#dc3545", hover_color="#c82333",
            command=app.delete_selected,
        )
        self.delete_btn.pack(side="left", padx=(12, 0))
        Tooltip(self.delete_btn, "Delete selected files permanently (Del)")

        # Right side: Pause/Cancel controls (hidden when not active)
        self.control_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.control_frame.pack(side="right", padx=10, pady=6)

        self.pause_btn = ctk.CTkButton(
            self.control_frame, text="⏸ Pause", width=75, height=30,
            corner_radius=6, font=ctk.CTkFont(size=11),
            command=app.pause_transfer,
            state="disabled",
        )
        self.pause_btn.pack(side="left", padx=(0, 4))
        Tooltip(self.pause_btn, "Pause / Resume current transfer")

        self.cancel_btn = ctk.CTkButton(
            self.control_frame, text="✖ Cancel", width=75, height=30,
            corner_radius=6, font=ctk.CTkFont(size=11),
            fg_color="#dc3545", hover_color="#c82333",
            command=app.cancel_transfer,
            state="disabled",
        )
        self.cancel_btn.pack(side="left")
        Tooltip(self.cancel_btn, "Cancel current transfer")

    def set_transfer_active(self, active: bool):
        """Enable/disable pause and cancel buttons."""
        state = "normal" if active else "disabled"
        self.pause_btn.configure(state=state)
        self.cancel_btn.configure(state=state)
        if not active:
            self.pause_btn.configure(text="⏸ Pause")

    def set_paused(self, paused: bool):
        """Toggle pause button text."""
        self.pause_btn.configure(text="▶ Resume" if paused else "⏸ Pause")

    def apply_theme(self, colors: dict):
        """Apply theme to action bar."""
        self.configure(fg_color=colors["surface"])
        self.pause_btn.configure(
            fg_color=colors["badge_bg"],
            hover_color=colors["surface_hover"],
            text_color=colors["text_primary"],
        )


class ProgressBar(ctk.CTkFrame):
    """Bottom progress bar showing transfer status."""

    def __init__(self, parent, app):
        super().__init__(parent, height=38, corner_radius=0)
        self.app = app
        self.pack_propagate(False)

        # Left: status text
        self.status_label = ctk.CTkLabel(
            self, text="Ready",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            anchor="w",
        )
        self.status_label.pack(side="left", padx=12)

        # Right: speed + ETA
        self.speed_label = ctk.CTkLabel(
            self, text="",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            anchor="e",
        )
        self.speed_label.pack(side="right", padx=12)

        # Center: progress bar
        self.progress = ctk.CTkProgressBar(self, height=10, corner_radius=5)
        self.progress.pack(fill="x", padx=120, pady=12)
        self.progress.set(0)

    def update_progress(self, progress):
        """Update from a TransferProgress dataclass."""
        if progress.total_bytes > 0:
            pct = progress.transferred_bytes / progress.total_bytes
            self.progress.set(min(pct, 1.0))
        else:
            self.progress.set(0)

        # Status text
        if progress.is_active:
            self.status_label.configure(
                text=f"⬇ {progress.current_file} ({progress.completed_files}/{progress.total_files})"
            )
            # Speed + ETA
            speed_str = f"{format_size(int(progress.speed_bps))}/s"
            eta_str = format_duration(progress.eta_seconds) if progress.eta_seconds > 0 else "—"
            pct_str = f"{pct * 100:.1f}%" if progress.total_bytes > 0 else ""
            self.speed_label.configure(text=f"{pct_str} │ {speed_str} │ ETA: {eta_str}")
        else:
            if progress.total_files > 0:
                self.status_label.configure(
                    text=f"✅ Done: {progress.completed_files} success, "
                         f"{progress.skipped_files} skipped, {progress.failed_files} failed"
                )
                self.speed_label.configure(text="")
            else:
                self.speed_label.configure(text="")

    def set_status(self, text: str):
        """Set a simple status message."""
        self.status_label.configure(text=text)
        self.speed_label.configure(text="")

    def reset(self):
        """Reset progress to zero."""
        self.progress.set(0)
        self.status_label.configure(text="Ready")
        self.speed_label.configure(text="")

    def apply_theme(self, colors: dict):
        """Apply theme colors."""
        self.configure(fg_color=colors["header_bg"])
        self.status_label.configure(text_color=colors["text_primary"])
        self.speed_label.configure(text_color=colors["text_secondary"])
        self.progress.configure(
            progress_color=colors["primary"],
            fg_color=colors["border"],
        )
