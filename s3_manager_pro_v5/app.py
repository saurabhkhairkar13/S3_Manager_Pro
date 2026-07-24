"""Main Application — wires UI components to backend, handles state and navigation."""
import os
import sys
import logging
import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk

from s3_manager_pro_v5.utils.constants import (
    APP_TITLE, DARK_THEME, LIGHT_THEME, LOG_FILE
)
from s3_manager_pro_v5.utils.formatting import format_size, NON_GLACIER_CLASSES
from s3_manager_pro_v5.backend.auth import CredentialManager, BookmarkManager
from s3_manager_pro_v5.backend.s3_client import S3Client
from s3_manager_pro_v5.backend.transfer import TransferEngine
from s3_manager_pro_v5.ui.header import HeaderBar
from s3_manager_pro_v5.ui.sidebar import Sidebar
from s3_manager_pro_v5.ui.breadcrumb import BreadcrumbBar
from s3_manager_pro_v5.ui.file_table import FileTable
from s3_manager_pro_v5.ui.action_bar import ActionBar, ProgressBar
from s3_manager_pro_v5.ui.notifications import notify_download_complete, notify_upload_complete
from s3_manager_pro_v5.ui.dialogs.transfer_queue import TransferHistory

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class S3ManagerApp:
    """Main application controller."""

    def __init__(self):
        # State
        self.is_dark = True
        self.current_bucket = ""
        self.current_prefix = ""
        self.s3_client = None
        self.transfer_engine = None
        self.transfer_history = TransferHistory()

        # Managers
        self.cred_manager = CredentialManager()
        self.bookmark_manager = BookmarkManager()

        # Setup CTk
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Create window
        self.root = ctk.CTk()
        self.root.title(APP_TITLE)
        self.root.geometry("1350x850")
        self.root.minsize(1100, 700)

        # Set app icon
        self._set_app_icon()

        # Set theme from saved settings
        saved_theme = self.cred_manager.get("theme", "dark")
        self.is_dark = saved_theme == "dark"
        ctk.set_appearance_mode("dark" if self.is_dark else "light")

        # Build UI
        self._build_ui()
        self._apply_theme()
        self._bind_keyboard_shortcuts()
        self._setup_drag_and_drop()

        # Check if first launch (no settings file exists)
        if self._is_first_launch():
            self.root.after(200, self._show_setup_wizard)
        else:
            # Auto-connect on startup
            self.root.after(300, self._auto_connect)

    def _is_first_launch(self) -> bool:
        """Check if this is the first time running the app."""
        from s3_manager_pro_v5.utils.constants import SETTINGS_FILE
        return not os.path.exists(SETTINGS_FILE)

    def _show_setup_wizard(self):
        """Show the first-launch setup wizard."""
        from s3_manager_pro_v5.ui.wizard import SetupWizard
        SetupWizard(self.root, self._on_wizard_complete, is_dark=self.is_dark)

    def _on_wizard_complete(self, settings: dict, access_key: str, secret_key: str):
        """Called when the setup wizard finishes."""
        # Save settings
        self.cred_manager.save_settings(settings)

        # Store credentials securely
        if access_key and secret_key:
            self.cred_manager.store_credentials(access_key, secret_key)

        # Apply theme from wizard choice
        self.is_dark = settings.get("theme", "dark") == "dark"
        ctk.set_appearance_mode("dark" if self.is_dark else "light")
        self._apply_theme()

        # Connect
        self.root.after(500, self._auto_connect)

    def _set_app_icon(self):
        """Set the application window icon."""
        try:
            icon_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "app_icon.ico"
            )
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass  # Skip if icon not available

    def _build_ui(self):
        """Construct the main layout — professional UI with menu bar, toolbar, details panel."""
        from s3_manager_pro_v5.ui.menu_bar import MenuBar
        from s3_manager_pro_v5.ui.toolbar import Toolbar
        from s3_manager_pro_v5.ui.details_panel import DetailsPanel
        from s3_manager_pro_v5.ui.status_bar import StatusBar

        # ── Menu Bar (File/Edit/View/Bucket/Tools/Help) ──
        # Must be created AFTER file_table exists, so we build it last and assign

        # ── Header bar (top — connection info) ──
        self.header = HeaderBar(self.root, self)
        self.header.pack(fill="x", side="top")

        # ── Toolbar (icon buttons) ──
        self.toolbar = Toolbar(self.root, self)
        self.toolbar.pack(fill="x", side="top")

        # ── Status Bar (very bottom) ──
        self.status_bar = StatusBar(self.root, self)
        self.status_bar.pack(fill="x", side="bottom")

        # ── Progress bar (above status bar) ──
        self.progress_bar = ProgressBar(self.root, self)
        self.progress_bar.pack(fill="x", side="bottom")

        # ── Action bar (above progress — Download/Upload/Restore/Share/Sync/Delete) ──
        self.action_bar = ActionBar(self.root, self)
        self.action_bar.pack(fill="x", side="bottom")

        # ── Middle container (sidebar + main area + details panel) ──
        self.middle = ctk.CTkFrame(self.root, corner_radius=0, fg_color="transparent")
        self.middle.pack(fill="both", expand=True, side="top")

        # Sidebar (left — buckets, stats, bookmarks)
        self.sidebar = Sidebar(self.middle, self)
        self.sidebar.pack(fill="y", side="left")

        # Details Panel (right — file info, quick actions)
        self.details_panel = DetailsPanel(self.middle, self)
        self.details_panel.pack(fill="y", side="right")

        # Center content area
        self.content = ctk.CTkFrame(self.middle, corner_radius=0, fg_color="transparent")
        self.content.pack(fill="both", expand=True, side="left")

        # Breadcrumb (top of content)
        self.breadcrumb = BreadcrumbBar(self.content, self)
        self.breadcrumb.pack(fill="x", side="top")

        # File table (main area)
        self.file_table = FileTable(self.content, self)
        self.file_table.pack(fill="both", expand=True, side="top")

        # ── Now create Menu Bar (needs file_table to exist) ──
        self.menu_bar = MenuBar(self.root, self)

    def _bind_keyboard_shortcuts(self):
        """Bind keyboard shortcuts."""
        self.root.bind("<Control-d>", lambda e: self.download_selected())
        self.root.bind("<Control-u>", lambda e: self.upload_files())
        self.root.bind("<Control-a>", lambda e: self.file_table._select_all())
        self.root.bind("<Control-Shift-A>", lambda e: self.file_table._deselect_all())
        self.root.bind("<Control-f>", lambda e: self.breadcrumb.focus_search())
        self.root.bind("<Control-l>", lambda e: self.copy_presigned_url())
        self.root.bind("<Control-e>", lambda e: self.export_csv())
        self.root.bind("<Control-i>", lambda e: self.show_properties())
        self.root.bind("<Control-t>", lambda e: self.open_transfer_queue())
        self.root.bind("<Control-p>", lambda e: self.open_file_preview())
        self.root.bind("<Control-Shift-F>", lambda e: self.open_smart_search())
        self.root.bind("<Control-Shift-S>", lambda e: self.open_analytics())
        self.root.bind("<F5>", lambda e: self.refresh_listing())
        self.root.bind("<Delete>", lambda e: self.delete_selected())
        self.root.bind("<BackSpace>", lambda e: self._navigate_up())
        self.root.bind("<Control-comma>", lambda e: self.open_settings())
        self.root.bind("<Escape>", lambda e: self.breadcrumb.clear_search())

    def _setup_drag_and_drop(self):
        """Setup drag-and-drop on file table if tkinterdnd2 is available."""
        try:
            from s3_manager_pro_v5.ui.drag_drop import setup_dnd
            setup_dnd(self.file_table, self)
        except Exception:
            pass  # Silently skip if DnD not available

    def _apply_theme(self):
        """Apply current theme to all components."""
        colors = DARK_THEME if self.is_dark else LIGHT_THEME
        self.root.configure(fg_color=colors["bg"])
        self.header.apply_theme(colors)
        self.header.update_theme_icon(self.is_dark)
        self.sidebar.apply_theme(colors)
        self.breadcrumb.apply_theme(colors)
        self.file_table.apply_theme(colors)
        self.action_bar.apply_theme(colors)
        self.progress_bar.apply_theme(colors)
        self.toolbar.apply_theme(colors)
        self.details_panel.apply_theme(colors)
        self.status_bar.apply_theme(colors)

    # ═══════════════════════════════════════════
    # THEME
    # ═══════════════════════════════════════════
    def toggle_theme(self):
        """Toggle between dark and light theme."""
        self.is_dark = not self.is_dark
        ctk.set_appearance_mode("dark" if self.is_dark else "light")
        self._apply_theme()

        # Save preference
        settings = self.cred_manager.settings.copy()
        settings["theme"] = "dark" if self.is_dark else "light"
        self.cred_manager.save_settings(settings)

    # ═══════════════════════════════════════════
    # CONNECTION
    # ═══════════════════════════════════════════
    def disconnect(self):
        """Disconnect from AWS — clear session."""
        self.s3_client = None
        self.transfer_engine = None
        self.header.set_disconnected("Disconnected")
        self.status_bar.set_disconnected("Disconnected")
        self.sidebar.set_buckets([])
        self.sidebar.clear_stats()
        self.file_table.set_objects([])
        self.breadcrumb.set_path("", "")
        self.progress_bar.set_status("Disconnected — click Connect or open Settings to reconnect")
        from s3_manager_pro_v5.ui.toast import show_toast
        show_toast(self.root, "Disconnected from AWS", "info")

    def _auto_connect(self):
        """Auto-connect using saved credentials."""
        auth_mode = self.cred_manager.get("auth_mode", "keys")
        region = self.cred_manager.get("region", "ap-south-1")
        profile = self.cred_manager.get("profile", "")
        access_key, secret_key = self.cred_manager.get_credentials()

        if not access_key and not profile:
            self.header.set_disconnected("No credentials — press ⚙ to configure")
            return

        self.header.set_region(region)
        self.progress_bar.set_status("Connecting...")

        def do_connect():
            self.s3_client = S3Client(
                region=region,
                profile=profile if auth_mode == "profile" else None,
                access_key=access_key if auth_mode == "keys" else None,
                secret_key=secret_key if auth_mode == "keys" else None,
            )
            success, message = self.s3_client.connect()

            def update_ui():
                if success:
                    self.header.set_connected(message)
                    self.status_bar.set_connected(message, self.s3_client.region)
                    self.transfer_engine = TransferEngine(self.s3_client)
                    self.transfer_engine.set_progress_callback(self._on_transfer_progress)
                    self._load_buckets()
                    self.progress_bar.set_status(f"Connected — {message}")
                else:
                    self.header.set_disconnected(message)
                    self.status_bar.set_disconnected(message)
                    self.progress_bar.set_status(f"❌ {message}")
                    # Show error dialog with retry option
                    from s3_manager_pro_v5.ui.error_handler import show_error
                    error_info = {
                        "title": "🔌 Connection Failed",
                        "message": message,
                        "help": "Check your credentials in Settings (⚙) and verify your internet connection.",
                        "retryable": True,
                    }
                    show_error(self.root, error_info, on_retry=self._auto_connect, is_dark=self.is_dark)

            self.root.after(0, update_ui)

        threading.Thread(target=do_connect, daemon=True).start()

    def _load_buckets(self):
        """Load bucket list into sidebar."""
        if not self.s3_client or not self.s3_client.is_connected:
            return

        def do_load():
            buckets = self.s3_client.list_buckets()
            self.root.after(0, lambda: self.sidebar.set_buckets(buckets))
            # Restore last bucket
            last_bucket = self.cred_manager.get("last_bucket", "")
            if last_bucket and last_bucket in buckets:
                last_prefix = self.cred_manager.get("last_prefix", "")
                self.root.after(100, lambda: self.navigate_to(last_bucket, last_prefix))

        threading.Thread(target=do_load, daemon=True).start()

    # ═══════════════════════════════════════════
    # NAVIGATION
    # ═══════════════════════════════════════════
    def on_bucket_selected(self, bucket: str):
        """Handle bucket selection from sidebar (single click)."""
        pass  # Just highlight, don't navigate yet

    def on_bucket_navigate(self, bucket: str):
        """Handle bucket double-click — navigate into it."""
        self.navigate_to(bucket, "")

    def navigate_to(self, bucket: str, prefix: str):
        """Navigate to a specific bucket/prefix and load objects."""
        self.current_bucket = bucket
        self.current_prefix = prefix
        self.breadcrumb.set_path(bucket, prefix)
        self.breadcrumb.clear_search()
        self._load_objects()

        # Save last location
        settings = self.cred_manager.settings.copy()
        settings["last_bucket"] = bucket
        settings["last_prefix"] = prefix
        self.cred_manager.save_settings(settings)

    def navigate_into_folder(self, folder_key: str):
        """Navigate into a sub-folder."""
        self.navigate_to(self.current_bucket, folder_key)

    def _navigate_up(self):
        """Navigate up one folder level."""
        if not self.current_prefix:
            return
        prefix = self.current_prefix.rstrip("/")
        if "/" in prefix:
            parent = prefix.rsplit("/", 1)[0] + "/"
        else:
            parent = ""
        self.navigate_to(self.current_bucket, parent)

    def navigate_to_bookmark(self, bookmark: dict):
        """Navigate to a bookmarked path."""
        self.navigate_to(bookmark["bucket"], bookmark.get("prefix", ""))

    def _load_objects(self):
        """Load objects for current bucket/prefix."""
        if not self.s3_client or not self.s3_client.is_connected:
            return

        self.progress_bar.set_status(f"Loading s3://{self.current_bucket}/{self.current_prefix}...")
        self.file_table.show_loading(f"Loading s3://{self.current_bucket}/{self.current_prefix}...")

        def do_load():
            try:
                result = self.s3_client.list_objects_page(
                    self.current_bucket, self.current_prefix
                )
                all_objects = result.folders + result.objects

                # If there are more, keep loading in background
                while result.is_truncated:
                    result = self.s3_client.list_objects_page(
                        self.current_bucket, self.current_prefix,
                        continuation_token=result.continuation_token
                    )
                    all_objects.extend(result.objects)

                def update_ui():
                    self.file_table.set_objects(all_objects)
                    total_size = sum(o.size for o in all_objects if not o.is_folder)
                    folders = sum(1 for o in all_objects if o.is_folder)
                    files = len(all_objects) - folders
                    glacier_count = sum(
                        1 for o in all_objects
                        if not o.is_folder and o.storage_class not in NON_GLACIER_CLASSES
                    )
                    self.sidebar.update_stats(files, total_size, glacier_count)
                    if files == 0 and folders == 0:
                        self.progress_bar.set_status("No objects found in this location.")
                    else:
                        self.progress_bar.set_status(
                            f"Loaded {folders} folders, {files:,} files ({format_size(total_size)})"
                        )

                self.root.after(0, update_ui)

            except Exception as e:
                error_msg = str(e)
                def show_error():
                    from s3_manager_pro_v5.ui.error_handler import show_error as display_error
                    display_error(self.root, e, on_retry=self._load_objects, is_dark=self.is_dark)
                    self.progress_bar.set_status(f"❌ Failed to list objects: {error_msg[:60]}")
                self.root.after(0, show_error)

        threading.Thread(target=do_load, daemon=True).start()

    def refresh_listing(self):
        """Refresh current listing."""
        if self.current_bucket:
            self._load_objects()

    def on_search_filter(self, text: str):
        """Handle search filter change from breadcrumb."""
        self.file_table.set_filter(text)

    # ═══════════════════════════════════════════
    # BOOKMARKS
    # ═══════════════════════════════════════════
    def add_bookmark(self):
        """Bookmark current path."""
        if not self.current_bucket:
            return
        self.bookmark_manager.add(self.current_bucket, self.current_prefix)
        self.sidebar.set_bookmarks(self.bookmark_manager.bookmarks)
        from s3_manager_pro_v5.ui.toast import show_toast
        show_toast(self.root, f"Bookmarked: {self.current_bucket}/{self.current_prefix}", "info")

    # ═══════════════════════════════════════════
    # TRANSFERS
    # ═══════════════════════════════════════════
    def download_selected(self):
        """Download selected files."""
        if not self.s3_client or not self.transfer_engine:
            messagebox.showwarning("Warning", "Not connected. Configure credentials in Settings.")
            return

        selected = self.file_table.get_selected_objects()
        if not selected:
            messagebox.showwarning("Warning", "No files selected for download.")
            return

        download_dir = self.cred_manager.get("download_dir", "")
        if not download_dir:
            download_dir = filedialog.askdirectory(title="Select Download Folder")
            if not download_dir:
                return

        total_size = sum(o.size for o in selected)
        confirm = messagebox.askyesno(
            "Confirm Download",
            f"Download {len(selected)} files ({format_size(total_size)}) to:\n{download_dir}\n\nContinue?"
        )
        if not confirm:
            return

        self.action_bar.set_transfer_active(True)
        parallel = self.cred_manager.get("parallel", 3)

        # Add to transfer history
        for obj in selected:
            filename = obj.key.split("/")[-1] if "/" in obj.key else obj.key
            self.transfer_history.add_record("download", filename, obj.size, "active")

        def do_download():
            import time
            start_time = time.time()
            result = self.transfer_engine.download_files(
                bucket=self.current_bucket,
                objects=selected,
                download_dir=download_dir,
                prefix=self.current_prefix,
                parallel=int(parallel),
            )
            elapsed = time.time() - start_time
            self.root.after(0, lambda: self.action_bar.set_transfer_active(False))

            # Show completion summary dialog with errors
            def show_summary():
                from s3_manager_pro_v5.ui.dialogs.transfer_summary import TransferSummaryDialog
                TransferSummaryDialog(
                    self.root, self.is_dark, "download",
                    success=result.completed_files,
                    skipped=result.skipped_files,
                    failed=result.failed_files,
                    total_size=result.transferred_bytes,
                    elapsed_seconds=elapsed,
                    errors=result.errors,
                    download_dir=download_dir,
                )

            self.root.after(0, show_summary)

            # Send system notification
            notify_download_complete(
                result.completed_files, result.failed_files, format_size(total_size)
            )

        threading.Thread(target=do_download, daemon=True).start()

    def upload_files(self):
        """Open full upload dialog."""
        if not self.s3_client or not self.transfer_engine:
            messagebox.showwarning("Warning", "Not connected.")
            return
        if not self.current_bucket:
            messagebox.showwarning("Warning", "Select a bucket first.")
            return
        from s3_manager_pro_v5.ui.dialogs.upload_dialog import UploadDialog
        UploadDialog(self.root, self, self.current_bucket, self.current_prefix)

    def restore_glacier(self):
        """Open Smart Glacier Restore dialog with cost estimation."""
        if not self.s3_client:
            return

        selected = self.file_table.get_selected_objects()
        glacier_objects = [o for o in selected if o.storage_class not in NON_GLACIER_CLASSES]

        if not glacier_objects:
            messagebox.showinfo("Info", "No Glacier/Deep Archive files selected.\n"
                                "Only Glacier-class files need restore before download.")
            return

        from s3_manager_pro_v5.ui.dialogs.glacier_restore import GlacierRestoreDialog
        GlacierRestoreDialog(self.root, self, self.current_bucket, glacier_objects)

    def pause_transfer(self):
        """Pause/Resume current transfer."""
        if self.transfer_engine:
            self.transfer_engine.pause()
            self.action_bar.set_paused(self.transfer_engine.is_paused)

    def cancel_transfer(self):
        """Cancel current transfer."""
        if self.transfer_engine:
            if messagebox.askyesno("Cancel", "Cancel the current transfer?"):
                self.transfer_engine.cancel()

    def _on_transfer_progress(self, progress):
        """Callback from TransferEngine — update progress bar."""
        self.root.after(0, lambda: self.progress_bar.update_progress(progress))

    # ═══════════════════════════════════════════
    # S3 ACTIONS
    # ═══════════════════════════════════════════
    def copy_presigned_url(self):
        """Open Presigned URL Generator dialog."""
        if not self.s3_client:
            return

        obj = self.file_table.get_focused_object()
        if not obj or obj.is_folder:
            messagebox.showinfo("Info", "Select a file first.")
            return

        from s3_manager_pro_v5.ui.dialogs.presigned_url import PresignedURLDialog
        filename = obj.key.split("/")[-1] if "/" in obj.key else obj.key
        PresignedURLDialog(self.root, self, self.current_bucket, obj.key, filename)

    def copy_s3_path(self):
        """Copy S3 path to clipboard."""
        obj = self.file_table.get_focused_object()
        if obj:
            path = f"s3://{self.current_bucket}/{obj.key}"
            self.root.clipboard_clear()
            self.root.clipboard_append(path)
            self.progress_bar.set_status(f"📋 Copied: {path}")

    def show_properties(self):
        """Show object properties panel."""
        obj = self.file_table.get_focused_object()
        if not obj or not self.s3_client or obj.is_folder:
            return
        from s3_manager_pro_v5.ui.dialogs.properties import PropertiesPanel
        PropertiesPanel(self.root, self, self.current_bucket, obj)

    def change_storage_class(self):
        """Open Bulk Storage Class Change dialog."""
        if not self.s3_client:
            return
        selected = self.file_table.get_selected_objects()
        if not selected:
            messagebox.showwarning("Warning", "No files selected.")
            return
        from s3_manager_pro_v5.ui.dialogs.storage_class import StorageClassDialog
        StorageClassDialog(self.root, self, self.current_bucket, selected)

    def delete_selected(self):
        """Delete selected objects."""
        if not self.s3_client:
            return

        selected = self.file_table.get_selected_objects()
        if not selected:
            messagebox.showwarning("Warning", "No files selected.")
            return

        confirm = messagebox.askyesno(
            "⚠️ Confirm Delete",
            f"Permanently delete {len(selected)} objects from:\n"
            f"s3://{self.current_bucket}/{self.current_prefix}\n\n"
            f"This cannot be undone!",
            icon="warning"
        )
        if not confirm:
            return

        def do_delete():
            try:
                keys = [o.key for o in selected]
                success, errors = self.s3_client.delete_objects(self.current_bucket, keys)

                def show_result():
                    if errors > 0:
                        messagebox.showerror(
                            "Delete Failed",
                            f"Deleted {success} objects successfully.\n"
                            f"Failed to delete {errors} objects.\n\n"
                            f"Possible reasons:\n"
                            f"• Permission denied (check IAM policy)\n"
                            f"• Object lock enabled\n"
                            f"• Bucket versioning with MFA delete"
                        )
                    else:
                        self.progress_bar.set_status(f"✅ Deleted {success} objects successfully.")
                        from s3_manager_pro_v5.ui.toast import show_toast
                        show_toast(self.root, f"{success} objects deleted successfully")
                    self.refresh_listing()

                self.root.after(0, show_result)

            except Exception as e:
                def show_error():
                    from s3_manager_pro_v5.ui.error_handler import show_error as display_error
                    display_error(self.root, e, is_dark=self.is_dark)
                    self.progress_bar.set_status(f"❌ Delete failed: {str(e)[:50]}")
                self.root.after(0, show_error)

        threading.Thread(target=do_delete, daemon=True).start()

    def open_sync_dialog(self):
        """Open S3 Sync dialog with dry-run preview."""
        if not self.s3_client:
            messagebox.showwarning("Warning", "Not connected.")
            return
        if not self.current_bucket:
            messagebox.showwarning("Warning", "Select a bucket first.")
            return
        from s3_manager_pro_v5.ui.dialogs.sync_dialog import SyncDialog
        SyncDialog(self.root, self, self.current_bucket, self.current_prefix)

    # ═══════════════════════════════════════════
    # NEW FEATURES (Sprint 2 & 3)
    # ═══════════════════════════════════════════
    def open_versioning(self):
        """Open file versioning viewer for focused object."""
        if not self.s3_client:
            return
        obj = self.file_table.get_focused_object()
        if not obj or obj.is_folder:
            messagebox.showinfo("Versioning", "Select a file to view its versions.")
            return
        from s3_manager_pro_v5.ui.dialogs.versioning import VersioningDialog
        VersioningDialog(self.root, self, self.current_bucket, obj.key)

    def open_cost_estimation(self):
        """Open cost estimation dialog."""
        if not self.file_table._all_objects:
            messagebox.showwarning("Cost", "Load files first.")
            return
        from s3_manager_pro_v5.ui.dialogs.cost_estimation import CostEstimationDialog
        objects = [o for o in self.file_table._all_objects if not o.is_folder]
        CostEstimationDialog(self.root, self, objects, self.current_bucket)

    def export_csv(self):
        """Export current file listing to CSV."""
        from s3_manager_pro_v5.ui.dialogs.export_csv import export_to_csv
        objects = [o for o in self.file_table._all_objects if not o.is_folder]
        export_to_csv(self.root, objects, self.current_bucket, self.current_prefix)

    def open_transfer_queue(self):
        """Open transfer queue/history dialog."""
        from s3_manager_pro_v5.ui.dialogs.transfer_queue import TransferQueueDialog
        TransferQueueDialog(self.root, self, self.transfer_history)

    def open_profile_switcher(self):
        """Open multi-account profile switcher."""
        from s3_manager_pro_v5.ui.dialogs.profile_switcher import ProfileSwitcherDialog
        ProfileSwitcherDialog(self.root, self)

    def open_analytics(self):
        """Open bucket analytics dashboard."""
        if not self.s3_client or not self.current_bucket:
            messagebox.showwarning("Warning", "Select a bucket first.")
            return
        from s3_manager_pro_v5.ui.dialogs.analytics import AnalyticsDashboard
        AnalyticsDashboard(self.root, self, self.current_bucket, self.current_prefix)

    def open_smart_search(self):
        """Open smart search across all buckets."""
        if not self.s3_client:
            messagebox.showwarning("Warning", "Not connected.")
            return
        from s3_manager_pro_v5.ui.dialogs.smart_search import SmartSearchDialog
        SmartSearchDialog(self.root, self)

    def open_file_preview(self):
        """Open file preview for focused object."""
        if not self.s3_client:
            return
        obj = self.file_table.get_focused_object()
        if not obj or obj.is_folder:
            messagebox.showinfo("Preview", "Select a file to preview.")
            return
        from s3_manager_pro_v5.ui.dialogs.file_preview import FilePreviewPanel
        FilePreviewPanel(self.root, self, self.current_bucket, obj)

    def open_cost_advisor(self):
        """Open intelligent cost advisor."""
        if not self.file_table._all_objects:
            messagebox.showwarning("Warning", "Load files first.")
            return
        from s3_manager_pro_v5.ui.dialogs.cost_advisor import CostAdvisorDialog
        objects = [o for o in self.file_table._all_objects if not o.is_folder]
        CostAdvisorDialog(self.root, self, self.current_bucket, objects)

    def open_cost_intelligence(self):
        """Open full cost intelligence center (access patterns, trends, budget, regions)."""
        if not self.file_table._all_objects:
            messagebox.showwarning("Warning", "Load files first.")
            return
        from s3_manager_pro_v5.ui.dialogs.cost_intelligence import CostIntelligenceDialog
        objects = [o for o in self.file_table._all_objects if not o.is_folder]
        CostIntelligenceDialog(self.root, self, self.current_bucket, objects)

    def open_bandwidth_control(self):
        """Open bandwidth throttle dialog."""
        from s3_manager_pro_v5.ui.dialogs.bandwidth import BandwidthDialog
        BandwidthDialog(self.root, self)

    def open_bulk_tag_editor(self):
        """Open bulk tag editor for selected objects."""
        if not self.s3_client:
            return
        selected = self.file_table.get_selected_objects()
        if not selected:
            messagebox.showwarning("Warning", "No files selected for tagging.")
            return
        from s3_manager_pro_v5.ui.dialogs.bulk_tags import BulkTagEditorDialog
        BulkTagEditorDialog(self.root, self, self.current_bucket, selected)

    def open_scheduled_sync(self):
        """Open scheduled auto-sync manager."""
        if not self.s3_client:
            messagebox.showwarning("Warning", "Not connected.")
            return
        from s3_manager_pro_v5.ui.dialogs.scheduled_sync import ScheduledSyncDialog
        ScheduledSyncDialog(self.root, self)

    def open_health_check(self):
        """Run S3 security health check across all buckets."""
        if not self.s3_client:
            messagebox.showwarning("Warning", "Not connected.")
            return
        from s3_manager_pro_v5.ui.dialogs.health_check import HealthCheckDialog
        HealthCheckDialog(self.root, self)

    def open_speed_graph(self):
        """Open real-time transfer speed graph."""
        from s3_manager_pro_v5.ui.dialogs.speed_graph import SpeedGraphDialog
        SpeedGraphDialog(self.root, self)

    def open_diff_viewer(self):
        """Open object diff viewer for focused file."""
        if not self.s3_client:
            return
        obj = self.file_table.get_focused_object()
        if not obj or obj.is_folder:
            messagebox.showinfo("Diff", "Select a text file to compare versions.")
            return
        from s3_manager_pro_v5.ui.dialogs.diff_viewer import DiffViewerDialog
        DiffViewerDialog(self.root, self, self.current_bucket, obj.key)

    def open_cloudfront_invalidation(self):
        """Open CloudFront invalidation dialog."""
        if not self.s3_client:
            return
        selected = self.file_table.get_selected_objects()
        if not selected:
            messagebox.showwarning("Warning", "No files selected for invalidation.")
            return
        keys = [o.key for o in selected]
        from s3_manager_pro_v5.ui.dialogs.cloudfront import CloudFrontInvalidationDialog
        CloudFrontInvalidationDialog(self.root, self, keys)

    def open_bucket_management(self):
        """Open bucket management dialog."""
        if not self.s3_client:
            messagebox.showwarning("Warning", "Not connected.")
            return
        from s3_manager_pro_v5.ui.dialogs.bucket_management import BucketManagementDialog
        BucketManagementDialog(self.root, self)

    # ═══════════════════════════════════════════
    # SPRINT 7: COMPETITOR GAP CLOSERS
    # ═══════════════════════════════════════════
    def open_acl_editor(self, key=None):
        """Open ACL/Permission editor."""
        if not self.s3_client or not self.current_bucket:
            messagebox.showwarning("Warning", "Select a bucket first.")
            return
        from s3_manager_pro_v5.ui.dialogs.acl_editor import ACLEditorDialog
        ACLEditorDialog(self.root, self, self.current_bucket, key)

    def open_cors_editor(self):
        """Open CORS configuration editor."""
        if not self.s3_client or not self.current_bucket:
            messagebox.showwarning("Warning", "Select a bucket first.")
            return
        from s3_manager_pro_v5.ui.dialogs.cors_editor import CORSEditorDialog
        CORSEditorDialog(self.root, self, self.current_bucket)

    def open_website_hosting(self):
        """Open static website hosting config."""
        if not self.s3_client or not self.current_bucket:
            messagebox.showwarning("Warning", "Select a bucket first.")
            return
        from s3_manager_pro_v5.ui.dialogs.website_hosting import WebsiteHostingDialog
        WebsiteHostingDialog(self.root, self, self.current_bucket)

    def open_object_lock(self):
        """Open object lock/retention viewer."""
        if not self.s3_client:
            return
        obj = self.file_table.get_focused_object()
        if not obj or obj.is_folder:
            messagebox.showinfo("Object Lock", "Select a file to view lock/retention.")
            return
        from s3_manager_pro_v5.ui.dialogs.object_lock import ObjectLockDialog
        ObjectLockDialog(self.root, self, self.current_bucket, obj.key)

    def open_folder_size(self):
        """Calculate folder size — use loaded data if available for current prefix."""
        if not self.s3_client or not self.current_bucket:
            return

        obj = self.file_table.get_focused_object()
        prefix = obj.key if obj and obj.is_folder else self.current_prefix

        # If we already have the data loaded for this prefix, show it instantly
        if prefix == self.current_prefix and self.file_table._all_objects:
            from tkinter import messagebox
            objects = [o for o in self.file_table._all_objects if not o.is_folder]
            total_size = sum(o.size for o in objects)
            from s3_manager_pro_v5.utils.formatting import format_size
            messagebox.showinfo(
                "📁 Folder Size",
                f"Bucket: {self.current_bucket}\n"
                f"Prefix: {prefix or '(root)'}\n\n"
                f"Files: {len(objects)}\n"
                f"Total Size: {format_size(total_size)}\n\n"
                f"(Based on currently loaded objects)"
            )
            return

        from s3_manager_pro_v5.ui.dialogs.folder_size import FolderSizeDialog
        FolderSizeDialog(self.root, self, self.current_bucket, prefix)

    def open_batch_rename(self):
        """Open batch rename/move dialog."""
        if not self.s3_client:
            return
        selected = self.file_table.get_selected_objects()
        if not selected:
            messagebox.showwarning("Warning", "No files selected for rename.")
            return
        from s3_manager_pro_v5.ui.dialogs.batch_rename import BatchRenameDialog
        BatchRenameDialog(self.root, self, self.current_bucket, selected)

    def open_cross_bucket_copy(self):
        """Open copy/move between buckets dialog."""
        if not self.s3_client:
            return
        selected = self.file_table.get_selected_objects()
        if not selected:
            messagebox.showwarning("Warning", "No files selected.")
            return
        from s3_manager_pro_v5.ui.dialogs.cross_bucket_copy import CrossBucketCopyDialog
        CrossBucketCopyDialog(self.root, self, self.current_bucket, selected)

    def open_url_customizer(self):
        """Open object URL customizer."""
        if not self.s3_client:
            return
        obj = self.file_table.get_focused_object()
        if not obj or obj.is_folder:
            messagebox.showinfo("URL", "Select a file to generate URLs.")
            return
        from s3_manager_pro_v5.ui.dialogs.url_customizer import URLCustomizerDialog
        region = self.cred_manager.get("region", "ap-south-1")
        URLCustomizerDialog(self.root, self, self.current_bucket, obj.key, region)

    def open_resume_transfers(self):
        """Open resume incomplete transfers dialog."""
        from s3_manager_pro_v5.ui.dialogs.transfer_resume import ResumeTransfersDialog
        ResumeTransfersDialog(self.root, self)

    def open_multipart_cleaner(self):
        """Open orphaned multipart upload cleaner (hidden cost recovery)."""
        if not self.s3_client:
            messagebox.showwarning("Warning", "Not connected.")
            return
        from s3_manager_pro_v5.ui.dialogs.multipart_cleaner import MultipartCleanerDialog
        MultipartCleanerDialog(self.root, self, self.current_bucket or None)

    # ═══════════════════════════════════════════
    # SETTINGS
    # ═══════════════════════════════════════════
    def open_settings(self):
        """Open settings dialog."""
        win = ctk.CTkToplevel(self.root)
        win.title("Settings")
        win.geometry("500x650")
        win.transient(self.root)
        win.grab_set()
        win.resizable(False, False)

        colors = DARK_THEME if self.is_dark else LIGHT_THEME
        win.configure(fg_color=colors["bg"])

        ctk.CTkLabel(win, text="⚙ Settings",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=colors["text_primary"]).pack(pady=(20, 15))

        form = ctk.CTkFrame(win, fg_color="transparent")
        form.pack(fill="x", padx=30)

        # Auth mode
        ctk.CTkLabel(form, text="Authentication Mode:",
                     text_color=colors["text_primary"]).pack(anchor="w")
        auth_var = ctk.StringVar(value=self.cred_manager.get("auth_mode", "keys"))
        auth_row = ctk.CTkFrame(form, fg_color="transparent")
        auth_row.pack(anchor="w", pady=(0, 8))
        ctk.CTkRadioButton(auth_row, text="Access Keys", variable=auth_var, value="keys").pack(side="left", padx=(0, 15))
        ctk.CTkRadioButton(auth_row, text="AWS Profile", variable=auth_var, value="profile").pack(side="left")

        # Access Key
        ctk.CTkLabel(form, text="Access Key ID:", text_color=colors["text_primary"]).pack(anchor="w")
        ak_entry = ctk.CTkEntry(form, width=400, placeholder_text="AKIA...")
        ak_entry.pack(anchor="w", pady=(0, 6))
        access_key, secret_key = self.cred_manager.get_credentials()
        if access_key:
            ak_entry.insert(0, access_key)

        # Secret Key
        ctk.CTkLabel(form, text="Secret Access Key:", text_color=colors["text_primary"]).pack(anchor="w")
        sk_entry = ctk.CTkEntry(form, width=400, show="*", placeholder_text="Secret...")
        sk_entry.pack(anchor="w", pady=(0, 6))
        if secret_key:
            sk_entry.insert(0, secret_key)

        # Profile
        ctk.CTkLabel(form, text="AWS Profile Name:", text_color=colors["text_primary"]).pack(anchor="w")
        prof_entry = ctk.CTkEntry(form, width=400, placeholder_text="default")
        prof_entry.insert(0, self.cred_manager.get("profile", ""))
        prof_entry.pack(anchor="w", pady=(0, 6))

        # Region
        ctk.CTkLabel(form, text="Region:", text_color=colors["text_primary"]).pack(anchor="w")
        region_entry = ctk.CTkEntry(form, width=400)
        region_entry.insert(0, self.cred_manager.get("region", "ap-south-1"))
        region_entry.pack(anchor="w", pady=(0, 6))

        # Validate button
        validate_row = ctk.CTkFrame(form, fg_color="transparent")
        validate_row.pack(fill="x", pady=(8, 8))

        validate_status = ctk.CTkLabel(validate_row, text="", font=ctk.CTkFont(size=11))
        validate_status.pack(side="right")

        def do_validate():
            validate_status.configure(text="⏳ Validating...", text_color=colors["warning"])
            win.update()
            try:
                import boto3
                region = region_entry.get().strip() or "ap-south-1"
                session_kwargs = {"region_name": region}
                if auth_var.get() == "keys":
                    ak = ak_entry.get().strip()
                    sk = sk_entry.get().strip()
                    if not ak or not sk:
                        validate_status.configure(text="❌ Access Key and Secret Key required", text_color=colors["danger"])
                        return
                    session_kwargs["aws_access_key_id"] = ak
                    session_kwargs["aws_secret_access_key"] = sk
                else:
                    prof = prof_entry.get().strip()
                    if not prof:
                        validate_status.configure(text="❌ Profile name required", text_color=colors["danger"])
                        return
                    session_kwargs["profile_name"] = prof

                session = boto3.Session(**session_kwargs)
                sts = session.client("sts")
                identity = sts.get_caller_identity()
                account = identity.get("Account", "")
                user = identity.get("Arn", "").split("/")[-1]
                validate_status.configure(
                    text=f"✅ Connected: {account} | {user}",
                    text_color=colors["success"]
                )
            except Exception as e:
                error_msg = str(e)
                if "InvalidClientTokenId" in error_msg:
                    validate_status.configure(text="❌ Invalid Access Key ID", text_color=colors["danger"])
                elif "SignatureDoesNotMatch" in error_msg:
                    validate_status.configure(text="❌ Invalid Secret Key", text_color=colors["danger"])
                elif "not found" in error_msg.lower():
                    validate_status.configure(text=f"❌ Profile not found", text_color=colors["danger"])
                else:
                    validate_status.configure(text=f"❌ {error_msg[:50]}", text_color=colors["danger"])

        ctk.CTkButton(validate_row, text="🔐 Validate Connection", width=170, height=32,
                      corner_radius=6, fg_color=colors["primary"],
                      hover_color=colors["primary_hover"],
                      font=ctk.CTkFont(size=12, weight="bold"),
                      command=do_validate).pack(side="left")

        # Download dir
        ctk.CTkLabel(form, text="Download Folder:", text_color=colors["text_primary"]).pack(anchor="w")
        dir_row = ctk.CTkFrame(form, fg_color="transparent")
        dir_row.pack(fill="x", pady=(0, 6))
        dir_entry = ctk.CTkEntry(dir_row, width=330)
        dir_entry.insert(0, self.cred_manager.get("download_dir", ""))
        dir_entry.pack(side="left", padx=(0, 5))
        ctk.CTkButton(dir_row, text="Browse", width=65, height=28, corner_radius=6,
                      command=lambda: self._browse_dir(dir_entry)).pack(side="left")

        # Parallel
        ctk.CTkLabel(form, text="Parallel Transfers:", text_color=colors["text_primary"]).pack(anchor="w")
        par_entry = ctk.CTkEntry(form, width=80)
        par_entry.insert(0, str(self.cred_manager.get("parallel", 3)))
        par_entry.pack(anchor="w", pady=(0, 10))

        # Status
        status_label = ctk.CTkLabel(form, text="", font=ctk.CTkFont(size=11))
        status_label.pack(anchor="w")

        # Save button
        def save_settings():
            new_settings = {
                "auth_mode": auth_var.get(),
                "profile": prof_entry.get().strip(),
                "region": region_entry.get().strip() or "ap-south-1",
                "download_dir": dir_entry.get().strip(),
                "parallel": int(par_entry.get().strip() or 3),
                "theme": "dark" if self.is_dark else "light",
                "last_bucket": self.cred_manager.get("last_bucket", ""),
                "last_prefix": self.cred_manager.get("last_prefix", ""),
            }
            self.cred_manager.save_settings(new_settings)

            # Store credentials securely
            ak = ak_entry.get().strip()
            sk = sk_entry.get().strip()
            if ak and sk:
                self.cred_manager.store_credentials(ak, sk)

            status_label.configure(text="✓ Settings saved!", text_color=colors["success"])
            self.root.after(1000, lambda: win.destroy())
            self.root.after(1200, self._auto_connect)

        ctk.CTkButton(form, text="Save & Reconnect", width=150, height=38,
                      corner_radius=8, font=ctk.CTkFont(size=13, weight="bold"),
                      fg_color=colors["success"], hover_color="#1fa339",
                      command=save_settings).pack(pady=(15, 0))

    def _browse_dir(self, entry):
        d = filedialog.askdirectory()
        if d:
            entry.delete(0, "end")
            entry.insert(0, d)

    # ═══════════════════════════════════════════
    # HELP / ABOUT / LOG
    # ═══════════════════════════════════════════
    def _show_shortcuts_help(self):
        """Show keyboard shortcuts dialog."""
        shortcuts = (
            "Ctrl+D  — Download selected\n"
            "Ctrl+U  — Upload files\n"
            "Ctrl+A  — Select all\n"
            "Ctrl+F  — Filter/Search\n"
            "Ctrl+Shift+F — Smart Search (all buckets)\n"
            "Ctrl+P  — Preview file\n"
            "Ctrl+L  — Generate share URL\n"
            "Ctrl+E  — Export to CSV\n"
            "Ctrl+I  — Properties\n"
            "Ctrl+T  — Transfer queue\n"
            "Ctrl+,  — Settings\n"
            "F5      — Refresh\n"
            "Delete  — Delete selected\n"
            "Backspace — Go up one folder\n"
            "Space   — Toggle selection\n"
            "Enter   — Open folder / Download\n"
            "Escape  — Clear search"
        )
        messagebox.showinfo("⌨️ Keyboard Shortcuts", shortcuts)

    def _show_about(self):
        """Show about dialog."""
        import webbrowser

        colors = DARK_THEME if self.is_dark else LIGHT_THEME
        win = ctk.CTkToplevel(self.root)
        win.title("About S3 Manager Pro")
        win.geometry("450x380")
        win.transient(self.root)
        win.grab_set()
        win.resizable(False, False)
        win.configure(fg_color=colors["bg"])

        ctk.CTkLabel(win, text="◉ S3 Manager Pro",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=colors["primary"]).pack(pady=(25, 3))

        ctk.CTkLabel(win, text="v5.0.0",
                     font=ctk.CTkFont(size=12),
                     text_color=colors["text_secondary"]).pack(pady=(0, 15))

        ctk.CTkLabel(win, text="The S3 desktop client that AWS Console\nshould have been.",
                     font=ctk.CTkFont(size=12),
                     text_color=colors["text_primary"],
                     justify="center").pack(pady=(0, 15))

        ctk.CTkLabel(win, text="75+ features │ Python + CustomTkinter + Boto3",
                     font=ctk.CTkFont(size=11),
                     text_color=colors["text_secondary"]).pack(pady=(0, 20))

        # Developer info
        dev_frame = ctk.CTkFrame(win, fg_color=colors["surface"], corner_radius=10)
        dev_frame.pack(fill="x", padx=30, pady=(0, 15))

        ctk.CTkLabel(dev_frame, text="Built by",
                     font=ctk.CTkFont(size=10),
                     text_color=colors["text_secondary"]).pack(pady=(10, 0))

        ctk.CTkLabel(dev_frame, text="Saurabh Khairkar",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=colors["text_primary"]).pack(pady=(2, 0))

        ctk.CTkLabel(dev_frame, text="AWS Cloud Engineer",
                     font=ctk.CTkFont(size=11),
                     text_color=colors["text_secondary"]).pack(pady=(0, 5))

        ctk.CTkButton(dev_frame, text="🔗 Connect on LinkedIn", width=180, height=30,
                      corner_radius=6, fg_color="#0077b5", hover_color="#005582",
                      font=ctk.CTkFont(size=11, weight="bold"),
                      command=lambda: webbrowser.open("https://www.linkedin.com/in/saurabh-khairkar-8398b711b/")
                      ).pack(pady=(5, 12))

        ctk.CTkLabel(win, text="Built with AI-assisted development",
                     font=ctk.CTkFont(size=10),
                     text_color=colors["text_secondary"]).pack(pady=(0, 5))

        ctk.CTkButton(win, text="Close", width=70, height=28,
                      corner_radius=6, fg_color=colors["badge_bg"],
                      hover_color=colors["surface_hover"],
                      text_color=colors["text_primary"],
                      command=win.destroy).pack(pady=(5, 15))

    def start_guided_tour(self):
        """Start the interactive guided tour."""
        from s3_manager_pro_v5.ui.guided_tour import GuidedTour
        GuidedTour(self.root, self)

    def open_feature_guide(self):
        """Open the full feature guide with all features explained."""
        from s3_manager_pro_v5.ui.help_guide import FullHelpDialog
        FullHelpDialog(self.root, self)

    def show_help_for(self, topic: str):
        """Show contextual help for a specific feature."""
        from s3_manager_pro_v5.ui.help_guide import HelpGuideDialog
        HelpGuideDialog(self.root, self, topic)

    def _show_activity_log(self):
        """Show activity log panel."""
        from s3_manager_pro_v5.ui.dialogs.activity_log import ActivityLogger
        activity_logger = ActivityLogger()
        # Show in a simple toplevel with the logs
        colors = DARK_THEME if self.is_dark else LIGHT_THEME
        win = ctk.CTkToplevel(self.root)
        win.title("📋 Activity Log")
        win.geometry("600x400")
        win.transient(self.root)
        win.configure(fg_color=colors["bg"])

        textbox = ctk.CTkTextbox(win, font=ctk.CTkFont(family="Consolas", size=10),
                                 fg_color=colors["surface"], text_color=colors["text_primary"])
        textbox.pack(fill="both", expand=True, padx=10, pady=10)

        logs = activity_logger.get_logs()
        if logs:
            for timestamp, level, msg in logs:
                textbox.insert("end", f"[{timestamp}] [{level.upper()}] {msg}\n")
        else:
            textbox.insert("end", "No activity logged yet.")
        textbox.configure(state="disabled")

        ctk.CTkButton(win, text="Close", width=70, height=28,
                      corner_radius=6, command=win.destroy).pack(pady=(0, 10))

    # ═══════════════════════════════════════════
    # RUN
    # ═══════════════════════════════════════════
    def run(self):
        """Start the application main loop."""
        # Load bookmarks into sidebar
        self.sidebar.set_bookmarks(self.bookmark_manager.bookmarks)
        self.root.mainloop()


def main():
    """Application entry point."""
    app = S3ManagerApp()
    app.run()


if __name__ == "__main__":
    main()
