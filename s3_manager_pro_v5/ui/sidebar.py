"""Sidebar — bucket tree, quick stats, bookmarks."""
import tkinter as tk
import customtkinter as ctk
from s3_manager_pro_v5.utils.formatting import format_size


class Sidebar(ctk.CTkFrame):
    """Left panel with bucket list, stats summary, and bookmarks."""

    def __init__(self, parent, app):
        super().__init__(parent, width=220, corner_radius=0)
        self.app = app
        self.pack_propagate(False)

        # ── BUCKETS Section ──
        self.buckets_header = ctk.CTkLabel(
            self, text="🪣 BUCKETS",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            anchor="w",
        )
        self.buckets_header.pack(fill="x", padx=12, pady=(12, 4))

        # Bucket listbox frame
        self.bucket_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.bucket_frame.pack(fill="both", expand=True, padx=8, pady=(0, 5))

        # Bucket list (using tkinter Listbox for scrollable list)
        self.bucket_listbox = tk.Listbox(
            self.bucket_frame,
            font=("Segoe UI", 10),
            selectmode="single",
            borderwidth=0,
            highlightthickness=0,
            activestyle="none",
        )
        self.bucket_listbox.pack(fill="both", expand=True)
        self.bucket_listbox.bind("<<ListboxSelect>>", self._on_bucket_select)
        self.bucket_listbox.bind("<Double-Button-1>", self._on_bucket_double_click)

        # ── Separator ──
        self.separator1 = ctk.CTkFrame(self, height=1)
        self.separator1.pack(fill="x", padx=12, pady=5)

        # ── QUICK STATS Section ──
        self.stats_header = ctk.CTkLabel(
            self, text="📊 QUICK STATS",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            anchor="w",
        )
        self.stats_header.pack(fill="x", padx=12, pady=(5, 4))

        self.stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.stats_frame.pack(fill="x", padx=12, pady=(0, 5))

        self.stat_objects = ctk.CTkLabel(
            self.stats_frame, text="Objects: —",
            font=ctk.CTkFont(size=11), anchor="w",
        )
        self.stat_objects.pack(fill="x")

        self.stat_size = ctk.CTkLabel(
            self.stats_frame, text="Size: —",
            font=ctk.CTkFont(size=11), anchor="w",
        )
        self.stat_size.pack(fill="x")

        self.stat_glacier = ctk.CTkLabel(
            self.stats_frame, text="Glacier: —",
            font=ctk.CTkFont(size=11), anchor="w",
        )
        self.stat_glacier.pack(fill="x")

        # ── Separator ──
        self.separator2 = ctk.CTkFrame(self, height=1)
        self.separator2.pack(fill="x", padx=12, pady=5)

        # ── BOOKMARKS Section ──
        self.bookmarks_header = ctk.CTkLabel(
            self, text="⭐ BOOKMARKS",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            anchor="w",
        )
        self.bookmarks_header.pack(fill="x", padx=12, pady=(5, 4))

        self.bookmarks_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.bookmarks_frame.pack(fill="x", padx=8, pady=(0, 10))

        self.bookmark_buttons = []
        self.no_bookmarks_label = ctk.CTkLabel(
            self.bookmarks_frame, text="No bookmarks yet",
            font=ctk.CTkFont(size=10), text_color="gray",
        )
        self.no_bookmarks_label.pack(anchor="w", padx=4)

    def set_buckets(self, bucket_names: list):
        """Populate the bucket list."""
        self.bucket_listbox.delete(0, tk.END)
        for name in bucket_names:
            self.bucket_listbox.insert(tk.END, f"  {name}")

    def get_selected_bucket(self) -> str:
        """Get currently selected bucket name."""
        selection = self.bucket_listbox.curselection()
        if selection:
            return self.bucket_listbox.get(selection[0]).strip()
        return ""

    def _on_bucket_select(self, event):
        """Handle single-click bucket selection."""
        bucket = self.get_selected_bucket()
        if bucket:
            self.app.on_bucket_selected(bucket)

    def _on_bucket_double_click(self, event):
        """Handle double-click to browse bucket."""
        bucket = self.get_selected_bucket()
        if bucket:
            self.app.on_bucket_navigate(bucket)

    def update_stats(self, total_objects: int, total_size: int, glacier_count: int):
        """Update the quick stats display."""
        self.stat_objects.configure(text=f"Objects: {total_objects:,}")
        self.stat_size.configure(text=f"Size: {format_size(total_size)}")
        if total_objects > 0:
            glacier_pct = (glacier_count / total_objects) * 100
            self.stat_glacier.configure(text=f"Glacier: {glacier_pct:.0f}%")
        else:
            self.stat_glacier.configure(text="Glacier: —")

    def clear_stats(self):
        """Clear stats display."""
        self.stat_objects.configure(text="Objects: —")
        self.stat_size.configure(text="Size: —")
        self.stat_glacier.configure(text="Glacier: —")

    def set_bookmarks(self, bookmarks: list):
        """Update bookmarks display."""
        # Clear existing
        for btn in self.bookmark_buttons:
            btn.destroy()
        self.bookmark_buttons.clear()

        if not bookmarks:
            self.no_bookmarks_label.pack(anchor="w", padx=4)
            return

        self.no_bookmarks_label.pack_forget()
        for i, bm in enumerate(bookmarks[:8]):  # Show max 8
            label = bm.get("label", f"{bm['bucket']}/{bm['prefix']}")
            btn = ctk.CTkButton(
                self.bookmarks_frame,
                text=f"📌 {label[:25]}",
                font=ctk.CTkFont(size=10),
                height=24,
                corner_radius=4,
                anchor="w",
                command=lambda b=bm: self.app.navigate_to_bookmark(b),
            )
            btn.pack(fill="x", padx=2, pady=1)
            self.bookmark_buttons.append(btn)

    def apply_theme(self, colors: dict):
        """Apply theme colors to sidebar."""
        self.configure(fg_color=colors["sidebar_bg"])
        self.buckets_header.configure(text_color=colors["text_primary"])
        self.stats_header.configure(text_color=colors["text_primary"])
        self.bookmarks_header.configure(text_color=colors["text_primary"])
        self.stat_objects.configure(text_color=colors["text_secondary"])
        self.stat_size.configure(text_color=colors["text_secondary"])
        self.stat_glacier.configure(text_color=colors["text_secondary"])
        self.separator1.configure(fg_color=colors["border"])
        self.separator2.configure(fg_color=colors["border"])
        self.no_bookmarks_label.configure(text_color=colors["text_secondary"])

        # Style the listbox
        self.bucket_listbox.configure(
            bg=colors["sidebar_bg"],
            fg=colors["text_primary"],
            selectbackground=colors["primary"],
            selectforeground="#ffffff",
        )

        for btn in self.bookmark_buttons:
            btn.configure(
                fg_color=colors["surface"],
                hover_color=colors["surface_hover"],
                text_color=colors["text_primary"],
            )
