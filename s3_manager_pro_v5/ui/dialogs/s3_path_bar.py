"""S3 Path Bar Widget - Navigate S3 by typing s3://bucket/path URLs."""

import customtkinter as ctk

from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME
from s3_manager_pro_v5.utils.formatting import format_size


class S3PathBar(ctk.CTkFrame):
    """A navigation bar widget for typing and navigating to S3 paths.

    Users can type s3://bucket/prefix URLs and press Enter or click Go
    to navigate directly to that location.
    """

    def __init__(self, parent, app):
        """Initialize the S3 path bar.

        Args:
            parent: Parent widget.
            app: Application instance with navigate_to(bucket, prefix) method.
        """
        super().__init__(parent)
        self.app = app

        self._build_ui()

    def _build_ui(self):
        """Build the path bar UI components."""
        self.grid_columnconfigure(1, weight=1)

        # Label
        self.label = ctk.CTkLabel(
            self,
            text="S3 Path:",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.label.grid(row=0, column=0, padx=(8, 4), pady=6, sticky="w")

        # Entry field
        self.path_entry = ctk.CTkEntry(
            self,
            placeholder_text="s3://bucket-name/prefix/path/",
            font=ctk.CTkFont(size=12),
        )
        self.path_entry.grid(row=0, column=1, padx=4, pady=6, sticky="ew")
        self.path_entry.bind("<Return>", lambda event: self._on_navigate())

        # Go button
        self.go_button = ctk.CTkButton(
            self,
            text="Go",
            width=60,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_navigate,
        )
        self.go_button.grid(row=0, column=2, padx=(4, 8), pady=6)

    def set_path(self, bucket: str, prefix: str = ""):
        """Update the displayed path based on current navigation state.

        Args:
            bucket: The S3 bucket name.
            prefix: The S3 key prefix (folder path).
        """
        if bucket:
            path = f"s3://{bucket}/{prefix}" if prefix else f"s3://{bucket}/"
        else:
            path = "s3://"

        self.path_entry.delete(0, "end")
        self.path_entry.insert(0, path)

    def _on_navigate(self):
        """Parse the entered S3 URL and navigate to it."""
        raw_path = self.path_entry.get().strip()

        # Strip the s3:// prefix
        if raw_path.startswith("s3://"):
            path = raw_path[5:]
        elif raw_path.startswith("S3://"):
            path = raw_path[5:]
        else:
            path = raw_path

        # Remove leading slash if present
        path = path.lstrip("/")

        if not path:
            # Navigate to bucket list (root)
            self.app.navigate_to("", "")
            return

        # Split into bucket and prefix
        parts = path.split("/", 1)
        bucket = parts[0]
        prefix = parts[1] if len(parts) > 1 else ""

        self.app.navigate_to(bucket, prefix)

    def get_current_path(self) -> str:
        """Return the current path string in the entry field.

        Returns:
            The current S3 path as a string.
        """
        return self.path_entry.get().strip()
