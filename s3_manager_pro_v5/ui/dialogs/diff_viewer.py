"""Object Diff Viewer — compare two versions of a file side-by-side."""
import difflib
import threading
import customtkinter as ctk
from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME
from s3_manager_pro_v5.utils.formatting import format_size


class DiffViewerDialog:
    """Compare two versions of a text/JSON file with diffs highlighted."""

    def __init__(self, parent, app, bucket: str, key: str):
        self.app = app
        self.bucket = bucket
        self.key = key

        colors = DARK_THEME if app.is_dark else LIGHT_THEME
        filename = key.split("/")[-1] if "/" in key else key

        self.win = ctk.CTkToplevel(parent)
        self.win.title(f"🔀 Diff Viewer — {filename}")
        self.win.geometry("900x600")
        self.win.transient(parent)
        self.win.grab_set()
        self.win.resizable(True, True)
        self.win.configure(fg_color=colors["bg"])

        # Title
        ctk.CTkLabel(self.win, text="🔀 Object Version Diff",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=colors["text_primary"]).pack(pady=(15, 5))
        ctk.CTkLabel(self.win, text=f"File: {filename}",
                     font=ctk.CTkFont(size=12),
                     text_color=colors["text_secondary"]).pack(pady=(0, 10))

        # Loading
        self.status_label = ctk.CTkLabel(self.win, text="⏳ Loading versions...",
                                         font=ctk.CTkFont(size=11),
                                         text_color=colors["text_secondary"])
        self.status_label.pack()

        # Diff content area (side-by-side)
        self.diff_frame = ctk.CTkFrame(self.win, fg_color="transparent")
        self.diff_frame.pack(fill="both", expand=True, padx=15, pady=(10, 5))

        # Close
        ctk.CTkButton(self.win, text="Close", width=80, height=32,
                      corner_radius=6, fg_color=colors["badge_bg"],
                      hover_color=colors["surface_hover"],
                      text_color=colors["text_primary"],
                      command=self.win.destroy).pack(pady=(5, 15))

        # Load versions
        threading.Thread(target=self._load_versions, daemon=True).start()

    def _load_versions(self):
        """Load the two most recent versions and compute diff."""
        try:
            response = self.app.s3_client.s3_client.list_object_versions(
                Bucket=self.bucket, Prefix=self.key
            )

            versions = [v for v in response.get("Versions", []) if v["Key"] == self.key]
            versions.sort(key=lambda v: v["LastModified"], reverse=True)

            if len(versions) < 2:
                self.win.after(0, lambda: self.status_label.configure(
                    text="⚠ Need at least 2 versions to compare. Only found 1.",
                    text_color="#ff9800"
                ))
                return

            # Get the two most recent versions
            v1_id = versions[0]["VersionId"]
            v2_id = versions[1]["VersionId"]
            v1_date = versions[0]["LastModified"].strftime("%Y-%m-%d %H:%M")
            v2_date = versions[1]["LastModified"].strftime("%Y-%m-%d %H:%M")

            # Download both versions
            resp1 = self.app.s3_client.s3_client.get_object(
                Bucket=self.bucket, Key=self.key, VersionId=v1_id
            )
            text1 = resp1["Body"].read().decode("utf-8", errors="replace")

            resp2 = self.app.s3_client.s3_client.get_object(
                Bucket=self.bucket, Key=self.key, VersionId=v2_id
            )
            text2 = resp2["Body"].read().decode("utf-8", errors="replace")

            self.win.after(0, lambda: self._show_diff(text1, text2, v1_date, v2_date))

        except Exception as e:
            error_msg = str(e)
            if "not enabled" in error_msg.lower() or "NoSuchVersion" in error_msg:
                self.win.after(0, lambda: self.status_label.configure(
                    text="⚠ Versioning not enabled on this bucket.",
                    text_color="#ff9800"
                ))
            else:
                self.win.after(0, lambda: self.status_label.configure(
                    text=f"❌ Error: {error_msg[:60]}", text_color="#f44336"
                ))

    def _show_diff(self, text1: str, text2: str, date1: str, date2: str):
        """Display the diff between two versions."""
        self.status_label.configure(text=f"Comparing: {date2} (old) ↔ {date1} (new)")

        colors = DARK_THEME if self.app.is_dark else LIGHT_THEME

        # Compute unified diff
        lines1 = text2.splitlines(keepends=True)  # Older version
        lines2 = text1.splitlines(keepends=True)  # Newer version

        diff = list(difflib.unified_diff(
            lines1, lines2,
            fromfile=f"Previous ({date2})",
            tofile=f"Current ({date1})",
            lineterm=""
        ))

        # Display
        textbox = ctk.CTkTextbox(self.diff_frame,
                                 font=ctk.CTkFont(family="Consolas", size=11),
                                 fg_color=colors["surface"],
                                 text_color=colors["text_primary"],
                                 wrap="none")
        textbox.pack(fill="both", expand=True)

        if not diff:
            textbox.insert("end", "✅ No differences found — versions are identical.")
        else:
            # Stats
            added = sum(1 for l in diff if l.startswith("+") and not l.startswith("+++"))
            removed = sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))

            header = f"Changes: +{added} lines added, -{removed} lines removed\n{'─' * 60}\n\n"
            textbox.insert("end", header)

            for line in diff:
                if line.startswith("+++") or line.startswith("---"):
                    textbox.insert("end", line + "\n")
                elif line.startswith("@@"):
                    textbox.insert("end", f"\n{line}\n")
                elif line.startswith("+"):
                    textbox.insert("end", f"  + {line[1:]}\n")
                elif line.startswith("-"):
                    textbox.insert("end", f"  - {line[1:]}\n")
                else:
                    textbox.insert("end", f"    {line}\n")

        textbox.configure(state="disabled")

        # Summary
        total1 = len(lines1)
        total2 = len(lines2)
        ctk.CTkLabel(self.diff_frame,
                     text=f"Old: {total1} lines │ New: {total2} lines │ "
                          f"Changed: {abs(total2 - total1)} net lines",
                     font=ctk.CTkFont(size=10),
                     text_color=colors["text_secondary"]).pack(anchor="w", pady=(3, 0))
