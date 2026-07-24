"""Virtual/Paginated File Table with column sorting, selection, and storage class badges."""
import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from s3_manager_pro_v5.utils.formatting import (
    format_size, get_file_icon, STORAGE_CLASS_INFO, NON_GLACIER_CLASSES
)


class FileTable(ctk.CTkFrame):
    """Main file table with sortable columns, pagination, and selection."""

    def __init__(self, parent, app):
        super().__init__(parent, corner_radius=0)
        self.app = app
        self._all_objects = []  # All objects (unfiltered)
        self._display_objects = []  # Filtered + sorted objects
        self._selected_indices = set()
        self._sort_column = "filename"
        self._sort_reverse = False
        self._page = 0
        self._page_size = 200
        self._filter_text = ""

        # ── Top bar: file count + pagination ──
        self.info_bar = ctk.CTkFrame(self, height=32, fg_color="transparent")
        self.info_bar.pack(fill="x", padx=10, pady=(6, 2))

        self.file_count_label = ctk.CTkLabel(
            self.info_bar, text="No files loaded",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
        )
        self.file_count_label.pack(side="left")

        # Pagination controls
        self.page_frame = ctk.CTkFrame(self.info_bar, fg_color="transparent")
        self.page_frame.pack(side="right")

        self.prev_btn = ctk.CTkButton(
            self.page_frame, text="◀", width=28, height=24, corner_radius=4,
            command=self._prev_page,
        )
        self.prev_btn.pack(side="left", padx=2)

        self.page_label = ctk.CTkLabel(
            self.page_frame, text="Page 1",
            font=ctk.CTkFont(size=11),
        )
        self.page_label.pack(side="left", padx=5)

        self.next_btn = ctk.CTkButton(
            self.page_frame, text="▶", width=28, height=24, corner_radius=4,
            command=self._next_page,
        )
        self.next_btn.pack(side="left", padx=2)

        # Select all / Deselect all
        self.select_frame = ctk.CTkFrame(self.info_bar, fg_color="transparent")
        self.select_frame.pack(side="right", padx=(0, 15))

        self.select_all_btn = ctk.CTkButton(
            self.select_frame, text="Select All", width=75, height=24,
            corner_radius=4, font=ctk.CTkFont(size=10),
            command=self._select_all,
        )
        self.select_all_btn.pack(side="left", padx=2)

        self.deselect_btn = ctk.CTkButton(
            self.select_frame, text="Deselect", width=65, height=24,
            corner_radius=4, font=ctk.CTkFont(size=10),
            command=self._deselect_all,
        )
        self.deselect_btn.pack(side="left", padx=2)

        self.selected_label = ctk.CTkLabel(
            self.select_frame, text="0 selected",
            font=ctk.CTkFont(size=11), text_color="gray",
        )
        self.selected_label.pack(side="left", padx=(8, 0))

        # ── Treeview ──
        self.tree_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.tree_frame.pack(fill="both", expand=True, padx=8, pady=(0, 5))

        # Loading overlay (shown during listing)
        self._loading_frame = ctk.CTkFrame(self.tree_frame, fg_color="transparent")
        self._loading_visible = False
        self._spinner_angle = 0
        self._spinner_after_id = None

        self._loading_label = ctk.CTkLabel(
            self._loading_frame, text="",
            font=ctk.CTkFont(size=14),
        )
        self._loading_label.pack(expand=True)

        columns = ("select", "icon", "filename", "size", "storage", "modified", "status")
        self.tree = ttk.Treeview(
            self.tree_frame, columns=columns, show="headings", selectmode="extended"
        )

        # Define column headings (sortable)
        self.tree.heading("select", text="✓", command=lambda: self._toggle_all_page())
        self.tree.heading("icon", text="")
        self.tree.heading("filename", text="Name ↕", command=lambda: self._sort_by("filename"))
        self.tree.heading("size", text="Size ↕", command=lambda: self._sort_by("size"))
        self.tree.heading("storage", text="Class ↕", command=lambda: self._sort_by("storage"))
        self.tree.heading("modified", text="Modified ↕", command=lambda: self._sort_by("modified"))
        self.tree.heading("status", text="Status", command=lambda: self._sort_by("status"))

        # Column widths
        self.tree.column("select", width=35, anchor="center", stretch=False)
        self.tree.column("icon", width=30, anchor="center", stretch=False)
        self.tree.column("filename", width=350, anchor="w")
        self.tree.column("size", width=90, anchor="e")
        self.tree.column("storage", width=110, anchor="center")
        self.tree.column("modified", width=130, anchor="center")
        self.tree.column("status", width=90, anchor="center")

        # Scrollbars
        scrollbar_y = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar_y.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar_y.pack(side="right", fill="y")

        # Bindings
        self.tree.bind("<ButtonRelease-1>", self._on_click)
        self.tree.bind("<Double-Button-1>", self._on_double_click)
        self.tree.bind("<Button-3>", self._on_right_click)

        # Keyboard navigation
        self.tree.bind("<space>", self._on_space_key)
        self.tree.bind("<Return>", self._on_enter_key)
        self.tree.bind("<Up>", self._on_arrow_key)
        self.tree.bind("<Down>", self._on_arrow_key)

        # Context menu — concise with "More Actions" submenu
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="⬇ Download", command=lambda: self.app.download_selected())
        self.context_menu.add_command(label="👁 Preview", command=lambda: self.app.open_file_preview())
        self.context_menu.add_command(label="🔗 Share URL", command=lambda: self.app.copy_presigned_url())
        self.context_menu.add_command(label="📋 Copy Path", command=lambda: self.app.copy_s3_path())
        self.context_menu.add_separator()
        self.context_menu.add_command(label="📝 Properties", command=lambda: self.app.show_properties())
        self.context_menu.add_command(label="🗑 Delete", command=lambda: self.app.delete_selected())
        self.context_menu.add_separator()

        # "More Actions" submenu
        more_menu = tk.Menu(self.context_menu, tearoff=0)
        more_menu.add_command(label="🌐 URL Formats", command=lambda: self.app.open_url_customizer())
        more_menu.add_command(label="📜 View Versions", command=lambda: self.app.open_versioning())
        more_menu.add_command(label="🔀 Compare Versions", command=lambda: self.app.open_diff_viewer())
        more_menu.add_command(label="🔒 Object Lock", command=lambda: self.app.open_object_lock())
        more_menu.add_separator()
        more_menu.add_command(label="🏷️ Edit Tags", command=lambda: self.app.open_bulk_tag_editor())
        more_menu.add_command(label="🔄 Change Storage Class", command=lambda: self.app.change_storage_class())
        more_menu.add_command(label="✏️ Batch Rename", command=lambda: self.app.open_batch_rename())
        more_menu.add_command(label="📤 Copy/Move to Bucket", command=lambda: self.app.open_cross_bucket_copy())
        more_menu.add_command(label="📁 Calculate Folder Size", command=lambda: self.app.open_folder_size())
        more_menu.add_separator()
        more_menu.add_command(label="📊 Analytics", command=lambda: self.app.open_analytics())
        more_menu.add_command(label="💡 Cost Advisor", command=lambda: self.app.open_cost_advisor())
        more_menu.add_command(label="📊 Export to CSV", command=lambda: self.app.export_csv())
        self.context_menu.add_cascade(label="More Actions  ▸", menu=more_menu)

    def show_loading(self, message: str = "Loading..."):
        """Show loading spinner overlay on the file table."""
        if self._loading_visible:
            return
        self._loading_visible = True
        self._loading_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._loading_frame.lift()
        self._animate_spinner(message)

    def hide_loading(self):
        """Hide the loading spinner."""
        self._loading_visible = False
        if self._spinner_after_id:
            self.after_cancel(self._spinner_after_id)
            self._spinner_after_id = None
        self._loading_frame.place_forget()

    def _animate_spinner(self, message: str):
        """Animate the loading spinner text."""
        if not self._loading_visible:
            return
        spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self._spinner_angle = (self._spinner_angle + 1) % len(spinner_chars)
        char = spinner_chars[self._spinner_angle]
        self._loading_label.configure(text=f"{char}  {message}")
        self._spinner_after_id = self.after(100, lambda: self._animate_spinner(message))

    def set_objects(self, objects: list):
        """Set all objects and refresh display."""
        self.hide_loading()
        self._all_objects = objects
        self._selected_indices = set()
        self._page = 0
        self._apply_filter_and_sort()

    def add_objects(self, objects: list):
        """Append more objects (for lazy loading)."""
        self._all_objects.extend(objects)
        self._apply_filter_and_sort()

    def set_filter(self, text: str):
        """Update the search filter and refresh."""
        self._filter_text = text.strip().lower()
        self._page = 0
        self._apply_filter_and_sort()

    def _apply_filter_and_sort(self):
        """Filter, sort, and render current page."""
        # Filter
        if self._filter_text:
            self._display_objects = [
                obj for obj in self._all_objects
                if self._filter_text in self._get_display_name(obj).lower()
            ]
        else:
            self._display_objects = list(self._all_objects)

        # Sort
        self._apply_sort()

        # Render
        self._render_page()

    def _apply_sort(self):
        """Sort display objects by current sort column."""
        key_fn = None
        if self._sort_column == "filename":
            key_fn = lambda o: (not o.is_folder, self._get_display_name(o).lower())
        elif self._sort_column == "size":
            key_fn = lambda o: (not o.is_folder, o.size)
        elif self._sort_column == "storage":
            key_fn = lambda o: (not o.is_folder, o.storage_class)
        elif self._sort_column == "modified":
            key_fn = lambda o: (not o.is_folder, o.last_modified)
        elif self._sort_column == "status":
            key_fn = lambda o: (not o.is_folder, self._get_status(o))

        if key_fn:
            self._display_objects.sort(key=key_fn, reverse=self._sort_reverse)

    def _sort_by(self, column: str):
        """Handle column header click for sorting."""
        if self._sort_column == column:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_column = column
            self._sort_reverse = False

        # Update column headers to show sort direction
        arrow = "↓" if self._sort_reverse else "↑"
        for col in ("filename", "size", "storage", "modified", "status"):
            text = col.capitalize()
            if col == "filename":
                text = "Name"
            if col == self._sort_column:
                self.tree.heading(col, text=f"{text} {arrow}")
            else:
                self.tree.heading(col, text=f"{text} ↕")

        self._apply_filter_and_sort()

    def _render_page(self):
        """Render the current page of objects into the treeview."""
        self.tree.delete(*self.tree.get_children())

        total = len(self._display_objects)

        # Empty state
        if total == 0 and not self._filter_text:
            if len(self._all_objects) == 0:
                # No objects loaded at all
                self.tree.insert("", "end", iid="empty", values=(
                    "", "", "No files here. Upload files to get started.", "", "", "", ""
                ))
                self.file_count_label.configure(text="Empty — upload files or select a different bucket")
                self.page_label.configure(text="")
                return

        if total == 0 and self._filter_text:
            self.tree.insert("", "end", iid="empty", values=(
                "", "", f"No files matching '{self._filter_text}'", "", "", "", ""
            ))
            self.file_count_label.configure(text=f"No results for '{self._filter_text}'")
            return

        start = self._page * self._page_size
        end = min(start + self._page_size, total)
        page_objects = self._display_objects[start:end]

        for i, obj in enumerate(page_objects):
            global_idx = start + i
            name = self._get_display_name(obj)
            icon = "📁" if obj.is_folder else get_file_icon(name)
            size_str = "—" if obj.is_folder else format_size(obj.size)
            storage = "" if obj.is_folder else self._get_storage_display(obj.storage_class)
            modified = obj.last_modified if obj.last_modified else "—"
            status = "—" if obj.is_folder else self._get_status(obj)
            selected = "☑" if global_idx in self._selected_indices else "☐"

            # Row tag for styling
            if obj.is_folder:
                tag = "folder"
            elif obj.storage_class in ("GLACIER", "DEEP_ARCHIVE"):
                tag = "glacier"
            elif i % 2 == 0:
                tag = "even"
            else:
                tag = "odd"

            self.tree.insert(
                "", "end", iid=str(global_idx),
                values=(selected, icon, name, size_str, storage, modified, status),
                tags=(tag,),
            )

        # Update labels
        total_size = sum(o.size for o in self._all_objects if not o.is_folder)
        folders = sum(1 for o in self._display_objects if o.is_folder)
        files = total - folders

        if self._filter_text:
            self.file_count_label.configure(
                text=f"Showing {total:,} of {len(self._all_objects):,} ({format_size(total_size)})"
            )
        else:
            self.file_count_label.configure(
                text=f"{folders} folders, {files:,} files ({format_size(total_size)})"
            )

        # Pagination label
        total_pages = max(1, (total + self._page_size - 1) // self._page_size)
        self.page_label.configure(text=f"Page {self._page + 1}/{total_pages}")

        # Enable/disable pagination buttons
        self.prev_btn.configure(state="normal" if self._page > 0 else "disabled")
        self.next_btn.configure(state="normal" if end < total else "disabled")

        self._update_selection_label()

    def _get_display_name(self, obj) -> str:
        """Get display name from full key."""
        if obj.is_folder:
            return obj.key.rstrip("/").split("/")[-1] + "/"
        return obj.key.split("/")[-1] if "/" in obj.key else obj.key

    def _get_storage_display(self, storage_class: str) -> str:
        """Get storage class display with icon."""
        info = STORAGE_CLASS_INFO.get(storage_class, {"icon": "⚪", "label": storage_class})
        return f"{info['icon']} {info['label']}"

    def _get_status(self, obj) -> str:
        """Get status string for an object."""
        if obj.storage_class in NON_GLACIER_CLASSES:
            return "Ready"
        return "Frozen"

    # ── Events ──

    def _on_click(self, event):
        """Handle click — toggle selection on checkbox column, update details panel."""
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return

        col = self.tree.identify_column(event.x)
        item = self.tree.identify_row(event.y)
        if not item:
            return

        # Column #1 = select checkbox
        if col == "#1":
            idx = int(item)
            if idx in self._selected_indices:
                self._selected_indices.discard(idx)
                self.tree.set(item, "select", "☐")
            else:
                self._selected_indices.add(idx)
                self.tree.set(item, "select", "☑")
            self._update_selection_label()

        # Update details panel with clicked item
        idx = int(item)
        if idx < len(self._display_objects):
            obj = self._display_objects[idx]
            self._notify_details_panel(obj)

    def _on_double_click(self, event):
        """Handle double-click — navigate into folder."""
        item = self.tree.identify_row(event.y)
        if not item:
            return
        idx = int(item)
        if idx < len(self._display_objects):
            obj = self._display_objects[idx]
            if obj.is_folder:
                self.app.navigate_into_folder(obj.key)

    def _on_right_click(self, event):
        """Show context menu."""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            # Also select it
            idx = int(item)
            self._selected_indices.add(idx)
            self.tree.set(item, "select", "☑")
            self._update_selection_label()
            self.context_menu.post(event.x_root, event.y_root)

    def _on_space_key(self, event):
        """Toggle selection on focused item with Space key."""
        selected = self.tree.selection()
        if selected:
            for item in selected:
                idx = int(item)
                if idx in self._selected_indices:
                    self._selected_indices.discard(idx)
                    self.tree.set(item, "select", "☐")
                else:
                    self._selected_indices.add(idx)
                    self.tree.set(item, "select", "☑")
            self._update_selection_label()
        return "break"

    def _on_enter_key(self, event):
        """Open folder or download file on Enter key."""
        selected = self.tree.selection()
        if selected:
            idx = int(selected[0])
            if idx < len(self._display_objects):
                obj = self._display_objects[idx]
                if obj.is_folder:
                    self.app.navigate_into_folder(obj.key)
                else:
                    self.app.download_selected()
        return "break"

    def _on_arrow_key(self, event):
        """Handle arrow key navigation — ensure focus stays in tree."""
        # Default treeview handles Up/Down, just make sure we update selection label
        self.tree.after(50, self._update_selection_label)

    def focus_table(self):
        """Focus the treeview for keyboard navigation."""
        self.tree.focus_set()
        children = self.tree.get_children()
        if children:
            self.tree.selection_set(children[0])
            self.tree.focus(children[0])

    def _toggle_all_page(self):
        """Toggle select all on current page."""
        start = self._page * self._page_size
        end = min(start + self._page_size, len(self._display_objects))

        # Check if all on page are selected
        page_indices = set(range(start, end))
        all_selected = page_indices.issubset(self._selected_indices)

        if all_selected:
            self._selected_indices -= page_indices
            for item in self.tree.get_children():
                self.tree.set(item, "select", "☐")
        else:
            self._selected_indices |= page_indices
            for item in self.tree.get_children():
                self.tree.set(item, "select", "☑")

        self._update_selection_label()

    def _select_all(self):
        """Select all objects (all pages)."""
        self._selected_indices = set(
            i for i, o in enumerate(self._display_objects) if not o.is_folder
        )
        # Update visible checkmarks
        for item in self.tree.get_children():
            idx = int(item)
            obj = self._display_objects[idx]
            if not obj.is_folder:
                self.tree.set(item, "select", "☑")
        self._update_selection_label()

    def _deselect_all(self):
        """Deselect all."""
        self._selected_indices.clear()
        for item in self.tree.get_children():
            self.tree.set(item, "select", "☐")
        self._update_selection_label()

    def _update_selection_label(self):
        """Update the '3 selected (4.2 MB)' label."""
        selected_objects = self.get_selected_objects()
        total_size = sum(o.size for o in selected_objects)
        self.selected_label.configure(
            text=f"{len(selected_objects)} selected ({format_size(total_size)})"
        )

        # Update details panel for multi-selection
        if len(selected_objects) > 1:
            if hasattr(self.app, 'details_panel'):
                self.app.details_panel.show_multi_selection(selected_objects)

        # Update status bar selection count
        if hasattr(self.app, 'status_bar'):
            self.app.status_bar.set_selection(len(selected_objects), total_size)

    def _notify_details_panel(self, obj):
        """Notify the details panel about a clicked object."""
        if not hasattr(self.app, 'details_panel'):
            return

        selected = self.get_selected_objects()
        if len(selected) > 1:
            self.app.details_panel.show_multi_selection(selected)
        elif obj.is_folder:
            self.app.details_panel.show_folder_details(obj)
        else:
            self.app.details_panel.show_file_details(obj)

    def get_selected_objects(self) -> list:
        """Get list of selected S3Object instances."""
        selected = []
        for idx in sorted(self._selected_indices):
            if idx < len(self._display_objects):
                obj = self._display_objects[idx]
                if not obj.is_folder:
                    selected.append(obj)
        return selected

    def get_focused_object(self):
        """Get the object under cursor/selection."""
        selected = self.tree.selection()
        if selected:
            idx = int(selected[0])
            if idx < len(self._display_objects):
                return self._display_objects[idx]
        return None

    # ── Pagination ──

    def _prev_page(self):
        if self._page > 0:
            self._page -= 1
            self._render_page()

    def _next_page(self):
        total_pages = (len(self._display_objects) + self._page_size - 1) // self._page_size
        if self._page < total_pages - 1:
            self._page += 1
            self._render_page()

    # ── Theme ──

    def apply_theme(self, colors: dict):
        """Apply theme to the file table."""
        self.configure(fg_color=colors["bg"])
        self.file_count_label.configure(text_color=colors["text_primary"])
        self.page_label.configure(text_color=colors["text_secondary"])
        self.selected_label.configure(text_color=colors["text_secondary"])

        self.prev_btn.configure(
            fg_color=colors["surface"], hover_color=colors["surface_hover"],
            text_color=colors["text_primary"],
        )
        self.next_btn.configure(
            fg_color=colors["surface"], hover_color=colors["surface_hover"],
            text_color=colors["text_primary"],
        )
        self.select_all_btn.configure(
            fg_color=colors["surface"], hover_color=colors["surface_hover"],
            text_color=colors["text_primary"],
        )
        self.deselect_btn.configure(
            fg_color=colors["surface"], hover_color=colors["surface_hover"],
            text_color=colors["text_primary"],
        )

        # Style ttk Treeview
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("Treeview",
                        background=colors["bg"],
                        foreground=colors["text_primary"],
                        fieldbackground=colors["bg"],
                        borderwidth=0,
                        font=("Segoe UI", 10))
        style.configure("Treeview.Heading",
                        background=colors["surface"],
                        foreground=colors["text_primary"],
                        font=("Segoe UI", 10, "bold"),
                        borderwidth=0)
        style.map("Treeview",
                  background=[("selected", colors["primary"])],
                  foreground=[("selected", "#ffffff")])
        style.map("Treeview.Heading",
                  background=[("active", colors["surface_hover"])])

        # Row tag colors (alternating + folder + glacier)
        self.tree.tag_configure("even", background=colors["bg"])
        self.tree.tag_configure("odd", background=colors["surface"])
        self.tree.tag_configure("folder", background=colors["surface"], font=("Segoe UI", 10, "bold"))
        self.tree.tag_configure("glacier", background="#1a237e" if self.app.is_dark else "#e3f2fd")

        # Scrollbar styling
        style.configure("Vertical.TScrollbar",
                        background=colors["surface"],
                        troughcolor=colors["bg"],
                        borderwidth=0,
                        arrowcolor=colors["text_secondary"])
