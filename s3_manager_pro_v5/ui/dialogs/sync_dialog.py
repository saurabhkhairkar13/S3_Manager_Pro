"""S3 Sync Dialog — compare local ↔ S3, dry-run preview, execute sync."""
import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog
import customtkinter as ctk
from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME
from s3_manager_pro_v5.utils.formatting import format_size


class SyncDialog:
    """S3 Sync with dry-run preview showing what will upload/download/delete."""

    def __init__(self, parent, app, bucket: str, prefix: str):
        self.app = app
        self.bucket = bucket
        self.prefix = prefix
        self.sync_plan = []  # List of (action, path, size) tuples
        self._cancel = False

        colors = DARK_THEME if app.is_dark else LIGHT_THEME

        self.win = ctk.CTkToplevel(parent)
        self.win.title("📋 S3 Sync — Dry Run Preview")
        self.win.geometry("700x550")
        self.win.transient(parent)
        self.win.grab_set()
        self.win.resizable(True, True)
        self.win.configure(fg_color=colors["bg"])

        # Title
        ctk.CTkLabel(self.win, text="📋 S3 Sync",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=colors["text_primary"]).pack(pady=(15, 5))

        # Path config
        path_frame = ctk.CTkFrame(self.win, fg_color=colors["surface"], corner_radius=8)
        path_frame.pack(fill="x", padx=20, pady=(5, 10))

        # Local folder
        local_row = ctk.CTkFrame(path_frame, fg_color="transparent")
        local_row.pack(fill="x", padx=12, pady=(10, 5))
        ctk.CTkLabel(local_row, text="Local:", width=60,
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=colors["text_primary"]).pack(side="left")
        self.local_entry = ctk.CTkEntry(local_row, width=400, placeholder_text="Select local folder...")
        self.local_entry.pack(side="left", padx=(5, 5))
        ctk.CTkButton(local_row, text="Browse", width=70, height=28,
                      corner_radius=6, command=self._browse_local).pack(side="left")

        # Remote path (read-only display)
        remote_row = ctk.CTkFrame(path_frame, fg_color="transparent")
        remote_row.pack(fill="x", padx=12, pady=(0, 10))
        ctk.CTkLabel(remote_row, text="Remote:", width=60,
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=colors["text_primary"]).pack(side="left")
        ctk.CTkLabel(remote_row, text=f"s3://{bucket}/{prefix}",
                     font=ctk.CTkFont(size=12),
                     text_color=colors["primary"]).pack(side="left", padx=5)

        # Sync direction
        dir_frame = ctk.CTkFrame(path_frame, fg_color="transparent")
        dir_frame.pack(fill="x", padx=12, pady=(0, 10))
        ctk.CTkLabel(dir_frame, text="Direction:", width=60,
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=colors["text_primary"]).pack(side="left")
        self.direction_var = ctk.StringVar(value="upload")
        ctk.CTkRadioButton(dir_frame, text="Local → S3 (Upload)", variable=self.direction_var,
                           value="upload", text_color=colors["text_primary"]).pack(side="left", padx=(5, 15))
        ctk.CTkRadioButton(dir_frame, text="S3 → Local (Download)", variable=self.direction_var,
                           value="download", text_color=colors["text_primary"]).pack(side="left")

        # Options
        opts_frame = ctk.CTkFrame(path_frame, fg_color="transparent")
        opts_frame.pack(fill="x", padx=12, pady=(0, 10))
        self.delete_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(opts_frame, text="Delete files at destination not in source",
                        variable=self.delete_var,
                        text_color=colors["text_primary"]).pack(side="left")

        # Dry Run button
        btn_row = ctk.CTkFrame(self.win, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=5)

        self.dryrun_btn = ctk.CTkButton(
            btn_row, text="🔍 Dry Run (Preview)", width=160, height=34,
            corner_radius=8, font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=colors["primary"], hover_color=colors["primary_hover"],
            command=self._run_dry_run,
        )
        self.dryrun_btn.pack(side="left", padx=(0, 10))

        self.status_label = ctk.CTkLabel(btn_row, text="",
                                         font=ctk.CTkFont(size=11),
                                         text_color=colors["text_secondary"])
        self.status_label.pack(side="left")

        # Results table
        self.result_frame = ctk.CTkFrame(self.win, fg_color="transparent")
        self.result_frame.pack(fill="both", expand=True, padx=20, pady=(5, 5))

        columns = ("action", "path", "size")
        self.tree = ttk.Treeview(self.result_frame, columns=columns, show="headings", height=12)
        self.tree.heading("action", text="Action")
        self.tree.heading("path", text="File")
        self.tree.heading("size", text="Size")
        self.tree.column("action", width=100, anchor="center")
        self.tree.column("path", width=400, anchor="w")
        self.tree.column("size", width=100, anchor="e")

        scrollbar = ttk.Scrollbar(self.result_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Apply treeview theme
        style = ttk.Style()
        style.configure("Treeview",
                        background=colors["bg"],
                        foreground=colors["text_primary"],
                        fieldbackground=colors["bg"])
        style.configure("Treeview.Heading",
                        background=colors["surface"],
                        foreground=colors["text_primary"])

        # Summary + Execute
        self.summary_frame = ctk.CTkFrame(self.win, fg_color="transparent")
        self.summary_frame.pack(fill="x", padx=20, pady=(5, 15))

        self.summary_label = ctk.CTkLabel(self.summary_frame, text="Run dry-run to preview changes",
                                          font=ctk.CTkFont(size=12),
                                          text_color=colors["text_secondary"])
        self.summary_label.pack(side="left")

        self.execute_btn = ctk.CTkButton(
            self.summary_frame, text="▶ Execute Sync", width=130, height=34,
            corner_radius=8, font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=colors["success"], hover_color="#1fa339",
            command=self._execute_sync, state="disabled",
        )
        self.execute_btn.pack(side="right", padx=(10, 0))

        ctk.CTkButton(self.summary_frame, text="Cancel", width=80, height=34,
                      corner_radius=8, fg_color=colors["badge_bg"],
                      hover_color=colors["surface_hover"],
                      text_color=colors["text_primary"],
                      command=self.win.destroy).pack(side="right")

    def _browse_local(self):
        d = filedialog.askdirectory(parent=self.win)
        if d:
            self.local_entry.delete(0, "end")
            self.local_entry.insert(0, d)

    def _run_dry_run(self):
        """Compare local vs S3 and show what would be synced."""
        local_dir = self.local_entry.get().strip()
        if not local_dir:
            self.status_label.configure(text="Select a local folder first", text_color="#f44336")
            return
        if not os.path.isdir(local_dir):
            self.status_label.configure(text="Folder does not exist", text_color="#f44336")
            return

        self.dryrun_btn.configure(state="disabled")
        self.status_label.configure(text="Comparing...", text_color="#ff9800")
        self.tree.delete(*self.tree.get_children())
        self.sync_plan.clear()

        direction = self.direction_var.get()
        include_deletes = self.delete_var.get()

        def do_compare():
            try:
                # Get S3 objects
                s3_objects = {}
                result = self.app.s3_client.list_objects_page(
                    self.bucket, self.prefix, delimiter=""
                )
                for obj in result.objects:
                    relative = obj.key[len(self.prefix):] if obj.key.startswith(self.prefix) else obj.key
                    s3_objects[relative] = {"size": obj.size, "modified": obj.last_modified}

                while result.is_truncated:
                    result = self.app.s3_client.list_objects_page(
                        self.bucket, self.prefix, delimiter="",
                        continuation_token=result.continuation_token
                    )
                    for obj in result.objects:
                        relative = obj.key[len(self.prefix):] if obj.key.startswith(self.prefix) else obj.key
                        s3_objects[relative] = {"size": obj.size, "modified": obj.last_modified}

                # Get local files
                local_files = {}
                for root, dirs, files in os.walk(local_dir):
                    for f in files:
                        full_path = os.path.join(root, f)
                        relative = os.path.relpath(full_path, local_dir).replace(os.sep, "/")
                        local_files[relative] = {"size": os.path.getsize(full_path)}

                # Compare
                plan = []

                if direction == "upload":
                    # Files to upload (new or modified)
                    for rel, info in local_files.items():
                        if rel not in s3_objects:
                            plan.append(("⬆ UPLOAD (new)", rel, info["size"]))
                        elif info["size"] != s3_objects[rel]["size"]:
                            plan.append(("⬆ UPLOAD (mod)", rel, info["size"]))

                    # Files to delete from S3
                    if include_deletes:
                        for rel in s3_objects:
                            if rel not in local_files:
                                plan.append(("🗑 DELETE", rel, s3_objects[rel]["size"]))
                else:
                    # Files to download (new or modified)
                    for rel, info in s3_objects.items():
                        if rel not in local_files:
                            plan.append(("⬇ DOWNLOAD (new)", rel, info["size"]))
                        elif info["size"] != local_files[rel]["size"]:
                            plan.append(("⬇ DOWNLOAD (mod)", rel, info["size"]))

                    # Files to delete locally
                    if include_deletes:
                        for rel in local_files:
                            if rel not in s3_objects:
                                plan.append(("🗑 DELETE", rel, local_files[rel]["size"]))

                self.sync_plan = plan
                self.win.after(0, lambda: self._show_results(plan))

            except Exception as e:
                self.win.after(0, lambda: self.status_label.configure(
                    text=f"Error: {str(e)[:50]}", text_color="#f44336"
                ))
            finally:
                self.win.after(0, lambda: self.dryrun_btn.configure(state="normal"))

        threading.Thread(target=do_compare, daemon=True).start()

    def _show_results(self, plan):
        """Display the sync plan in the treeview."""
        self.tree.delete(*self.tree.get_children())

        upload_count = download_count = delete_count = 0
        total_transfer = 0

        for action, path, size in plan:
            self.tree.insert("", "end", values=(action, path, format_size(size)))
            if "UPLOAD" in action:
                upload_count += 1
                total_transfer += size
            elif "DOWNLOAD" in action:
                download_count += 1
                total_transfer += size
            elif "DELETE" in action:
                delete_count += 1

        parts = []
        if upload_count:
            parts.append(f"{upload_count} upload")
        if download_count:
            parts.append(f"{download_count} download")
        if delete_count:
            parts.append(f"{delete_count} delete")

        if parts:
            summary = f"{', '.join(parts)} │ Transfer: {format_size(total_transfer)}"
            self.summary_label.configure(text=summary, text_color="#00c853")
            self.execute_btn.configure(state="normal")
        else:
            self.summary_label.configure(text="✓ Already in sync — no changes needed", text_color="#00c853")

        self.status_label.configure(text=f"Found {len(plan)} changes", text_color="#00c853")

    def _execute_sync(self):
        """Execute the sync plan."""
        if not self.sync_plan:
            return

        from tkinter import messagebox
        confirm = messagebox.askyesno(
            "Confirm Sync",
            f"Execute {len(self.sync_plan)} operations?\n\nThis will modify files.",
            parent=self.win
        )
        if not confirm:
            return

        self.execute_btn.configure(state="disabled")
        self.dryrun_btn.configure(state="disabled")
        local_dir = self.local_entry.get().strip()
        direction = self.direction_var.get()

        def do_sync():
            success = 0
            failed = 0

            for action, rel_path, size in self.sync_plan:
                if self._cancel:
                    break

                try:
                    if "UPLOAD" in action:
                        local_path = os.path.join(local_dir, rel_path.replace("/", os.sep))
                        s3_key = self.prefix + rel_path
                        self.app.s3_client.s3_client.upload_file(local_path, self.bucket, s3_key)
                        success += 1

                    elif "DOWNLOAD" in action:
                        s3_key = self.prefix + rel_path
                        local_path = os.path.join(local_dir, rel_path.replace("/", os.sep))
                        os.makedirs(os.path.dirname(local_path), exist_ok=True)
                        self.app.s3_client.s3_client.download_file(self.bucket, s3_key, local_path)
                        success += 1

                    elif "DELETE" in action:
                        if direction == "upload":
                            # Delete from S3
                            s3_key = self.prefix + rel_path
                            self.app.s3_client.s3_client.delete_object(Bucket=self.bucket, Key=s3_key)
                        else:
                            # Delete local
                            local_path = os.path.join(local_dir, rel_path.replace("/", os.sep))
                            if os.path.exists(local_path):
                                os.remove(local_path)
                        success += 1

                except Exception as e:
                    failed += 1

                self.win.after(0, lambda s=success, f=failed: self.status_label.configure(
                    text=f"Progress: {s} done, {f} failed"
                ))

            self.win.after(0, lambda: self.status_label.configure(
                text=f"✓ Sync complete: {success} success, {failed} failed",
                text_color="#00c853"
            ))
            self.win.after(0, lambda: self.execute_btn.configure(state="disabled"))

        threading.Thread(target=do_sync, daemon=True).start()
