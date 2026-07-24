"""Incomplete Multipart Upload Manager — Find and clean orphaned upload parts.

Problem: When a multipart upload fails or is abandoned, the uploaded parts remain
in S3 and continue incurring storage costs. These are invisible in the Console's
object listing. AWS charges for this storage silently.

This tool:
1. Scans buckets for incomplete multipart uploads
2. Shows how much space (and cost) they're wasting
3. Allows one-click cleanup (abort uploads)
4. Can set lifecycle rules to auto-clean in future
"""
import threading
from datetime import datetime, timedelta
import customtkinter as ctk
from tkinter import messagebox
from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME
from s3_manager_pro_v5.utils.formatting import format_size


class MultipartCleanerDialog:
    """Find and clean incomplete/orphaned multipart uploads that waste money."""

    def __init__(self, parent, app, bucket: str = None):
        self.app = app
        self.bucket = bucket  # If None, scan all buckets
        self.uploads = []  # List of incomplete uploads found
        self.total_wasted = 0

        colors = DARK_THEME if app.is_dark else LIGHT_THEME

        self.win = ctk.CTkToplevel(parent)
        self.win.title("🧹 Incomplete Multipart Upload Cleaner")
        self.win.geometry("750x580")
        self.win.transient(parent)
        self.win.grab_set()
        self.win.resizable(True, True)
        self.win.configure(fg_color=colors["bg"])

        # Title
        ctk.CTkLabel(self.win, text="🧹 Orphaned Multipart Upload Cleaner",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=colors["text_primary"]).pack(pady=(15, 3))

        ctk.CTkLabel(self.win, text="Find hidden incomplete uploads that are silently costing you money",
                     font=ctk.CTkFont(size=11),
                     text_color=colors["text_secondary"]).pack(pady=(0, 10))

        # Info card
        info_card = ctk.CTkFrame(self.win, fg_color=colors["surface"], corner_radius=8)
        info_card.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(info_card,
                     text="⚠️ When multipart uploads fail or are cancelled, uploaded parts remain in S3.\n"
                          "These parts are INVISIBLE in the S3 Console but you're still charged for storage.\n"
                          "This tool finds and removes them to recover wasted spend.",
                     font=ctk.CTkFont(size=11),
                     text_color=colors["warning"],
                     justify="left", wraplength=680).pack(padx=15, pady=10)

        # Scan controls
        scan_frame = ctk.CTkFrame(self.win, fg_color="transparent")
        scan_frame.pack(fill="x", padx=20, pady=(0, 5))

        scope_text = f"Bucket: {bucket}" if bucket else "All Buckets"
        ctk.CTkLabel(scan_frame, text=f"Scan scope: {scope_text}",
                     font=ctk.CTkFont(size=12),
                     text_color=colors["text_primary"]).pack(side="left")

        self.scan_btn = ctk.CTkButton(
            scan_frame, text="🔍 Scan for Orphaned Uploads", width=220, height=32,
            corner_radius=8, fg_color=colors["primary"], hover_color=colors["primary_hover"],
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._start_scan,
        )
        self.scan_btn.pack(side="right")

        # Status + cost summary
        self.summary_frame = ctk.CTkFrame(self.win, fg_color="transparent")
        self.summary_frame.pack(fill="x", padx=20, pady=5)

        self.status_label = ctk.CTkLabel(self.summary_frame, text="Click 'Scan' to find orphaned uploads",
                                         font=ctk.CTkFont(size=11),
                                         text_color=colors["text_secondary"])
        self.status_label.pack(side="left")

        self.cost_label = ctk.CTkLabel(self.summary_frame, text="",
                                       font=ctk.CTkFont(size=12, weight="bold"),
                                       text_color=colors["danger"])
        self.cost_label.pack(side="right")

        # Results list
        self.results_frame = ctk.CTkScrollableFrame(self.win, fg_color="transparent")
        self.results_frame.pack(fill="both", expand=True, padx=20, pady=(5, 5))

        # Bottom buttons
        btn_frame = ctk.CTkFrame(self.win, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(5, 15))

        self.clean_all_btn = ctk.CTkButton(
            btn_frame, text="🗑 Abort All Orphaned Uploads", width=230, height=36,
            corner_radius=8, font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=colors["danger"], hover_color=colors["danger_hover"],
            command=self._clean_all, state="disabled",
        )
        self.clean_all_btn.pack(side="left", padx=(0, 10))

        self.lifecycle_btn = ctk.CTkButton(
            btn_frame, text="⚙ Set Auto-Cleanup Rule", width=180, height=36,
            corner_radius=8, font=ctk.CTkFont(size=12),
            fg_color=colors["primary"], hover_color=colors["primary_hover"],
            command=self._set_lifecycle_rule, state="disabled",
        )
        self.lifecycle_btn.pack(side="left", padx=(0, 10))

        ctk.CTkButton(btn_frame, text="Close", width=70, height=36,
                      corner_radius=8, fg_color=colors["badge_bg"],
                      hover_color=colors["surface_hover"],
                      text_color=colors["text_primary"],
                      command=self.win.destroy).pack(side="right")

    def _start_scan(self):
        """Scan for incomplete multipart uploads."""
        self.scan_btn.configure(state="disabled")
        self.status_label.configure(text="⏳ Scanning...", text_color="#ff9800")
        self.uploads.clear()
        self.total_wasted = 0

        # Clear previous results
        for widget in self.results_frame.winfo_children():
            widget.destroy()

        def do_scan():
            try:
                s3 = self.app.s3_client.s3_client

                if self.bucket:
                    buckets_to_scan = [self.bucket]
                else:
                    buckets_to_scan = self.app.s3_client.list_buckets()

                for bucket in buckets_to_scan:
                    self.win.after(0, lambda b=bucket: self.status_label.configure(
                        text=f"⏳ Scanning: {b}..."
                    ))

                    try:
                        # List incomplete multipart uploads
                        paginator = s3.get_paginator("list_multipart_uploads")
                        for page in paginator.paginate(Bucket=bucket):
                            for upload in page.get("Uploads", []):
                                upload_id = upload["UploadId"]
                                key = upload["Key"]
                                initiated = upload["Initiated"]

                                # Get parts to calculate size
                                total_size = 0
                                part_count = 0
                                try:
                                    parts_resp = s3.list_parts(
                                        Bucket=bucket, Key=key, UploadId=upload_id
                                    )
                                    for part in parts_resp.get("Parts", []):
                                        total_size += part["Size"]
                                        part_count += 1

                                    # Check for more parts (paginate)
                                    while parts_resp.get("IsTruncated", False):
                                        parts_resp = s3.list_parts(
                                            Bucket=bucket, Key=key, UploadId=upload_id,
                                            PartNumberMarker=parts_resp["NextPartNumberMarker"]
                                        )
                                        for part in parts_resp.get("Parts", []):
                                            total_size += part["Size"]
                                            part_count += 1
                                except Exception:
                                    pass

                                age_days = (datetime.now(initiated.tzinfo) - initiated).days

                                entry = {
                                    "bucket": bucket,
                                    "key": key,
                                    "upload_id": upload_id,
                                    "initiated": initiated.strftime("%Y-%m-%d %H:%M"),
                                    "age_days": age_days,
                                    "size": total_size,
                                    "parts": part_count,
                                }
                                self.uploads.append(entry)
                                self.total_wasted += total_size

                    except Exception:
                        pass  # Skip buckets we can't access

                self.win.after(0, self._show_results)

            except Exception as e:
                self.win.after(0, lambda: self.status_label.configure(
                    text=f"❌ Scan failed: {str(e)[:50]}", text_color="#f44336"
                ))
            finally:
                self.win.after(0, lambda: self.scan_btn.configure(state="normal"))

        threading.Thread(target=do_scan, daemon=True).start()

    def _show_results(self):
        """Display scan results."""
        colors = DARK_THEME if self.app.is_dark else LIGHT_THEME

        if not self.uploads:
            self.status_label.configure(
                text="✅ No orphaned multipart uploads found! Your buckets are clean.",
                text_color=colors["success"]
            )
            self.cost_label.configure(text="$0 wasted")
            return

        # Cost calculation (assuming STANDARD storage)
        wasted_gb = self.total_wasted / (1024 ** 3)
        monthly_waste = wasted_gb * 0.023  # Approximate

        self.status_label.configure(
            text=f"⚠️ Found {len(self.uploads)} orphaned uploads │ "
                 f"{format_size(self.total_wasted)} wasted storage",
            text_color=colors["warning"]
        )
        self.cost_label.configure(
            text=f"💸 Wasting ~${monthly_waste:.4f}/month"
        )

        self.clean_all_btn.configure(state="normal")
        self.lifecycle_btn.configure(state="normal")

        # Render each upload
        for i, upload in enumerate(self.uploads):
            card = ctk.CTkFrame(self.results_frame, fg_color=colors["surface"], corner_radius=6)
            card.pack(fill="x", pady=2)

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=12, pady=8)

            # Left info
            filename = upload["key"].split("/")[-1] if "/" in upload["key"] else upload["key"]
            age_color = colors["danger"] if upload["age_days"] > 7 else colors["warning"]

            info_frame = ctk.CTkFrame(inner, fg_color="transparent")
            info_frame.pack(side="left", fill="x", expand=True)

            ctk.CTkLabel(info_frame, text=f"📄 {filename}",
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=colors["text_primary"]).pack(anchor="w")

            ctk.CTkLabel(info_frame,
                         text=f"Bucket: {upload['bucket']} │ "
                              f"Parts: {upload['parts']} │ "
                              f"Size: {format_size(upload['size'])} │ "
                              f"Age: {upload['age_days']} days │ "
                              f"Started: {upload['initiated']}",
                         font=ctk.CTkFont(size=10),
                         text_color=colors["text_secondary"]).pack(anchor="w")

            # Abort button for individual upload
            ctk.CTkButton(inner, text="🗑 Abort", width=60, height=26,
                          corner_radius=4, font=ctk.CTkFont(size=10),
                          fg_color=colors["danger"], hover_color=colors["danger_hover"],
                          command=lambda idx=i: self._abort_single(idx)).pack(side="right")

    def _abort_single(self, index: int):
        """Abort a single incomplete upload."""
        upload = self.uploads[index]
        try:
            self.app.s3_client.s3_client.abort_multipart_upload(
                Bucket=upload["bucket"],
                Key=upload["key"],
                UploadId=upload["upload_id"],
            )
            self.uploads.pop(index)
            # Refresh display
            for widget in self.results_frame.winfo_children():
                widget.destroy()
            self._show_results()
        except Exception as e:
            messagebox.showerror("Abort Failed", str(e), parent=self.win)

    def _clean_all(self):
        """Abort ALL orphaned multipart uploads."""
        confirm = messagebox.askyesno(
            "Confirm Cleanup",
            f"Abort all {len(self.uploads)} orphaned multipart uploads?\n\n"
            f"This will free {format_size(self.total_wasted)} of wasted storage.\n"
            f"Estimated savings: ~${self.total_wasted / (1024**3) * 0.023:.4f}/month\n\n"
            f"This cannot be undone (but it only removes failed upload chunks,\n"
            f"not your actual files).",
            parent=self.win
        )
        if not confirm:
            return

        self.clean_all_btn.configure(state="disabled")

        def do_clean():
            success = 0
            failed = 0

            for upload in self.uploads:
                try:
                    self.app.s3_client.s3_client.abort_multipart_upload(
                        Bucket=upload["bucket"],
                        Key=upload["key"],
                        UploadId=upload["upload_id"],
                    )
                    success += 1
                except Exception:
                    failed += 1

            self.win.after(0, lambda: self.status_label.configure(
                text=f"✅ Cleaned! {success} uploads aborted, {failed} failed. "
                     f"Freed {format_size(self.total_wasted)}",
                text_color="#00c853"
            ))
            self.win.after(0, lambda: self.cost_label.configure(text="💚 $0 wasted now"))

            # Clear the list
            self.uploads.clear()
            for widget in self.results_frame.winfo_children():
                self.win.after(0, widget.destroy)

            # Notification
            from s3_manager_pro_v5.ui.notifications import send_notification
            send_notification("🧹 Cleanup Complete",
                              f"Removed {success} orphaned uploads. Freed {format_size(self.total_wasted)}")

        threading.Thread(target=do_clean, daemon=True).start()

    def _set_lifecycle_rule(self):
        """Set a lifecycle rule to auto-clean incomplete uploads after N days."""
        colors = DARK_THEME if self.app.is_dark else LIGHT_THEME

        # Ask for days
        dialog = ctk.CTkToplevel(self.win)
        dialog.title("Auto-Cleanup Rule")
        dialog.geometry("400x250")
        dialog.transient(self.win)
        dialog.grab_set()
        dialog.configure(fg_color=colors["bg"])

        ctk.CTkLabel(dialog, text="⚙ Set Auto-Cleanup Lifecycle Rule",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=colors["text_primary"]).pack(pady=(20, 10))

        ctk.CTkLabel(dialog, text="Automatically abort incomplete uploads older than:",
                     font=ctk.CTkFont(size=11),
                     text_color=colors["text_secondary"]).pack()

        days_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        days_frame.pack(pady=10)

        days_entry = ctk.CTkEntry(days_frame, width=60, height=30)
        days_entry.insert(0, "7")
        days_entry.pack(side="left", padx=(0, 5))
        ctk.CTkLabel(days_frame, text="days",
                     text_color=colors["text_primary"]).pack(side="left")

        def apply_rule():
            days = int(days_entry.get().strip() or 7)
            bucket = self.bucket or (self.uploads[0]["bucket"] if self.uploads else "")
            if not bucket:
                return

            try:
                s3 = self.app.s3_client.s3_client

                # Get existing lifecycle rules
                try:
                    existing = s3.get_bucket_lifecycle_configuration(Bucket=bucket)
                    rules = existing.get("Rules", [])
                except Exception:
                    rules = []

                # Add multipart cleanup rule
                rules.append({
                    "ID": "s3-manager-pro-multipart-cleanup",
                    "Status": "Enabled",
                    "Filter": {"Prefix": ""},
                    "AbortIncompleteMultipartUpload": {
                        "DaysAfterInitiation": days
                    },
                })

                s3.put_bucket_lifecycle_configuration(
                    Bucket=bucket,
                    LifecycleConfiguration={"Rules": rules}
                )

                dialog.destroy()
                messagebox.showinfo("Rule Applied",
                                    f"✅ Lifecycle rule set on '{bucket}':\n"
                                    f"Incomplete uploads will be auto-cleaned after {days} days.",
                                    parent=self.win)

            except Exception as e:
                messagebox.showerror("Failed", f"Could not set lifecycle rule:\n{str(e)}", parent=dialog)

        ctk.CTkButton(dialog, text="✓ Apply Rule", width=120, height=32,
                      corner_radius=8, fg_color=colors["success"], hover_color="#1fa339",
                      command=apply_rule).pack(pady=10)
