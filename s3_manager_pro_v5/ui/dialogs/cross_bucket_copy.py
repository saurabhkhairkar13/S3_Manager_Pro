"""Cross-Bucket Copy/Move Dialog for S3 Manager Pro v5.0."""

import threading
import customtkinter as ctk

from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME
from s3_manager_pro_v5.utils.formatting import format_size


class CrossBucketCopyDialog:
    """Copy or move objects between S3 buckets."""

    def __init__(self, parent, app, source_bucket: str, selected_objects: list[str]):
        self.parent = parent
        self.app = app
        self.source_bucket = source_bucket
        self.selected_objects = selected_objects
        self._cancelled = False
        self.target_buckets: list[str] = []

        self._build_ui()
        self._load_buckets()

    def _build_ui(self):
        """Build the dialog UI."""
        self.dialog = ctk.CTkToplevel(self.parent)
        self.dialog.title("Cross-Bucket Copy/Move")
        self.dialog.geometry("600x500")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

        # Header
        ctk.CTkLabel(
            self.dialog,
            text="📦 Cross-Bucket Copy / Move",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=15, pady=(15, 5))

        ctk.CTkLabel(
            self.dialog,
            text=f"Source: {self.source_bucket} | Objects: {len(self.selected_objects)}",
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=15, pady=(0, 10))

        # Source objects display
        source_frame = ctk.CTkFrame(self.dialog)
        source_frame.pack(fill="x", padx=15, pady=5)

        ctk.CTkLabel(
            source_frame,
            text="Selected Objects:",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(5, 0))

        self.source_list = ctk.CTkTextbox(source_frame, height=100, state="disabled")
        self.source_list.pack(fill="x", padx=10, pady=5)
        self.source_list.configure(state="normal")
        for obj in self.selected_objects[:20]:
            self.source_list.insert("end", f"  {obj}\n")
        if len(self.selected_objects) > 20:
            self.source_list.insert("end", f"  ... and {len(self.selected_objects) - 20} more\n")
        self.source_list.configure(state="disabled")

        # Target configuration
        target_frame = ctk.CTkFrame(self.dialog)
        target_frame.pack(fill="x", padx=15, pady=10)

        ctk.CTkLabel(
            target_frame,
            text="Target Configuration:",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        # Target bucket dropdown
        bucket_row = ctk.CTkFrame(target_frame, fg_color="transparent")
        bucket_row.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(bucket_row, text="Target Bucket:").pack(side="left", padx=(0, 10))
        self.bucket_dropdown = ctk.CTkComboBox(
            bucket_row, values=["Loading..."], width=300
        )
        self.bucket_dropdown.pack(side="left", padx=5)

        # Target prefix
        prefix_row = ctk.CTkFrame(target_frame, fg_color="transparent")
        prefix_row.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(prefix_row, text="Target Prefix:").pack(side="left", padx=(0, 10))
        self.prefix_entry = ctk.CTkEntry(prefix_row, width=300, placeholder_text="e.g., backups/2024/")
        self.prefix_entry.pack(side="left", padx=5)

        # Operation mode
        mode_row = ctk.CTkFrame(target_frame, fg_color="transparent")
        mode_row.pack(fill="x", padx=10, pady=(5, 10))

        ctk.CTkLabel(mode_row, text="Operation:").pack(side="left", padx=(0, 10))
        self.mode_var = ctk.StringVar(value="copy")
        ctk.CTkRadioButton(
            mode_row, text="Copy", variable=self.mode_var, value="copy"
        ).pack(side="left", padx=10)
        ctk.CTkRadioButton(
            mode_row, text="Move (Copy + Delete Source)", variable=self.mode_var, value="move"
        ).pack(side="left", padx=10)

        # Progress section
        self.progress_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        self.progress_frame.pack(fill="x", padx=15, pady=5)

        self.progress_label = ctk.CTkLabel(self.progress_frame, text="")
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)

        # Buttons
        btn_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=(10, 15))

        self.execute_btn = ctk.CTkButton(
            btn_frame,
            text="🚀 Start Transfer",
            command=self._execute_transfer,
            fg_color="green",
        )
        self.execute_btn.pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            command=self._cancel,
        ).pack(side="right", padx=5)

    def _load_buckets(self):
        """Load available buckets in a background thread."""
        thread = threading.Thread(target=self._fetch_buckets, daemon=True)
        thread.start()

    def _fetch_buckets(self):
        """Fetch bucket list from S3."""
        try:
            s3_client = self.app.s3_client
            response = s3_client.list_buckets()
            self.target_buckets = [
                b["Name"] for b in response.get("Buckets", [])
            ]
            self.dialog.after(0, self._update_bucket_dropdown)
        except Exception as e:
            self.dialog.after(
                0, lambda: self.progress_label.configure(text=f"Error loading buckets: {e}")
            )

    def _update_bucket_dropdown(self):
        """Update the bucket dropdown with fetched values."""
        if self.target_buckets:
            self.bucket_dropdown.configure(values=self.target_buckets)
            self.bucket_dropdown.set(self.target_buckets[0])
        else:
            self.bucket_dropdown.configure(values=["No buckets found"])

    def _execute_transfer(self):
        """Start the transfer operation."""
        target_bucket = self.bucket_dropdown.get()
        if not target_bucket or target_bucket in ("Loading...", "No buckets found"):
            self.progress_label.pack(anchor="w", padx=5)
            self.progress_label.configure(text="⚠️ Please select a valid target bucket")
            return

        self.execute_btn.configure(state="disabled")
        self.progress_label.pack(anchor="w", padx=5, pady=2)
        self.progress_bar.pack(fill="x", padx=5, pady=2)
        self.progress_bar.set(0)

        thread = threading.Thread(target=self._do_transfer, daemon=True)
        thread.start()

    def _do_transfer(self):
        """Perform the copy/move in a background thread."""
        target_bucket = self.bucket_dropdown.get()
        target_prefix = self.prefix_entry.get().strip()
        is_move = self.mode_var.get() == "move"
        total = len(self.selected_objects)
        success_count = 0
        error_count = 0

        try:
            s3_client = self.app.s3_client

            for i, key in enumerate(self.selected_objects):
                if self._cancelled:
                    break

                # Compute target key
                filename = key.rsplit("/", 1)[-1]
                target_key = target_prefix + filename if target_prefix else filename

                try:
                    from s3_manager_pro_v5.backend.large_file_ops import copy_object_any_size, move_object_any_size

                    if is_move:
                        move_object_any_size(
                            s3_client, self.source_bucket, key,
                            target_bucket, target_key
                        )
                    else:
                        copy_object_any_size(
                            s3_client, self.source_bucket, key,
                            target_bucket, target_key
                        )

                    success_count += 1
                except Exception:
                    error_count += 1

                progress = (i + 1) / total
                self.dialog.after(
                    0,
                    lambda p=progress, idx=i: self._update_progress(p, idx, total),
                )

            op_name = "Moved" if is_move else "Copied"
            self.dialog.after(
                0, lambda: self._transfer_complete(op_name, success_count, error_count)
            )

        except Exception as e:
            self.dialog.after(0, lambda: self._transfer_error(str(e)))

    def _update_progress(self, progress: float, current: int, total: int):
        """Update progress during transfer."""
        self.progress_bar.set(progress)
        self.progress_label.configure(text=f"Transferring {current + 1}/{total}...")

    def _transfer_complete(self, op_name: str, success: int, errors: int):
        """Handle transfer completion."""
        self.progress_bar.set(1.0)
        self.progress_label.configure(
            text=f"✅ {op_name}: {success} objects, {errors} errors"
        )
        self.execute_btn.configure(state="normal", text="✅ Done")

    def _transfer_error(self, error_msg: str):
        """Handle transfer error."""
        self.progress_label.configure(text=f"❌ Error: {error_msg}")
        self.execute_btn.configure(state="normal")

    def _cancel(self):
        """Cancel and close."""
        self._cancelled = True
        self.dialog.destroy()
