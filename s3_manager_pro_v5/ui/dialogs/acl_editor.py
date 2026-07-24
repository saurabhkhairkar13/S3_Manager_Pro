"""ACL Editor Dialog - View and edit bucket policies and object ACLs."""

import json
import threading

import customtkinter as ctk

from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME
from s3_manager_pro_v5.utils.formatting import format_size


class ACLEditorDialog(ctk.CTkToplevel):
    """Dialog to view and edit S3 bucket policy or object ACL.

    If key is None, shows bucket policy as a JSON editor.
    If key is provided, shows object ACL with grantees.
    """

    def __init__(self, parent, app, bucket: str, key: str | None = None):
        """Initialize the ACL editor dialog.

        Args:
            parent: Parent widget.
            app: Application instance with S3 client access.
            bucket: S3 bucket name.
            key: Optional S3 object key. If None, edits bucket policy.
        """
        super().__init__(parent)
        self.app = app
        self.bucket = bucket
        self.key = key

        # Configure window
        if key:
            self.title(f"Object ACL - {key}")
        else:
            self.title(f"Bucket Policy - {bucket}")

        self.geometry("750x550")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._load_data()

    def _build_ui(self):
        """Build the dialog UI."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        if self.key:
            header_text = f"Object ACL: {self.key}"
        else:
            header_text = f"Bucket Policy: {self.bucket}"

        header = ctk.CTkLabel(
            self,
            text=header_text,
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        header.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="w")

        # Text editor area
        self.text_editor = ctk.CTkTextbox(
            self,
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="none",
        )
        self.text_editor.grid(row=1, column=0, padx=16, pady=8, sticky="nsew")

        # Status label
        self.status_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=11),
            anchor="w",
        )
        self.status_label.grid(row=2, column=0, padx=16, pady=(0, 4), sticky="w")

        # Button frame
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=3, column=0, padx=16, pady=(4, 16), sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)

        self.validate_btn = ctk.CTkButton(
            button_frame,
            text="Validate JSON",
            width=120,
            command=self._validate_json,
        )
        self.validate_btn.grid(row=0, column=1, padx=4)

        self.save_btn = ctk.CTkButton(
            button_frame,
            text="Save",
            width=100,
            command=self._save,
        )
        self.save_btn.grid(row=0, column=2, padx=4)

        self.cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancel",
            width=100,
            command=self.destroy,
        )
        self.cancel_btn.grid(row=0, column=3, padx=4)

    def _load_data(self):
        """Load bucket policy or object ACL from S3."""
        self._set_status("Loading...")
        thread = threading.Thread(target=self._fetch_data, daemon=True)
        thread.start()

    def _fetch_data(self):
        """Fetch data from S3 in a background thread."""
        try:
            s3_client = self.app.s3_client

            if self.key:
                # Load object ACL
                response = s3_client.get_object_acl(
                    Bucket=self.bucket, Key=self.key
                )
                # Remove ResponseMetadata for cleaner display
                response.pop("ResponseMetadata", None)
                content = json.dumps(response, indent=2, default=str)
            else:
                # Load bucket policy
                try:
                    response = s3_client.get_bucket_policy(Bucket=self.bucket)
                    policy_str = response.get("Policy", "{}")
                    # Pretty print the policy JSON
                    policy = json.loads(policy_str)
                    content = json.dumps(policy, indent=2)
                except s3_client.exceptions.NoSuchBucketPolicy:
                    content = self._get_empty_policy_template()
                except Exception as e:
                    if "NoSuchBucketPolicy" in str(e):
                        content = self._get_empty_policy_template()
                    else:
                        raise

            self.after(0, self._display_content, content)
            self.after(0, self._set_status, "Loaded successfully.")

        except Exception as e:
            self.after(0, self._set_status, f"Error loading: {e}")
            self.after(
                0, self._display_content, f"// Error loading data:\n// {e}"
            )

    def _get_empty_policy_template(self) -> str:
        """Return a template for an empty bucket policy.

        Returns:
            JSON string of an empty policy template.
        """
        template = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "ExampleStatement",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{self.bucket}/*",
                }
            ],
        }
        return json.dumps(template, indent=2)

    def _display_content(self, content: str):
        """Display content in the text editor.

        Args:
            content: Text content to display.
        """
        self.text_editor.delete("1.0", "end")
        self.text_editor.insert("1.0", content)

    def _validate_json(self):
        """Validate the JSON content in the editor."""
        content = self.text_editor.get("1.0", "end").strip()
        try:
            json.loads(content)
            self._set_status("✓ Valid JSON")
        except json.JSONDecodeError as e:
            self._set_status(f"✗ Invalid JSON: {e}")

    def _save(self):
        """Save the policy or ACL back to S3."""
        content = self.text_editor.get("1.0", "end").strip()

        # Validate JSON first
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as e:
            self._set_status(f"✗ Cannot save - invalid JSON: {e}")
            return

        self._set_status("Saving...")
        self.save_btn.configure(state="disabled")

        thread = threading.Thread(
            target=self._do_save, args=(parsed,), daemon=True
        )
        thread.start()

    def _do_save(self, parsed: dict):
        """Perform the save operation in a background thread.

        Args:
            parsed: Parsed JSON data to save.
        """
        try:
            s3_client = self.app.s3_client

            if self.key:
                # Save object ACL
                acl_config = {
                    "Grants": parsed.get("Grants", []),
                    "Owner": parsed.get("Owner", {}),
                }
                s3_client.put_object_acl(
                    Bucket=self.bucket,
                    Key=self.key,
                    AccessControlPolicy=acl_config,
                )
                self.after(0, self._set_status, "✓ Object ACL saved successfully.")
            else:
                # Save bucket policy
                policy_str = json.dumps(parsed)
                s3_client.put_bucket_policy(
                    Bucket=self.bucket, Policy=policy_str
                )
                self.after(0, self._set_status, "✓ Bucket policy saved successfully.")

        except Exception as e:
            self.after(0, self._set_status, f"✗ Save failed: {e}")
        finally:
            self.after(0, lambda: self.save_btn.configure(state="normal"))

    def _set_status(self, message: str):
        """Update the status label.

        Args:
            message: Status message to display.
        """
        self.status_label.configure(text=message)
