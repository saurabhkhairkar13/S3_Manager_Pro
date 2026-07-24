"""Main application shell — theme toggle, header bar, layout manager."""
import customtkinter as ctk
from s3_manager_pro_v5.utils.constants import APP_TITLE, DARK_THEME, LIGHT_THEME


class HeaderBar(ctk.CTkFrame):
    """Top header bar with app title, account info, region, theme toggle, settings."""

    def __init__(self, parent, app):
        super().__init__(parent, height=48, corner_radius=0)
        self.app = app
        self.pack_propagate(False)

        # App title
        self.title_label = ctk.CTkLabel(
            self, text="◉ S3 Manager Pro",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
        )
        self.title_label.pack(side="left", padx=(15, 12))

        # Connection indicator
        self.connection_dot = ctk.CTkLabel(
            self, text="●", font=ctk.CTkFont(size=12),
            text_color="#dc3545",
        )
        self.connection_dot.pack(side="left", padx=(0, 5))

        # Account label
        self.account_label = ctk.CTkLabel(
            self, text="Not connected",
            font=ctk.CTkFont(family="Segoe UI", size=11),
        )
        self.account_label.pack(side="left", padx=(0, 8))

        # Connect/Disconnect button
        self.connect_btn = ctk.CTkButton(
            self, text="Connect", width=75, height=26, corner_radius=6,
            font=ctk.CTkFont(size=10),
            fg_color="#28a745", hover_color="#218838",
            command=self.app._auto_connect,
        )
        self.connect_btn.pack(side="left", padx=(0, 15))

        # Right side buttons
        # Settings gear
        self.settings_btn = ctk.CTkButton(
            self, text="⚙", width=34, height=34, corner_radius=8,
            font=ctk.CTkFont(size=16),
            command=self.app.open_settings,
        )
        self.settings_btn.pack(side="right", padx=(5, 12))

        # Theme toggle
        self.theme_btn = ctk.CTkButton(
            self, text="🌙", width=34, height=34, corner_radius=8,
            font=ctk.CTkFont(size=16),
            command=self.app.toggle_theme,
        )
        self.theme_btn.pack(side="right", padx=5)

        # Add tooltips
        from s3_manager_pro_v5.ui.tooltip import Tooltip
        Tooltip(self.settings_btn, "Settings — credentials, region, preferences (Ctrl+,)")
        Tooltip(self.theme_btn, "Toggle Dark / Light theme")

        # Region selector
        self.region_label = ctk.CTkLabel(
            self, text="Region:",
            font=ctk.CTkFont(size=11),
        )
        self.region_label.pack(side="right", padx=(5, 2))

        self.region_display = ctk.CTkLabel(
            self, text="ap-south-1",
            font=ctk.CTkFont(size=11, weight="bold"),
        )
        self.region_display.pack(side="right", padx=(0, 10))

    def set_connected(self, account_info: str):
        """Update connection status to connected."""
        self.connection_dot.configure(text_color="#00c853")
        self.account_label.configure(text=account_info)
        self.connect_btn.configure(
            text="Disconnect", fg_color="#dc3545", hover_color="#c82333",
            command=self.app.disconnect
        )

    def set_disconnected(self, message: str = "Not connected"):
        """Update connection status to disconnected."""
        self.connection_dot.configure(text_color="#dc3545")
        self.account_label.configure(text=message)
        self.connect_btn.configure(
            text="Connect", fg_color="#28a745", hover_color="#218838",
            command=self.app._auto_connect
        )

    def set_region(self, region: str):
        self.region_display.configure(text=region)

    def update_theme_icon(self, is_dark: bool):
        self.theme_btn.configure(text="☀️" if is_dark else "🌙")

    def apply_theme(self, colors: dict):
        """Apply theme colors to header."""
        self.configure(fg_color=colors["header_bg"])
        self.title_label.configure(text_color=colors["primary"])
        self.account_label.configure(text_color=colors["text_secondary"])
        self.region_label.configure(text_color=colors["text_secondary"])
        self.region_display.configure(text_color=colors["text_primary"])
        self.settings_btn.configure(
            fg_color=colors["surface"],
            hover_color=colors["surface_hover"],
            text_color=colors["text_primary"],
        )
        self.theme_btn.configure(
            fg_color=colors["surface"],
            hover_color=colors["surface_hover"],
            text_color=colors["text_primary"],
        )
