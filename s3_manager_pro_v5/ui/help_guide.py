"""Help Guide — contextual help with simple explanations for every feature.

Provides plain-English descriptions of what each feature does,
when to use it, and step-by-step instructions.
"""
import customtkinter as ctk
from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME


# Help database — every feature explained in plain English
HELP_DATABASE = {
    # ── Core Operations ──
    "download": {
        "title": "⬇ Download Files",
        "what": "Save cloud files to your computer.",
        "when": "When you need a local copy of files stored in S3.",
        "how": "1. Check ✓ the files you want\n2. Click ⬇ Download\n3. Choose where to save\n4. Wait for completion",
        "tips": "• Downloads resume automatically if interrupted\n• Multiple files download in parallel (faster)\n• Glacier files must be 'Restored' first",
    },
    "upload": {
        "title": "⬆ Upload Files",
        "what": "Send files from your computer to the cloud.",
        "when": "When you want to store files in S3 for backup, sharing, or hosting.",
        "how": "1. Click ⬆ Upload\n2. Select files or a folder\n3. Choose storage class\n4. Click Upload",
        "tips": "• You can drag-and-drop files onto the app\n• Large files automatically use multipart upload\n• 'Skip existing' avoids re-uploading same files",
    },
    "share_url": {
        "title": "🔗 Share URL (Presigned Link)",
        "what": "Create a temporary link that anyone can use to download a file — no login needed.",
        "when": "When you want to share a file with a client, colleague, or anyone outside your team.",
        "how": "1. Select a file\n2. Click 🔗 Share\n3. Choose expiry (1 hour to 7 days)\n4. Click 'Generate URL'\n5. Copy and send the link",
        "tips": "• The link expires automatically — secure!\n• Anyone with the link can download (no AWS account needed)\n• Great for sending large files instead of email attachments",
    },
    "delete": {
        "title": "🗑 Delete Files",
        "what": "Permanently remove files from cloud storage.",
        "when": "When files are no longer needed and you want to save storage costs.",
        "how": "1. Select files\n2. Click 🗑 Delete\n3. Confirm the deletion",
        "tips": "• ⚠️ Deleted files cannot be recovered (unless versioning is enabled)\n• Check 'View → File Versions' before deleting\n• You won't be charged for deleted data",
    },
    "sync": {
        "title": "📋 S3 Sync",
        "what": "Keep a local folder and a cloud folder in sync — like Dropbox.",
        "when": "When you want automatic backup or need local and cloud copies to match.",
        "how": "1. Click 📋 Sync\n2. Select your local folder\n3. Click 'Dry Run' to preview changes\n4. Review what will upload/download\n5. Click 'Execute Sync'",
        "tips": "• 'Dry Run' shows what WOULD happen without doing it\n• Use 'Scheduled Sync' for automatic recurring sync\n• Great for backups and deployments",
    },
    "restore": {
        "title": "🔄 Glacier Restore",
        "what": "Unfreeze archived files so you can download them.",
        "when": "When you need to access files stored in Glacier (cheap archive storage).",
        "how": "1. Select Glacier files (shown as 'Frozen')\n2. Click 🔄 Restore\n3. Choose speed (Expedited=fast/expensive, Bulk=slow/cheap)\n4. Wait for restore to complete (hours to minutes)",
        "tips": "• Expedited: 1-5 minutes (costs more)\n• Standard: 3-5 hours (balanced)\n• Bulk: 5-12 hours (cheapest)\n• Restored copies are available for 7 days",
    },

    # ── Advanced Features ──
    "cost_advisor": {
        "title": "💡 Cost Advisor",
        "what": "Analyzes your files and tells you exactly how to save money.",
        "when": "When you want to reduce your AWS storage bill.",
        "how": "1. Go to Tools → Cost & Optimization → Cost Advisor\n2. Review recommendations\n3. Click '⚡ Apply' on any recommendation",
        "tips": "• Moves old unused files to cheaper storage\n• Shows exact savings: '$X/month'\n• One-click to apply — no manual work\n• Check 'Cost Intelligence Center' for full analysis",
    },
    "smart_search": {
        "title": "🔍 Smart Search",
        "what": "Search for files across ALL your buckets at once.",
        "when": "When you know the filename but not which bucket it's in.",
        "how": "1. Go to Tools → Smart Search (or Ctrl+Shift+F)\n2. Type the filename or extension\n3. Results show file + which bucket it's in\n4. Double-click to navigate there",
        "tips": "• Searches all buckets you have access to\n• Use '.json' to find all JSON files\n• Use 'backup' to find all backup-related files",
    },
    "file_preview": {
        "title": "👁 File Preview",
        "what": "View file contents without downloading the entire file.",
        "when": "When you need to check what's inside a file quickly.",
        "how": "1. Click a file\n2. Click 👁 Preview (or Ctrl+P)\n3. Content shows in a popup",
        "tips": "• Works for: text, JSON, CSV, images, code files\n• JSON is automatically formatted (pretty-printed)\n• Images show as thumbnails\n• Max preview size: 5 MB",
    },
    "health_check": {
        "title": "🛡️ Security Health Check",
        "what": "Scans all your buckets for security problems.",
        "when": "Monthly or whenever you want to check if your data is safe.",
        "how": "1. Go to Tools → Security Health Check\n2. Wait for scan to complete\n3. Review findings (Red=Critical, Orange=High)\n4. Fix issues or export report",
        "tips": "• Checks: public access, encryption, versioning, logging\n• Red (Critical) = fix immediately (data could be public!)\n• Orange (High) = fix soon\n• Export report as CSV for your team",
    },
    "multipart_cleaner": {
        "title": "🧹 Orphaned Upload Cleaner",
        "what": "Finds hidden failed uploads that are secretly costing you money.",
        "when": "Monthly — to check for invisible wasted storage.",
        "how": "1. Go to Tools → Orphaned Upload Cleaner\n2. Click 'Scan'\n3. See how much money is being wasted\n4. Click 'Abort All' to clean up\n5. Set 'Auto-Cleanup Rule' to prevent in future",
        "tips": "• Failed multipart uploads are INVISIBLE in AWS Console\n• You're still charged for their storage\n• This tool finds and removes them\n• Set lifecycle rule = never worry again",
    },
    "batch_rename": {
        "title": "✏️ Batch Rename",
        "what": "Rename multiple files at once — add prefix, suffix, or find-replace.",
        "when": "When you need to rename many files (e.g., add date prefix to all).",
        "how": "1. Select files\n2. Right-click → Batch Rename\n3. Choose: Add Prefix, Add Suffix, Find & Replace, or Change Extension\n4. Preview changes\n5. Click 'Execute'",
        "tips": "• Preview shows old name → new name before applying\n• 'Find & Replace' works on filenames\n• Cannot be undone — check preview carefully!",
    },
    "cross_bucket_copy": {
        "title": "📤 Copy/Move Between Buckets",
        "what": "Copy or move files from one bucket to another.",
        "when": "When reorganizing data, creating backups, or migrating between environments.",
        "how": "1. Select files\n2. Right-click → Copy/Move to Bucket\n3. Choose destination bucket\n4. Choose Copy or Move\n5. Click 'Execute'",
        "tips": "• Copy = files exist in both places\n• Move = files removed from source after copying\n• Works across regions\n• Great for prod → backup migrations",
    },
    "scheduled_sync": {
        "title": "⏰ Scheduled Auto-Sync",
        "what": "Automatically sync a folder to/from S3 on a schedule — like Dropbox.",
        "when": "When you want automatic recurring backups without manual work.",
        "how": "1. Go to Tools → S3 Sync → Scheduled Auto-Sync\n2. Click '+ Add' with folder, bucket, and interval\n3. It runs automatically in the background",
        "tips": "• Runs every X minutes while the app is open\n• Shows last sync status\n• Pause/resume individual jobs\n• Great for automated backups",
    },
    "bucket_management": {
        "title": "🪣 Bucket Management",
        "what": "Create, delete, and configure S3 buckets.",
        "when": "When you need a new bucket or want to configure security settings.",
        "how": "1. Go to Bucket → Create Bucket\n2. Enter a unique name\n3. Enable recommended settings (encryption, versioning)\n4. Click 'Create'",
        "tips": "• Bucket names must be globally unique\n• Always enable 'Block Public Access' (security)\n• Enable 'Encryption' (data protection)\n• Enable 'Versioning' (accidental delete protection)",
    },
    "analytics": {
        "title": "📊 Bucket Analytics",
        "what": "Visual overview of what's in your bucket — sizes, types, costs.",
        "when": "When you want to understand your storage usage.",
        "how": "1. Go to Bucket → Bucket Analytics\n2. View: storage breakdown, file types, largest files\n3. Use insights to optimize costs",
        "tips": "• Shows storage class breakdown (bar chart)\n• Lists top 10 largest files\n• Shows monthly cost estimate\n• Helps identify where to save money",
    },
    "bandwidth": {
        "title": "🚦 Bandwidth Control",
        "what": "Limit upload/download speed so the app doesn't use all your internet.",
        "when": "When uploading/downloading large files during work hours.",
        "how": "1. Go to Tools → Bandwidth Control\n2. Enable throttle\n3. Set max speed (MB/s) with slider\n4. Click 'Apply'",
        "tips": "• Use '5 MB/s' during work to keep internet fast for others\n• Set 'Unlimited' at night for maximum speed\n• Presets: 1, 5, 10, 50 MB/s or Unlimited",
    },
    "versioning": {
        "title": "📜 File Versions",
        "what": "See all previous versions of a file — and restore any old version.",
        "when": "When you accidentally overwrote a file and need the old one back.",
        "how": "1. Select a file\n2. Right-click → View Versions\n3. See all versions with dates\n4. Click 'Restore' to make an old version current",
        "tips": "• Only works if 'Versioning' is enabled on the bucket\n• Each version is a complete copy of the file\n• 'Download Version' saves a specific old version to your computer",
    },
    "cloudfront": {
        "title": "☁️ CloudFront Invalidation",
        "what": "Clear the CDN cache so updated files are served immediately.",
        "when": "After uploading new versions of website files (HTML, CSS, images).",
        "how": "1. Select updated files\n2. Go to Tools → CloudFront Invalidation\n3. Enter your Distribution ID\n4. Click 'Create Invalidation'",
        "tips": "• Only needed if you use CloudFront CDN\n• Without invalidation, old cached files may be served for 24 hours\n• '/*' invalidates everything (use sparingly — costs per path)",
    },
}


