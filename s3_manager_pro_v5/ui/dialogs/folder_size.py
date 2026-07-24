"""Folder Size Calculator Dialog for S3 Manager Pro v5.0."""

import threading
import customtkinter as ctk

from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME
from s3_manager_pro_v5.utils.formatting import format_size


class FolderSizeDialog:
    """Calculate and display total size of all objects under a given S3 prefix."""

    def __init__(self, parent, app, bucket: str, prefix: str):
        self.parent = parent
        self.app = app
        self.bucket = bucket
        self.prefix = prefix
        self.total_files = 0
        self.total_size = 0
        self.storage_classes: dict[str, dict[str, int]] = {}
        self._cancelled = False

        self._build_ui()
        self._start_calculation()

    def _build_ui(self):
        """Build the dialog UI."""
        self.dialog = ctk.CTkToplevel(self.parent)
        self.dialog.title(f"Folder Size - {self.prefix or '/'}")
        self.dialog.geometry("500x520")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

        # Header
        header_frame = ctk.CTkFrame(self.dialog)
        header_frame.pack(fill="x", padx=15, pady=(15, 5))

        ctk.CTkLabel(
            header_frame,
            text="📁 Folder Size Calculator",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=10, pady=5)

        ctk.CTkLabel(
            header_frame,
            text=f"Bucket: {self.bucket}",
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=10)

        ctk.CTkLabel(
            header_frame,
            text=f"Prefix: {self.prefix or '(root)'}",
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=10, pady=(0, 5))

        # Progress section
        self.progress_frame = ctk.CTkFrame(self.dialog)
        self.progress_frame.pack(fill="x", padx=15, pady=10)

        self.status_label = ctk.CTkLabel(
            self.progress_frame,
            text="Calculating...",
            font=ctk.CTkFont(size=12),
        )
        self.status_label.pack(anchor="w", padx=10, pady=5)

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.pack(fill="x", padx=10, pady=5)
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start()

        # Results section
        self.results_frame = ctk.CTkFrame(self.dialog)
        self.results_frame.pack(fill="both", expand=True, padx=15, pady=5)

        self.results_text = ctk.CTkTextbox(self.results_frame, state="disabled")
        self.results_text.pack(fill="both", expand=True, padx=10, pady=10)

        # Buttons
        btn_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=(5, 15))

        self.copy_btn = ctk.CTkButton(
            btn_frame,
            text="📋 Copy to Clipboard",
            command=self._copy_to_clipboard,
            state="disabled",
        )
        self.copy_btn.pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            command=self._cancel,
        ).pack(side="right", padx=5)

    def _start_calculation(self):
        """Start the size calculation in a background thread."""
        thread = threading.Thread(target=self._calculate_size, daemon=True)
        thread.start()

    def _calculate_size(self):
        """Calculate total size using S3 paginator."""
        try:
            s3_client = self.app.s3_client
            paginator = s3_client.get_paginator("list_objects_v2")
            page_iterator = paginator.paginate(
                Bucket=self.bucket,
                Prefix=self.prefix,
            )

            for page in page_iterator:
                if self._cancelled:
                    return

                contents = page.get("Contents", [])
                for obj in contents:
                    if self._cancelled:
                        return

                    self.total_files += 1
                    size = obj.get("Size", 0)
                    self.total_size += size

                    storage_class = obj.get("StorageClass", "STANDARD")
                    if storage_class not in self.storage_classes:
                        self.storage_classes[storage_class] = {"count": 0, "size": 0}
                    self.storage_classes[storage_class]["count"] += 1
                    self.storage_classes[storage_class]["size"] += size

                # Update progress on UI thread
                self.dialog.after(0, self._update_progress)

            self.dialog.after(0, self._show_results)

        except Exception as e:
            self.dialog.after(0, lambda: self._show_error(str(e)))

    def _update_progress(self):
        """Update progress label with current count."""
        self.status_label.configure(
            text=f"Scanning... {self.total_files} files found ({format_size(self.total_size)})"
        )

    def _show_results(self):
        """Display final results."""
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.status_label.configure(text="✅ Calculation complete")

        result_text = self._format_results()

        self.results_text.configure(state="normal")
        self.results_text.delete("1.0", "end")
        self.results_text.insert("1.0", result_text)
        self.results_text.configure(state="disabled")

        self.copy_btn.configure(state="normal")

    def _format_results(self) -> str:
        """Format the results as a readable string."""
        lines = [
            f"Folder Size Report",
            f"{'=' * 40}",
            f"Bucket:       {self.bucket}",
            f"Prefix:       {self.prefix or '(root)'}",
            f"",
            f"Total Files:  {self.total_files:,}",
            f"Total Size:   {format_size(self.total_size)}",
            f"",
            f"Storage Class Breakdown:",
            f"{'-' * 40}",
        ]

        for sc, data in sorted(self.storage_classes.items()):
            lines.append(
                f"  {sc:<20} {data['count']:>8,} files  {format_size(data['size']):>12}"
            )

        return "\n".join(lines)

    def _show_error(self, error_msg: str):
        """Display an error message."""
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.status_label.configure(text=f"❌ Error: {error_msg}")

    def _copy_to_clipboard(self):
        """Copy results to system clipboard."""
        result_text = self._format_results()
        self.dialog.clipboard_clear()
        self.dialog.clipboard_append(result_text)
        self.copy_btn.configure(text="✅ Copied!")
        self.dialog.after(2000, lambda: self.copy_btn.configure(text="📋 Copy to Clipboard"))

    def _cancel(self):
        """Cancel the operation and close dialog."""
        self._cancelled = True
        self.dialog.destroy()
