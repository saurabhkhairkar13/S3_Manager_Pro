"""Menu Bar — organizes ALL 75+ features into logical menu groups.

Information Architecture:
  File     → Connection, Export, Settings, Quit
  Edit     → Select, Copy, Rename, Tags, Delete
  View     → Theme, Panels, Refresh, Sorting
  Bucket   → Management, Config, ACL, CORS, Website, Health
  Tools    → Sync, Cost, Analytics, Search, Multipart Cleanup
  Help     → Shortcuts, About
"""
import tkinter as tk


class MenuBar:
    """Top menu bar with all features organized into logical groups."""

    def __init__(self, root, app):
        self.app = app
        self.root = root

        # Create the menu bar
        self.menubar = tk.Menu(root, tearoff=0)

        # ═══════════════════════════════════════
        # FILE MENU
        # ═══════════════════════════════════════
        file_menu = tk.Menu(self.menubar, tearoff=0)
        file_menu.add_command(label="Connect / Reconnect", command=app._auto_connect, accelerator="")
        file_menu.add_command(label="Switch Account...", command=app.open_profile_switcher)
        file_menu.add_separator()
        file_menu.add_command(label="Upload Files...", command=app.upload_files, accelerator="Ctrl+U")
        file_menu.add_command(label="Upload Folder...", command=app.upload_files)
        file_menu.add_command(label="Download Selected", command=app.download_selected, accelerator="Ctrl+D")
        file_menu.add_command(label="Resume Transfers...", command=app.open_resume_transfers)
        file_menu.add_separator()
        file_menu.add_command(label="Export File List to CSV...", command=app.export_csv, accelerator="Ctrl+E")
        file_menu.add_separator()
        file_menu.add_command(label="Settings...", command=app.open_settings, accelerator="Ctrl+,")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=root.quit)
        self.menubar.add_cascade(label="File", menu=file_menu)

        # ═══════════════════════════════════════
        # EDIT MENU
        # ═══════════════════════════════════════
        edit_menu = tk.Menu(self.menubar, tearoff=0)
        edit_menu.add_command(label="Select All", command=app.file_table._select_all, accelerator="Ctrl+A")
        edit_menu.add_command(label="Deselect All", command=app.file_table._deselect_all, accelerator="Ctrl+Shift+A")
        edit_menu.add_separator()
        edit_menu.add_command(label="Copy S3 Path", command=app.copy_s3_path)
        edit_menu.add_command(label="Copy Share URL", command=app.copy_presigned_url, accelerator="Ctrl+L")
        edit_menu.add_command(label="URL Formats...", command=app.open_url_customizer)
        edit_menu.add_separator()
        edit_menu.add_command(label="Batch Rename...", command=app.open_batch_rename)
        edit_menu.add_command(label="Copy/Move to Bucket...", command=app.open_cross_bucket_copy)
        edit_menu.add_command(label="Change Storage Class...", command=app.change_storage_class)
        edit_menu.add_command(label="Edit Tags...", command=app.open_bulk_tag_editor)
        edit_menu.add_separator()
        edit_menu.add_command(label="Delete Selected", command=app.delete_selected, accelerator="Del")
        self.menubar.add_cascade(label="Edit", menu=edit_menu)

        # ═══════════════════════════════════════
        # VIEW MENU
        # ═══════════════════════════════════════
        view_menu = tk.Menu(self.menubar, tearoff=0)
        view_menu.add_command(label="Toggle Dark/Light Theme", command=app.toggle_theme)
        view_menu.add_separator()
        view_menu.add_command(label="Refresh", command=app.refresh_listing, accelerator="F5")
        view_menu.add_separator()
        view_menu.add_command(label="File Preview", command=app.open_file_preview, accelerator="Ctrl+P")
        view_menu.add_command(label="Properties", command=app.show_properties, accelerator="Ctrl+I")
        view_menu.add_command(label="Object Lock/Retention", command=app.open_object_lock)
        view_menu.add_separator()
        view_menu.add_command(label="File Versions", command=app.open_versioning)
        view_menu.add_command(label="Compare Versions (Diff)", command=app.open_diff_viewer)
        view_menu.add_separator()
        view_menu.add_command(label="Transfer Queue", command=app.open_transfer_queue, accelerator="Ctrl+T")
        view_menu.add_command(label="Speed Graph", command=app.open_speed_graph)
        view_menu.add_command(label="Activity Log", command=app._show_activity_log)
        self.menubar.add_cascade(label="View", menu=view_menu)

        # ═══════════════════════════════════════
        # BUCKET MENU
        # ═══════════════════════════════════════
        bucket_menu = tk.Menu(self.menubar, tearoff=0)
        bucket_menu.add_command(label="Create Bucket...", command=app.open_bucket_management)
        bucket_menu.add_command(label="Delete Bucket...", command=app.open_bucket_management)
        bucket_menu.add_separator()
        bucket_menu.add_command(label="Bucket Properties / Configure", command=app.open_bucket_management)
        bucket_menu.add_command(label="ACL & Permissions...", command=app.open_acl_editor)
        bucket_menu.add_command(label="CORS Configuration...", command=app.open_cors_editor)
        bucket_menu.add_command(label="Static Website Hosting...", command=app.open_website_hosting)
        bucket_menu.add_separator()
        bucket_menu.add_command(label="Calculate Folder Size", command=app.open_folder_size)
        bucket_menu.add_command(label="Bucket Analytics", command=app.open_analytics, accelerator="Ctrl+Shift+S")
        self.menubar.add_cascade(label="Bucket", menu=bucket_menu)

        # ═══════════════════════════════════════
        # TOOLS MENU
        # ═══════════════════════════════════════
        tools_menu = tk.Menu(self.menubar, tearoff=0)

        # Sync submenu
        sync_sub = tk.Menu(tools_menu, tearoff=0)
        sync_sub.add_command(label="One-Time Sync (Dry Run)...", command=app.open_sync_dialog)
        sync_sub.add_command(label="Scheduled Auto-Sync...", command=app.open_scheduled_sync)
        tools_menu.add_cascade(label="📋 S3 Sync", menu=sync_sub)

        tools_menu.add_separator()

        # Cost submenu
        cost_sub = tk.Menu(tools_menu, tearoff=0)
        cost_sub.add_command(label="Cost Estimation", command=app.open_cost_estimation)
        cost_sub.add_command(label="Cost Advisor (Recommendations)", command=app.open_cost_advisor)
        cost_sub.add_command(label="Cost Intelligence Center", command=app.open_cost_intelligence)
        tools_menu.add_cascade(label="💰 Cost & Optimization", menu=cost_sub)

        tools_menu.add_separator()

        # Glacier submenu
        glacier_sub = tk.Menu(tools_menu, tearoff=0)
        glacier_sub.add_command(label="Restore Selected Files...", command=app.restore_glacier)
        tools_menu.add_cascade(label="🧊 Glacier", menu=glacier_sub)

        tools_menu.add_separator()
        tools_menu.add_command(label="🔍 Smart Search (All Buckets)...", command=app.open_smart_search, accelerator="Ctrl+Shift+F")
        tools_menu.add_command(label="🛡️ Security Health Check...", command=app.open_health_check)
        tools_menu.add_command(label="🧹 Orphaned Upload Cleaner...", command=app.open_multipart_cleaner)
        tools_menu.add_command(label="☁️ CloudFront Invalidation...", command=app.open_cloudfront_invalidation)
        tools_menu.add_separator()
        tools_menu.add_command(label="🚦 Bandwidth Control...", command=app.open_bandwidth_control)
        self.menubar.add_cascade(label="Tools", menu=tools_menu)

        # ═══════════════════════════════════════
        # HELP MENU
        # ═══════════════════════════════════════
        help_menu = tk.Menu(self.menubar, tearoff=0)
        help_menu.add_command(label="🎓 Guided Tour (Walkthrough)", command=app.start_guided_tour)
        help_menu.add_command(label="📖 Feature Guide (All Features Explained)", command=app.open_feature_guide)
        help_menu.add_separator()

        # User Guide submenu — how to use each feature
        guide_menu = tk.Menu(help_menu, tearoff=0)
        guide_menu.add_command(label="⬇ How to Download Files", command=lambda: app.show_help_for("download"))
        guide_menu.add_command(label="⬆ How to Upload Files", command=lambda: app.show_help_for("upload"))
        guide_menu.add_command(label="🔗 How to Share Files (Presigned URL)", command=lambda: app.show_help_for("share_url"))
        guide_menu.add_command(label="🗑 How to Delete Files", command=lambda: app.show_help_for("delete"))
        guide_menu.add_separator()
        guide_menu.add_command(label="📋 How to Sync Folders", command=lambda: app.show_help_for("sync"))
        guide_menu.add_command(label="⏰ How to Schedule Auto-Sync", command=lambda: app.show_help_for("scheduled_sync"))
        guide_menu.add_command(label="🔄 How to Restore Glacier Files", command=lambda: app.show_help_for("restore"))
        guide_menu.add_separator()
        guide_menu.add_command(label="💡 How to Save Money (Cost Advisor)", command=lambda: app.show_help_for("cost_advisor"))
        guide_menu.add_command(label="🧹 How to Clean Orphaned Uploads", command=lambda: app.show_help_for("multipart_cleaner"))
        guide_menu.add_command(label="🛡️ How to Check Security", command=lambda: app.show_help_for("health_check"))
        guide_menu.add_separator()
        guide_menu.add_command(label="🔍 How to Search Across Buckets", command=lambda: app.show_help_for("smart_search"))
        guide_menu.add_command(label="👁 How to Preview Files", command=lambda: app.show_help_for("file_preview"))
        guide_menu.add_command(label="📜 How to View File Versions", command=lambda: app.show_help_for("versioning"))
        guide_menu.add_command(label="✏️ How to Batch Rename", command=lambda: app.show_help_for("batch_rename"))
        guide_menu.add_command(label="📤 How to Copy/Move Between Buckets", command=lambda: app.show_help_for("cross_bucket_copy"))
        guide_menu.add_separator()
        guide_menu.add_command(label="🪣 How to Manage Buckets", command=lambda: app.show_help_for("bucket_management"))
        guide_menu.add_command(label="📊 How to View Analytics", command=lambda: app.show_help_for("analytics"))
        guide_menu.add_command(label="🚦 How to Control Bandwidth", command=lambda: app.show_help_for("bandwidth"))
        guide_menu.add_command(label="☁️ How to Invalidate CloudFront", command=lambda: app.show_help_for("cloudfront"))
        help_menu.add_cascade(label="📚 User Guide (How To...)", menu=guide_menu)

        help_menu.add_separator()
        help_menu.add_command(label="Keyboard Shortcuts", command=app._show_shortcuts_help)
        help_menu.add_separator()
        help_menu.add_command(label="About S3 Manager Pro", command=app._show_about)
        self.menubar.add_cascade(label="Help", menu=help_menu)

        # Set the menu bar
        root.configure(menu=self.menubar)