class HelpGuideDialog:
    """Contextual help dialog — shows explanation for a specific feature."""

    def __init__(self, parent, app, topic: str):
        """
        Args:
            topic: Key from HELP_DATABASE (e.g., 'download', 'share_url')
        """
        self.app = app
        colors = DARK_THEME if app.is_dark else LIGHT_THEME

        help_data = HELP_DATABASE.get(topic, {
            "title": "❓ Help",
            "what": "No help available for this topic.",
            "when": "",
            "how": "",
            "tips": "",
        })

        self.win = ctk.CTkToplevel(parent)
        self.win.title(f"❓ Help — {help_data['title']}")
        self.win.geometry("500x430")
        self.win.transient(parent)
        self.win.grab_set()
        self.win.resizable(False, True)
        self.win.configure(fg_color=colors["bg"])

        # Scrollable content
        content = ctk.CTkScrollableFrame(self.win, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=(15, 5))

        # Title
        ctk.CTkLabel(content, text=help_data["title"],
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=colors["text_primary"]).pack(anchor="w", pady=(0, 10))

        # What
        self._section(content, "💡 What does this do?", help_data["what"], colors)

        # When
        if help_data.get("when"):
            self._section(content, "📅 When to use it?", help_data["when"], colors)

        # How
        if help_data.get("how"):
            self._section(content, "📋 How to use it:", help_data["how"], colors)

        # Tips
        if help_data.get("tips"):
            self._section(content, "💡 Tips:", help_data["tips"], colors)

        # Close
        ctk.CTkButton(self.win, text="Got it!", width=90, height=32,
                      corner_radius=8, fg_color=colors["primary"],
                      hover_color=colors["primary_hover"],
                      font=ctk.CTkFont(size=12, weight="bold"),
                      command=self.win.destroy).pack(pady=(5, 15))

    def _section(self, parent, title: str, text: str, colors: dict):
        """Add a help section."""
        ctk.CTkLabel(parent, text=title,
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=colors["primary"]).pack(anchor="w", pady=(10, 3))
        ctk.CTkLabel(parent, text=text,
                     font=ctk.CTkFont(size=11),
                     text_color=colors["text_primary"],
                     justify="left", wraplength=430).pack(anchor="w", padx=10)


