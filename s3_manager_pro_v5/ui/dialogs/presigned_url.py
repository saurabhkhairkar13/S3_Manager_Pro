"""Presigned URL Generator Dialog — custom expiry, copy button, email option."""
import customtkinter as ctk
from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME


class PresignedURLDialog:
    """Generate presigned URLs with custom expiry options."""

    def __init__(self, parent, app, bucket: str, key: str, filename: str):
        self.app = app
        self.bucket = bucket
        self.key = key
        self.generated_url = ""

        colors = DARK_THEME if app.is_dark else LIGHT_THEME

        self.win = ctk.CTkToplevel(parent)
        self.win.title("🔗 Generate Shareable URL")
        self.win.geometry("550x520")
        self.win.transient(parent)
        self.win.grab_set()
        self.win.resizable(False, True)
        self.win.configure(fg_color=colors["bg"])

        # Title
        ctk.CTkLabel(self.win, text="🔗 Generate Shareable URL",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=colors["text_primary"]).pack(pady=(20, 5))

        # File info
        ctk.CTkLabel(self.win, text=f"File: {filename}",
                     font=ctk.CTkFont(size=12),
                     text_color=colors["text_secondary"]).pack(pady=(0, 15))

        # Expiry options
        form = ctk.CTkFrame(self.win, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=30, pady=(0, 15))

        ctk.CTkLabel(form, text="Link Expiry:",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=colors["text_primary"]).pack(anchor="w", pady=(0, 8))

        self.expiry_var = ctk.StringVar(value="3600")

        options = [
            ("1 hour", "3600"),
            ("6 hours", "21600"),
            ("24 hours", "86400"),
            ("7 days", "604800"),
            ("Custom", "custom"),
        ]

        for label, value in options:
            ctk.CTkRadioButton(
                form, text=label, variable=self.expiry_var, value=value,
                font=ctk.CTkFont(size=12),
                text_color=colors["text_primary"],
                command=self._on_expiry_change,
            ).pack(anchor="w", padx=10, pady=2)

        # Custom input
        self.custom_frame = ctk.CTkFrame(form, fg_color="transparent")
        self.custom_frame.pack(fill="x", padx=10, pady=(5, 0))

        self.custom_entry = ctk.CTkEntry(self.custom_frame, width=80, placeholder_text="hours")
        self.custom_entry.pack(side="left", padx=(20, 5))
        ctk.CTkLabel(self.custom_frame, text="hours (max 168 = 7 days)",
                     text_color=colors["text_secondary"],
                     font=ctk.CTkFont(size=11)).pack(side="left")
        self.custom_frame.pack_forget()  # Hidden initially

        # Generate button
        ctk.CTkButton(form, text="⚡ Generate URL", width=150, height=36,
                      corner_radius=8, font=ctk.CTkFont(size=13, weight="bold"),
                      fg_color=colors["primary"], hover_color=colors["primary_hover"],
                      command=self._generate).pack(pady=(15, 10))

        # URL display
        self.url_frame = ctk.CTkFrame(form, fg_color=colors["surface"], corner_radius=8)
        self.url_frame.pack(fill="x", pady=(5, 10))

        self.url_textbox = ctk.CTkTextbox(self.url_frame, height=50, wrap="word",
                                          font=ctk.CTkFont(family="Consolas", size=10),
                                          fg_color=colors["surface"],
                                          text_color=colors["text_primary"])
        self.url_textbox.pack(fill="x", padx=8, pady=8)
        self.url_textbox.insert("0.0", "Click 'Generate URL' to create a shareable link")
        self.url_textbox.configure(state="disabled")

        # Copy button
        btn_row = ctk.CTkFrame(form, fg_color="transparent")
        btn_row.pack(fill="x")

        self.copy_btn = ctk.CTkButton(
            btn_row, text="📋 Copy URL", width=110, height=32,
            corner_radius=6, font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=colors["success"], hover_color="#1fa339",
            command=self._copy_url, state="disabled",
        )
        self.copy_btn.pack(side="left", padx=(0, 8))

        self.status_label = ctk.CTkLabel(btn_row, text="",
                                         font=ctk.CTkFont(size=11),
                                         text_color=colors["success"])
        self.status_label.pack(side="left")

        ctk.CTkButton(btn_row, text="Close", width=70, height=32,
                      corner_radius=6, fg_color=colors["badge_bg"],
                      hover_color=colors["surface_hover"],
                      text_color=colors["text_primary"],
                      command=self.win.destroy).pack(side="right")

    def _on_expiry_change(self):
        if self.expiry_var.get() == "custom":
            self.custom_frame.pack(fill="x", padx=10, pady=(5, 0))
        else:
            self.custom_frame.pack_forget()

    def _generate(self):
        """Generate the presigned URL."""
        expiry_val = self.expiry_var.get()

        if expiry_val == "custom":
            try:
                hours = float(self.custom_entry.get().strip())
                expires_in = int(hours * 3600)
                if expires_in <= 0 or expires_in > 604800:
                    self.status_label.configure(text="Max 168 hours (7 days)", text_color="#f44336")
                    return
            except ValueError:
                self.status_label.configure(text="Enter valid hours", text_color="#f44336")
                return
        else:
            expires_in = int(expiry_val)

        url = self.app.s3_client.generate_presigned_url(self.bucket, self.key, expires_in)

        if url:
            self.generated_url = url
            self.url_textbox.configure(state="normal")
            self.url_textbox.delete("0.0", "end")
            self.url_textbox.insert("0.0", url)
            self.url_textbox.configure(state="disabled")
            self.copy_btn.configure(state="normal")
            hours = expires_in / 3600
            self.status_label.configure(
                text=f"✓ Generated (expires in {hours:.0f}h)", text_color="#00c853"
            )
        else:
            self.status_label.configure(text="✗ Generation failed", text_color="#f44336")

    def _copy_url(self):
        """Copy URL to clipboard."""
        if self.generated_url:
            self.win.clipboard_clear()
            self.win.clipboard_append(self.generated_url)
            self.status_label.configure(text="✓ Copied to clipboard!", text_color="#00c853")
