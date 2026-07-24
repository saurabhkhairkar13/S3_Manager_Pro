"""CloudFront Invalidation — invalidate CDN cache for files."""
import threading
import customtkinter as ctk
from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME


class CloudFrontInvalidationDialog:
    """Invalidate CloudFront distribution cache for selected files."""

    def __init__(self, parent, app, selected_keys: list):
        self.app = app
        self.keys = selected_keys

        colors = DARK_THEME if app.is_dark else LIGHT_THEME

        self.win = ctk.CTkToplevel(parent)
        self.win.title("☁️ CloudFront Invalidation")
        self.win.geometry("550x500")
        self.win.transient(parent)
        self.win.grab_set()
        self.win.resizable(False, True)
        self.win.configure(fg_color=colors["bg"])

        # Title
        ctk.CTkLabel(self.win, text="☁️ CloudFront Invalidation",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=colors["text_primary"]).pack(pady=(15, 5))
        ctk.CTkLabel(self.win, text="Invalidate CDN cache for uploaded/changed files",
                     font=ctk.CTkFont(size=11),
                     text_color=colors["text_secondary"]).pack(pady=(0, 10))

        form = ctk.CTkFrame(self.win, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=20)

        # Distribution ID
        ctk.CTkLabel(form, text="CloudFront Distribution ID:",
                     font=ctk.CTkFont(size=12),
                     text_color=colors["text_primary"]).pack(anchor="w")
        self.dist_entry = ctk.CTkEntry(form, width=400, height=32,
                                       placeholder_text="E1234567890ABC")
        self.dist_entry.pack(anchor="w", pady=(2, 10))

        # Or select from list
        ctk.CTkButton(form, text="🔄 Load Distributions", width=160, height=28,
                      corner_radius=6, fg_color=colors["badge_bg"],
                      hover_color=colors["surface_hover"],
                      text_color=colors["text_primary"],
                      command=self._load_distributions).pack(anchor="w", pady=(0, 10))

        self.dist_list_var = ctk.StringVar(value="")
        self.dist_menu = ctk.CTkOptionMenu(form, variable=self.dist_list_var,
                                           values=["(Load distributions first)"],
                                           width=400, height=30)
        self.dist_menu.pack(anchor="w", pady=(0, 10))

        # Paths to invalidate
        ctk.CTkLabel(form, text=f"Paths to invalidate ({len(selected_keys)} files):",
                     font=ctk.CTkFont(size=12),
                     text_color=colors["text_primary"]).pack(anchor="w")

        paths_box = ctk.CTkTextbox(form, height=100,
                                   font=ctk.CTkFont(family="Consolas", size=10),
                                   fg_color=colors["surface"],
                                   text_color=colors["text_primary"])
        paths_box.pack(fill="x", pady=(2, 10))

        # Generate invalidation paths (/ prefixed)
        for key in selected_keys[:50]:
            path = "/" + key if not key.startswith("/") else key
            paths_box.insert("end", path + "\n")
        if len(selected_keys) > 50:
            paths_box.insert("end", f"\n... and {len(selected_keys) - 50} more")

        self.paths_box = paths_box

        # Or invalidate all
        self.all_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(form, text="Invalidate ALL paths (/*) — use with caution",
                        variable=self.all_var,
                        text_color=colors["text_primary"]).pack(anchor="w", pady=(0, 10))

        # Buttons
        btn_frame = ctk.CTkFrame(form, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(5, 0))

        self.invalidate_btn = ctk.CTkButton(
            btn_frame, text="⚡ Create Invalidation", width=180, height=36,
            corner_radius=8, font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=colors["primary"], hover_color=colors["primary_hover"],
            command=self._create_invalidation,
        )
        self.invalidate_btn.pack(side="left", padx=(0, 10))

        self.status_label = ctk.CTkLabel(btn_frame, text="",
                                         font=ctk.CTkFont(size=11))
        self.status_label.pack(side="left")

        ctk.CTkButton(btn_frame, text="Close", width=70, height=36,
                      corner_radius=8, fg_color=colors["badge_bg"],
                      hover_color=colors["surface_hover"],
                      text_color=colors["text_primary"],
                      command=self.win.destroy).pack(side="right")

    def _load_distributions(self):
        """Load CloudFront distributions."""
        def do_load():
            try:
                cf_client = self.app.s3_client.session.client("cloudfront")
                response = cf_client.list_distributions()
                items = response.get("DistributionList", {}).get("Items", [])

                dist_options = []
                for item in items:
                    dist_id = item["Id"]
                    domain = item.get("DomainName", "")
                    comment = item.get("Comment", "")[:30]
                    label = f"{dist_id} — {domain}"
                    if comment:
                        label += f" ({comment})"
                    dist_options.append(label)

                if dist_options:
                    self.win.after(0, lambda: self.dist_menu.configure(values=dist_options))
                    self.win.after(0, lambda: self.status_label.configure(
                        text=f"Found {len(dist_options)} distributions", text_color="#00c853"
                    ))
                else:
                    self.win.after(0, lambda: self.status_label.configure(
                        text="No distributions found", text_color="#ff9800"
                    ))

            except Exception as e:
                self.win.after(0, lambda: self.status_label.configure(
                    text=f"❌ {str(e)[:50]}", text_color="#f44336"
                ))

        threading.Thread(target=do_load, daemon=True).start()

    def _create_invalidation(self):
        """Create a CloudFront invalidation."""
        dist_id = self.dist_entry.get().strip()
        if not dist_id:
            # Try to get from dropdown
            selected = self.dist_list_var.get()
            if selected and "—" in selected:
                dist_id = selected.split("—")[0].strip()

        if not dist_id:
            self.status_label.configure(text="❌ Distribution ID required", text_color="#f44336")
            return

        # Get paths
        if self.all_var.get():
            paths = ["/*"]
        else:
            paths = ["/" + k if not k.startswith("/") else k for k in self.keys]

        self.invalidate_btn.configure(state="disabled")
        self.status_label.configure(text="⏳ Creating invalidation...", text_color="#ff9800")

        def do_invalidate():
            try:
                import time
                cf_client = self.app.s3_client.session.client("cloudfront")
                cf_client.create_invalidation(
                    DistributionId=dist_id,
                    InvalidationBatch={
                        "Paths": {
                            "Quantity": len(paths),
                            "Items": paths,
                        },
                        "CallerReference": f"s3-manager-pro-{int(time.time())}",
                    }
                )
                self.win.after(0, lambda: self.status_label.configure(
                    text=f"✅ Invalidation created for {len(paths)} paths",
                    text_color="#00c853"
                ))
                self.win.after(0, lambda: self.invalidate_btn.configure(state="normal"))

            except Exception as e:
                self.win.after(0, lambda: self.status_label.configure(
                    text=f"❌ {str(e)[:60]}", text_color="#f44336"
                ))
                self.win.after(0, lambda: self.invalidate_btn.configure(state="normal"))

        threading.Thread(target=do_invalidate, daemon=True).start()
