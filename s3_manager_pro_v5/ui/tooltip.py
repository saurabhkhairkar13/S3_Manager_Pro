"""Tooltip Widget — shows tooltip text when cursor hovers over any widget.

Usage:
    from s3_manager_pro_v5.ui.tooltip import Tooltip
    
    button = ctk.CTkButton(parent, text="⬇")
    Tooltip(button, "Download selected files (Ctrl+D)")
"""
import tkinter as tk


class Tooltip:
    """Attach a tooltip to any widget. Shows on hover after a short delay."""

    def __init__(self, widget, text: str, delay: int = 400):
        """
        Args:
            widget: The widget to attach tooltip to
            text: Tooltip text to display
            delay: Milliseconds before showing tooltip (default 400ms)
        """
        self.widget = widget
        self.text = text
        self.delay = delay
        self._tip_window = None
        self._after_id = None

        widget.bind("<Enter>", self._on_enter)
        widget.bind("<Leave>", self._on_leave)
        widget.bind("<ButtonPress>", self._on_leave)

    def _on_enter(self, event=None):
        """Start delay timer to show tooltip."""
        self._cancel()
        self._after_id = self.widget.after(self.delay, self._show_tip)

    def _on_leave(self, event=None):
        """Cancel and hide tooltip."""
        self._cancel()
        self._hide_tip()

    def _cancel(self):
        """Cancel the scheduled tooltip."""
        if self._after_id:
            self.widget.after_cancel(self._after_id)
            self._after_id = None

    def _show_tip(self):
        """Display the tooltip window."""
        if self._tip_window:
            return

        # Get widget position
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5

        # Create tooltip window
        self._tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)  # No window decorations
        tw.wm_geometry(f"+{x}+{y}")

        # Tooltip styling
        frame = tk.Frame(tw, background="#2d2d2d", borderwidth=1, relief="solid")
        frame.pack()

        label = tk.Label(
            frame,
            text=self.text,
            background="#2d2d2d",
            foreground="#ffffff",
            font=("Segoe UI", 9),
            padx=8,
            pady=4,
            justify="left",
        )
        label.pack()

        # Make sure tooltip stays on screen
        tw.update_idletasks()
        screen_width = tw.winfo_screenwidth()
        screen_height = tw.winfo_screenheight()
        tip_width = tw.winfo_width()
        tip_height = tw.winfo_height()

        if x + tip_width > screen_width:
            x = screen_width - tip_width - 10
        if y + tip_height > screen_height:
            y = self.widget.winfo_rooty() - tip_height - 5

        tw.wm_geometry(f"+{x}+{y}")

    def _hide_tip(self):
        """Hide and destroy the tooltip window."""
        if self._tip_window:
            self._tip_window.destroy()
            self._tip_window = None

    def update_text(self, new_text: str):
        """Update tooltip text dynamically."""
        self.text = new_text
