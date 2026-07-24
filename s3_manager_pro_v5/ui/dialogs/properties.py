"""Object Properties Panel — metadata, tags, ACL, content-type."""
import threading
import customtkinter as ctk
from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME
from s3_manager_pro_v5.utils.formatting import format_size, STORAGE_CLASS_INFO


class PropertiesPanel:
    """Show detailed object properties in a side panel / dialog."""

    def __init__(self, parent, app, bucket: str, obj):
        self.app = app
        self.bucket = bucket
        self.obj = obj

        colors = DARK_THEME if app.is_dark else LIGHT_THEME
        filename = obj.key.split("/")[-1] if "/" in obj.key else obj.key

        self.win = ctk.CTkToplevel(parent)
        self.win.title(f"📝 Properties — {filename}")
        self.win.geometry("450x550")
        self.win.transient(parent)
        self.win.grab_set()
        self.win.resizable(False, True)
        self.win.configure(fg_color=colors["bg"])

        # Title
        ctk.CTkLabel(self.win, text="📝 Object Properties",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=colors["text_primary"]).pack(pady=(15, 10))

        # Content frame (scrollable)
        self.content = ctk.CTkScrollableFrame(self.win, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=15, pady=(0, 5))

        # Loading indicator
        self.loading_label = ctk.CTkLabel(self.content, text="Loading properties...",
                                          text_color=colors["text_secondary"])
        self.loading_label.pack(pady=10)

        # Close button
        ctk.CTkButton(self.win, text="Close", width=80, height=32,
                      corner_radius=6, fg_color=colors["badge_bg"],
                      hover_color=colors["surface_hover"],
                      text_color=colors["text_primary"],
                      command=self.win.destroy).pack(pady=(5, 15))

        # Load properties
        self._load_properties()

    def _load_properties(self):
        """Load detailed object metadata from S3."""
        def do_load():
            try:
                metadata = self.app.s3_client.s3_client.head_object(
                    Bucket=self.bucket, Key=self.obj.key
                )

                # Try to get tags
                tags = {}
                try:
                    tag_response = self.app.s3_client.s3_client.get_object_tagging(
                        Bucket=self.bucket, Key=self.obj.key
                    )
                    for tag in tag_response.get("TagSet", []):
                        tags[tag["Key"]] = tag["Value"]
                except Exception:
                    pass

                self.win.after(0, lambda: self._display_properties(metadata, tags))

            except Exception as e:
                self.win.after(0, lambda: self.loading_label.configure(
                    text=f"Error: {str(e)}", text_color="#f44336"
                ))

        threading.Thread(target=do_load, daemon=True).start()

    def _display_properties(self, metadata: dict, tags: dict):
        """Render the properties."""
        self.loading_label.destroy()

        colors = DARK_THEME if self.app.is_dark else LIGHT_THEME
        filename = self.obj.key.split("/")[-1] if "/" in self.obj.key else self.obj.key

        # ── Basic Info ──
        self._add_section("📄 Basic Information")
        self._add_row("Key", self.obj.key)
        self._add_row("Filename", filename)
        self._add_row("Size", f"{format_size(self.obj.size)} ({self.obj.size:,} bytes)")
        self._add_row("Content-Type", metadata.get("ContentType", "N/A"))
        self._add_row("Last Modified", str(metadata.get("LastModified", "N/A")))
        self._add_row("ETag", metadata.get("ETag", "N/A").strip('"'))

        # ── Storage ──
        self._add_section("🗄️ Storage")
        sc = self.obj.storage_class
        info = STORAGE_CLASS_INFO.get(sc, {"icon": "⚪", "label": sc})
        self._add_row("Storage Class", f"{info['icon']} {sc}")

        # Restore status for Glacier
        restore = metadata.get("Restore", "")
        if restore:
            if 'ongoing-request="true"' in restore:
                self._add_row("Restore Status", "⏳ In Progress")
            elif 'ongoing-request="false"' in restore:
                self._add_row("Restore Status", "✅ Ready")
        elif sc not in ("STANDARD", "STANDARD_IA", "ONEZONE_IA", "INTELLIGENT_TIERING", "GLACIER_IR"):
            self._add_row("Restore Status", "🧊 Frozen (not requested)")

        # ── Server-Side Encryption ──
        sse = metadata.get("ServerSideEncryption", "")
        if sse:
            self._add_section("🔒 Encryption")
            self._add_row("SSE", sse)
            kms_key = metadata.get("SSEKMSKeyId", "")
            if kms_key:
                self._add_row("KMS Key", kms_key[:40] + "..." if len(kms_key) > 40 else kms_key)

        # ── Metadata ──
        user_metadata = metadata.get("Metadata", {})
        if user_metadata:
            self._add_section("🏷️ User Metadata")
            for k, v in user_metadata.items():
                self._add_row(k, v)

        # ── Tags ──
        self._add_section("🏷️ Tags")
        if tags:
            for k, v in tags.items():
                self._add_row(k, v)
        else:
            ctk.CTkLabel(self.content, text="  No tags",
                         font=ctk.CTkFont(size=11),
                         text_color="gray").pack(anchor="w")

        # ── Technical ──
        self._add_section("⚙️ Technical")
        self._add_row("Version ID", metadata.get("VersionId", "N/A"))
        self._add_row("Cache-Control", metadata.get("CacheControl", "N/A"))
        self._add_row("Content-Encoding", metadata.get("ContentEncoding", "N/A"))
        self._add_row("Content-Disposition", metadata.get("ContentDisposition", "N/A"))

        # S3 URI
        self._add_section("🔗 URIs")
        self._add_row("S3 URI", f"s3://{self.bucket}/{self.obj.key}")
        self._add_row("HTTPS URL", f"https://{self.bucket}.s3.amazonaws.com/{self.obj.key}")

    def _add_section(self, title: str):
        """Add a section header."""
        colors = DARK_THEME if self.app.is_dark else LIGHT_THEME
        ctk.CTkLabel(self.content, text=title,
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=colors["text_primary"]).pack(anchor="w", pady=(12, 4))

    def _add_row(self, label: str, value: str):
        """Add a key-value row."""
        colors = DARK_THEME if self.app.is_dark else LIGHT_THEME
        row = ctk.CTkFrame(self.content, fg_color="transparent")
        row.pack(fill="x", pady=1)

        ctk.CTkLabel(row, text=f"{label}:", width=130,
                     font=ctk.CTkFont(size=11),
                     text_color=colors["text_secondary"],
                     anchor="w").pack(side="left")
        ctk.CTkLabel(row, text=str(value),
                     font=ctk.CTkFont(size=11),
                     text_color=colors["text_primary"],
                     anchor="w", wraplength=250).pack(side="left", fill="x")
