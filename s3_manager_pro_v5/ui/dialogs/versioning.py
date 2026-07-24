"""File Versioning Viewer — list versions, restore previous versions."""
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME
from s3_manager_pro_v5.utils.formatting import format_size


class VersioningDialog:
    """View and restore file versions for a specific S3 object."""

    def __init__(self, parent, app, bucket: str, key: str):
        self.app = app
        self.bucket = bucket
        self.key = key
        self.versions = []

        colors = DARK_THEME if app.is_dark else LIGHT_THEME
        filename = key.split("/")[-1] if "/" in key else key

        self.win = ctk.CTkToplevel(parent)
        self.win.title(f"📜 Versions — {filename}")
        self.win.geometry("650x480")
        self.win.transient(parent)
        self.win.grab_set()
        self.win.resizable(True, True)
        self.win.configure(fg_color=colors["bg"])

        # Title
        ctk.CTkLabel(self.win, text="📜 File Version History",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=colors["text_primary"]).pack(pady=(15, 5))

        ctk.CTkLabel(self.win, text=f"File: {filename}",
                     font=ctk.CTkFont(size=12),
                     text_color=colors["text_secondary"]).pack(pady=(0, 10))

        # Version table
        self.tree_frame = ctk.CTkFrame(self.win, fg_color="transparent")
        self.tree_frame.pack(fill="both", expand=True, padx=15, pady=(0, 5))

        columns = ("version_id", "last_modified", "size", "is_latest", "is_delete_marker")
        self.tree = ttk.Treeview(self.tree_frame, columns=columns, show="headings", height=10)
        self.tree.heading("version_id", text="Version ID")
        self.tree.heading("last_modified", text="Modified")
        self.tree.heading("size", text="Size")
        self.tree.heading("is_latest", text="Latest")
        self.tree.heading("is_delete_marker", text="Delete Marker")

        self.tree.column("version_id", width=200, anchor="w")
        self.tree.column("last_modified", width=150, anchor="center")
        self.tree.column("size", width=90, anchor="e")
        self.tree.column("is_latest", width=60, anchor="center")
        self.tree.column("is_delete_marker", width=100, anchor="center")

        scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Theme treeview
        style = ttk.Style()
        style.configure("Treeview",
                        background=colors["bg"],
                        foreground=colors["text_primary"],
                        fieldbackground=colors["bg"])
        style.configure("Treeview.Heading",
                        background=colors["surface"],
                        foreground=colors["text_primary"])

        # Buttons
        btn_frame = ctk.CTkFrame(self.win, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=(5, 15))

        self.restore_btn = ctk.CTkButton(
            btn_frame, text="🔄 Restore Selected Version", width=190, height=34,
            corner_radius=8, font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=colors["primary"], hover_color=colors["primary_hover"],
            command=self._restore_version, state="disabled",
        )
        self.restore_btn.pack(side="left", padx=(0, 10))

        self.download_btn = ctk.CTkButton(
            btn_frame, text="⬇ Download Version", width=150, height=34,
            corner_radius=8, font=ctk.CTkFont(size=12),
            fg_color=colors["success"], hover_color="#1fa339",
            command=self._download_version, state="disabled",
        )
        self.download_btn.pack(side="left", padx=(0, 10))

        self.status_label = ctk.CTkLabel(btn_frame, text="Loading versions...",
                                         font=ctk.CTkFont(size=11),
                                         text_color=colors["text_secondary"])
        self.status_label.pack(side="left")

        ctk.CTkButton(btn_frame, text="Close", width=70, height=34,
                      corner_radius=8, fg_color=colors["badge_bg"],
                      hover_color=colors["surface_hover"],
                      text_color=colors["text_primary"],
                      command=self.win.destroy).pack(side="right")

        # Selection binding
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # Load versions
        self._load_versions()

    def _on_select(self, event):
        """Enable buttons when a version is selected."""
        sel = self.tree.selection()
        if sel:
            self.restore_btn.configure(state="normal")
            self.download_btn.configure(state="normal")
        else:
            self.restore_btn.configure(state="disabled")
            self.download_btn.configure(state="disabled")

    def _load_versions(self):
        """Load all versions of the object."""
        def do_load():
            try:
                response = self.app.s3_client.s3_client.list_object_versions(
                    Bucket=self.bucket, Prefix=self.key
                )

                versions = []
                for v in response.get("Versions", []):
                    if v["Key"] == self.key:
                        versions.append({
                            "version_id": v["VersionId"],
                            "last_modified": v["LastModified"].strftime("%Y-%m-%d %H:%M:%S"),
                            "size": v["Size"],
                            "is_latest": v["IsLatest"],
                            "is_delete_marker": False,
                        })

                for dm in response.get("DeleteMarkers", []):
                    if dm["Key"] == self.key:
                        versions.append({
                            "version_id": dm["VersionId"],
                            "last_modified": dm["LastModified"].strftime("%Y-%m-%d %H:%M:%S"),
                            "size": 0,
                            "is_latest": dm["IsLatest"],
                            "is_delete_marker": True,
                        })

                # Sort by date descending
                versions.sort(key=lambda x: x["last_modified"], reverse=True)
                self.versions = versions

                self.win.after(0, lambda: self._populate_tree(versions))

            except Exception as e:
                error_msg = str(e)
                if "NoSuchVersion" in error_msg or "not enabled" in error_msg.lower():
                    self.win.after(0, lambda: self.status_label.configure(
                        text="Versioning not enabled on this bucket", text_color="#f44336"
                    ))
                else:
                    self.win.after(0, lambda: self.status_label.configure(
                        text=f"Error: {error_msg[:50]}", text_color="#f44336"
                    ))

        threading.Thread(target=do_load, daemon=True).start()

    def _populate_tree(self, versions):
        """Populate the version tree."""
        self.tree.delete(*self.tree.get_children())

        for i, v in enumerate(versions):
            vid = v["version_id"]
            if len(vid) > 20:
                vid_display = vid[:10] + "..." + vid[-8:]
            else:
                vid_display = vid

            self.tree.insert("", "end", iid=str(i), values=(
                vid_display,
                v["last_modified"],
                format_size(v["size"]) if not v["is_delete_marker"] else "—",
                "✓" if v["is_latest"] else "",
                "🗑" if v["is_delete_marker"] else "",
            ))

        self.status_label.configure(
            text=f"Found {len(versions)} version(s)",
            text_color="#00c853" if versions else "#ff9800"
        )

    def _restore_version(self):
        """Restore selected version by copying it as the latest."""
        sel = self.tree.selection()
        if not sel:
            return

        idx = int(sel[0])
        version = self.versions[idx]

        if version["is_delete_marker"]:
            messagebox.showwarning("Cannot Restore",
                                   "Cannot restore a delete marker.",
                                   parent=self.win)
            return

        confirm = messagebox.askyesno(
            "Restore Version",
            f"Restore version from {version['last_modified']}?\n\n"
            f"This will copy this version as the new current version.",
            parent=self.win
        )
        if not confirm:
            return

        def do_restore():
            try:
                self.app.s3_client.s3_client.copy_object(
                    Bucket=self.bucket,
                    Key=self.key,
                    CopySource={
                        "Bucket": self.bucket,
                        "Key": self.key,
                        "VersionId": version["version_id"],
                    },
                )
                self.win.after(0, lambda: self.status_label.configure(
                    text="✓ Version restored successfully", text_color="#00c853"
                ))
                self.win.after(0, lambda: self.app.refresh_listing())
            except Exception as e:
                self.win.after(0, lambda: self.status_label.configure(
                    text=f"Restore failed: {str(e)[:40]}", text_color="#f44336"
                ))

        threading.Thread(target=do_restore, daemon=True).start()

    def _download_version(self):
        """Download a specific version of the file."""
        sel = self.tree.selection()
        if not sel:
            return

        idx = int(sel[0])
        version = self.versions[idx]

        if version["is_delete_marker"]:
            messagebox.showwarning("Cannot Download",
                                   "Cannot download a delete marker.",
                                   parent=self.win)
            return

        from tkinter import filedialog
        filename = self.key.split("/")[-1] if "/" in self.key else self.key
        name, ext = os.path.splitext(filename) if "." in filename else (filename, "")
        import os
        suggested = f"{name}_v{version['last_modified'][:10]}{ext}"

        filepath = filedialog.asksaveasfilename(
            parent=self.win,
            title="Save Version As",
            initialfile=suggested,
        )
        if not filepath:
            return

        def do_download():
            try:
                response = self.app.s3_client.s3_client.get_object(
                    Bucket=self.bucket,
                    Key=self.key,
                    VersionId=version["version_id"],
                )
                with open(filepath, "wb") as f:
                    for chunk in response["Body"].iter_chunks(8 * 1024 * 1024):
                        f.write(chunk)

                self.win.after(0, lambda: self.status_label.configure(
                    text=f"✓ Downloaded to {os.path.basename(filepath)}", text_color="#00c853"
                ))
            except Exception as e:
                self.win.after(0, lambda: self.status_label.configure(
                    text=f"Download failed: {str(e)[:40]}", text_color="#f44336"
                ))

        threading.Thread(target=do_download, daemon=True).start()