class FullHelpDialog:
    """Full help dialog showing ALL features in a searchable list."""

    def __init__(self, parent, app):
        self.app = app
        colors = DARK_THEME if app.is_dark else LIGHT_THEME

        self.win = ctk.CTkToplevel(parent)
        self.win.title("📖 Feature Guide — All Features Explained")
        self.win.geometry("600x550")
        self.win.transient(parent)
        self.win.grab_set()
        self.win.resizable(True, True)
        self.win.configure(fg_color=colors["bg"])

        # Title
        ctk.CTkLabel(self.win, text="📖 Feature Guide",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=colors["text_primary"]).pack(pady=(15, 5))
        ctk.CTkLabel(self.win, text="Every feature explained in simple words. Click any to learn more.",
                     font=ctk.CTkFont(size=11),
                     text_color=colors["text_secondary"]).pack(pady=(0, 10))

        # Search
        search_frame = ctk.CTkFrame(self.win, fg_color="transparent")
        search_frame.pack(fill="x", padx=20, pady=(0, 10))

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._filter())
        ctk.CTkEntry(search_frame, textvariable=self.search_var,
                     width=400, height=30, placeholder_text="🔍 Search features...",
                     font=ctk.CTkFont(size=11)).pack(side="left")

        # Feature list
        self.list_frame = ctk.CTkScrollableFrame(self.win, fg_color="transparent")
        self.list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 5))

        self._render_all()

        # Close
        ctk.CTkButton(self.win, text="Close", width=70, height=30,
                      corner_radius=6, fg_color=colors["badge_bg"],
                      hover_color=colors["surface_hover"],
                      text_color=colors["text_primary"],
                      command=self.win.destroy).pack(pady=(5, 15))

    def _render_all(self, filter_text: str = ""):
        """Render all help topics."""
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        colors = DARK_THEME if self.app.is_dark else LIGHT_THEME

        for topic, data in HELP_DATABASE.items():
            # Filter
            if filter_text:
                searchable = f"{data['title']} {data['what']} {data.get('tips', '')}".lower()
                if filter_text.lower() not in searchable:
                    continue

            card = ctk.CTkFrame(self.list_frame, fg_color=colors["surface"], corner_radius=6)
            card.pack(fill="x", pady=2)

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=12, pady=8)

            ctk.CTkLabel(inner, text=data["title"],
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=colors["text_primary"]).pack(anchor="w")

            ctk.CTkLabel(inner, text=data["what"],
                         font=ctk.CTkFont(size=10),
                         text_color=colors["text_secondary"],
                         wraplength=480).pack(anchor="w")

            ctk.CTkButton(inner, text="Learn More →", width=90, height=22,
                          corner_radius=4, font=ctk.CTkFont(size=10),
                          fg_color=colors["badge_bg"], hover_color=colors["surface_hover"],
                          text_color=colors["primary"],
                          command=lambda t=topic: HelpGuideDialog(self.win, self.app, t)
                          ).pack(anchor="e")

    def _filter(self):
        """Filter topics by search text."""
        self._render_all(self.search_var.get())
