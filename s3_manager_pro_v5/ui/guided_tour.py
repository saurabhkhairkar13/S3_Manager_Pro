"""Interactive Guided Tour — step-by-step walkthrough for new users.

Shows overlay cards highlighting each UI area with simple explanations.
Triggered on first launch or via Help → Guided Tour.
"""
import customtkinter as ctk
from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME


# Tour steps with simple, non-technical language
TOUR_STEPS = [
    {
        "title": "👋 Welcome to S3 Manager Pro!",
        "description": (
            "This app helps you manage files stored in Amazon's cloud storage (S3).\n\n"
            "Think of it like a file manager (like Windows Explorer) but for your\n"
            "cloud files. You can upload, download, share, and organize files.\n\n"
            "Let's take a quick tour to show you around!"
        ),
        "target": None,  # No specific target — centered
    },
    {
        "title": "🪣 Buckets (Left Panel)",
        "description": (
            "Buckets are like folders in the cloud — they hold your files.\n\n"
            "• Click a bucket name to select it\n"
            "• Double-click to open and see its files\n"
            "• The STATS section shows how much data you have\n"
            "• BOOKMARKS save your favorite locations for quick access"
        ),
        "target": "sidebar",
    },
    {
        "title": "📂 Breadcrumb Navigation (Top Bar)",
        "description": (
            "This shows where you are — like a path:\n"
            "  🪣 my-bucket  ›  reports  ›  2024\n\n"
            "• Click any part to jump back to that level\n"
            "• Use the search box to filter files by name\n"
            "• The ⭐ button saves current location as bookmark\n"
            "• The 🔄 button refreshes the file list"
        ),
        "target": "breadcrumb",
    },
    {
        "title": "📄 File List (Center)",
        "description": (
            "All your files appear here in a table:\n\n"
            "• ✓ Check the box to select files for download/actions\n"
            "• Click column headers (Name, Size, Class) to sort\n"
            "• Double-click a folder to open it\n"
            "• Right-click any file for more options\n"
            "• Use ◀ ▶ buttons to navigate pages if you have many files"
        ),
        "target": "file_table",
    },
    {
        "title": "📝 Details Panel (Right Side)",
        "description": (
            "When you click a file, this panel shows:\n\n"
            "• File name, size, and type\n"
            "• Quick action buttons (Download, Preview, Share)\n"
            "• Storage class (Standard = normal, Glacier = archived)\n\n"
            "If you select multiple files, it shows bulk actions\n"
            "like 'Download All' or 'Change Storage Class'."
        ),
        "target": "details_panel",
    },
    {
        "title": "⬇ Action Buttons (Bottom)",
        "description": (
            "These are your main actions:\n\n"
            "• ⬇ Download — Save selected files to your computer\n"
            "• ⬆ Upload — Send files from your computer to the cloud\n"
            "• 🔄 Restore — Unfreeze archived (Glacier) files\n"
            "• 🔗 Share — Create a link anyone can use to download\n"
            "• 📋 Sync — Keep a local folder in sync with the cloud\n"
            "• 🗑 Delete — Remove files permanently"
        ),
        "target": "action_bar",
    },
    {
        "title": "📋 Menu Bar (Top)",
        "description": (
            "The menu bar gives access to ALL features:\n\n"
            "• File — Upload, Download, Settings\n"
            "• Edit — Rename, Move, Copy, Tags, Delete\n"
            "• View — Preview files, Dark/Light theme\n"
            "• Bucket — Create/Delete buckets, Security settings\n"
            "• Tools — Sync, Cost analysis, Search, Health check\n"
            "• Help — Shortcuts, About, this Tour"
        ),
        "target": "menu",
    },
    {
        "title": "🔗 Sharing Files",
        "description": (
            "Need to share a file with someone?\n\n"
            "1. Select the file\n"
            "2. Click 🔗 Share (or right-click → Generate Share URL)\n"
            "3. Choose how long the link should work (1 hour to 7 days)\n"
            "4. Click 'Generate URL' → 'Copy URL'\n"
            "5. Paste the link in email/chat — anyone can download!\n\n"
            "No login needed for the person receiving the link."
        ),
        "target": None,
    },
    {
        "title": "💰 Cost Management",
        "description": (
            "Cloud storage costs money. This tool helps you save:\n\n"
            "• Tools → Cost Advisor — Shows exactly where to save money\n"
            "• 'Move 200 old files to Glacier = save $45/month'\n"
            "• One-click to apply the recommendation!\n\n"
            "• Tools → Orphaned Upload Cleaner — Finds invisible\n"
            "  wasted space that's costing you money silently"
        ),
        "target": None,
    },
    {
        "title": "✅ You're Ready!",
        "description": (
            "That's the basics! Here are some tips:\n\n"
            "• Hover over any button to see what it does\n"
            "• Right-click files for all available options\n"
            "• Press F5 to refresh the file list\n"
            "• Use Ctrl+F to quickly search/filter files\n"
            "• Check Help → Keyboard Shortcuts for all hotkeys\n\n"
            "You can replay this tour anytime from Help → Guided Tour."
        ),
        "target": None,
    },
]


