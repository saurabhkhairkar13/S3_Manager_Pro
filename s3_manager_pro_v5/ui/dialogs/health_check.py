"""S3 Health Check — Security audit across all buckets."""
import threading
import customtkinter as ctk
from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME


class HealthCheckDialog:
    """Scan all buckets for security/configuration issues."""

    def __init__(self, parent, app):
        self.app = app
        self.findings = []

        colors = DARK_THEME if app.is_dark else LIGHT_THEME

        self.win = ctk.CTkToplevel(parent)
        self.win.title("🛡️ S3 Health Check")
        self.win.geometry("700x550")
        self.win.transient(parent)
        self.win.grab_set()
        self.win.resizable(True, True)
        self.win.configure(fg_color=colors["bg"])

        ctk.CTkLabel(self.win, text="🛡️ S3 Security & Health Check",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=colors["text_primary"]).pack(pady=(15, 5))
        ctk.CTkLabel(self.win, text="Scanning all buckets for security and configuration issues...",
                     font=ctk.CTkFont(size=11),
                     text_color=colors["text_secondary"]).pack(pady=(0, 10))

        # Progress
        self.progress = ctk.CTkProgressBar(self.win, height=8, corner_radius=4)
        self.progress.pack(fill="x", padx=20, pady=(0, 5))
        self.progress.set(0)

        self.status_label = ctk.CTkLabel(self.win, text="⏳ Starting scan...",
                                         font=ctk.CTkFont(size=11),
                                         text_color=colors["text_secondary"])
        self.status_label.pack(anchor="w", padx=20)

        # Results
        self.results_frame = ctk.CTkScrollableFrame(self.win, fg_color="transparent")
        self.results_frame.pack(fill="both", expand=True, padx=20, pady=(10, 5))

        # Bottom
        btn_frame = ctk.CTkFrame(self.win, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(5, 15))

        self.export_btn = ctk.CTkButton(btn_frame, text="📋 Export Report", width=130, height=32,
                                        corner_radius=6, fg_color=colors["primary"],
                                        hover_color=colors["primary_hover"],
                                        command=self._export_report, state="disabled")
        self.export_btn.pack(side="left", padx=(0, 10))

        ctk.CTkButton(btn_frame, text="Close", width=70, height=32,
                      corner_radius=6, fg_color=colors["badge_bg"],
                      hover_color=colors["surface_hover"],
                      text_color=colors["text_primary"],
                      command=self.win.destroy).pack(side="right")

        # Start scan
        threading.Thread(target=self._run_scan, daemon=True).start()

    def _run_scan(self):
        """Scan all buckets for issues."""
        try:
            buckets = self.app.s3_client.list_buckets()
            total = len(buckets)

            for i, bucket in enumerate(buckets):
                self.win.after(0, lambda b=bucket, p=(i+1)/total: self._update_progress(b, p))
                self._check_bucket(bucket)

            self.win.after(0, self._show_results)

        except Exception as e:
            self.win.after(0, lambda: self.status_label.configure(
                text=f"❌ Scan failed: {str(e)[:50]}", text_color="#f44336"
            ))

    def _update_progress(self, bucket: str, pct: float):
        self.progress.set(pct)
        self.status_label.configure(text=f"Scanning: {bucket}...")

    def _check_bucket(self, bucket: str):
        """Run all checks on a single bucket."""
        s3 = self.app.s3_client.s3_client

        # Check 1: Public access
        try:
            acl = s3.get_bucket_acl(Bucket=bucket)
            for grant in acl.get("Grants", []):
                grantee = grant.get("Grantee", {})
                uri = grantee.get("URI", "")
                if "AllUsers" in uri or "AuthenticatedUsers" in uri:
                    self.findings.append({
                        "bucket": bucket,
                        "severity": "CRITICAL",
                        "check": "Public Access",
                        "detail": f"Bucket has public ACL grant: {grant.get('Permission', '')}",
                    })
        except Exception:
            pass

        # Check 2: Encryption
        try:
            s3.get_bucket_encryption(Bucket=bucket)
        except Exception as e:
            if "ServerSideEncryptionConfigurationNotFoundError" in str(e):
                self.findings.append({
                    "bucket": bucket,
                    "severity": "HIGH",
                    "check": "Encryption",
                    "detail": "No default encryption configured",
                })

        # Check 3: Versioning
        try:
            ver = s3.get_bucket_versioning(Bucket=bucket)
            status = ver.get("Status", "Disabled")
            if status != "Enabled":
                self.findings.append({
                    "bucket": bucket,
                    "severity": "MEDIUM",
                    "check": "Versioning",
                    "detail": f"Versioning is {status or 'Disabled'}",
                })
        except Exception:
            pass

        # Check 4: Logging
        try:
            logging_resp = s3.get_bucket_logging(Bucket=bucket)
            if not logging_resp.get("LoggingEnabled"):
                self.findings.append({
                    "bucket": bucket,
                    "severity": "LOW",
                    "check": "Access Logging",
                    "detail": "Server access logging not enabled",
                })
        except Exception:
            pass

        # Check 5: Lifecycle
        try:
            s3.get_bucket_lifecycle_configuration(Bucket=bucket)
        except Exception as e:
            if "NoSuchLifecycleConfiguration" in str(e):
                self.findings.append({
                    "bucket": bucket,
                    "severity": "LOW",
                    "check": "Lifecycle",
                    "detail": "No lifecycle rules configured (consider for cost optimization)",
                })

        # Check 6: Public Block
        try:
            pub_block = s3.get_public_access_block(Bucket=bucket)
            config = pub_block.get("PublicAccessBlockConfiguration", {})
            if not all([
                config.get("BlockPublicAcls", False),
                config.get("IgnorePublicAcls", False),
                config.get("BlockPublicPolicy", False),
                config.get("RestrictPublicBuckets", False),
            ]):
                self.findings.append({
                    "bucket": bucket,
                    "severity": "HIGH",
                    "check": "Public Access Block",
                    "detail": "Not all public access blocks are enabled",
                })
        except Exception:
            self.findings.append({
                "bucket": bucket,
                "severity": "MEDIUM",
                "check": "Public Access Block",
                "detail": "Could not verify public access block settings",
            })

    def _show_results(self):
        """Display scan results."""
        colors = DARK_THEME if self.app.is_dark else LIGHT_THEME
        self.progress.set(1)

        # Summary
        critical = sum(1 for f in self.findings if f["severity"] == "CRITICAL")
        high = sum(1 for f in self.findings if f["severity"] == "HIGH")
        medium = sum(1 for f in self.findings if f["severity"] == "MEDIUM")
        low = sum(1 for f in self.findings if f["severity"] == "LOW")

        if not self.findings:
            self.status_label.configure(text="✅ All checks passed! No issues found.", text_color="#00c853")
            return

        self.status_label.configure(
            text=f"Found {len(self.findings)} issues: "
                 f"🔴 {critical} Critical │ 🟠 {high} High │ 🟡 {medium} Medium │ 🔵 {low} Low",
            text_color="#ff9800" if critical == 0 else "#f44336"
        )
        self.export_btn.configure(state="normal")

        # Severity colors
        sev_colors = {
            "CRITICAL": "#f44336",
            "HIGH": "#ff9800",
            "MEDIUM": "#ffeb3b",
            "LOW": "#2196f3",
        }

        # Sort by severity
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        sorted_findings = sorted(self.findings, key=lambda f: severity_order.get(f["severity"], 4))

        for finding in sorted_findings:
            card = ctk.CTkFrame(self.results_frame, fg_color=colors["surface"], corner_radius=6)
            card.pack(fill="x", pady=2)

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=10, pady=6)

            sev_color = sev_colors.get(finding["severity"], "#888")
            ctk.CTkLabel(inner, text=f"● {finding['severity']}",
                         font=ctk.CTkFont(size=10, weight="bold"),
                         text_color=sev_color, width=70).pack(side="left")

            ctk.CTkLabel(inner, text=f"{finding['bucket']}",
                         font=ctk.CTkFont(size=10),
                         text_color=colors["primary"], width=120).pack(side="left", padx=(5, 10))

            ctk.CTkLabel(inner, text=f"{finding['check']}: {finding['detail']}",
                         font=ctk.CTkFont(size=10),
                         text_color=colors["text_primary"],
                         wraplength=350, justify="left").pack(side="left", fill="x")

    def _export_report(self):
        """Export findings to CSV."""
        import csv
        from tkinter import filedialog
        from datetime import datetime

        filepath = filedialog.asksaveasfilename(
            parent=self.win,
            title="Export Health Check Report",
            defaultextension=".csv",
            initialfile=f"s3_health_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            filetypes=[("CSV", "*.csv")],
        )
        if not filepath:
            return

        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Severity", "Bucket", "Check", "Detail"])
                for finding in self.findings:
                    writer.writerow([
                        finding["severity"],
                        finding["bucket"],
                        finding["check"],
                        finding["detail"],
                    ])

            from tkinter import messagebox
            messagebox.showinfo("Exported", f"Report saved to:\n{filepath}", parent=self.win)
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Export Failed", str(e), parent=self.win)
