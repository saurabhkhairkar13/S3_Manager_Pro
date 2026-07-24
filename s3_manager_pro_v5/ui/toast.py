"""Toast Notification — brief success/info banner that auto-hides.

Usage:
    from s3_manager_pro_v5.ui.toast import show_toast
    show_toast(app.root, "5 files moved to Glacier", type="success")
"""
import customtkinter as ctk


class Toast:
    """A brief notification banner that slides in at the top and auto-hides."""

    def __init__(self, parent, message: str, toast_type: str = "success", duration: int = 3000):
        """
        Args:
            parent: Parent widget (usually root)
            message: Text to display
            toast_type: "success", "info", "warning", "error"
            duration: Milliseconds to show before auto-hiding
        """
        colors = {
            "success": {"bg": "#1b5e20", "text": "#ffffff", "icon": "✅"},
            "info": {"bg": "#0d47a1", "text": "#ffffff", "icon": "ℹ️"},
            "warning": {"bg": "#e65100", "text": "#ffffff", "icon": "⚠️"},
            "error": {"bg": "#b71c1c", "text": "#ffffff", "icon": "❌"},
        }

        style = colors.get(toast_type, colors["info"])

        # Create the toast frame
        self.frame = ctk.CTkFrame(parent, fg_color=style["bg"],
                                  corner_radius=8, height=36)
        self.frame.place(relx=0.5, y=-40, anchor="n")  # Start hidden above screen

        # Content
        inner = ctk.CTkFrame(self.frame, fg_color="transparent")
        inner.pack(padx=15, pady=8)

        ctk.CTkLabel(inner, text=f"{style['icon']}  {message}",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=style["text"]).pack(side="left")

        # Close button
        ctk.CTkButton(inner, text="✕", width=20, height=20,
                      corner_radius=4, fg_color="transparent",
                      hover_color="#ffffff30", text_color=style["text"],
                      font=ctk.CTkFont(size=10),
                      command=self._hide).pack(side="left", padx=(15, 0))

        # Animate in
        self._animate_in(parent, duration)

    def _animate_in(self, parent, duration):
        """Slide the toast down from top."""
        self.frame.place(relx=0.5, y=5, anchor="n")
        self.frame.lift()

        # Auto-hide after duration
        self.frame.after(duration, self._hide)

    def _hide(self):
        """Remove the toast."""
        try:
            self.frame.destroy()
        except Exception:
            pass


def show_toast(parent, message: str, toast_type: str = "success", duration: int = 3000):
    """Convenience function to show a toast notification.

    Args:
        parent: Root window
        message: Text to display
        toast_type: "success", "info", "warning", "error"
        duration: Auto-hide after this many milliseconds (default 3s)
    """
    Toast(parent, message, toast_type, duration)
