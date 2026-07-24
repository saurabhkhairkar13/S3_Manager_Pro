"""Contextual Toolbar — icon-based toolbar that adapts to what's selected.

Shows different button groups based on context:
- Nothing selected: Upload, Sync, Search, Analytics
- Files selected: Download, Share, Delete, Rename, Move, Tags
- Transfer active: Pause, Resume, Cancel, Speed
"""
import customtkinter as ctk
from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME


class Toolbar(ctk.CTkFrame):
    """Icon toolbar with contextual button groups."""

    def __init__(self, parent, app):
        super().__init__(parent, height=40, corner_radius=0)
        self.app = app
        self.pack_propagate(False)

        # ── Group 1: File Operations (always visible) ──
        self.file_group = ctk.CTkFrame(self, fg_color="transparent")
        self.file_group.pack(side="left", padx=(10, 0))

        self.download_btn = self._btn(self.file_group, "⬇ Download", "Download selected files (Ctrl+D)", app.download_selected)
        self.upload_btn = self._btn(self.file_group, "⬆ Upload", "Upload files to S3 (Ctrl+U)", app.upload_files)
        self.refresh_btn = self._btn(self.file_group, "🔄 Refresh", "Refresh file list (F5)", app.refresh_listing)
        self.share_btn = self._btn(self.file_group, "🔗 Share", "Generate shareable URL (Ctrl+L)", app.copy_presigned_url)

        # Separator
        self._separator()

        # ── Group 2: Edit Operations (contextual) ──
        self.edit_group = ctk.CTkFrame(self, fg_color="transparent")
        self.edit_group.pack(side="left", padx=(5, 0))

        self.rename_btn = self._btn(self.edit_group, "✏️ Rename", "Batch rename files", app.open_batch_rename)
        self.move_btn = self._btn(self.edit_group, "📤 Move", "Copy/Move to another bucket", app.open_cross_bucket_copy)
        self.delete_btn = self._btn(self.edit_group, "🗑 Delete", "Delete selected files (Del)", app.delete_selected, danger=True)

        # Separator
        self._separator()

        # ── Group 3: Tools ──
        self.tools_group = ctk.CTkFrame(self, fg_color="transparent")
        self.tools_group.pack(side="left", padx=(5, 0))

        self.sync_btn = self._btn(self.tools_group, "📋 Sync", "Sync local folder with S3", app.open_sync_dialog)
        self.cost_btn = self._btn(self.tools_group, "💡 Cost", "Cost optimization advisor", app.open_cost_advisor)
        self.search_btn = self._btn(self.tools_group, "🔍 Search", "Search across all buckets (Ctrl+Shift+F)", app.open_smart_search)

        # ── Group 4: Transfer Controls (right side, hidden when inactive) ──
        self.transfer_group = ctk.CTkFrame(self, fg_color="transparent")
        self.transfer_group.pack(side="right", padx=(0, 10))

        self.pause_btn = self._btn(self.transfer_group, "⏸ Pause", "Pause/Resume transfer", app.pause_transfer, state="disabled")
        self.cancel_btn = self._btn(self.transfer_group, "✖ Cancel", "Cancel current transfer",  app.cancel_transfer,
                                    danger=True, state="disabled")

        # Bandwidth indicator
        self.bandwidth_label = ctk.CTkLabel(
            self.transfer_group, text="",
            font=ctk.CTkFont(size=10), text_color="gray",
        )
        self.bandwidth_label.pack(side="left", padx=(10, 0))

    def _btn(self, parent, text: str, tooltip: str, command, danger=False, state="normal"):
        """Create a toolbar button with text label and tooltip."""
        from s3_manager_pro_v5.ui.tooltip import Tooltip
        colors = DARK_THEME if self.app.is_dark else LIGHT_THEME
        fg = colors["danger"] if danger else colors["surface"]
        hover = colors["danger_hover"] if danger else colors["surface_hover"]

        # Auto width based on text
        width = max(70, len(text) * 8 + 16)

        btn = ctk.CTkButton(
            parent, text=text, width=width, height=30,
            corner_radius=6, font=ctk.CTkFont(size=11),
            fg_color=fg, hover_color=hover,
            text_color=colors["text_primary"],
            command=command, state=state,
        )
        btn.pack(side="left", padx=2)

        # Attach tooltip
        Tooltip(btn, tooltip)

        return btn

    def _separator(self):
        """Add a visual separator."""
        colors = DARK_THEME if self.app.is_dark else LIGHT_THEME
        sep = ctk.CTkFrame(self, width=1, height=24, fg_color=colors["border"])
        sep.pack(side="left", padx=8, pady=8)

    def set_transfer_active(self, active: bool):
        """Enable/disable transfer controls."""
        state = "normal" if active else "disabled"
        self.pause_btn.configure(state=state)
        self.cancel_btn.configure(state=state)

    def set_paused(self, paused: bool):
        self.pause_btn.configure(text="▶" if paused else "⏸")

    def update_selection_state(self, has_selection: bool):
        """Update button states based on selection."""
        state = "normal" if has_selection else "disabled"
        self.download_btn.configure(state=state)
        self.share_btn.configure(state=state)
        self.rename_btn.configure(state=state)
        self.move_btn.configure(state=state)
        self.delete_btn.configure(state=state)

    def apply_theme(self, colors: dict):
        """Apply theme to toolbar."""
        self.configure(fg_color=colors["header_bg"])

        for group in [self.file_group, self.edit_group, self.tools_group, self.transfer_group]:
            for child in group.winfo_children():
                if isinstance(child, ctk.CTkButton):
                    child.configure(
                        fg_color=colors["surface"],
                        hover_color=colors["surface_hover"],
                        text_color=colors["text_primary"],
                    )

        self.bandwidth_label.configure(text_color=colors["text_secondary"])
