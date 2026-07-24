"""Details Panel — Right-side panel showing file info, quick actions, and inline preview.

Shows contextual information based on what's selected:
- Single file: metadata, preview, quick actions
- Multiple files: selection summary, bulk actions
- Folder: size, contents count
- Nothing: bucket stats
"""
import threading
import customtkinter as ctk
from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME
from s3_manager_pro_v5.utils.formatting import format_size, get_file_icon, STORAGE_CLASS_INFO


class DetailsPanel(ctk.CTkFrame):
    """Right-side details/preview panel."""

    def __init__(self, parent, app):
        super().__init__(parent, width=260, corner_radius=0)
        self.app = app
        self.pack_propagate(False)
        self._current_obj = None

        colors = DARK_THEME if app.is_dark else LIGHT_THEME

        # Header
        self.header_label = ctk.CTkLabel(
            self, text="DETAILS",
            font=ctk.CTkFont(size=11, weight="bold"),
        )
        self.header_label.pack(fill="x", padx=12, pady=(10, 5))

        # Scrollable content
        self.content = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        # Show empty state
        self._show_empty()

    def _clear(self):
        """Clear all content."""
        for widget in self.content.winfo_children():
            widget.destroy()

    def _show_empty(self):
        """Show empty state when nothing is selected."""
        self._clear()
        colors = DARK_THEME if self.app.is_dark else LIGHT_THEME

        ctk.CTkLabel(self.content, text="📄",
                     font=ctk.CTkFont(size=32)).pack(pady=(30, 5))
        ctk.CTkLabel(self.content, text="Select a file\nto see details",
                     font=ctk.CTkFont(size=12),
                     text_color=colors["text_secondary"],
                     justify="center").pack()

    def show_file_details(self, obj):
        """Show details for a single file."""
        if obj == self._current_obj:
            return
        self._current_obj = obj
        self._clear()

        colors = DARK_THEME if self.app.is_dark else LIGHT_THEME
        filename = obj.key.split("/")[-1] if "/" in obj.key else obj.key
        icon = get_file_icon(filename)
        sc_info = STORAGE_CLASS_INFO.get(obj.storage_class, {"icon": "⚪", "label": obj.storage_class})

        # File icon + name
        ctk.CTkLabel(self.content, text=icon,
                     font=ctk.CTkFont(size=28)).pack(pady=(10, 3))

        ctk.CTkLabel(self.content, text=filename,
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=colors["text_primary"],
                     wraplength=230).pack(pady=(0, 10))

        # Info rows
        self._info_row("Size", format_size(obj.size))
        self._info_row("Class", f"{sc_info['icon']} {sc_info['label']}")
        self._info_row("Modified", obj.last_modified)
        if obj.etag:
            self._info_row("ETag", obj.etag[:16] + "...")

        # Status
        from s3_manager_pro_v5.utils.formatting import NON_GLACIER_CLASSES
        if obj.storage_class in NON_GLACIER_CLASSES:
            self._info_row("Status", "✅ Ready")
        else:
            self._info_row("Status", "🧊 Frozen")

        # Quick Actions
        ctk.CTkLabel(self.content, text="ACTIONS",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=colors["text_secondary"]).pack(anchor="w", padx=5, pady=(15, 5))

        self._action_btn("⬇ Download", self.app.download_selected, colors)
        self._action_btn("👁 Preview", self.app.open_file_preview, colors)
        self._action_btn("🔗 Share URL", self.app.copy_presigned_url, colors)
        self._action_btn("📝 Properties", self.app.show_properties, colors)
        self._action_btn("📜 Versions", self.app.open_versioning, colors)
        self._action_btn("🔀 Diff", self.app.open_diff_viewer, colors)

    def show_multi_selection(self, objects: list):
        """Show summary for multiple selected files."""
        self._current_obj = None
        self._clear()

        colors = DARK_THEME if self.app.is_dark else LIGHT_THEME
        total_size = sum(o.size for o in objects)

        ctk.CTkLabel(self.content, text="📦",
                     font=ctk.CTkFont(size=28)).pack(pady=(10, 3))

        ctk.CTkLabel(self.content, text=f"{len(objects)} files selected",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=colors["text_primary"]).pack(pady=(0, 5))

        self._info_row("Total Size", format_size(total_size))

        # Class breakdown
        classes = {}
        for o in objects:
            classes[o.storage_class] = classes.get(o.storage_class, 0) + 1
        for sc, count in classes.items():
            info = STORAGE_CLASS_INFO.get(sc, {"icon": "⚪"})
            self._info_row(f"{info['icon']} {sc}", f"{count} files")

        # Bulk Actions
        ctk.CTkLabel(self.content, text="BULK ACTIONS",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=colors["text_secondary"]).pack(anchor="w", padx=5, pady=(15, 5))

        self._action_btn("⬇ Download All", self.app.download_selected, colors)
        self._action_btn("📤 Copy/Move", self.app.open_cross_bucket_copy, colors)
        self._action_btn("✏️ Batch Rename", self.app.open_batch_rename, colors)
        self._action_btn("🏷️ Edit Tags", self.app.open_bulk_tag_editor, colors)
        self._action_btn("🔄 Change Class", self.app.change_storage_class, colors)
        self._action_btn("🗑 Delete", self.app.delete_selected, colors)

    def show_folder_details(self, obj):
        """Show details for a folder."""
        self._current_obj = obj
        self._clear()

        colors = DARK_THEME if self.app.is_dark else LIGHT_THEME
        folder_name = obj.key.rstrip("/").split("/")[-1]

        ctk.CTkLabel(self.content, text="📁",
                     font=ctk.CTkFont(size=28)).pack(pady=(10, 3))

        ctk.CTkLabel(self.content, text=folder_name,
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=colors["text_primary"]).pack(pady=(0, 10))

        # Actions
        ctk.CTkLabel(self.content, text="ACTIONS",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=colors["text_secondary"]).pack(anchor="w", padx=5, pady=(15, 5))

        self._action_btn("📂 Open", lambda: self.app.navigate_into_folder(obj.key), colors)
        self._action_btn("📁 Calculate Size", self.app.open_folder_size, colors)
        self._action_btn("⬇ Download Folder", self.app.download_selected, colors)

    def _info_row(self, label: str, value: str):
        """Add an info row."""
        colors = DARK_THEME if self.app.is_dark else LIGHT_THEME
        row = ctk.CTkFrame(self.content, fg_color="transparent")
        row.pack(fill="x", padx=5, pady=1)

        ctk.CTkLabel(row, text=label,
                     font=ctk.CTkFont(size=10),
                     text_color=colors["text_secondary"],
                     width=70, anchor="w").pack(side="left")
        ctk.CTkLabel(row, text=value,
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=colors["text_primary"],
                     anchor="w").pack(side="left", fill="x")

    def _action_btn(self, text: str, command, colors: dict):
        """Add a quick action button."""
        ctk.CTkButton(self.content, text=text, height=28, corner_radius=4,
                      font=ctk.CTkFont(size=11), anchor="w",
                      fg_color=colors["surface"], hover_color=colors["surface_hover"],
                      text_color=colors["text_primary"],
                      command=command).pack(fill="x", padx=5, pady=2)

    def apply_theme(self, colors: dict):
        """Apply theme to panel."""
        self.configure(fg_color=colors["sidebar_bg"])
        self.header_label.configure(text_color=colors["text_secondary"])
