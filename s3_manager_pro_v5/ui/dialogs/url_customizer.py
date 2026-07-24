"""Object URL Customizer Dialog for S3 Manager Pro v5.0."""

import customtkinter as ctk

from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME
from s3_manager_pro_v5.utils.formatting import format_size


class URLCustomizerDialog:
    """Display various URL formats for an S3 object with copy buttons."""

    def __init__(self, parent, app, bucket: str, key: str, region: str):
        self.parent = parent
        self.app = app
        self.bucket = bucket
        self.key = key
        self.region = region

        self._build_ui()

    def _build_ui(self):
        """Build the dialog UI."""
        self.dialog = ctk.CTkToplevel(self.parent)
        self.dialog.title(f"URL Formats - {self.key.rsplit('/', 1)[-1]}")
        self.dialog.geometry("700x470")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

        # Header
        ctk.CTkLabel(
            self.dialog,
            text="🔗 Object URL Formats",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=15, pady=(15, 5))

        ctk.CTkLabel(
            self.dialog,
            text=f"Bucket: {self.bucket} | Key: {self.key}",
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=15, pady=(0, 15))

        # Generate URLs
        urls = self._generate_urls()

        # Display each URL format
        for label, url in urls:
            self._create_url_row(label, url)

        # Close button
        ctk.CTkButton(
            self.dialog,
            text="Close",
            command=self.dialog.destroy,
            width=100,
        ).pack(pady=(20, 15))

    def _generate_urls(self) -> list[tuple[str, str]]:
        """Generate all URL formats for the object."""
        bucket = self.bucket
        key = self.key
        region = self.region

        # Virtual-hosted style
        if region and region != "us-east-1":
            virtual_hosted = f"https://{bucket}.s3.{region}.amazonaws.com/{key}"
        else:
            virtual_hosted = f"https://{bucket}.s3.amazonaws.com/{key}"

        # Path-style
        if region and region != "us-east-1":
            path_style = f"https://s3.{region}.amazonaws.com/{bucket}/{key}"
        else:
            path_style = f"https://s3.amazonaws.com/{bucket}/{key}"

        # S3 URI
        s3_uri = f"s3://{bucket}/{key}"

        # ARN
        arn = f"arn:aws:s3:::{bucket}/{key}"

        return [
            ("Virtual-Hosted Style", virtual_hosted),
            ("Path Style", path_style),
            ("S3 URI", s3_uri),
            ("ARN", arn),
        ]

    def _create_url_row(self, label: str, url: str):
        """Create a row with label, URL display, and copy button."""
        row_frame = ctk.CTkFrame(self.dialog)
        row_frame.pack(fill="x", padx=15, pady=5)

        # Label
        ctk.CTkLabel(
            row_frame,
            text=f"{label}:",
            font=ctk.CTkFont(size=12, weight="bold"),
            width=160,
            anchor="w",
        ).pack(side="left", padx=(10, 5), pady=8)

        # URL entry (read-only via disabled state workaround)
        url_entry = ctk.CTkEntry(row_frame, width=400)
        url_entry.pack(side="left", padx=5, pady=8, fill="x", expand=True)
        url_entry.insert(0, url)
        url_entry.configure(state="disabled")

        # Copy button
        copy_btn = ctk.CTkButton(
            row_frame,
            text="📋",
            width=40,
            command=lambda u=url, b=copy_btn: self._copy_url(u, b),
        )
        copy_btn.pack(side="right", padx=(5, 10), pady=8)

    def _copy_url(self, url: str, button: ctk.CTkButton):
        """Copy the URL to clipboard and show feedback."""
        self.dialog.clipboard_clear()
        self.dialog.clipboard_append(url)
        original_text = button.cget("text")
        button.configure(text="✅")
        self.dialog.after(1500, lambda: button.configure(text=original_text))
