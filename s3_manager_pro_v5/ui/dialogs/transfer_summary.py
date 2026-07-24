"""Transfer Completion Summary — detailed results after download/upload."""
import os
import sys
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME
from s3_manager_pro_v5.utils.formatting import format_size, format_duration


class TransferSummaryDialog:
    """Shows detailed results after a transfer operation completes."""

    def __init__(self, parent, is_dark: bool, operation: str,
                 success: int, skipped: int, failed: int,
                 total_size: int, elapsed_seconds: float,
                 errors: list = None, download_dir: str = ""):
        """
        Args:
            operation: "download" or "upload"
            success: number of successful files
            skipped: number of skipped files
            failed: number of failed files
            total_size: total bytes transferred
            elapsed_seconds: time taken
            errors: list of error message strings
            download_dir: path to open on button click
        """
        colors = DARK_THEME if is_dark else LIGHT_THEME
        self.download_dir = download_dir

        op_icon = "⬇" if operation == "download" else "⬆"
        op_title = "Download" if operation == "download" else "Upload"

        self.win = ctk.CTkToplevel(parent)
        self.win.title(f"{op_icon} {op_title} Complete")
        self.win.geometry("500x450")
        self.win.transient(parent)
        self.win.grab_set()
        self.win.resizable(False, True)
        self.win.configure(fg_color=colors["bg"])

        # Header — success or partial
        if failed == 0:
            header_text = f"✅ {op_title} Complete!"
            header_color = colors["success"]
        else:
            header_text = f"⚠️ {op_title} Finished with Errors"
            header_color = colors["warning"]

        ctk.CTkLabel(self.win, text=header_text,
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=header_color).pack(pady=(20, 10))

        # Summary stats
        stats_frame = ctk.CTkFrame(self.win, fg_color=colors["surface"], corner_radius=10)
        stats_frame.pack(fill="x", padx=25, pady=(0, 10))

        stats_inner = ctk.CTkFrame(stats_frame, fg_color="transparent")
        stats_inner.pack(padx=20, pady=15)

        # Three columns: Success | Skipped | Failed
        col_frame = ctk.CTkFrame(stats_inner, fg_color="transparent")
        col_frame.pack()

        self._stat_card(col_frame, "✅ Success", str(success), colors["success"], colors)
        self._stat_card(col_frame, "⏭ Skipped", str(skipped), colors["text_secondary"], colors)
        self._stat_card(col_frame, "❌ Failed", str(failed),
                        colors["danger"] if failed > 0 else colors["text_secondary"], colors)

        # Transfer info
        speed = total_size / elapsed_seconds if elapsed_seconds > 0 else 0
        info_text = (f"Total: {format_size(total_size)} │ "
                     f"Time: {format_duration(elapsed_seconds)} │ "
                     f"Speed: {format_size(int(speed))}/s")

        ctk.CTkLabel(stats_inner, text=info_text,
                     font=ctk.CTkFont(size=11),
                     text_color=colors["text_secondary"]).pack(pady=(10, 0))

        # Error details (if any)
        if errors and failed > 0:
            error_frame = ctk.CTkFrame(self.win, fg_color="transparent")
            error_frame.pack(fill="both", expand=True, padx=25, pady=(5, 5))

            ctk.CTkLabel(error_frame, text="❌ Errors:",
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=colors["danger"]).pack(anchor="w")

            error_box = ctk.CTkTextbox(error_frame, height=100,
                                       font=ctk.CTkFont(family="Consolas", size=10),
                                       fg_color=colors["surface"],
                                       text_color=colors["text_primary"])
            error_box.pack(fill="both", expand=True, pady=(5, 0))

            for err in errors[:20]:
                error_box.insert("end", f"• {err}\n")
            if len(errors) > 20:
                error_box.insert("end", f"\n... and {len(errors) - 20} more errors")
            error_box.configure(state="disabled")

        # Buttons
        btn_frame = ctk.CTkFrame(self.win, fg_color="transparent")
        btn_frame.pack(fill="x", padx=25, pady=(10, 20))

        if download_dir and operation == "download":
            ctk.CTkButton(btn_frame, text="📂 Open Folder", width=120, height=34,
                          corner_radius=8, fg_color=colors["primary"],
                          hover_color=colors["primary_hover"],
                          font=ctk.CTkFont(size=12),
                          command=self._open_folder).pack(side="left", padx=(0, 10))

        ctk.CTkButton(btn_frame, text="Close", width=80, height=34,
                      corner_radius=8, fg_color=colors["badge_bg"],
                      hover_color=colors["surface_hover"],
                      text_color=colors["text_primary"],
                      command=self.win.destroy).pack(side="right")

    def _stat_card(self, parent, label: str, value: str, value_color: str, colors: dict):
        """Create a small stat card."""
        card = ctk.CTkFrame(parent, fg_color="transparent", width=120)
        card.pack(side="left", padx=15)

        ctk.CTkLabel(card, text=value,
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=value_color).pack()
        ctk.CTkLabel(card, text=label,
                     font=ctk.CTkFont(size=11),
                     text_color=colors["text_secondary"]).pack()

    def _open_folder(self):
        """Open the download folder in file explorer."""
        if self.download_dir and os.path.exists(self.download_dir):
            if sys.platform == "win32":
                os.startfile(self.download_dir)
            elif sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", self.download_dir])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", self.download_dir])
