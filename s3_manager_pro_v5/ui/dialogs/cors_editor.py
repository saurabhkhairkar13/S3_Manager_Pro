"""CORS Editor Dialog - View and edit S3 bucket CORS configuration."""

import json
import threading

import customtkinter as ctk

from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME
from s3_manager_pro_v5.utils.formatting import format_size

# Common CORS presets
CORS_PRESETS = {
    "Allow All Origins": {
        "AllowedHeaders": ["*"],
        "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
        "AllowedOrigins": ["*"],
        "ExposeHeaders": ["ETag", "x-amz-request-id"],
        "MaxAgeSeconds": 3600,
    },
    "Allow Specific Origin": {
        "AllowedHeaders": ["*"],
        "AllowedMethods": ["GET", "PUT", "POST"],
        "AllowedOrigins": ["https://example.com"],
        "ExposeHeaders": ["ETag"],
        "MaxAgeSeconds": 3600,
    },
    "Read-Only (GET/HEAD)": {
        "AllowedHeaders": ["Authorization"],
        "AllowedMethods": ["GET", "HEAD"],
        "AllowedOrigins": ["*"],
        "ExposeHeaders": [],
        "MaxAgeSeconds": 86400,
    },
}


class CORSEditorDialog(ctk.CTkToplevel):
    """Dialog to view and edit S3 bucket CORS configuration.

    Loads current CORS rules, allows JSON editing, and supports
    adding common presets.
    """

    def __init__(self, parent, app, bucket: str):
        """Initialize the CORS editor dialog.

        Args:
            parent: Parent widget.
            app: Application instance with S3 client access.
            bucket: S3 bucket name.
        """
        super().__init__(parent)
        self.app = app
        self.bucket = bucket

        self.title(f"CORS Configuration - {bucket}")
        self.geometry("750x600")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._load_cors()

    def _build_ui(self):
        """Build the dialog UI."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Header
        header = ctk.CTkLabel(
            self,
            text=f"CORS Rules: {self.bucket}",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        header.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="w")

        # Preset buttons frame
        preset_frame = ctk.CTkFrame(self, fg_color="transparent")
        preset_frame.grid(row=1, column=0, padx=16, pady=(0, 8), sticky="ew")

        preset_label = ctk.CTkLabel(
            preset_frame,
            text="Add Preset:",
            font=ctk.CTkFont(size=12),
        )
        preset_label.pack(side="left", padx=(0, 8))

        for preset_name in CORS_PRESETS:
            btn = ctk.CTkButton(
                preset_frame,
                text=preset_name,
                width=140,
                height=28,
                font=ctk.CTkFont(size=11),
                command=lambda name=preset_name: self._add_preset(name),
            )
            btn.pack(side="left", padx=4)

        # Text editor for CORS JSON
        self.text_editor = ctk.CTkTextbox(
            self,
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="none",
        )
        self.text_editor.grid(row=2, column=0, padx=16, pady=8, sticky="nsew")

        # Status label
        self.status_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=11),
            anchor="w",
        )
        self.status_label.grid(row=3, column=0, padx=16, pady=(0, 4), sticky="w")

        # Button frame
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=4, column=0, padx=16, pady=(4, 16), sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)

        self.validate_btn = ctk.CTkButton(
            button_frame,
            text="Validate JSON",
            width=120,
            command=self._validate_json,
        )
        self.validate_btn.grid(row=0, column=1, padx=4)

        self.delete_btn = ctk.CTkButton(
            button_frame,
            text="Delete CORS",
            width=110,
            fg_color="red",
            hover_color="darkred",
            command=self._delete_cors,
        )
        self.delete_btn.grid(row=0, column=2, padx=4)

        self.save_btn = ctk.CTkButton(
            button_frame,
            text="Save",
            width=100,
            command=self._save,
        )
        self.save_btn.grid(row=0, column=3, padx=4)

        self.cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancel",
            width=100,
            command=self.destroy,
        )
        self.cancel_btn.grid(row=0, column=4, padx=4)

    def _load_cors(self):
        """Load current CORS configuration from S3."""
        self._set_status("Loading CORS configuration...")
        thread = threading.Thread(target=self._fetch_cors, daemon=True)
        thread.start()

    def _fetch_cors(self):
        """Fetch CORS configuration in a background thread."""
        try:
            s3_client = self.app.s3_client
            response = s3_client.get_bucket_cors(Bucket=self.bucket)
            rules = response.get("CORSRules", [])
            content = json.dumps({"CORSRules": rules}, indent=2)
            self.after(0, self._display_content, content)
            self.after(
                0, self._set_status, f"Loaded {len(rules)} CORS rule(s)."
            )

        except Exception as e:
            if "NoSuchCORSConfiguration" in str(e):
                empty = json.dumps({"CORSRules": []}, indent=2)
                self.after(0, self._display_content, empty)
                self.after(
                    0,
                    self._set_status,
                    "No CORS configuration found. Add rules below.",
                )
            else:
                self.after(0, self._set_status, f"Error loading CORS: {e}")
                self.after(0, self._display_content, "")

    def _display_content(self, content: str):
        """Display content in the text editor.

        Args:
            content: Text content to display.
        """
        self.text_editor.delete("1.0", "end")
        self.text_editor.insert("1.0", content)

    def _add_preset(self, preset_name: str):
        """Add a preset CORS rule to the current configuration.

        Args:
            preset_name: Name of the preset to add.
        """
        content = self.text_editor.get("1.0", "end").strip()

        try:
            current = json.loads(content) if content else {"CORSRules": []}
        except json.JSONDecodeError:
            current = {"CORSRules": []}

        rules = current.get("CORSRules", [])
        rules.append(CORS_PRESETS[preset_name].copy())
        current["CORSRules"] = rules

        self._display_content(json.dumps(current, indent=2))
        self._set_status(f"Added preset: {preset_name}")

    def _validate_json(self):
        """Validate the JSON content in the editor."""
        content = self.text_editor.get("1.0", "end").strip()
        try:
            parsed = json.loads(content)
            rules = parsed.get("CORSRules", [])
            if not isinstance(rules, list):
                self._set_status("✗ CORSRules must be a list")
                return
            self._set_status(f"✓ Valid JSON with {len(rules)} rule(s)")
        except json.JSONDecodeError as e:
            self._set_status(f"✗ Invalid JSON: {e}")

    def _save(self):
        """Save the CORS configuration to S3."""
        content = self.text_editor.get("1.0", "end").strip()

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as e:
            self._set_status(f"✗ Cannot save - invalid JSON: {e}")
            return

        rules = parsed.get("CORSRules", [])
        if not rules:
            self._set_status("✗ No CORS rules defined. Use 'Delete CORS' to remove.")
            return

        self._set_status("Saving CORS configuration...")
        self.save_btn.configure(state="disabled")

        thread = threading.Thread(
            target=self._do_save, args=(rules,), daemon=True
        )
        thread.start()

    def _do_save(self, rules: list):
        """Save CORS rules in a background thread.

        Args:
            rules: List of CORS rule dictionaries.
        """
        try:
            s3_client = self.app.s3_client
            s3_client.put_bucket_cors(
                Bucket=self.bucket,
                CORSConfiguration={"CORSRules": rules},
            )
            self.after(
                0,
                self._set_status,
                f"✓ CORS configuration saved ({len(rules)} rule(s)).",
            )
        except Exception as e:
            self.after(0, self._set_status, f"✗ Save failed: {e}")
        finally:
            self.after(0, lambda: self.save_btn.configure(state="normal"))

    def _delete_cors(self):
        """Delete the CORS configuration from the bucket."""
        self._set_status("Deleting CORS configuration...")
        thread = threading.Thread(target=self._do_delete, daemon=True)
        thread.start()

    def _do_delete(self):
        """Delete CORS in a background thread."""
        try:
            s3_client = self.app.s3_client
            s3_client.delete_bucket_cors(Bucket=self.bucket)
            self.after(0, self._set_status, "✓ CORS configuration deleted.")
            empty = json.dumps({"CORSRules": []}, indent=2)
            self.after(0, self._display_content, empty)
        except Exception as e:
            self.after(0, self._set_status, f"✗ Delete failed: {e}")

    def _set_status(self, message: str):
        """Update the status label.

        Args:
            message: Status message to display.
        """
        self.status_label.configure(text=message)
