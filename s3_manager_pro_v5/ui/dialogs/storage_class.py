"""Bulk Storage Class Changer — select target class, preview cost impact, execute."""
import threading
import customtkinter as ctk
from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME
from s3_manager_pro_v5.utils.formatting import format_size, STORAGE_CLASS_INFO


# S3 storage pricing per GB/month (us-east-1 approximate — for estimation)
STORAGE_COST_PER_GB = {
    "STANDARD": 0.023,
    "STANDARD_IA": 0.0125,
    "ONEZONE_IA": 0.01,
    "INTELLIGENT_TIERING": 0.023,  # Frequent tier
    "GLACIER_IR": 0.004,
    "GLACIER": 0.004,
    "DEEP_ARCHIVE": 0.00099,
}


class StorageClassDialog:
    """Bulk change storage class with cost comparison."""

    def __init__(self, parent, app, bucket: str, selected_objects: list):
        self.app = app
        self.bucket = bucket
        self.objects = selected_objects
        self.total_size_bytes = sum(o.size for o in selected_objects)
        self.total_size_gb = self.total_size_bytes / (1024 ** 3)

        colors = DARK_THEME if app.is_dark else LIGHT_THEME

        self.win = ctk.CTkToplevel(parent)
        self.win.title("🔄 Change Storage Class")
        self.win.geometry("520x520")
        self.win.transient(parent)
        self.win.grab_set()
        self.win.resizable(False, True)
        self.win.configure(fg_color=colors["bg"])

        # Title
        ctk.CTkLabel(self.win, text="🔄 Bulk Storage Class Change",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=colors["text_primary"]).pack(pady=(20, 5))

        # Selection info
        ctk.CTkLabel(self.win, text=f"Selected: {len(selected_objects)} files ({format_size(self.total_size_bytes)})",
                     font=ctk.CTkFont(size=12),
                     text_color=colors["text_secondary"]).pack(pady=(0, 10))

        # Current class breakdown
        current_breakdown = {}
        for obj in selected_objects:
            sc = obj.storage_class
            current_breakdown[sc] = current_breakdown.get(sc, 0) + 1

        breakdown_text = "  │  ".join(
            f"{STORAGE_CLASS_INFO.get(sc, {}).get('icon', '⚪')} {sc}: {count}"
            for sc, count in current_breakdown.items()
        )
        ctk.CTkLabel(self.win, text=f"Current: {breakdown_text}",
                     font=ctk.CTkFont(size=11),
                     text_color=colors["text_secondary"]).pack(pady=(0, 15))

        form = ctk.CTkFrame(self.win, fg_color="transparent")
        form.pack(fill="x", padx=30)

        # Target class selection
        ctk.CTkLabel(form, text="Move to Storage Class:",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=colors["text_primary"]).pack(anchor="w", pady=(0, 8))

        self.target_var = ctk.StringVar(value="STANDARD_IA")

        target_classes = [
            "STANDARD", "STANDARD_IA", "ONEZONE_IA",
            "INTELLIGENT_TIERING", "GLACIER_IR", "GLACIER", "DEEP_ARCHIVE",
        ]

        for sc in target_classes:
            info = STORAGE_CLASS_INFO.get(sc, {})
            ctk.CTkRadioButton(
                form, text=f"{info.get('icon', '')} {sc}",
                variable=self.target_var, value=sc,
                font=ctk.CTkFont(size=12),
                text_color=colors["text_primary"],
                command=self._update_cost_preview,
            ).pack(anchor="w", padx=10, pady=2)

        # Cost preview
        self.cost_frame = ctk.CTkFrame(form, fg_color=colors["surface"], corner_radius=8)
        self.cost_frame.pack(fill="x", pady=(15, 10))

        ctk.CTkLabel(self.cost_frame, text="💰 Cost Impact (Estimated)",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=colors["text_primary"]).pack(anchor="w", padx=12, pady=(10, 5))

        self.cost_current_label = ctk.CTkLabel(
            self.cost_frame, text="",
            font=ctk.CTkFont(size=11), text_color=colors["text_secondary"]
        )
        self.cost_current_label.pack(anchor="w", padx=12)

        self.cost_new_label = ctk.CTkLabel(
            self.cost_frame, text="",
            font=ctk.CTkFont(size=11), text_color=colors["text_secondary"]
        )
        self.cost_new_label.pack(anchor="w", padx=12)

        self.cost_savings_label = ctk.CTkLabel(
            self.cost_frame, text="",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=colors["success"]
        )
        self.cost_savings_label.pack(anchor="w", padx=12, pady=(5, 10))

        self._update_cost_preview()

        # Buttons
        btn_row = ctk.CTkFrame(form, fg_color="transparent")
        btn_row.pack(fill="x", pady=(10, 0))

        self.execute_btn = ctk.CTkButton(
            btn_row, text="⚡ Change Storage Class", width=180, height=36,
            corner_radius=8, font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=colors["primary"], hover_color=colors["primary_hover"],
            command=self._execute,
        )
        self.execute_btn.pack(side="left", padx=(0, 10))

        self.status_label = ctk.CTkLabel(btn_row, text="",
                                         font=ctk.CTkFont(size=11))
        self.status_label.pack(side="left")

        ctk.CTkButton(btn_row, text="Cancel", width=80, height=36,
                      corner_radius=8, fg_color=colors["badge_bg"],
                      hover_color=colors["surface_hover"],
                      text_color=colors["text_primary"],
                      command=self.win.destroy).pack(side="right")

    def _update_cost_preview(self):
        """Calculate and display cost comparison."""
        target = self.target_var.get()

        # Calculate current cost (weighted average)
        current_cost = 0
        for obj in self.objects:
            obj_gb = obj.size / (1024 ** 3)
            rate = STORAGE_COST_PER_GB.get(obj.storage_class, 0.023)
            current_cost += obj_gb * rate

        # Calculate new cost
        new_rate = STORAGE_COST_PER_GB.get(target, 0.023)
        new_cost = self.total_size_gb * new_rate

        savings = current_cost - new_cost
        savings_pct = (savings / current_cost * 100) if current_cost > 0 else 0

        self.cost_current_label.configure(text=f"Current: ${current_cost:.4f}/month")
        self.cost_new_label.configure(text=f"After change: ${new_cost:.4f}/month")

        if savings > 0:
            self.cost_savings_label.configure(
                text=f"💚 Save ${savings:.4f}/month ({savings_pct:.0f}% reduction)",
                text_color="#00c853"
            )
        elif savings < 0:
            self.cost_savings_label.configure(
                text=f"⚠️ Cost increases by ${abs(savings):.4f}/month",
                text_color="#ff9800"
            )
        else:
            self.cost_savings_label.configure(text="No cost change", text_color="gray")

    def _execute(self):
        """Execute the storage class change via S3 copy-in-place."""
        from tkinter import messagebox
        target = self.target_var.get()

        confirm = messagebox.askyesno(
            "Confirm Change",
            f"Change {len(self.objects)} objects to {target}?\n\n"
            f"This uses COPY operations (standard request charges apply).",
            parent=self.win
        )
        if not confirm:
            return

        self.execute_btn.configure(state="disabled")
        self.status_label.configure(text="Processing...", text_color="#ff9800")

        def do_change():
            success = 0
            failed = 0
            for obj in self.objects:
                try:
                    # S3 copy-in-place to change storage class
                    # For files > 5GB, use multipart copy
                    if obj.size >= 5 * 1024 * 1024 * 1024:
                        from s3_manager_pro_v5.backend.large_file_ops import _multipart_copy
                        # Need to use multipart with storage class
                        s3 = self.app.s3_client.s3_client
                        mpu = s3.create_multipart_upload(
                            Bucket=self.bucket, Key=obj.key, StorageClass=target
                        )
                        upload_id = mpu["UploadId"]
                        try:
                            parts = []
                            part_num = 1
                            copied = 0
                            part_size = 500 * 1024 * 1024
                            while copied < obj.size:
                                start = copied
                                end = min(copied + part_size - 1, obj.size - 1)
                                resp = s3.upload_part_copy(
                                    Bucket=self.bucket, Key=obj.key,
                                    UploadId=upload_id, PartNumber=part_num,
                                    CopySource={"Bucket": self.bucket, "Key": obj.key},
                                    CopySourceRange=f"bytes={start}-{end}",
                                )
                                parts.append({"PartNumber": part_num, "ETag": resp["CopyPartResult"]["ETag"]})
                                copied = end + 1
                                part_num += 1
                            s3.complete_multipart_upload(
                                Bucket=self.bucket, Key=obj.key,
                                UploadId=upload_id,
                                MultipartUpload={"Parts": parts},
                            )
                        except Exception:
                            s3.abort_multipart_upload(Bucket=self.bucket, Key=obj.key, UploadId=upload_id)
                            raise
                    else:
                        self.app.s3_client.s3_client.copy_object(
                            Bucket=self.bucket,
                            Key=obj.key,
                            CopySource={"Bucket": self.bucket, "Key": obj.key},
                            StorageClass=target,
                            MetadataDirective="COPY",
                        )
                    success += 1
                except Exception as e:
                    failed += 1

                self.win.after(0, lambda s=success, f=failed: self.status_label.configure(
                    text=f"Progress: {s}/{len(self.objects)}"
                ))

            self.win.after(0, lambda: self.status_label.configure(
                text=f"✓ Done: {success} changed, {failed} failed",
                text_color="#00c853"
            ))
            # Refresh the file list
            self.win.after(500, lambda: self.app.refresh_listing())

        threading.Thread(target=do_change, daemon=True).start()
