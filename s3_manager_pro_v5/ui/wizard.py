"""Setup Wizard — First-launch experience for new users.

A multi-step wizard with:
1. Welcome screen
2. Authentication mode selection (keys vs profile)
3. Credential entry + validation with spinner
4. Configuration (region, download folder, parallel)
5. Success screen with transition to dashboard
"""
import os
import threading
import customtkinter as ctk
from s3_manager_pro_v5.utils.constants import (
    DARK_THEME, LIGHT_THEME, AWS_REGIONS, APP_TITLE
)


class SetupWizard:
    """First-launch setup wizard. Call show() to display.
    Calls on_complete(settings_dict) when done.
    """

    def __init__(self, root, on_complete, is_dark=True):
        self.root = root
        self.on_complete = on_complete
        self.is_dark = is_dark
        self.colors = DARK_THEME if is_dark else LIGHT_THEME
        self.step = 0
        self.total_steps = 4

        # Wizard data
        self.auth_mode = "keys"
        self.access_key = ""
        self.secret_key = ""
        self.profile = ""
        self.region = "ap-south-1"
        self.download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        self.parallel = 3
        self.account_id = ""
        self.user_name = ""

        # Build wizard frame (overlays the entire window)
        self.frame = ctk.CTkFrame(root, fg_color=self.colors["bg"], corner_radius=0)
        self.frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        self._show_step_0()

    def destroy(self):
        """Remove the wizard overlay."""
        self.frame.destroy()

    def _clear_frame(self):
        """Clear all widgets in the wizard frame."""
        for widget in self.frame.winfo_children():
            widget.destroy()

    def _add_header(self, step_title: str):
        """Add consistent header with step indicator."""
        c = self.colors

        # Top section
        header = ctk.CTkFrame(self.frame, fg_color=c["surface"], height=100, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(header, text="◉ S3 Manager Pro",
                     font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
                     text_color=c["primary"]).pack(pady=(20, 2))

        ctk.CTkLabel(header, text=step_title,
                     font=ctk.CTkFont(size=13),
                     text_color=c["text_secondary"]).pack()

        # Progress dots
        dots_frame = ctk.CTkFrame(self.frame, fg_color="transparent", height=30)
        dots_frame.pack(fill="x", pady=(10, 5))

        dots_inner = ctk.CTkFrame(dots_frame, fg_color="transparent")
        dots_inner.pack()

        for i in range(self.total_steps):
            color = c["primary"] if i <= self.step else c["border"]
            size = 10 if i == self.step else 7
            ctk.CTkLabel(dots_inner, text="●", font=ctk.CTkFont(size=size),
                         text_color=color).pack(side="left", padx=4)

    def _add_nav_buttons(self, show_back=True, next_text="Next →", next_command=None):
        """Add navigation buttons at the bottom."""
        c = self.colors
        nav = ctk.CTkFrame(self.frame, fg_color="transparent")
        nav.pack(side="bottom", fill="x", padx=40, pady=20)

        if show_back and self.step > 0:
            ctk.CTkButton(nav, text="← Back", width=90, height=36,
                          corner_radius=8, fg_color=c["badge_bg"],
                          hover_color=c["surface_hover"],
                          text_color=c["text_primary"],
                          font=ctk.CTkFont(size=12),
                          command=self._go_back).pack(side="left")

        ctk.CTkButton(nav, text=next_text, width=130, height=36,
                      corner_radius=8, fg_color=c["primary"],
                      hover_color=c["primary_hover"],
                      font=ctk.CTkFont(size=13, weight="bold"),
                      command=next_command).pack(side="right")

    def _go_back(self):
        """Go to previous step."""
        self.step -= 1
        if self.step == 0:
            self._show_step_0()
        elif self.step == 1:
            self._show_step_1()
        elif self.step == 2:
            self._show_step_2()

    # ═══════════════════════════════════════════
    # STEP 0: Welcome
    # ═══════════════════════════════════════════
    def _show_step_0(self):
        """Welcome screen."""
        self.step = 0
        self._clear_frame()
        c = self.colors

        # Centered content
        center = ctk.CTkFrame(self.frame, fg_color="transparent")
        center.pack(expand=True)

        ctk.CTkLabel(center, text="◉",
                     font=ctk.CTkFont(size=48),
                     text_color=c["primary"]).pack(pady=(0, 5))

        ctk.CTkLabel(center, text="Welcome to S3 Manager Pro",
                     font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
                     text_color=c["text_primary"]).pack(pady=(0, 8))

        ctk.CTkLabel(center, text="The S3 desktop client that AWS Console should have been.",
                     font=ctk.CTkFont(size=13),
                     text_color=c["text_secondary"]).pack(pady=(0, 25))

        # Feature highlights
        features = [
            "⬇  Parallel downloads with auto-resume",
            "🔗  Presigned URL generation (one-click share)",
            "📋  S3 Sync with dry-run preview",
            "💰  Cost estimation & storage optimization",
            "🧊  Smart Glacier restore with cost per tier",
            "📜  File versioning & properties viewer",
        ]

        features_frame = ctk.CTkFrame(center, fg_color=c["surface"], corner_radius=12)
        features_frame.pack(padx=40, pady=(0, 20))

        for feat in features:
            ctk.CTkLabel(features_frame, text=feat,
                         font=ctk.CTkFont(size=12),
                         text_color=c["text_primary"],
                         anchor="w").pack(fill="x", padx=20, pady=3)

        ctk.CTkLabel(features_frame, text="").pack(pady=2)  # Bottom padding

        # Get Started button
        ctk.CTkButton(center, text="Get Started →", width=160, height=42,
                      corner_radius=10, fg_color=c["primary"],
                      hover_color=c["primary_hover"],
                      font=ctk.CTkFont(size=14, weight="bold"),
                      command=self._show_step_1).pack(pady=(10, 0))

        # Skip link
        ctk.CTkButton(center, text="Skip setup (configure later)",
                      width=180, height=28, corner_radius=6,
                      fg_color="transparent", hover_color=c["surface_hover"],
                      text_color=c["text_secondary"],
                      font=ctk.CTkFont(size=11),
                      command=self._skip_setup).pack(pady=(10, 0))

    # ═══════════════════════════════════════════
    # STEP 1: Authentication Mode
    # ═══════════════════════════════════════════
    def _show_step_1(self):
        """Choose authentication method."""
        self.step = 1
        self._clear_frame()
        c = self.colors

        self._add_header("Step 1 — Choose Authentication Method")

        content = ctk.CTkFrame(self.frame, fg_color="transparent")
        content.pack(expand=True, fill="both", padx=50)

        ctk.CTkLabel(content, text="How do you connect to AWS?",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=c["text_primary"]).pack(anchor="w", pady=(20, 15))

        self.auth_var = ctk.StringVar(value=self.auth_mode)

        # Option 1: Access Keys
        key_frame = ctk.CTkFrame(content, fg_color=c["surface"], corner_radius=10)
        key_frame.pack(fill="x", pady=(0, 10))

        key_inner = ctk.CTkFrame(key_frame, fg_color="transparent")
        key_inner.pack(fill="x", padx=15, pady=12)

        ctk.CTkRadioButton(key_inner, text="Access Key + Secret Key",
                           variable=self.auth_var, value="keys",
                           font=ctk.CTkFont(size=13, weight="bold"),
                           text_color=c["text_primary"]).pack(anchor="w")
        ctk.CTkLabel(key_inner, text="Use an IAM Access Key ID and Secret Access Key.\n"
                     "Best for: personal use, testing, development.",
                     font=ctk.CTkFont(size=11),
                     text_color=c["text_secondary"],
                     justify="left").pack(anchor="w", padx=24)

        # Option 2: AWS Profile
        prof_frame = ctk.CTkFrame(content, fg_color=c["surface"], corner_radius=10)
        prof_frame.pack(fill="x", pady=(0, 10))

        prof_inner = ctk.CTkFrame(prof_frame, fg_color="transparent")
        prof_inner.pack(fill="x", padx=15, pady=12)

        ctk.CTkRadioButton(prof_inner, text="AWS Named Profile",
                           variable=self.auth_var, value="profile",
                           font=ctk.CTkFont(size=13, weight="bold"),
                           text_color=c["text_primary"]).pack(anchor="w")
        ctk.CTkLabel(prof_inner, text="Use a profile from ~/.aws/credentials.\n"
                     "Best for: developers with AWS CLI configured.",
                     font=ctk.CTkFont(size=11),
                     text_color=c["text_secondary"],
                     justify="left").pack(anchor="w", padx=24)

        self._add_nav_buttons(show_back=True, next_text="Next →",
                              next_command=self._step1_next)

    def _step1_next(self):
        self.auth_mode = self.auth_var.get()
        self._show_step_2()

    # ═══════════════════════════════════════════
    # STEP 2: Credentials + Validation
    # ═══════════════════════════════════════════
    def _show_step_2(self):
        """Enter credentials and validate."""
        self.step = 2
        self._clear_frame()
        c = self.colors

        self._add_header("Step 2 — Enter Credentials")

        content = ctk.CTkFrame(self.frame, fg_color="transparent")
        content.pack(expand=True, fill="both", padx=50)

        if self.auth_mode == "keys":
            ctk.CTkLabel(content, text="Enter your AWS Access Keys",
                         font=ctk.CTkFont(size=15, weight="bold"),
                         text_color=c["text_primary"]).pack(anchor="w", pady=(20, 15))

            ctk.CTkLabel(content, text="Access Key ID:",
                         font=ctk.CTkFont(size=12),
                         text_color=c["text_primary"]).pack(anchor="w")
            self.ak_entry = ctk.CTkEntry(content, width=420, height=36,
                                         placeholder_text="AKIA...",
                                         font=ctk.CTkFont(family="Consolas", size=12))
            self.ak_entry.pack(anchor="w", pady=(2, 10))
            if self.access_key:
                self.ak_entry.insert(0, self.access_key)

            ctk.CTkLabel(content, text="Secret Access Key:",
                         font=ctk.CTkFont(size=12),
                         text_color=c["text_primary"]).pack(anchor="w")
            self.sk_entry = ctk.CTkEntry(content, width=420, height=36, show="*",
                                         placeholder_text="Your secret key...",
                                         font=ctk.CTkFont(family="Consolas", size=12))
            self.sk_entry.pack(anchor="w", pady=(2, 10))
            if self.secret_key:
                self.sk_entry.insert(0, self.secret_key)

        else:
            ctk.CTkLabel(content, text="Enter your AWS Profile Name",
                         font=ctk.CTkFont(size=15, weight="bold"),
                         text_color=c["text_primary"]).pack(anchor="w", pady=(20, 15))

            ctk.CTkLabel(content, text="Profile name (from ~/.aws/credentials):",
                         font=ctk.CTkFont(size=12),
                         text_color=c["text_primary"]).pack(anchor="w")
            self.prof_entry = ctk.CTkEntry(content, width=420, height=36,
                                           placeholder_text="default",
                                           font=ctk.CTkFont(size=12))
            self.prof_entry.pack(anchor="w", pady=(2, 10))
            if self.profile:
                self.prof_entry.insert(0, self.profile)

        # Region
        ctk.CTkLabel(content, text="AWS Region:",
                     font=ctk.CTkFont(size=12),
                     text_color=c["text_primary"]).pack(anchor="w", pady=(10, 0))
        self.region_menu = ctk.CTkOptionMenu(content, width=220, height=32,
                                             values=AWS_REGIONS)
        self.region_menu.set(self.region)
        self.region_menu.pack(anchor="w", pady=(2, 10))

        # Validate button + status
        val_row = ctk.CTkFrame(content, fg_color="transparent")
        val_row.pack(fill="x", pady=(10, 0))

        self.validate_btn = ctk.CTkButton(
            val_row, text="🔐 Validate Connection", width=180, height=36,
            corner_radius=8, fg_color=c["success"], hover_color="#1fa339",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._validate_credentials,
        )
        self.validate_btn.pack(side="left")

        self.spinner_label = ctk.CTkLabel(val_row, text="",
                                          font=ctk.CTkFont(size=12))
        self.spinner_label.pack(side="left", padx=15)

        # Status message
        self.validate_status = ctk.CTkLabel(content, text="",
                                            font=ctk.CTkFont(size=12))
        self.validate_status.pack(anchor="w", pady=(10, 0))

        self._add_nav_buttons(show_back=True, next_text="Validate & Continue →",
                              next_command=self._step2_validate_and_next)

    def _validate_credentials(self):
        """Validate credentials against AWS STS."""
        c = self.colors
        self.validate_btn.configure(state="disabled")
        self.spinner_label.configure(text="⏳ Connecting...", text_color=c["warning"])

        # If called directly (not from validate_and_next), don't auto-proceed
        if not hasattr(self, '_auto_proceed_on_success'):
            self._auto_proceed_on_success = False

        # Gather values
        region = self.region_menu.get()
        self.region = region

        if self.auth_mode == "keys":
            self.access_key = self.ak_entry.get().strip()
            self.secret_key = self.sk_entry.get().strip()
            if not self.access_key or not self.secret_key:
                self.spinner_label.configure(text="")
                self.validate_status.configure(
                    text="⚠ Access Key and Secret Key are required.",
                    text_color=c["danger"])
                self.validate_btn.configure(state="normal")
                return
        else:
            self.profile = self.prof_entry.get().strip()
            if not self.profile:
                self.spinner_label.configure(text="")
                self.validate_status.configure(
                    text="⚠ Profile name is required.",
                    text_color=c["danger"])
                self.validate_btn.configure(state="normal")
                return

        def do_validate():
            import boto3
            from botocore.exceptions import ClientError, NoCredentialsError, ProfileNotFound

            try:
                session_kwargs = {"region_name": region}
                if self.auth_mode == "keys":
                    session_kwargs["aws_access_key_id"] = self.access_key
                    session_kwargs["aws_secret_access_key"] = self.secret_key
                else:
                    session_kwargs["profile_name"] = self.profile

                session = boto3.Session(**session_kwargs)
                sts = session.client("sts")
                identity = sts.get_caller_identity()
                self.account_id = identity.get("Account", "")
                arn = identity.get("Arn", "")
                self.user_name = arn.split("/")[-1] if "/" in arn else arn

                self.frame.after(0, lambda: self._validation_success())

            except ProfileNotFound:
                self.frame.after(0, lambda: self._validation_failed(
                    f"Profile '{self.profile}' not found in ~/.aws/credentials"))
            except NoCredentialsError:
                self.frame.after(0, lambda: self._validation_failed(
                    "Invalid credentials. Check your Access Key and Secret Key."))
            except ClientError as e:
                msg = e.response["Error"]["Message"]
                self.frame.after(0, lambda: self._validation_failed(f"AWS Error: {msg}"))
            except Exception as e:
                self.frame.after(0, lambda: self._validation_failed(str(e)))

        threading.Thread(target=do_validate, daemon=True).start()

    def _validation_success(self):
        c = self.colors
        self.spinner_label.configure(text="")
        self.validate_status.configure(
            text=f"✅ Connected!  Account: {self.account_id} │ User: {self.user_name}",
            text_color=c["success"]
        )
        self.validate_btn.configure(state="normal", text="✓ Validated")

        # Auto-proceed to next step after brief delay
        if getattr(self, '_auto_proceed_on_success', False):
            self._auto_proceed_on_success = False
            self.frame.after(800, self._step2_next)

    def _validation_failed(self, message: str):
        c = self.colors
        self.spinner_label.configure(text="")
        self.validate_status.configure(text=f"❌ {message}", text_color=c["danger"])
        self.validate_btn.configure(state="normal")

    def _step2_validate_and_next(self):
        """Validate credentials then auto-proceed to step 3."""
        self._auto_proceed_on_success = True
        self._validate_credentials()

    def _step2_next(self):
        # Save values from entries
        if self.auth_mode == "keys":
            self.access_key = self.ak_entry.get().strip()
            self.secret_key = self.sk_entry.get().strip()
        else:
            self.profile = self.prof_entry.get().strip()
        self.region = self.region_menu.get()
        self._show_step_3()

    # ═══════════════════════════════════════════
    # STEP 3: Configuration
    # ═══════════════════════════════════════════
    def _show_step_3(self):
        """Configure download folder and parallel transfers."""
        self.step = 3
        self._clear_frame()
        c = self.colors

        self._add_header("Step 3 — Configuration")

        content = ctk.CTkFrame(self.frame, fg_color="transparent")
        content.pack(expand=True, fill="both", padx=50)

        ctk.CTkLabel(content, text="Configure your preferences",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=c["text_primary"]).pack(anchor="w", pady=(20, 15))

        # Download folder
        ctk.CTkLabel(content, text="Download Folder:",
                     font=ctk.CTkFont(size=12),
                     text_color=c["text_primary"]).pack(anchor="w")

        dir_row = ctk.CTkFrame(content, fg_color="transparent")
        dir_row.pack(fill="x", pady=(2, 15))

        self.dir_entry = ctk.CTkEntry(dir_row, width=350, height=34,
                                      font=ctk.CTkFont(size=11))
        self.dir_entry.insert(0, self.download_dir)
        self.dir_entry.pack(side="left", padx=(0, 8))

        ctk.CTkButton(dir_row, text="Browse", width=80, height=34,
                      corner_radius=6, fg_color=c["badge_bg"],
                      hover_color=c["surface_hover"],
                      text_color=c["text_primary"],
                      command=self._browse_dir).pack(side="left")

        # Parallel transfers
        ctk.CTkLabel(content, text="Parallel Transfers:",
                     font=ctk.CTkFont(size=12),
                     text_color=c["text_primary"]).pack(anchor="w")

        ctk.CTkLabel(content, text="How many files to download/upload simultaneously",
                     font=ctk.CTkFont(size=11),
                     text_color=c["text_secondary"]).pack(anchor="w")

        self.parallel_slider = ctk.CTkSlider(content, from_=1, to=10, number_of_steps=9,
                                             width=300)
        self.parallel_slider.set(self.parallel)
        self.parallel_slider.pack(anchor="w", pady=(5, 0))

        self.parallel_label = ctk.CTkLabel(content, text=f"{self.parallel} parallel transfers",
                                           font=ctk.CTkFont(size=11),
                                           text_color=c["text_secondary"])
        self.parallel_label.pack(anchor="w")
        self.parallel_slider.configure(command=self._on_slider_change)

        # Theme
        ctk.CTkLabel(content, text="Theme:",
                     font=ctk.CTkFont(size=12),
                     text_color=c["text_primary"]).pack(anchor="w", pady=(20, 0))

        theme_row = ctk.CTkFrame(content, fg_color="transparent")
        theme_row.pack(anchor="w", pady=(5, 0))

        self.theme_var = ctk.StringVar(value="dark" if self.is_dark else "light")
        ctk.CTkRadioButton(theme_row, text="🌙 Dark", variable=self.theme_var, value="dark",
                           text_color=c["text_primary"]).pack(side="left", padx=(0, 20))
        ctk.CTkRadioButton(theme_row, text="☀️ Light", variable=self.theme_var, value="light",
                           text_color=c["text_primary"]).pack(side="left")

        self._add_nav_buttons(show_back=True, next_text="Finish Setup ✓",
                              next_command=self._finish_setup)

    def _on_slider_change(self, value):
        self.parallel = int(value)
        self.parallel_label.configure(text=f"{self.parallel} parallel transfers")

    def _browse_dir(self):
        from tkinter import filedialog
        d = filedialog.askdirectory(parent=self.frame)
        if d:
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, d)

    # ═══════════════════════════════════════════
    # FINISH
    # ═══════════════════════════════════════════
    def _finish_setup(self):
        """Save settings and transition to dashboard."""
        self.download_dir = self.dir_entry.get().strip() or self.download_dir
        self.parallel = int(self.parallel_slider.get())
        theme = self.theme_var.get()

        settings = {
            "auth_mode": self.auth_mode,
            "profile": self.profile,
            "region": self.region,
            "download_dir": self.download_dir,
            "parallel": self.parallel,
            "theme": theme,
            "last_bucket": "",
            "last_prefix": "",
        }

        # Call completion handler with settings + credentials
        self.on_complete(settings, self.access_key, self.secret_key)

        # Show brief success then destroy
        self._show_success()

    def _show_success(self):
        """Show success animation briefly."""
        self._clear_frame()
        c = self.colors

        center = ctk.CTkFrame(self.frame, fg_color="transparent")
        center.pack(expand=True)

        ctk.CTkLabel(center, text="✅",
                     font=ctk.CTkFont(size=48)).pack(pady=(0, 10))

        ctk.CTkLabel(center, text="You're all set!",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=c["text_primary"]).pack(pady=(0, 5))

        if self.account_id:
            ctk.CTkLabel(center, text=f"Connected to AWS Account: {self.account_id}",
                         font=ctk.CTkFont(size=13),
                         text_color=c["success"]).pack(pady=(0, 5))

        ctk.CTkLabel(center, text="Loading dashboard...",
                     font=ctk.CTkFont(size=12),
                     text_color=c["text_secondary"]).pack(pady=(10, 0))

        # Auto-destroy after brief delay
        self.frame.after(1500, self.destroy)

    def _skip_setup(self):
        """Skip setup — use empty defaults."""
        settings = {
            "auth_mode": "keys",
            "profile": "",
            "region": "ap-south-1",
            "download_dir": os.path.join(os.path.expanduser("~"), "Downloads"),
            "parallel": 3,
            "theme": "dark",
            "last_bucket": "",
            "last_prefix": "",
        }
        self.on_complete(settings, "", "")
        self.destroy()
