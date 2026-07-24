"""Object Lock Dialog - View S3 object lock and retention settings."""

import threading
from datetime import datetime

import customtkinter as ctk

from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME
from s3_manager_pro_v5.utils.formatting import format_size


class ObjectLockDialog(ctk.CTkToplevel):
    """Dialog to view object lock, retention, and legal hold settings.

    Displays retention mode (Governance/Compliance), retain until date,
    and legal hold status for a specific S3 object.
    """

    def __init__(self, parent, app, bucket: str, key: str):
        """Initialize the object lock dialog.

        Args:
            parent: Parent widget.
            app: Application instance with S3 client access.
            bucket: S3 bucket name.
            key: S3 object key.
        """
        super().__init__(parent)
        self.app = app
        self.bucket = bucket
        self.key = key

        self.title(f"Object Lock - {key}")
        self.geometry("550x420")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._load_lock_info()

    def _build_ui(self):
        """Build the dialog UI."""
        self.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkLabel(
            self,
            text="Object Lock & Retention",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        )
        header.grid(row=0, column=0, padx=16, pady=(16, 4), sticky="w")

        # Object info
        obj_label = ctk.CTkLabel(
            self,
            text=f"Bucket: {self.bucket}",
            font=ctk.CTkFont(size=12),
            anchor="w",
        )
        obj_label.grid(row=1, column=0, padx=16, pady=(4, 0), sticky="w")

        key_label = ctk.CTkLabel(
            self,
            text=f"Key: {self.key}",
            font=ctk.CTkFont(size=12),
            anchor="w",
        )
        key_label.grid(row=2, column=0, padx=16, pady=(2, 12), sticky="w")

        # Retention section
        retention_frame = ctk.CTkFrame(self)
        retention_frame.grid(row=3, column=0, padx=16, pady=8, sticky="ew")
        retention_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            retention_frame,
            text="Retention Settings",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, padx=12, pady=(12, 8), sticky="w")

        # Retention mode
        ctk.CTkLabel(
            retention_frame,
            text="Mode:",
            font=ctk.CTkFont(size=12),
        ).grid(row=1, column=0, padx=(12, 8), pady=4, sticky="w")

        self.mode_label = ctk.CTkLabel(
            retention_frame,
            text="Loading...",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        )
        self.mode_label.grid(row=1, column=1, padx=(0, 12), pady=4, sticky="w")

        # Retain until date
        ctk.CTkLabel(
            retention_frame,
            text="Retain Until:",
            font=ctk.CTkFont(size=12),
        ).grid(row=2, column=0, padx=(12, 8), pady=4, sticky="w")

        self.retain_until_label = ctk.CTkLabel(
            retention_frame,
            text="Loading...",
            font=ctk.CTkFont(size=12),
            anchor="w",
        )
        self.retain_until_label.grid(row=2, column=1, padx=(0, 12), pady=4, sticky="w")

        # Remaining days
        ctk.CTkLabel(
            retention_frame,
            text="Remaining:",
            font=ctk.CTkFont(size=12),
        ).grid(row=3, column=0, padx=(12, 8), pady=(4, 12), sticky="w")

        self.remaining_label = ctk.CTkLabel(
            retention_frame,
            text="Loading...",
            font=ctk.CTkFont(size=12),
            anchor="w",
        )
        self.remaining_label.grid(
            row=3, column=1, padx=(0, 12), pady=(4, 12), sticky="w"
        )

        # Legal hold section
        legal_frame = ctk.CTkFrame(self)
        legal_frame.grid(row=4, column=0, padx=16, pady=8, sticky="ew")
        legal_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            legal_frame,
            text="Legal Hold",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, padx=12, pady=(12, 8), sticky="w")

        ctk.CTkLabel(
            legal_frame,
            text="Status:",
            font=ctk.CTkFont(size=12),
        ).grid(row=1, column=0, padx=(12, 8), pady=(4, 12), sticky="w")

        self.legal_hold_label = ctk.CTkLabel(
            legal_frame,
            text="Loading...",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        )
        self.legal_hold_label.grid(
            row=1, column=1, padx=(0, 12), pady=(4, 12), sticky="w"
        )

        # Status
        self.status_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=11),
            anchor="w",
        )
        self.status_label.grid(row=5, column=0, padx=16, pady=(8, 4), sticky="w")

        # Close button
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=6, column=0, padx=16, pady=(4, 16), sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)

        self.refresh_btn = ctk.CTkButton(
            button_frame,
            text="Refresh",
            width=100,
            command=self._load_lock_info,
        )
        self.refresh_btn.grid(row=0, column=1, padx=4)

        self.close_btn = ctk.CTkButton(
            button_frame,
            text="Close",
            width=100,
            command=self.destroy,
        )
        self.close_btn.grid(row=0, column=2, padx=4)

    def _load_lock_info(self):
        """Load object lock information from S3."""
        self._set_status("Loading object lock information...")
        thread = threading.Thread(target=self._fetch_lock_info, daemon=True)
        thread.start()

    def _fetch_lock_info(self):
        """Fetch retention and legal hold info in a background thread."""
        retention_mode = "Not set"
        retain_until = "N/A"
        remaining = "N/A"
        legal_hold = "Not set"
        errors = []

        s3_client = self.app.s3_client

        # Fetch retention
        try:
            response = s3_client.get_object_retention(
                Bucket=self.bucket, Key=self.key
            )
            retention = response.get("Retention", {})
            retention_mode = retention.get("Mode", "Not set")
            retain_date = retention.get("RetainUntilDate")

            if retain_date:
                if isinstance(retain_date, datetime):
                    retain_until = retain_date.strftime("%Y-%m-%d %H:%M:%S UTC")
                    delta = retain_date.replace(tzinfo=None) - datetime.utcnow()
                    if delta.days > 0:
                        remaining = f"{delta.days} days remaining"
                    elif delta.days == 0:
                        remaining = "Expires today"
                    else:
                        remaining = "Expired"
                else:
                    retain_until = str(retain_date)
                    remaining = "Unable to calculate"

        except Exception as e:
            if "ObjectLockConfigurationNotFoundError" in str(e):
                retention_mode = "Not configured"
                retain_until = "Object Lock not enabled"
                remaining = "N/A"
            elif "NoSuchObjectLockConfiguration" in str(e):
                retention_mode = "Not configured"
                retain_until = "N/A"
                remaining = "N/A"
            else:
                errors.append(f"Retention: {e}")
                retention_mode = "Error"

        # Fetch legal hold
        try:
            response = s3_client.get_object_legal_hold(
                Bucket=self.bucket, Key=self.key
            )
            hold = response.get("LegalHold", {})
            status = hold.get("Status", "OFF")
            legal_hold = status
        except Exception as e:
            if "ObjectLockConfigurationNotFoundError" in str(e):
                legal_hold = "Not configured"
            elif "NoSuchObjectLockConfiguration" in str(e):
                legal_hold = "Not configured"
            else:
                errors.append(f"Legal Hold: {e}")
                legal_hold = "Error"

        # Update UI
        self.after(0, self._update_retention_display, retention_mode, retain_until, remaining)
        self.after(0, self._update_legal_hold_display, legal_hold)

        if errors:
            self.after(0, self._set_status, f"Errors: {'; '.join(errors)}")
        else:
            self.after(0, self._set_status, "Loaded successfully.")

    def _update_retention_display(
        self, mode: str, retain_until: str, remaining: str
    ):
        """Update retention display labels.

        Args:
            mode: Retention mode (Governance/Compliance/Not set).
            retain_until: Retain until date string.
            remaining: Remaining time description.
        """
        self.mode_label.configure(text=mode)
        self.retain_until_label.configure(text=retain_until)
        self.remaining_label.configure(text=remaining)

        # Color coding for mode
        if mode == "COMPLIANCE":
            self.mode_label.configure(text_color="red")
        elif mode == "GOVERNANCE":
            self.mode_label.configure(text_color="orange")
        else:
            self.mode_label.configure(text_color=("gray20", "gray80"))

    def _update_legal_hold_display(self, status: str):
        """Update legal hold display label.

        Args:
            status: Legal hold status string.
        """
        self.legal_hold_label.configure(text=status)

        if status == "ON":
            self.legal_hold_label.configure(text_color="red")
        elif status == "OFF":
            self.legal_hold_label.configure(text_color="green")
        else:
            self.legal_hold_label.configure(text_color=("gray20", "gray80"))

    def _set_status(self, message: str):
        """Update the status label.

        Args:
            message: Status message to display.
        """
        self.status_label.configure(text=message)
