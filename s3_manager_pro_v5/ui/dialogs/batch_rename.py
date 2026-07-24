"""Batch Rename/Move Objects Dialog for S3 Manager Pro v5.0."""

import os
import threading
import customtkinter as ctk

from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME
from s3_manager_pro_v5.utils.formatting import format_size


class BatchRenameDialog:
    """Batch rename or move S3 objects with preview."""

    def __init__(self, parent, app, bucket: str, objects: list[str]):
        self.parent = parent
        self.app = app
        self.bucket = bucket
        self.objects = objects
        self._cancelled = False

        self._build_ui()

    def _build_ui(self):
        """Build the dialog UI."""
        self.dialog = ctk.CTkToplevel(self.parent)
        self.dialog.title(f"Batch Rename - {len(self.objects)} objects")
        self.dialog.geometry("750x600")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

        # Header
        ctk.CTkLabel(
            self.dialog,
            text="🔄 Batch Rename / Move Objects",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=15, pady=(15, 5))

        ctk.CTkLabel(
            self.dialog,
            text=f"Bucket: {self.bucket} | Selected: {len(self.objects)} objects",
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=15, pady=(0, 10))

        # Operation type selection
        options_frame = ctk.CTkFrame(self.dialog)
        options_frame.pack(fill="x", padx=15, pady=5)

        ctk.CTkLabel(
            options_frame,
            text="Rename Operation:",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        self.operation_var = ctk.StringVar(value="add_prefix")

        ops = [
            ("Add Prefix", "add_prefix"),
            ("Add Suffix", "add_suffix"),
            ("Find & Replace", "find_replace"),
            ("Change Extension", "change_extension"),
        ]

        radio_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        radio_frame.pack(fill="x", padx=10, pady=5)

        for text, value in ops:
            ctk.CTkRadioButton(
                radio_frame,
                text=text,
                variable=self.operation_var,
                value=value,
                command=self._update_input_fields,
            ).pack(side="left", padx=10)

        # Input fields
        self.input_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        self.input_frame.pack(fill="x", padx=10, pady=10)

        # Field 1
        self.label1 = ctk.CTkLabel(self.input_frame, text="Prefix:")
        self.label1.pack(side="left", padx=(0, 5))
        self.entry1 = ctk.CTkEntry(self.input_frame, width=200)
        self.entry1.pack(side="left", padx=5)

        # Field 2 (for find & replace)
        self.label2 = ctk.CTkLabel(self.input_frame, text="")
        self.label2.pack(side="left", padx=(20, 5))
        self.entry2 = ctk.CTkEntry(self.input_frame, width=200)
        self.entry2.pack(side="left", padx=5)
        self.label2.pack_forget()
        self.entry2.pack_forget()

        # Preview button
        ctk.CTkButton(
            options_frame,
            text="👁 Preview Changes",
            command=self._generate_preview,
        ).pack(anchor="w", padx=10, pady=(0, 10))

        # Preview section
        preview_label = ctk.CTkLabel(
            self.dialog,
            text="Preview (Old → New):",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        preview_label.pack(anchor="w", padx=15, pady=(10, 5))

        self.preview_text = ctk.CTkTextbox(self.dialog, height=250)
        self.preview_text.pack(fill="both", expand=True, padx=15, pady=5)

        # Progress
        self.progress_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        self.progress_frame.pack(fill="x", padx=15, pady=5)

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_label = ctk.CTkLabel(self.progress_frame, text="")

        # Buttons
        btn_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=(5, 15))

        self.execute_btn = ctk.CTkButton(
            btn_frame,
            text="🚀 Execute Rename",
            command=self._execute_rename,
            fg_color="green",
        )
        self.execute_btn.pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="Close",
            command=self._close,
        ).pack(side="right", padx=5)

        self._update_input_fields()

    def _update_input_fields(self):
        """Update input labels based on selected operation."""
        op = self.operation_var.get()

        # Reset visibility
        self.label2.pack_forget()
        self.entry2.pack_forget()

        if op == "add_prefix":
            self.label1.configure(text="Prefix:")
            self.entry1.delete(0, "end")
        elif op == "add_suffix":
            self.label1.configure(text="Suffix:")
            self.entry1.delete(0, "end")
        elif op == "find_replace":
            self.label1.configure(text="Find:")
            self.entry1.delete(0, "end")
            self.label2.configure(text="Replace:")
            self.label2.pack(side="left", padx=(20, 5))
            self.entry2.delete(0, "end")
            self.entry2.pack(side="left", padx=5)
        elif op == "change_extension":
            self.label1.configure(text="New Extension:")
            self.entry1.delete(0, "end")
            self.entry1.insert(0, ".txt")

    def _compute_new_key(self, key: str) -> str:
        """Compute the new key based on the selected operation."""
        op = self.operation_var.get()
        value1 = self.entry1.get()
        value2 = self.entry2.get()

        # Get just the filename part (after last /)
        parts = key.rsplit("/", 1)
        prefix_path = parts[0] + "/" if len(parts) > 1 else ""
        filename = parts[-1]

        if op == "add_prefix":
            return prefix_path + value1 + filename
        elif op == "add_suffix":
            name, ext = os.path.splitext(filename)
            return prefix_path + name + value1 + ext
        elif op == "find_replace":
            new_filename = filename.replace(value1, value2)
            return prefix_path + new_filename
        elif op == "change_extension":
            name, _ = os.path.splitext(filename)
            ext = value1 if value1.startswith(".") else "." + value1
            return prefix_path + name + ext

        return key

    def _generate_preview(self):
        """Generate preview of renames."""
        self.preview_text.delete("1.0", "end")

        for key in self.objects:
            new_key = self._compute_new_key(key)
            changed = " ✓" if key != new_key else " (no change)"
            self.preview_text.insert("end", f"{key}\n  → {new_key}{changed}\n\n")

    def _execute_rename(self):
        """Execute the batch rename operation."""
        self.execute_btn.configure(state="disabled")
        self.progress_label.pack(anchor="w", padx=5, pady=2)
        self.progress_bar.pack(fill="x", padx=5, pady=2)
        self.progress_bar.set(0)

        thread = threading.Thread(target=self._do_rename, daemon=True)
        thread.start()

    def _do_rename(self):
        """Perform the rename operations in a background thread."""
        total = len(self.objects)
        success_count = 0
        error_count = 0

        try:
            s3_client = self.app.s3_client

            for i, key in enumerate(self.objects):
                if self._cancelled:
                    break

                new_key = self._compute_new_key(key)
                if new_key == key:
                    continue

                try:
                    # Copy to new key
                    s3_client.copy_object(
                        Bucket=self.bucket,
                        CopySource={"Bucket": self.bucket, "Key": key},
                        Key=new_key,
                    )
                    # Delete old key
                    s3_client.delete_object(Bucket=self.bucket, Key=key)
                    success_count += 1
                except Exception:
                    error_count += 1

                progress = (i + 1) / total
                self.dialog.after(
                    0,
                    lambda p=progress, idx=i: self._update_rename_progress(p, idx, total),
                )

            self.dialog.after(
                0, lambda: self._rename_complete(success_count, error_count)
            )

        except Exception as e:
            self.dialog.after(0, lambda: self._rename_error(str(e)))

    def _update_rename_progress(self, progress: float, current: int, total: int):
        """Update progress bar during rename."""
        self.progress_bar.set(progress)
        self.progress_label.configure(text=f"Processing {current + 1}/{total}...")

    def _rename_complete(self, success: int, errors: int):
        """Handle rename completion."""
        self.progress_bar.set(1.0)
        self.progress_label.configure(
            text=f"✅ Complete: {success} renamed, {errors} errors"
        )
        self.execute_btn.configure(state="normal", text="✅ Done")

    def _rename_error(self, error_msg: str):
        """Handle rename error."""
        self.progress_label.configure(text=f"❌ Error: {error_msg}")
        self.execute_btn.configure(state="normal")

    def _close(self):
        """Close the dialog."""
        self._cancelled = True
        self.dialog.destroy()
