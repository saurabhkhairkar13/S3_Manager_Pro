"""Smart Search — search by filename/extension across ALL buckets."""
import threading
import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME
from s3_manager_pro_v5.utils.formatting import format_size, get_file_icon


class SmartSearchDialog:
    """Search files by name/extension across all buckets simultaneously."""

    def __init__(self, parent, app):
        self.app = app
        self._cancel = False
        self._results = []

        colors = DARK_THEME if app.is_dark else LIGHT_THEME

        self.win = ctk.CTkToplevel(parent)
        self.win.title("🔍 Smart Search — All Buckets")
        self.win.geometry("800x550")
        self.win.transient(parent)
        self.win.grab_set()
        self.win.resizable(True, True)
        self.win.configure(fg_color=colors["bg"])

        # Title
        ctk.CTkLabel(self.win, text="🔍 Search Across All Buckets",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=colors["text_primary"]).pack(pady=(15, 10))

        # Search input
        search_frame = ctk.CTkFrame(self.win, fg_color="transparent")
        search_frame.pack(fill="x", padx=20, pady=(0, 10))

        self.search_entry = ctk.CTkEntry(search_frame, width=450, height=36,
                                         placeholder_text="Enter filename, extension (.json), or pattern...",
                                         font=ctk.CTkFont(size=12))
        self.search_entry.pack(side="left", padx=(0, 8))
        self.search_entry.bind("<Return>", lambda e: self._start_search())

        self.search_btn = ctk.CTkButton(
            search_frame, text="🔍 Search", width=100, height=36,
            corner_radius=8, font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=colors["primary"], hover_color=colors["primary_hover"],
            command=self._start_search,
        )
        self.search_btn.pack(side="left", padx=(0, 8))

        self.cancel_btn = ctk.CTkButton(
            search_frame, text="Stop", width=60, height=36,
            corner_radius=8, fg_color=colors["danger"], hover_color=colors["danger_hover"],
            command=self._cancel_search, state="disabled",
        )
        self.cancel_btn.pack(side="left")

        # Options
        opts_frame = ctk.CTkFrame(self.win, fg_color="transparent")
        opts_frame.pack(fill="x", padx=20, pady=(0, 5))

        self.case_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(opts_frame, text="Case sensitive", variable=self.case_var,
                        text_color=colors["text_primary"],
                        font=ctk.CTkFont(size=11)).pack(side="left", padx=(0, 15))

        self.max_var = ctk.StringVar(value="100")
        ctk.CTkLabel(opts_frame, text="Max results:", font=ctk.CTkFont(size=11),
                     text_color=colors["text_secondary"]).pack(side="left")
        ctk.CTkEntry(opts_frame, textvariable=self.max_var, width=50, height=26).pack(side="left", padx=5)

        # Status
        self.status_label = ctk.CTkLabel(self.win, text="Enter search term and press Enter",
                                         font=ctk.CTkFont(size=11),
                                         text_color=colors["text_secondary"])
        self.status_label.pack(anchor="w", padx=20)

        # Results table
        tree_frame = ctk.CTkFrame(self.win, fg_color="transparent")
        tree_frame.pack(fill="both", expand=True, padx=20, pady=(5, 5))

        columns = ("icon", "filename", "bucket", "path", "size", "class")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15)
        self.tree.heading("icon", text="")
        self.tree.heading("filename", text="File")
        self.tree.heading("bucket", text="Bucket")
        self.tree.heading("path", text="Path")
        self.tree.heading("size", text="Size")
        self.tree.heading("class", text="Class")

        self.tree.column("icon", width=25, anchor="center", stretch=False)
        self.tree.column("filename", width=200, anchor="w")
        self.tree.column("bucket", width=120, anchor="w")
        self.tree.column("path", width=200, anchor="w")
        self.tree.column("size", width=80, anchor="e")
        self.tree.column("class", width=90, anchor="center")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Double-click to navigate
        self.tree.bind("<Double-Button-1>", self._on_double_click)

        # Style
        style = ttk.Style()
        style.configure("Treeview",
                        background=colors["bg"],
                        foreground=colors["text_primary"],
                        fieldbackground=colors["bg"])
        style.configure("Treeview.Heading",
                        background=colors["surface"],
                        foreground=colors["text_primary"])

        # Bottom
        btn_frame = ctk.CTkFrame(self.win, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(5, 15))

        ctk.CTkButton(btn_frame, text="📂 Navigate to Selected", width=160, height=32,
                      corner_radius=6, fg_color=colors["success"], hover_color="#1fa339",
                      command=self._navigate_to).pack(side="left", padx=(0, 10))

        ctk.CTkButton(btn_frame, text="Close", width=70, height=32,
                      corner_radius=6, fg_color=colors["badge_bg"],
                      hover_color=colors["surface_hover"],
                      text_color=colors["text_primary"],
                      command=self.win.destroy).pack(side="right")

    def _start_search(self):
        """Start searching across all buckets."""
        query = self.search_entry.get().strip()
        if not query:
            return

        self._cancel = False
        self._results.clear()
        self.tree.delete(*self.tree.get_children())
        self.search_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.status_label.configure(text="🔍 Searching...", text_color="#ff9800")

        max_results = int(self.max_var.get() or 100)
        case_sensitive = self.case_var.get()

        def do_search():
            buckets = self.app.s3_client.list_buckets()
            results_found = 0

            for bucket in buckets:
                if self._cancel or results_found >= max_results:
                    break

                self.win.after(0, lambda b=bucket: self.status_label.configure(
                    text=f"🔍 Searching: {b}... ({results_found} found)"
                ))

                try:
                    paginator = self.app.s3_client.s3_client.get_paginator("list_objects_v2")
                    for page in paginator.paginate(Bucket=bucket):
                        if self._cancel or results_found >= max_results:
                            break

                        for obj in page.get("Contents", []):
                            if self._cancel or results_found >= max_results:
                                break

                            key = obj["Key"]
                            filename = key.split("/")[-1] if "/" in key else key

                            # Match
                            match = False
                            if case_sensitive:
                                match = query in filename
                            else:
                                match = query.lower() in filename.lower()

                            if match:
                                result = {
                                    "bucket": bucket,
                                    "key": key,
                                    "filename": filename,
                                    "size": obj["Size"],
                                    "storage_class": obj.get("StorageClass", "STANDARD"),
                                }
                                self._results.append(result)
                                results_found += 1

                                self.win.after(0, lambda r=result: self._add_result(r))

                except Exception:
                    pass  # Skip buckets we can't access

            final_msg = f"✅ Search complete: {results_found} results found"
            if self._cancel:
                final_msg = f"⛔ Search stopped: {results_found} results found"

            self.win.after(0, lambda: self.status_label.configure(
                text=final_msg, text_color="#00c853"))
            self.win.after(0, lambda: self.search_btn.configure(state="normal"))
            self.win.after(0, lambda: self.cancel_btn.configure(state="disabled"))

        threading.Thread(target=do_search, daemon=True).start()

    def _add_result(self, result):
        """Add a search result to the tree."""
        icon = get_file_icon(result["filename"])
        path = result["key"].rsplit("/", 1)[0] + "/" if "/" in result["key"] else ""
        self.tree.insert("", "end", values=(
            icon,
            result["filename"],
            result["bucket"],
            path,
            format_size(result["size"]),
            result["storage_class"],
        ))

    def _cancel_search(self):
        self._cancel = True

    def _on_double_click(self, event):
        """Navigate to the selected result."""
        self._navigate_to()

    def _navigate_to(self):
        """Navigate to the bucket/prefix of selected result."""
        sel = self.tree.selection()
        if not sel:
            return

        idx = self.tree.index(sel[0])
        if idx < len(self._results):
            result = self._results[idx]
            prefix = result["key"].rsplit("/", 1)[0] + "/" if "/" in result["key"] else ""
            self.win.destroy()
            self.app.navigate_to(result["bucket"], prefix)
