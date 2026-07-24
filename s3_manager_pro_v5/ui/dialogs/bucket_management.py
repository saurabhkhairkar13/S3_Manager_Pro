"""Bucket Management — create, delete, configure buckets."""
import threading
import customtkinter as ctk
from tkinter import messagebox
from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME, AWS_REGIONS


class BucketManagementDialog:
    """Create, delete, and configure S3 buckets."""

    def __init__(self, parent, app):
        self.app = app
        colors = DARK_THEME if app.is_dark else LIGHT_THEME

        self.win = ctk.CTkToplevel(parent)
        self.win.title("🪣 Bucket Management")
        self.win.geometry("520x500")
        self.win.transient(parent)
        self.win.grab_set()
        self.win.resizable(False, True)
        self.win.configure(fg_color=colors["bg"])

        # Title
        ctk.CTkLabel(self.win, text="🪣 Bucket Management",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=colors["text_primary"]).pack(pady=(15, 10))

        # Tabs using CTkTabview
        self.tabview = ctk.CTkTabview(self.win, fg_color=colors["surface"])
        self.tabview.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # Tab 1: Create Bucket
        tab_create = self.tabview.add("Create")
        self._build_create_tab(tab_create, colors)

        # Tab 2: Delete Bucket
        tab_delete = self.tabview.add("Delete")
        self._build_delete_tab(tab_delete, colors)

        # Tab 3: Configure
        tab_config = self.tabview.add("Configure")
        self._build_config_tab(tab_config, colors)

        # Close
        ctk.CTkButton(self.win, text="Close", width=80, height=32,
                      corner_radius=6, fg_color=colors["badge_bg"],
                      hover_color=colors["surface_hover"],
                      text_color=colors["text_primary"],
                      command=self.win.destroy).pack(pady=(0, 15))

    def _build_create_tab(self, parent, colors):
        """Build the create bucket tab."""
        ctk.CTkLabel(parent, text="Create New Bucket",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=colors["text_primary"]).pack(anchor="w", padx=10, pady=(10, 8))

        form = ctk.CTkFrame(parent, fg_color="transparent")
        form.pack(fill="x", padx=10)

        ctk.CTkLabel(form, text="Bucket Name:", text_color=colors["text_primary"]).pack(anchor="w")
        self.create_name = ctk.CTkEntry(form, width=350, height=32,
                                        placeholder_text="my-bucket-name (lowercase, no spaces)")
        self.create_name.pack(anchor="w", pady=(2, 8))

        ctk.CTkLabel(form, text="Region:", text_color=colors["text_primary"]).pack(anchor="w")
        self.create_region = ctk.CTkOptionMenu(form, values=AWS_REGIONS, width=200, height=30)
        self.create_region.set(self.app.cred_manager.get("region", "ap-south-1"))
        self.create_region.pack(anchor="w", pady=(2, 8))

        # Options
        self.versioning_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(form, text="Enable Versioning", variable=self.versioning_var,
                        text_color=colors["text_primary"]).pack(anchor="w", pady=2)

        self.encryption_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(form, text="Enable Default Encryption (AES-256)", variable=self.encryption_var,
                        text_color=colors["text_primary"]).pack(anchor="w", pady=2)

        self.block_public_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(form, text="Block All Public Access", variable=self.block_public_var,
                        text_color=colors["text_primary"]).pack(anchor="w", pady=2)

        # Status + button
        self.create_status = ctk.CTkLabel(form, text="", font=ctk.CTkFont(size=11))
        self.create_status.pack(anchor="w", pady=(8, 0))

        ctk.CTkButton(form, text="🪣 Create Bucket", width=150, height=34,
                      corner_radius=8, fg_color=colors["success"], hover_color="#1fa339",
                      font=ctk.CTkFont(size=12, weight="bold"),
                      command=self._create_bucket).pack(anchor="w", pady=(8, 0))

    def _build_delete_tab(self, parent, colors):
        """Build the delete bucket tab."""
        ctk.CTkLabel(parent, text="Delete Empty Bucket",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=colors["text_primary"]).pack(anchor="w", padx=10, pady=(10, 8))

        form = ctk.CTkFrame(parent, fg_color="transparent")
        form.pack(fill="x", padx=10)

        ctk.CTkLabel(form, text="Bucket Name:", text_color=colors["text_primary"]).pack(anchor="w")
        self.delete_name = ctk.CTkEntry(form, width=350, height=32,
                                        placeholder_text="Enter bucket name to delete")
        self.delete_name.pack(anchor="w", pady=(2, 8))

        ctk.CTkLabel(form, text="⚠️ Type the bucket name again to confirm:",
                     font=ctk.CTkFont(size=11),
                     text_color=colors["warning"]).pack(anchor="w")
        self.delete_confirm = ctk.CTkEntry(form, width=350, height=32,
                                           placeholder_text="Confirm bucket name")
        self.delete_confirm.pack(anchor="w", pady=(2, 8))

        ctk.CTkLabel(form, text="⚠️ Bucket must be empty. This cannot be undone!",
                     font=ctk.CTkFont(size=11),
                     text_color=colors["danger"]).pack(anchor="w", pady=(5, 0))

        self.delete_status = ctk.CTkLabel(form, text="", font=ctk.CTkFont(size=11))
        self.delete_status.pack(anchor="w", pady=(8, 0))

        ctk.CTkButton(form, text="🗑 Delete Bucket", width=150, height=34,
                      corner_radius=8, fg_color=colors["danger"], hover_color=colors["danger_hover"],
                      font=ctk.CTkFont(size=12, weight="bold"),
                      command=self._delete_bucket).pack(anchor="w", pady=(8, 0))

    def _build_config_tab(self, parent, colors):
        """Build the configure bucket tab."""
        ctk.CTkLabel(parent, text="Configure Bucket",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=colors["text_primary"]).pack(anchor="w", padx=10, pady=(10, 8))

        form = ctk.CTkFrame(parent, fg_color="transparent")
        form.pack(fill="x", padx=10)

        ctk.CTkLabel(form, text="Bucket:", text_color=colors["text_primary"]).pack(anchor="w")
        self.config_bucket = ctk.CTkEntry(form, width=350, height=32)
        if self.app.current_bucket:
            self.config_bucket.insert(0, self.app.current_bucket)
        self.config_bucket.pack(anchor="w", pady=(2, 8))

        ctk.CTkLabel(form, text="Quick Actions:",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=colors["text_primary"]).pack(anchor="w", pady=(5, 5))

        actions = [
            ("Enable Versioning", self._enable_versioning),
            ("Enable Encryption", self._enable_encryption),
            ("Block Public Access", self._block_public),
        ]

        for label, cmd in actions:
            ctk.CTkButton(form, text=f"✓ {label}", width=200, height=30,
                          corner_radius=6, fg_color=colors["primary"],
                          hover_color=colors["primary_hover"],
                          font=ctk.CTkFont(size=11),
                          anchor="w", command=cmd).pack(anchor="w", pady=3)

        self.config_status = ctk.CTkLabel(form, text="", font=ctk.CTkFont(size=11))
        self.config_status.pack(anchor="w", pady=(10, 0))

    def _create_bucket(self):
        """Create a new S3 bucket."""
        name = self.create_name.get().strip()
        region = self.create_region.get()

        if not name:
            self.create_status.configure(text="❌ Bucket name required", text_color="#f44336")
            return

        def do_create():
            try:
                s3 = self.app.s3_client.s3_client
                create_kwargs = {"Bucket": name}
                if region != "us-east-1":
                    create_kwargs["CreateBucketConfiguration"] = {"LocationConstraint": region}

                s3.create_bucket(**create_kwargs)

                # Enable encryption if checked
                if self.encryption_var.get():
                    s3.put_bucket_encryption(
                        Bucket=name,
                        ServerSideEncryptionConfiguration={
                            "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
                        }
                    )

                # Enable versioning if checked
                if self.versioning_var.get():
                    s3.put_bucket_versioning(
                        Bucket=name,
                        VersioningConfiguration={"Status": "Enabled"}
                    )

                # Block public access if checked
                if self.block_public_var.get():
                    s3.put_public_access_block(
                        Bucket=name,
                        PublicAccessBlockConfiguration={
                            "BlockPublicAcls": True,
                            "IgnorePublicAcls": True,
                            "BlockPublicPolicy": True,
                            "RestrictPublicBuckets": True,
                        }
                    )

                self.win.after(0, lambda: self.create_status.configure(
                    text=f"✅ Bucket '{name}' created successfully!", text_color="#00c853"
                ))
                # Refresh bucket list
                self.win.after(500, lambda: self.app._load_buckets())

            except Exception as e:
                self.win.after(0, lambda: self.create_status.configure(
                    text=f"❌ {str(e)[:60]}", text_color="#f44336"
                ))

        threading.Thread(target=do_create, daemon=True).start()

    def _delete_bucket(self):
        """Delete an empty bucket."""
        name = self.delete_name.get().strip()
        confirm = self.delete_confirm.get().strip()

        if not name:
            self.delete_status.configure(text="❌ Bucket name required", text_color="#f44336")
            return
        if name != confirm:
            self.delete_status.configure(text="❌ Names don't match", text_color="#f44336")
            return

        def do_delete():
            try:
                self.app.s3_client.s3_client.delete_bucket(Bucket=name)
                self.win.after(0, lambda: self.delete_status.configure(
                    text=f"✅ Bucket '{name}' deleted!", text_color="#00c853"
                ))
                self.win.after(500, lambda: self.app._load_buckets())
            except Exception as e:
                error_msg = str(e)
                if "BucketNotEmpty" in error_msg:
                    msg = "❌ Bucket is not empty. Delete all objects first."
                else:
                    msg = f"❌ {error_msg[:60]}"
                self.win.after(0, lambda: self.delete_status.configure(
                    text=msg, text_color="#f44336"
                ))

        threading.Thread(target=do_delete, daemon=True).start()

    def _enable_versioning(self):
        bucket = self.config_bucket.get().strip()
        if not bucket:
            return
        try:
            self.app.s3_client.s3_client.put_bucket_versioning(
                Bucket=bucket, VersioningConfiguration={"Status": "Enabled"})
            self.config_status.configure(text=f"✅ Versioning enabled on {bucket}", text_color="#00c853")
        except Exception as e:
            self.config_status.configure(text=f"❌ {str(e)[:50]}", text_color="#f44336")

    def _enable_encryption(self):
        bucket = self.config_bucket.get().strip()
        if not bucket:
            return
        try:
            self.app.s3_client.s3_client.put_bucket_encryption(
                Bucket=bucket,
                ServerSideEncryptionConfiguration={
                    "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
                })
            self.config_status.configure(text=f"✅ Encryption enabled on {bucket}", text_color="#00c853")
        except Exception as e:
            self.config_status.configure(text=f"❌ {str(e)[:50]}", text_color="#f44336")

    def _block_public(self):
        bucket = self.config_bucket.get().strip()
        if not bucket:
            return
        try:
            self.app.s3_client.s3_client.put_public_access_block(
                Bucket=bucket,
                PublicAccessBlockConfiguration={
                    "BlockPublicAcls": True, "IgnorePublicAcls": True,
                    "BlockPublicPolicy": True, "RestrictPublicBuckets": True,
                })
            self.config_status.configure(text=f"✅ Public access blocked on {bucket}", text_color="#00c853")
        except Exception as e:
            self.config_status.configure(text=f"❌ {str(e)[:50]}", text_color="#f44336")
