"""Website Hosting Dialog - Configure S3 static website hosting."""

import json
import threading

import customtkinter as ctk

from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME
from s3_manager_pro_v5.utils.formatting import format_size


class WebsiteHostingDialog(ctk.CTkToplevel):
    """Dialog to configure S3 static website hosting.

    Allows enabling/disabling website hosting, setting index and error
    documents, and configuring redirect rules.
    """

    def __init__(self, parent, app, bucket: str):
        """Initialize the website hosting dialog.

        Args:
            parent: Parent widget.
            app: Application instance with S3 client access.
            bucket: S3 bucket name.
        """
        super().__init__(parent)
        self.app = app
        self.bucket = bucket

        self.title(f"Static Website Hosting - {bucket}")
        self.geometry("650x580")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self._hosting_enabled = ctk.BooleanVar(value=False)

        self._build_ui()
        self._load_config()

    def _build_ui(self):
        """Build the dialog UI."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)

        # Header
        header = ctk.CTkLabel(
            self,
            text=f"Website Hosting: {self.bucket}",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        header.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="w")

        # Enable/Disable toggle
        toggle_frame = ctk.CTkFrame(self, fg_color="transparent")
        toggle_frame.grid(row=1, column=0, padx=16, pady=(8, 4), sticky="ew")

        self.enable_switch = ctk.CTkSwitch(
            toggle_frame,
            text="Enable Static Website Hosting",
            variable=self._hosting_enabled,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_toggle,
        )
        self.enable_switch.pack(side="left")

        # Configuration frame
        self.config_frame = ctk.CTkFrame(self)
        self.config_frame.grid(row=2, column=0, padx=16, pady=8, sticky="ew")
        self.config_frame.grid_columnconfigure(1, weight=1)

        # Index document
        ctk.CTkLabel(
            self.config_frame,
            text="Index Document:",
            font=ctk.CTkFont(size=12),
        ).grid(row=0, column=0, padx=(12, 8), pady=8, sticky="w")

        self.index_entry = ctk.CTkEntry(
            self.config_frame,
            placeholder_text="index.html",
            font=ctk.CTkFont(size=12),
        )
        self.index_entry.grid(row=0, column=1, padx=(0, 12), pady=8, sticky="ew")

        # Error document
        ctk.CTkLabel(
            self.config_frame,
            text="Error Document:",
            font=ctk.CTkFont(size=12),
        ).grid(row=1, column=0, padx=(12, 8), pady=8, sticky="w")

        self.error_entry = ctk.CTkEntry(
            self.config_frame,
            placeholder_text="error.html",
            font=ctk.CTkFont(size=12),
        )
        self.error_entry.grid(row=1, column=1, padx=(0, 12), pady=8, sticky="ew")

        # Website endpoint display
        ctk.CTkLabel(
            self.config_frame,
            text="Endpoint:",
            font=ctk.CTkFont(size=12),
        ).grid(row=2, column=0, padx=(12, 8), pady=8, sticky="w")

        self.endpoint_label = ctk.CTkLabel(
            self.config_frame,
            text=f"http://{self.bucket}.s3-website-<region>.amazonaws.com",
            font=ctk.CTkFont(size=11),
            anchor="w",
        )
        self.endpoint_label.grid(row=2, column=1, padx=(0, 12), pady=8, sticky="w")

        # Redirect rules section
        redirect_label = ctk.CTkLabel(
            self,
            text="Redirect Rules (JSON, optional):",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        )
        redirect_label.grid(row=3, column=0, padx=16, pady=(12, 4), sticky="w")

        # Redirect rules hint
        hint_label = ctk.CTkLabel(
            self,
            text="Define routing rules as a JSON array. Leave empty for no redirect rules.",
            font=ctk.CTkFont(size=11),
            anchor="w",
        )
        hint_label.grid(row=4, column=0, padx=16, pady=(0, 4), sticky="w")

        # Redirect rules text editor
        self.redirect_editor = ctk.CTkTextbox(
            self,
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="none",
            height=150,
        )
        self.redirect_editor.grid(row=5, column=0, padx=16, pady=(0, 8), sticky="nsew")

        # Status
        self.status_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=11),
            anchor="w",
        )
        self.status_label.grid(row=6, column=0, padx=16, pady=(0, 4), sticky="w")

        # Button frame
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=7, column=0, padx=16, pady=(4, 16), sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)

        self.save_btn = ctk.CTkButton(
            button_frame,
            text="Save",
            width=100,
            command=self._save,
        )
        self.save_btn.grid(row=0, column=1, padx=4)

        self.cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancel",
            width=100,
            command=self.destroy,
        )
        self.cancel_btn.grid(row=0, column=2, padx=4)

    def _on_toggle(self):
        """Handle the enable/disable toggle."""
        enabled = self._hosting_enabled.get()
        state = "normal" if enabled else "disabled"
        self.index_entry.configure(state=state)
        self.error_entry.configure(state=state)
        self.redirect_editor.configure(state=state)

    def _load_config(self):
        """Load current website hosting configuration from S3."""
        self._set_status("Loading website configuration...")
        thread = threading.Thread(target=self._fetch_config, daemon=True)
        thread.start()

    def _fetch_config(self):
        """Fetch website hosting config in a background thread."""
        try:
            s3_client = self.app.s3_client
            response = s3_client.get_bucket_website(Bucket=self.bucket)
            response.pop("ResponseMetadata", None)

            index_doc = response.get("IndexDocument", {}).get("Suffix", "")
            error_doc = response.get("ErrorDocument", {}).get("Key", "")
            redirect_rules = response.get("RoutingRules", [])

            self.after(0, self._populate_config, index_doc, error_doc, redirect_rules)
            self.after(0, self._set_status, "Website hosting is enabled.")

        except Exception as e:
            if "NoSuchWebsiteConfiguration" in str(e):
                self.after(0, self._set_hosting_disabled)
                self.after(
                    0,
                    self._set_status,
                    "Website hosting is not enabled for this bucket.",
                )
            else:
                self.after(0, self._set_status, f"Error loading config: {e}")

    def _populate_config(
        self, index_doc: str, error_doc: str, redirect_rules: list
    ):
        """Populate the UI with loaded configuration.

        Args:
            index_doc: Index document suffix.
            error_doc: Error document key.
            redirect_rules: List of routing rules.
        """
        self._hosting_enabled.set(True)
        self._on_toggle()

        self.index_entry.delete(0, "end")
        self.index_entry.insert(0, index_doc)

        self.error_entry.delete(0, "end")
        self.error_entry.insert(0, error_doc)

        if redirect_rules:
            rules_json = json.dumps(redirect_rules, indent=2)
            self.redirect_editor.delete("1.0", "end")
            self.redirect_editor.insert("1.0", rules_json)

    def _set_hosting_disabled(self):
        """Set UI to reflect that hosting is disabled."""
        self._hosting_enabled.set(False)
        self._on_toggle()

    def _save(self):
        """Save the website hosting configuration."""
        enabled = self._hosting_enabled.get()

        if not enabled:
            # Delete website configuration
            self._set_status("Disabling website hosting...")
            self.save_btn.configure(state="disabled")
            thread = threading.Thread(target=self._do_delete, daemon=True)
            thread.start()
            return

        # Validate inputs
        index_doc = self.index_entry.get().strip()
        if not index_doc:
            self._set_status("✗ Index document is required.")
            return

        error_doc = self.error_entry.get().strip()
        redirect_text = self.redirect_editor.get("1.0", "end").strip()

        # Parse redirect rules if provided
        redirect_rules = None
        if redirect_text:
            try:
                redirect_rules = json.loads(redirect_text)
                if not isinstance(redirect_rules, list):
                    self._set_status("✗ Redirect rules must be a JSON array.")
                    return
            except json.JSONDecodeError as e:
                self._set_status(f"✗ Invalid redirect rules JSON: {e}")
                return

        self._set_status("Saving website configuration...")
        self.save_btn.configure(state="disabled")

        thread = threading.Thread(
            target=self._do_save,
            args=(index_doc, error_doc, redirect_rules),
            daemon=True,
        )
        thread.start()

    def _do_save(
        self, index_doc: str, error_doc: str, redirect_rules: list | None
    ):
        """Save website configuration in a background thread.

        Args:
            index_doc: Index document suffix.
            error_doc: Error document key.
            redirect_rules: Optional list of routing rules.
        """
        try:
            s3_client = self.app.s3_client

            config: dict = {
                "IndexDocument": {"Suffix": index_doc},
            }

            if error_doc:
                config["ErrorDocument"] = {"Key": error_doc}

            if redirect_rules:
                config["RoutingRules"] = redirect_rules

            s3_client.put_bucket_website(
                Bucket=self.bucket,
                WebsiteConfiguration=config,
            )
            self.after(
                0, self._set_status, "✓ Website hosting configuration saved."
            )
        except Exception as e:
            self.after(0, self._set_status, f"✗ Save failed: {e}")
        finally:
            self.after(0, lambda: self.save_btn.configure(state="normal"))

    def _do_delete(self):
        """Delete website hosting configuration in a background thread."""
        try:
            s3_client = self.app.s3_client
            s3_client.delete_bucket_website(Bucket=self.bucket)
            self.after(0, self._set_status, "✓ Website hosting disabled.")
        except Exception as e:
            self.after(0, self._set_status, f"✗ Failed to disable: {e}")
        finally:
            self.after(0, lambda: self.save_btn.configure(state="normal"))

    def _set_status(self, message: str):
        """Update the status label.

        Args:
            message: Status message to display.
        """
        self.status_label.configure(text=message)
