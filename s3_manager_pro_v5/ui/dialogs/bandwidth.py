"""Bandwidth Throttle — limit upload/download speed."""
import time
import threading
import customtkinter as ctk
from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME


class BandwidthThrottle:
    """Token-bucket rate limiter for controlling transfer speed."""

    def __init__(self, max_bytes_per_second: int = 0):
        """
        Args:
            max_bytes_per_second: Max speed in bytes/sec. 0 = unlimited.
        """
        self._max_bps = max_bytes_per_second
        self._lock = threading.Lock()
        self._tokens = 0
        self._last_time = time.time()
        self.enabled = max_bytes_per_second > 0

    @property
    def max_bps(self) -> int:
        return self._max_bps

    @max_bps.setter
    def max_bps(self, value: int):
        with self._lock:
            self._max_bps = value
            self.enabled = value > 0

    def throttle(self, bytes_to_transfer: int):
        """Call before transferring bytes. Blocks if rate limit exceeded."""
        if not self.enabled or self._max_bps <= 0:
            return

        with self._lock:
            now = time.time()
            elapsed = now - self._last_time
            self._tokens += elapsed * self._max_bps
            self._tokens = min(self._tokens, self._max_bps * 2)  # Max burst = 2 seconds
            self._last_time = now

            if bytes_to_transfer <= self._tokens:
                self._tokens -= bytes_to_transfer
                return

            # Need to wait
            deficit = bytes_to_transfer - self._tokens
            wait_time = deficit / self._max_bps
            self._tokens = 0

        if wait_time > 0:
            time.sleep(wait_time)


class BandwidthDialog:
    """Dialog to configure bandwidth throttling."""

    def __init__(self, parent, app):
        self.app = app
        colors = DARK_THEME if app.is_dark else LIGHT_THEME

        self.win = ctk.CTkToplevel(parent)
        self.win.title("🚦 Bandwidth Control")
        self.win.geometry("420x380")
        self.win.transient(parent)
        self.win.grab_set()
        self.win.resizable(False, True)
        self.win.configure(fg_color=colors["bg"])

        # Title
        ctk.CTkLabel(self.win, text="🚦 Bandwidth Throttle",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=colors["text_primary"]).pack(pady=(20, 5))

        ctk.CTkLabel(self.win, text="Limit transfer speed to avoid network saturation",
                     font=ctk.CTkFont(size=11),
                     text_color=colors["text_secondary"]).pack(pady=(0, 15))

        form = ctk.CTkFrame(self.win, fg_color="transparent")
        form.pack(fill="x", padx=30)

        # Enable/disable
        current_limit = getattr(app, '_bandwidth_limit_mbps', 0)
        self.enabled_var = ctk.BooleanVar(value=current_limit > 0)
        ctk.CTkCheckBox(form, text="Enable bandwidth throttle",
                        variable=self.enabled_var,
                        text_color=colors["text_primary"],
                        font=ctk.CTkFont(size=12),
                        command=self._toggle_slider).pack(anchor="w", pady=(0, 15))

        # Speed slider
        ctk.CTkLabel(form, text="Max Speed (MB/s):",
                     font=ctk.CTkFont(size=12),
                     text_color=colors["text_primary"]).pack(anchor="w")

        self.speed_slider = ctk.CTkSlider(form, from_=1, to=100, number_of_steps=99, width=300)
        self.speed_slider.set(current_limit if current_limit > 0 else 10)
        self.speed_slider.configure(command=self._on_slider_change)
        self.speed_slider.pack(anchor="w", pady=(5, 5))

        self.speed_label = ctk.CTkLabel(form, text=f"{int(self.speed_slider.get())} MB/s",
                                        font=ctk.CTkFont(size=14, weight="bold"),
                                        text_color=colors["primary"])
        self.speed_label.pack(anchor="w")

        # Presets
        preset_frame = ctk.CTkFrame(form, fg_color="transparent")
        preset_frame.pack(fill="x", pady=(10, 0))

        ctk.CTkLabel(preset_frame, text="Presets:", font=ctk.CTkFont(size=11),
                     text_color=colors["text_secondary"]).pack(side="left", padx=(0, 10))

        for label, value in [("1 MB/s", 1), ("5 MB/s", 5), ("10 MB/s", 10), ("50 MB/s", 50), ("Unlimited", 0)]:
            ctk.CTkButton(preset_frame, text=label, width=65, height=26,
                          corner_radius=4, font=ctk.CTkFont(size=10),
                          fg_color=colors["badge_bg"], hover_color=colors["surface_hover"],
                          text_color=colors["text_primary"],
                          command=lambda v=value: self._set_preset(v)).pack(side="left", padx=2)

        # Apply button
        btn_frame = ctk.CTkFrame(form, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(20, 0))

        ctk.CTkButton(btn_frame, text="✓ Apply", width=100, height=34,
                      corner_radius=8, font=ctk.CTkFont(size=12, weight="bold"),
                      fg_color=colors["success"], hover_color="#1fa339",
                      command=self._apply).pack(side="left", padx=(0, 10))

        ctk.CTkButton(btn_frame, text="Close", width=70, height=34,
                      corner_radius=8, fg_color=colors["badge_bg"],
                      hover_color=colors["surface_hover"],
                      text_color=colors["text_primary"],
                      command=self.win.destroy).pack(side="right")

        self._toggle_slider()

    def _on_slider_change(self, value):
        self.speed_label.configure(text=f"{int(value)} MB/s")

    def _toggle_slider(self):
        if self.enabled_var.get():
            self.speed_slider.configure(state="normal")
        else:
            self.speed_slider.configure(state="disabled")
            self.speed_label.configure(text="Unlimited")

    def _set_preset(self, value):
        if value == 0:
            self.enabled_var.set(False)
            self._toggle_slider()
        else:
            self.enabled_var.set(True)
            self.speed_slider.set(value)
            self.speed_label.configure(text=f"{value} MB/s")
            self._toggle_slider()

    def _apply(self):
        """Apply bandwidth limit."""
        if self.enabled_var.get():
            mbps = int(self.speed_slider.get())
            bps = mbps * 1024 * 1024
            self.app._bandwidth_limit_mbps = mbps
        else:
            bps = 0
            self.app._bandwidth_limit_mbps = 0

        # Update throttle on transfer engine
        if not hasattr(self.app, '_throttle'):
            self.app._throttle = BandwidthThrottle(bps)
        else:
            self.app._throttle.max_bps = bps

        status = f"🚦 Bandwidth: {self.app._bandwidth_limit_mbps} MB/s" if bps > 0 else "🚦 Bandwidth: Unlimited"
        self.app.progress_bar.set_status(status)
        self.win.destroy()
