"""Status Bar — rich bottom bar with connection, selection, transfer, and activity info."""
import customtkinter as ctk
from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME
from s3_manager_pro_v5.utils.formatting import format_size


class StatusBar(ctk.CTkFrame):
    """Bottom status bar with multiple info sections."""

    def __init__(self, parent, app):
        super().__init__(parent, height=26, corner_radius=0)
        self.app = app
        self.pack_propagate(False)

        colors = DARK_THEME if app.is_dark else LIGHT_THEME

        # Left: Connection status
        self.connection_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.connection_frame.pack(side="left", padx=(10, 0))

        self.connection_dot = ctk.CTkLabel(
            self.connection_frame, text="●",
            font=ctk.CTkFont(size=9), text_color="#dc3545",
        )
        self.connection_dot.pack(side="left", padx=(0, 4))

        self.connection_label = ctk.CTkLabel(
            self.connection_frame, text="Disconnected",
            font=ctk.CTkFont(size=10),
        )
        self.connection_label.pack(side="left")

        # Separator
        self._sep()

        # Region
        self.region_label = ctk.CTkLabel(
            self, text="",
            font=ctk.CTkFont(size=10),
        )
        self.region_label.pack(side="left", padx=5)

        self._sep()

        # Selection info
        self.selection_label = ctk.CTkLabel(
            self, text="No selection",
            font=ctk.CTkFont(size=10),
        )
        self.selection_label.pack(side="left", padx=5)

        self._sep()

        # Transfer status (right side)
        self.transfer_label = ctk.CTkLabel(
            self, text="",
            font=ctk.CTkFont(size=10),
        )
        self.transfer_label.pack(side="right", padx=(5, 10))

        # Status message (center-right)
        self.status_label = ctk.CTkLabel(
            self, text="Ready",
            font=ctk.CTkFont(size=10),
        )
        self.status_label.pack(side="right", padx=5)

    def _sep(self):
        """Add vertical separator."""
        colors = DARK_THEME if self.app.is_dark else LIGHT_THEME
        ctk.CTkLabel(self, text="│",
                     font=ctk.CTkFont(size=10),
                     text_color=colors["border"]).pack(side="left", padx=3)

    def set_connected(self, account_info: str, region: str):
        """Update to connected state."""
        self.connection_dot.configure(text_color="#00c853")
        self.connection_label.configure(text=account_info)
        self.region_label.configure(text=region)

    def set_disconnected(self, message: str = "Disconnected"):
        """Update to disconnected state."""
        self.connection_dot.configure(text_color="#dc3545")
        self.connection_label.configure(text=message)

    def set_selection(self, count: int, total_size: int):
        """Update selection info."""
        if count == 0:
            self.selection_label.configure(text="No selection")
        else:
            self.selection_label.configure(text=f"{count} selected ({format_size(total_size)})")

    def set_status(self, text: str):
        """Set status message."""
        self.status_label.configure(text=text)

    def set_transfer(self, text: str):
        """Set transfer status (speed, ETA)."""
        self.transfer_label.configure(text=text)

    def apply_theme(self, colors: dict):
        """Apply theme to status bar."""
        self.configure(fg_color=colors["header_bg"])
        self.connection_label.configure(text_color=colors["text_secondary"])
        self.region_label.configure(text_color=colors["text_secondary"])
        self.selection_label.configure(text_color=colors["text_secondary"])
        self.status_label.configure(text_color=colors["text_primary"])
        self.transfer_label.configure(text_color=colors["primary"])