class GuidedTour:
    """Interactive step-by-step guided tour — floating window over the app."""

    def __init__(self, root, app):
        self.root = root
        self.app = app
        self.current_step = 0
        self.total_steps = len(TOUR_STEPS)

        colors = DARK_THEME if app.is_dark else LIGHT_THEME

        # Floating Toplevel window (app stays visible behind it)
        self.win = ctk.CTkToplevel(root)
        self.win.title("🎓 Guided Tour")
        self.win.geometry("520x330")
        self.win.resizable(False, False)
        self.win.attributes("-topmost", True)
        self.win.configure(fg_color=colors["bg"])
        self.win.protocol("WM_DELETE_WINDOW", self._finish)

        # Position at center-right of screen so app is visible on left
        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()
        x = screen_w - 560
        y = screen_h // 2 - 165
        self.win.geometry(f"520x330+{x}+{y}")

        # Card content
        self.card_inner = ctk.CTkFrame(self.win, fg_color="transparent")
        self.card_inner.pack(fill="both", expand=True, padx=20, pady=15)

        # Step indicator
        self.step_label = ctk.CTkLabel(
            self.card_inner, text="",
            font=ctk.CTkFont(size=10),
            text_color=colors["text_secondary"],
        )
        self.step_label.pack(anchor="w")

        # Title
        self.title_label = ctk.CTkLabel(
            self.card_inner, text="",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=colors["text_primary"],
        )
        self.title_label.pack(anchor="w", pady=(5, 8))

        # Description
        self.desc_label = ctk.CTkLabel(
            self.card_inner, text="",
            font=ctk.CTkFont(size=12),
            text_color=colors["text_primary"],
            justify="left",
            wraplength=420,
        )
        self.desc_label.pack(anchor="w", pady=(0, 15))

        # Navigation buttons
        self.nav_frame = ctk.CTkFrame(self.card_inner, fg_color="transparent")
        self.nav_frame.pack(fill="x")

        self.skip_btn = ctk.CTkButton(
            self.nav_frame, text="Skip Tour", width=80, height=30,
            corner_radius=6, fg_color="transparent",
            hover_color=colors["surface_hover"],
            text_color=colors["text_secondary"],
            font=ctk.CTkFont(size=11),
            command=self._skip,
        )
        self.skip_btn.pack(side="left")

        self.next_btn = ctk.CTkButton(
            self.nav_frame, text="Next →", width=90, height=32,
            corner_radius=8, fg_color=colors["primary"],
            hover_color=colors["primary_hover"],
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._next,
        )
        self.next_btn.pack(side="right")

        self.back_btn = ctk.CTkButton(
            self.nav_frame, text="← Back", width=80, height=30,
            corner_radius=6, fg_color=colors["badge_bg"],
            hover_color=colors["surface_hover"],
            text_color=colors["text_primary"],
            font=ctk.CTkFont(size=11),
            command=self._back,
        )
        self.back_btn.pack(side="right", padx=(0, 8))

        # Progress dots
        self.dots_frame = ctk.CTkFrame(self.card_inner, fg_color="transparent")
        self.dots_frame.pack(pady=(10, 0))

        # Show first step
        self._show_step()

    def _show_step(self):
        """Display the current step."""
        step = TOUR_STEPS[self.current_step]
        colors = DARK_THEME if self.app.is_dark else LIGHT_THEME

        # Update content
        self.step_label.configure(text=f"Step {self.current_step + 1} of {self.total_steps}")
        self.title_label.configure(text=step["title"])
        self.desc_label.configure(text=step["description"])

        # Update buttons
        if self.current_step == 0:
            self.back_btn.pack_forget()
            self.next_btn.configure(text="Start Tour →")
        elif self.current_step == self.total_steps - 1:
            self.back_btn.pack(side="right", padx=(0, 8))
            self.next_btn.configure(text="✓ Finish")
        else:
            self.back_btn.pack(side="right", padx=(0, 8))
            self.next_btn.configure(text="Next →")

        # Update progress dots
        for widget in self.dots_frame.winfo_children():
            widget.destroy()

        for i in range(self.total_steps):
            color = colors["primary"] if i == self.current_step else colors["border"]
            size = 9 if i == self.current_step else 7
            ctk.CTkLabel(self.dots_frame, text="●",
                         font=ctk.CTkFont(size=size),
                         text_color=color).pack(side="left", padx=2)

        # Highlight target area (visual hint)
        self._highlight_target(step.get("target"))

    def _highlight_target(self, target: str):
        """Visually indicate which area the step is about."""
        if not target:
            return

        # Flash the target area's border or update window title to show context
        area_names = {
            "sidebar": "👈 Look at the LEFT PANEL",
            "breadcrumb": "👆 Look at the TOP BAR (below toolbar)",
            "file_table": "👈 Look at the CENTER TABLE",
            "details_panel": "👉 Look at the RIGHT PANEL",
            "action_bar": "👇 Look at the BOTTOM BUTTONS",
            "menu": "👆 Look at the TOP MENU (File, Edit, View...)",
        }
        hint = area_names.get(target, "")
        if hint:
            self.win.title(f"🎓 Tour — {hint}")

    def _next(self):
        """Go to next step or finish."""
        if self.current_step >= self.total_steps - 1:
            self._finish()
        else:
            self.current_step += 1
            self._show_step()

    def _back(self):
        """Go to previous step."""
        if self.current_step > 0:
            self.current_step -= 1
            self._show_step()

    def _skip(self):
        """Skip the tour."""
        self._finish()

    def _finish(self):
        """End the tour and close the window."""
        self.win.destroy()
