"""Breadcrumb navigation bar — clickable path segments + search."""
import customtkinter as ctk


class BreadcrumbBar(ctk.CTkFrame):
    """Breadcrumb navigation with clickable path segments and search box."""

    def __init__(self, parent, app):
        super().__init__(parent, height=40, corner_radius=0)
        self.app = app
        self.pack_propagate(False)
        self._segments = []  # List of (text, prefix) tuples
        self._segment_widgets = []

        # Left side: breadcrumb path
        self.path_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.path_frame.pack(side="left", fill="x", expand=True, padx=(12, 5), pady=5)

        # Bookmark button (add current path to bookmarks)
        self.bookmark_btn = ctk.CTkButton(
            self, text="⭐", width=30, height=28, corner_radius=6,
            font=ctk.CTkFont(size=14),
            command=self.app.add_bookmark,
        )
        self.bookmark_btn.pack(side="right", padx=(0, 8))

        # Refresh button
        self.refresh_btn = ctk.CTkButton(
            self, text="🔄", width=30, height=28, corner_radius=6,
            font=ctk.CTkFont(size=14),
            command=self.app.refresh_listing,
        )
        self.refresh_btn.pack(side="right", padx=(0, 4))

        # Search box
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self._on_search_changed)
        self.search_entry = ctk.CTkEntry(
            self, textvariable=self.search_var,
            width=200, height=28, corner_radius=6,
            placeholder_text="🔍 Filter files...",
            font=ctk.CTkFont(size=11),
        )
        self.search_entry.pack(side="right", padx=(5, 4))

    def set_path(self, bucket: str, prefix: str):
        """Update breadcrumb path. E.g. bucket='my-bucket', prefix='folder1/folder2/'"""
        # Clear existing segments
        for widget in self._segment_widgets:
            widget.destroy()
        self._segment_widgets.clear()
        self._segments.clear()

        if not bucket:
            label = ctk.CTkLabel(
                self.path_frame, text="Select a bucket to begin",
                font=ctk.CTkFont(size=12), text_color="gray",
            )
            label.pack(side="left")
            self._segment_widgets.append(label)
            return

        # Bucket segment (always root)
        self._add_segment(f"🪣 {bucket}", bucket, "")

        # Path segments
        if prefix:
            parts = prefix.strip("/").split("/")
            accumulated = ""
            for part in parts:
                accumulated += part + "/"
                self._add_separator()
                self._add_segment(part, bucket, accumulated)

    def _add_segment(self, text: str, bucket: str, prefix: str):
        """Add a clickable breadcrumb segment."""
        btn = ctk.CTkButton(
            self.path_frame,
            text=text,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            height=26,
            corner_radius=4,
            command=lambda b=bucket, p=prefix: self.app.navigate_to(b, p),
        )
        btn.pack(side="left", padx=1)
        self._segment_widgets.append(btn)
        self._segments.append((text, prefix))

    def _add_separator(self):
        """Add a › separator between segments."""
        sep = ctk.CTkLabel(
            self.path_frame, text="›",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        sep.pack(side="left", padx=3)
        self._segment_widgets.append(sep)

    def _on_search_changed(self, *args):
        """Notify app of search filter change."""
        self.app.on_search_filter(self.search_var.get())

    def get_search_text(self) -> str:
        return self.search_var.get().strip()

    def clear_search(self):
        self.search_var.set("")

    def focus_search(self):
        """Focus the search entry."""
        self.search_entry.focus_set()

    def apply_theme(self, colors: dict):
        """Apply theme colors to breadcrumb bar."""
        self.configure(fg_color=colors["surface"])

        self.bookmark_btn.configure(
            fg_color=colors["badge_bg"],
            hover_color=colors["surface_hover"],
            text_color=colors["warning"],
        )
        self.refresh_btn.configure(
            fg_color=colors["badge_bg"],
            hover_color=colors["surface_hover"],
            text_color=colors["text_primary"],
        )
        self.search_entry.configure(
            fg_color=colors["bg"],
            text_color=colors["text_primary"],
            border_color=colors["border"],
        )

        # Style breadcrumb buttons
        for widget in self._segment_widgets:
            if isinstance(widget, ctk.CTkButton):
                widget.configure(
                    fg_color="transparent",
                    hover_color=colors["surface_hover"],
                    text_color=colors["primary"],
                )
            elif isinstance(widget, ctk.CTkLabel):
                widget.configure(text_color=colors["text_secondary"])
