"""Bulk Tag Editor — add/remove/edit tags on multiple S3 objects."""
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME


class BulkTagEditorDialog:
    """Edit tags on multiple S3 objects at once."""

    def __init__(self, parent, app, bucket: str, objects: list):
        self.app = app
        self.bucket = bucket
        self.objects = objects
        self.tags_to_add = []
        self.tags_to_remove = []

        colors = DARK_THEME if app.is_dark else LIGHT_THEME

        self.win = ctk.CTkToplevel(parent)
        self.win.title("🏷️ Bulk Tag Editor")
        self.win.geometry("580x520")
        self.win.transient(parent)
        self.win.grab_set()
        self.win.resizable(False, True)
        self.win.configure(fg_color=colors["bg"])

        # Title
        ctk.CTkLabel(self.win, text="🏷️ Bulk Tag Editor",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=colors["text_primary"]).pack(pady=(15, 5))

        ctk.CTkLabel(self.win, text=f"Apply tags to {len(objects)} selected objects",
                     font=ctk.CTkFont(size=12),
                     text_color=colors["text_secondary"]).pack(pady=(0, 15))

        form = ctk.CTkFrame(self.win, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=20)

        # ── Add Tags Section ──
        ctk.CTkLabel(form, text="Add Tags:",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=colors["text_primary"]).pack(anchor="w", pady=(0, 5))

        # Tag input row
        add_row = ctk.CTkFrame(form, fg_color="transparent")
        add_row.pack(fill="x", pady=(0, 5))

        ctk.CTkLabel(add_row, text="Key:", font=ctk.CTkFont(size=11),
                     text_color=colors["text_secondary"]).pack(side="left")
        self.key_entry = ctk.CTkEntry(add_row, width=150, height=28, placeholder_text="tag-key")
        self.key_entry.pack(side="left", padx=(5, 10))

        ctk.CTkLabel(add_row, text="Value:", font=ctk.CTkFont(size=11),
                     text_color=colors["text_secondary"]).pack(side="left")
        self.value_entry = ctk.CTkEntry(add_row, width=150, height=28, placeholder_text="tag-value")
        self.value_entry.pack(side="left", padx=(5, 10))

        ctk.CTkButton(add_row, text="+ Add", width=60, height=28,
                      corner_radius=4, fg_color=colors["success"], hover_color="#1fa339",
                      command=self._add_tag).pack(side="left")

        # Tags list
        self.tags_frame = ctk.CTkFrame(form, fg_color=colors["surface"], corner_radius=8, height=120)
        self.tags_frame.pack(fill="x", pady=(5, 10))

        self.tags_list = ctk.CTkScrollableFrame(self.tags_frame, fg_color="transparent", height=100)
        self.tags_list.pack(fill="both", expand=True, padx=5, pady=5)

        self.no_tags_label = ctk.CTkLabel(self.tags_list, text="No tags added yet. Add tags above.",
                                          font=ctk.CTkFont(size=11),
                                          text_color=colors["text_secondary"])
        self.no_tags_label.pack(pady=10)

        # ── Remove Tags Section ──
        ctk.CTkLabel(form, text="Remove Tags (by key):",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=colors["text_primary"]).pack(anchor="w", pady=(10, 5))

        remove_row = ctk.CTkFrame(form, fg_color="transparent")
        remove_row.pack(fill="x", pady=(0, 5))

        self.remove_key_entry = ctk.CTkEntry(remove_row, width=200, height=28,
                                             placeholder_text="Key to remove")
        self.remove_key_entry.pack(side="left", padx=(0, 10))

        ctk.CTkButton(remove_row, text="+ Remove This Key", width=130, height=28,
                      corner_radius=4, fg_color=colors["danger"], hover_color=colors["danger_hover"],
                      command=self._add_remove_tag).pack(side="left")

        # Remove list
        self.remove_list_frame = ctk.CTkFrame(form, fg_color="transparent")
        self.remove_list_frame.pack(fill="x", pady=(5, 10))

        # ── Common Tags Presets ──
        ctk.CTkLabel(form, text="Quick Presets:",
                     font=ctk.CTkFont(size=11),
                     text_color=colors["text_secondary"]).pack(anchor="w", pady=(5, 3))

        preset_frame = ctk.CTkFrame(form, fg_color="transparent")
        preset_frame.pack(fill="x")

        presets = [
            ("Environment=production", "Environment", "production"),
            ("Environment=development", "Environment", "development"),
            ("Backup=true", "Backup", "true"),
            ("Archive=true", "Archive", "true"),
            ("Project=main", "Project", "main"),
        ]

        for label, key, value in presets:
            ctk.CTkButton(preset_frame, text=label, height=24, corner_radius=4,
                          font=ctk.CTkFont(size=10),
                          fg_color=colors["badge_bg"], hover_color=colors["surface_hover"],
                          text_color=colors["text_primary"],
                          command=lambda k=key, v=value: self._quick_add(k, v)).pack(side="left", padx=2, pady=2)

        # ── Apply Button ──
        btn_frame = ctk.CTkFrame(form, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(15, 5))

        self.apply_btn = ctk.CTkButton(
            btn_frame, text="⚡ Apply Tags to All Selected", width=220, height=36,
            corner_radius=8, font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=colors["primary"], hover_color=colors["primary_hover"],
            command=self._apply_tags,
        )
        self.apply_btn.pack(side="left", padx=(0, 10))

        self.status_label = ctk.CTkLabel(btn_frame, text="",
                                         font=ctk.CTkFont(size=11))
        self.status_label.pack(side="left")

        ctk.CTkButton(btn_frame, text="Close", width=70, height=36,
                      corner_radius=8, fg_color=colors["badge_bg"],
                      hover_color=colors["surface_hover"],
                      text_color=colors["text_primary"],
                      command=self.win.destroy).pack(side="right")

    def _add_tag(self):
        """Add a tag to the list."""
        key = self.key_entry.get().strip()
        value = self.value_entry.get().strip()
        if not key:
            return

        self.tags_to_add.append({"Key": key, "Value": value})
        self._refresh_tag_list()
        self.key_entry.delete(0, "end")
        self.value_entry.delete(0, "end")

    def _quick_add(self, key: str, value: str):
        """Quick-add a preset tag."""
        self.tags_to_add.append({"Key": key, "Value": value})
        self._refresh_tag_list()

    def _add_remove_tag(self):
        """Add a key to remove list."""
        key = self.remove_key_entry.get().strip()
        if not key or key in self.tags_to_remove:
            return
        self.tags_to_remove.append(key)
        self.remove_key_entry.delete(0, "end")
        self._refresh_remove_list()

    def _refresh_tag_list(self):
        """Refresh the tags-to-add display."""
        for widget in self.tags_list.winfo_children():
            widget.destroy()

        colors = DARK_THEME if self.app.is_dark else LIGHT_THEME

        if not self.tags_to_add:
            ctk.CTkLabel(self.tags_list, text="No tags added yet.",
                         font=ctk.CTkFont(size=11),
                         text_color=colors["text_secondary"]).pack(pady=10)
            return

        for i, tag in enumerate(self.tags_to_add):
            row = ctk.CTkFrame(self.tags_list, fg_color="transparent")
            row.pack(fill="x", pady=1)

            ctk.CTkLabel(row, text=f"🏷️ {tag['Key']} = {tag['Value']}",
                         font=ctk.CTkFont(size=11),
                         text_color=colors["text_primary"]).pack(side="left")

            ctk.CTkButton(row, text="✕", width=22, height=22, corner_radius=4,
                          fg_color=colors["danger"], hover_color=colors["danger_hover"],
                          font=ctk.CTkFont(size=10),
                          command=lambda idx=i: self._remove_add_tag(idx)).pack(side="right")

    def _remove_add_tag(self, index: int):
        if 0 <= index < len(self.tags_to_add):
            self.tags_to_add.pop(index)
            self._refresh_tag_list()

    def _refresh_remove_list(self):
        """Refresh remove keys display."""
        for widget in self.remove_list_frame.winfo_children():
            widget.destroy()

        colors = DARK_THEME if self.app.is_dark else LIGHT_THEME
        for key in self.tags_to_remove:
            ctk.CTkLabel(self.remove_list_frame, text=f"❌ Remove: {key}",
                         font=ctk.CTkFont(size=11),
                         text_color=colors["danger"]).pack(anchor="w")

    def _apply_tags(self):
        """Apply tag changes to all selected objects."""
        if not self.tags_to_add and not self.tags_to_remove:
            messagebox.showinfo("Tags", "No tags to add or remove.", parent=self.win)
            return

        self.apply_btn.configure(state="disabled")
        self.status_label.configure(text="⏳ Applying tags...", text_color="#ff9800")

        def do_apply():
            success = 0
            failed = 0

            for obj in self.objects:
                try:
                    # Get existing tags
                    try:
                        resp = self.app.s3_client.s3_client.get_object_tagging(
                            Bucket=self.bucket, Key=obj.key
                        )
                        existing_tags = {t["Key"]: t["Value"] for t in resp.get("TagSet", [])}
                    except Exception:
                        existing_tags = {}

                    # Remove specified keys
                    for key in self.tags_to_remove:
                        existing_tags.pop(key, None)

                    # Add new tags
                    for tag in self.tags_to_add:
                        existing_tags[tag["Key"]] = tag["Value"]

                    # Put updated tags
                    tag_set = [{"Key": k, "Value": v} for k, v in existing_tags.items()]
                    self.app.s3_client.s3_client.put_object_tagging(
                        Bucket=self.bucket,
                        Key=obj.key,
                        Tagging={"TagSet": tag_set}
                    )
                    success += 1

                except Exception:
                    failed += 1

                self.win.after(0, lambda s=success, f=failed: self.status_label.configure(
                    text=f"Progress: {s}/{len(self.objects)}"
                ))

            final_msg = f"✅ Done: {success} tagged, {failed} failed"
            self.win.after(0, lambda: self.status_label.configure(text=final_msg, text_color="#00c853"))
            self.win.after(0, lambda: self.apply_btn.configure(state="normal"))

        threading.Thread(target=do_apply, daemon=True).start()
