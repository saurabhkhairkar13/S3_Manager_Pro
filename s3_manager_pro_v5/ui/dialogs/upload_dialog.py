"""Upload Dialog — folder upload, storage class picker, skip existing, progress."""
import os
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox
from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME
from s3_manager_pro_v5.utils.formatting import format_size


class UploadDialog:
    """Full-featured upload dialog with folder support, class selection, and progress."""

    def __init__(self, parent, app, bucket: str, prefix: str):
        self.app = app
        self.bucket = bucket
        self.prefix = prefix
        self.upload_files = []
        self.base_folder = None
        self._cancel = False

        colors = DARK_THEME if app.is_dark else LIGHT_THEME

        self.win = ctk.CTkToplevel(parent)
        self.win.title("⬆ Upload Files")
        self.win.geometry("560x520")
        self.win.transient(parent)
        self.win.grab_set()
        self.win.resizable(False, True)
        self.win.configure(fg_color=colors["bg"])

        # Title
        ctk.CTkLabel(self.win, text="⬆ Upload Files to S3",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=colors["text_primary"]).pack(pady=(20, 5))

        # Target
        ctk.CTkLabel(self.win, text=f"Target: s3://{bucket}/{prefix}",
                     font=ctk.CTkFont(size=12),
                     text_color=colors["primary"]).pack(pady=(0, 15))

        form = ctk.CTkFrame(self.win, fg_color="transparent")
        form.pack(fill="x", padx=25)

        # File selection buttons
        btn_row = ctk.CTkFrame(form, fg_color="transparent")
        btn_row.pack(fill="x", pady=(0, 8))

        ctk.CTkButton(btn_row, text="📄 Select Files", width=120, height=32,
                      corner_radius=6, fg_color=colors["primary"],
                      hover_color=colors["primary_hover"],
                      command=self._select_files).pack(side="left", padx=(0, 8))

        ctk.CTkButton(btn_row, text="📁 Select Folder", width=120, height=32,
                      corner_radius=6, fg_color=colors["primary"],
                      hover_color=colors["primary_hover"],
                      command=self._select_folder).pack(side="left")

        self.file_label = ctk.CTkLabel(form, text="No files selected",
                                       font=ctk.CTkFont(size=11),
                                       text_color=colors["text_secondary"])
        self.file_label.pack(anchor="w", pady=(0, 10))

        # Upload prefix (editable)
        ctk.CTkLabel(form, text="Upload Prefix:",
                     font=ctk.CTkFont(size=12),
                     text_color=colors["text_primary"]).pack(anchor="w")
        self.prefix_entry = ctk.CTkEntry(form, width=450, placeholder_text="folder/subfolder/")
        self.prefix_entry.insert(0, prefix)
        self.prefix_entry.pack(anchor="w", pady=(0, 10))

        # Storage class
        ctk.CTkLabel(form, text="Storage Class:",
                     font=ctk.CTkFont(size=12),
                     text_color=colors["text_primary"]).pack(anchor="w")
        self.storage_var = ctk.StringVar(value="STANDARD")
        ctk.CTkOptionMenu(
            form, variable=self.storage_var, width=220, height=30,
            values=["STANDARD", "STANDARD_IA", "ONEZONE_IA",
                    "INTELLIGENT_TIERING", "GLACIER_IR", "GLACIER", "DEEP_ARCHIVE"],
        ).pack(anchor="w", pady=(0, 10))

        # Options row
        opts_row = ctk.CTkFrame(form, fg_color="transparent")
        opts_row.pack(fill="x", pady=(0, 10))

        self.skip_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(opts_row, text="Skip existing files (same size)",
                        variable=self.skip_var,
                        text_color=colors["text_primary"]).pack(side="left")

        # Parallel
        ctk.CTkLabel(form, text="Parallel Uploads:",
                     font=ctk.CTkFont(size=12),
                     text_color=colors["text_primary"]).pack(anchor="w")
        self.parallel_entry = ctk.CTkEntry(form, width=60)
        self.parallel_entry.insert(0, str(app.cred_manager.get("parallel", 3)))
        self.parallel_entry.pack(anchor="w", pady=(0, 10))

        # Progress
        self.progress = ctk.CTkProgressBar(form, height=10, corner_radius=5)
        self.progress.pack(fill="x", pady=(5, 5))
        self.progress.set(0)

        self.status_label = ctk.CTkLabel(form, text="",
                                         font=ctk.CTkFont(size=11),
                                         text_color=colors["text_secondary"])
        self.status_label.pack(anchor="w", pady=(0, 10))

        # Buttons
        btn_frame = ctk.CTkFrame(form, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(5, 0))

        self.upload_btn = ctk.CTkButton(
            btn_frame, text="⬆ Upload", width=100, height=34,
            corner_radius=8, font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=colors["success"], hover_color="#1fa339",
            command=self._start_upload,
        )
        self.upload_btn.pack(side="left", padx=(0, 10))

        self.cancel_btn = ctk.CTkButton(
            btn_frame, text="Cancel Upload", width=110, height=34,
            corner_radius=8, font=ctk.CTkFont(size=12),
            fg_color=colors["danger"], hover_color=colors["danger_hover"],
            command=self._cancel_upload, state="disabled",
        )
        self.cancel_btn.pack(side="left", padx=(0, 10))

        ctk.CTkButton(btn_frame, text="Close", width=70, height=34,
                      corner_radius=8, fg_color=colors["badge_bg"],
                      hover_color=colors["surface_hover"],
                      text_color=colors["text_primary"],
                      command=self.win.destroy).pack(side="right")

    def _select_files(self):
        """Select multiple files."""
        files = filedialog.askopenfilenames(title="Select Files", parent=self.win)
        if files:
            self.upload_files = list(files)
            self.base_folder = None
            total = sum(os.path.getsize(f) for f in self.upload_files)
            self.file_label.configure(text=f"{len(self.upload_files)} files ({format_size(total)})")

    def _select_folder(self):
        """Select a folder for upload."""
        folder = filedialog.askdirectory(title="Select Folder", parent=self.win)
        if folder:
            self.upload_files = []
            self.base_folder = folder
            for root, dirs, files in os.walk(folder):
                for f in files:
                    self.upload_files.append(os.path.join(root, f))
            if self.upload_files:
                total = sum(os.path.getsize(f) for f in self.upload_files)
                self.file_label.configure(
                    text=f"📁 {os.path.basename(folder)} — {len(self.upload_files)} files ({format_size(total)})"
                )

    def _start_upload(self):
        """Start the upload process."""
        if not self.upload_files:
            messagebox.showwarning("Upload", "No files selected.", parent=self.win)
            return

        self.upload_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self._cancel = False

        upload_prefix = self.prefix_entry.get().strip()
        if upload_prefix and not upload_prefix.endswith("/"):
            upload_prefix += "/"

        storage_class = self.storage_var.get()
        skip_existing = self.skip_var.get()
        parallel = int(self.parallel_entry.get().strip() or 3)

        total_size = sum(os.path.getsize(f) for f in self.upload_files)
        uploaded = [0]

        def do_upload():
            from concurrent.futures import ThreadPoolExecutor, as_completed
            from botocore.exceptions import ClientError

            success = 0
            failed = 0
            skipped = 0
            error_messages = []

            def upload_one(local_path):
                nonlocal success, failed, skipped
                if self._cancel:
                    return

                file_size = os.path.getsize(local_path)
                filename = os.path.basename(local_path)

                # Determine S3 key
                if self.base_folder and local_path.startswith(self.base_folder):
                    relative = os.path.relpath(local_path, self.base_folder).replace(os.sep, "/")
                    s3_key = upload_prefix + relative
                else:
                    s3_key = upload_prefix + filename

                # Skip existing
                if skip_existing:
                    try:
                        resp = self.app.s3_client.s3_client.head_object(Bucket=self.bucket, Key=s3_key)
                        if resp["ContentLength"] == file_size:
                            skipped += 1
                            uploaded[0] += file_size
                            pct = uploaded[0] / total_size if total_size > 0 else 0
                            self.win.after(0, lambda p=pct: self.progress.set(min(p, 1.0)))
                            return
                    except ClientError:
                        pass

                self.win.after(0, lambda fn=filename: self.status_label.configure(
                    text=f"Uploading: {fn}"
                ))

                try:
                    from s3_manager_pro_v5.backend.large_file_ops import upload_file_any_size
                    upload_file_any_size(
                        self.app.s3_client.s3_client,
                        local_path, self.bucket, s3_key,
                        storage_class=storage_class,
                    )
                    success += 1
                    uploaded[0] += file_size
                    pct = uploaded[0] / total_size if total_size > 0 else 0
                    self.win.after(0, lambda p=pct: self.progress.set(min(p, 1.0)))
                except Exception as e:
                    failed += 1
                    error_messages.append(f"{filename}: {str(e)}")

            with ThreadPoolExecutor(max_workers=parallel) as executor:
                futures = [executor.submit(upload_one, f) for f in self.upload_files]
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception:
                        pass

            # Done
            msg = f"✓ Done: {success} uploaded, {skipped} skipped, {failed} failed"
            self.win.after(0, lambda: self.status_label.configure(text=msg, text_color="#00c853"))
            self.win.after(0, lambda: self.progress.set(1.0))
            self.win.after(0, lambda: self.upload_btn.configure(state="normal"))
            self.win.after(0, lambda: self.cancel_btn.configure(state="disabled"))
            self.win.after(0, lambda: self.app.refresh_listing())

            # Show error details if any
            if failed > 0 and error_messages:
                error_detail = "\n".join(error_messages[:15])
                if len(error_messages) > 15:
                    error_detail += f"\n\n... and {len(error_messages) - 15} more errors"
                from tkinter import messagebox
                self.win.after(100, lambda: messagebox.showerror(
                    "Upload Errors",
                    f"Failed to upload {failed} file(s):\n\n{error_detail}",
                    parent=self.win
                ))

            # Send notification
            from s3_manager_pro_v5.ui.notifications import notify_upload_complete
            notify_upload_complete(success, failed, format_size(total_size))

        threading.Thread(target=do_upload, daemon=True).start()

    def _cancel_upload(self):
        """Cancel the upload."""
        self._cancel = True
        self.status_label.configure(text="Cancelling...")
