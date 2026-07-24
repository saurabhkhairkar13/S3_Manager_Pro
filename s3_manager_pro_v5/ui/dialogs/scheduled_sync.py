"""Scheduled Auto-Sync — recurring sync between local folder and S3."""
import os
import time
import json
import threading
import logging
from datetime import datetime
import customtkinter as ctk
from tkinter import filedialog, messagebox
from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME
from s3_manager_pro_v5.utils.formatting import format_size

logger = logging.getLogger(__name__)

SYNC_JOBS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "s3_sync_jobs.json"
)


class SyncScheduler:
    """Background scheduler that runs sync jobs at configured intervals."""

    def __init__(self, app):
        self.app = app
        self._jobs = self._load_jobs()
        self._running = False
        self._thread = None
        self._stop_event = threading.Event()

    def _load_jobs(self) -> list:
        if not os.path.exists(SYNC_JOBS_FILE):
            return []
        try:
            with open(SYNC_JOBS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_jobs(self):
        try:
            with open(SYNC_JOBS_FILE, "w") as f:
                json.dump(self._jobs, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save sync jobs: {e}")

    def add_job(self, name: str, local_dir: str, bucket: str, prefix: str,
                direction: str, interval_minutes: int, enabled: bool = True):
        """Add a new sync job."""
        job = {
            "name": name,
            "local_dir": local_dir,
            "bucket": bucket,
            "prefix": prefix,
            "direction": direction,  # "upload" or "download"
            "interval_minutes": interval_minutes,
            "enabled": enabled,
            "last_run": None,
            "last_status": "Never run",
            "created": datetime.now().isoformat(),
        }
        self._jobs.append(job)
        self._save_jobs()

    def remove_job(self, index: int):
        if 0 <= index < len(self._jobs):
            self._jobs.pop(index)
            self._save_jobs()

    def toggle_job(self, index: int):
        if 0 <= index < len(self._jobs):
            self._jobs[index]["enabled"] = not self._jobs[index]["enabled"]
            self._save_jobs()

    @property
    def jobs(self) -> list:
        return self._jobs

    def start(self):
        """Start the background scheduler."""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Sync scheduler started")

    def stop(self):
        """Stop the scheduler."""
        self._running = False
        self._stop_event.set()
        logger.info("Sync scheduler stopped")

    def _run_loop(self):
        """Main scheduler loop — checks jobs every 60 seconds."""
        while not self._stop_event.is_set():
            for i, job in enumerate(self._jobs):
                if self._stop_event.is_set():
                    break
                if not job["enabled"]:
                    continue

                # Check if it's time to run
                last_run = job.get("last_run")
                interval = job["interval_minutes"] * 60

                should_run = False
                if last_run is None:
                    should_run = True
                else:
                    try:
                        last_dt = datetime.fromisoformat(last_run)
                        elapsed = (datetime.now() - last_dt).total_seconds()
                        should_run = elapsed >= interval
                    except Exception:
                        should_run = True

                if should_run:
                    self._execute_job(i, job)

            # Sleep 60 seconds between checks
            self._stop_event.wait(60)

    def _execute_job(self, index: int, job: dict):
        """Execute a single sync job."""
        logger.info(f"Running sync job: {job['name']}")
        try:
            if not self.app.s3_client or not self.app.s3_client.is_connected:
                job["last_status"] = "Failed: Not connected"
                self._save_jobs()
                return

            local_dir = job["local_dir"]
            bucket = job["bucket"]
            prefix = job["prefix"]
            direction = job["direction"]

            if not os.path.isdir(local_dir):
                job["last_status"] = f"Failed: Local folder not found"
                self._save_jobs()
                return

            # Get S3 objects
            s3_objects = {}
            result = self.app.s3_client.list_objects_page(bucket, prefix, delimiter="")
            for obj in result.objects:
                relative = obj.key[len(prefix):] if obj.key.startswith(prefix) else obj.key
                s3_objects[relative] = obj.size
            while result.is_truncated:
                result = self.app.s3_client.list_objects_page(
                    bucket, prefix, delimiter="",
                    continuation_token=result.continuation_token
                )
                for obj in result.objects:
                    relative = obj.key[len(prefix):] if obj.key.startswith(prefix) else obj.key
                    s3_objects[relative] = obj.size

            # Get local files
            local_files = {}
            for root, dirs, files in os.walk(local_dir):
                for f in files:
                    full_path = os.path.join(root, f)
                    relative = os.path.relpath(full_path, local_dir).replace(os.sep, "/")
                    local_files[relative] = os.path.getsize(full_path)

            # Sync
            synced = 0
            if direction == "upload":
                for rel, size in local_files.items():
                    if rel not in s3_objects or s3_objects[rel] != size:
                        local_path = os.path.join(local_dir, rel.replace("/", os.sep))
                        s3_key = prefix + rel
                        try:
                            self.app.s3_client.s3_client.upload_file(local_path, bucket, s3_key)
                            synced += 1
                        except Exception:
                            pass
            else:  # download
                for rel, size in s3_objects.items():
                    if rel not in local_files or local_files[rel] != size:
                        s3_key = prefix + rel
                        local_path = os.path.join(local_dir, rel.replace("/", os.sep))
                        os.makedirs(os.path.dirname(local_path), exist_ok=True)
                        try:
                            self.app.s3_client.s3_client.download_file(bucket, s3_key, local_path)
                            synced += 1
                        except Exception:
                            pass

            job["last_run"] = datetime.now().isoformat()
            job["last_status"] = f"OK: {synced} files synced" if synced > 0 else "OK: Already in sync"
            self._jobs[index] = job
            self._save_jobs()
            logger.info(f"Sync job '{job['name']}' complete: {synced} files")

        except Exception as e:
            job["last_status"] = f"Failed: {str(e)[:50]}"
            self._save_jobs()
            logger.error(f"Sync job failed: {e}")


class ScheduledSyncDialog:
    """Dialog to manage scheduled sync jobs."""

    def __init__(self, parent, app):
        self.app = app

        # Initialize scheduler if not exists
        if not hasattr(app, '_sync_scheduler'):
            app._sync_scheduler = SyncScheduler(app)
            app._sync_scheduler.start()

        self.scheduler = app._sync_scheduler
        colors = DARK_THEME if app.is_dark else LIGHT_THEME

        self.win = ctk.CTkToplevel(parent)
        self.win.title("⏰ Scheduled Auto-Sync")
        self.win.geometry("650x480")
        self.win.transient(parent)
        self.win.grab_set()
        self.win.resizable(True, True)
        self.win.configure(fg_color=colors["bg"])

        # Title
        ctk.CTkLabel(self.win, text="⏰ Scheduled Auto-Sync",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=colors["text_primary"]).pack(pady=(15, 5))
        ctk.CTkLabel(self.win, text="Automatically sync folders to/from S3 at set intervals",
                     font=ctk.CTkFont(size=11),
                     text_color=colors["text_secondary"]).pack(pady=(0, 10))

        # Jobs list
        self.jobs_frame = ctk.CTkScrollableFrame(self.win, fg_color="transparent", height=250)
        self.jobs_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        self._refresh_jobs()

        # Add job section
        add_frame = ctk.CTkFrame(self.win, fg_color=colors["surface"], corner_radius=8)
        add_frame.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(add_frame, text="Add New Sync Job:",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=colors["text_primary"]).pack(anchor="w", padx=12, pady=(10, 5))

        row1 = ctk.CTkFrame(add_frame, fg_color="transparent")
        row1.pack(fill="x", padx=12, pady=3)

        self.name_entry = ctk.CTkEntry(row1, width=150, height=28, placeholder_text="Job name")
        self.name_entry.pack(side="left", padx=(0, 5))

        self.dir_entry = ctk.CTkEntry(row1, width=200, height=28, placeholder_text="Local folder")
        self.dir_entry.pack(side="left", padx=(0, 5))

        ctk.CTkButton(row1, text="...", width=30, height=28, corner_radius=4,
                      command=self._browse).pack(side="left", padx=(0, 5))

        row2 = ctk.CTkFrame(add_frame, fg_color="transparent")
        row2.pack(fill="x", padx=12, pady=(3, 10))

        self.bucket_entry = ctk.CTkEntry(row2, width=120, height=28, placeholder_text="Bucket")
        self.bucket_entry.pack(side="left", padx=(0, 5))
        if app.current_bucket:
            self.bucket_entry.insert(0, app.current_bucket)

        self.prefix_entry = ctk.CTkEntry(row2, width=120, height=28, placeholder_text="Prefix")
        self.prefix_entry.pack(side="left", padx=(0, 5))
        if app.current_prefix:
            self.prefix_entry.insert(0, app.current_prefix)

        self.dir_var = ctk.StringVar(value="upload")
        ctk.CTkOptionMenu(row2, variable=self.dir_var, values=["upload", "download"],
                          width=90, height=28).pack(side="left", padx=(0, 5))

        self.interval_entry = ctk.CTkEntry(row2, width=50, height=28, placeholder_text="min")
        self.interval_entry.insert(0, "60")
        self.interval_entry.pack(side="left", padx=(0, 5))
        ctk.CTkLabel(row2, text="min", font=ctk.CTkFont(size=10),
                     text_color=colors["text_secondary"]).pack(side="left", padx=(0, 10))

        ctk.CTkButton(row2, text="+ Add", width=60, height=28, corner_radius=4,
                      fg_color=colors["success"], hover_color="#1fa339",
                      command=self._add_job).pack(side="left")

        # Close
        ctk.CTkButton(self.win, text="Close", width=80, height=32,
                      corner_radius=6, fg_color=colors["badge_bg"],
                      hover_color=colors["surface_hover"],
                      text_color=colors["text_primary"],
                      command=self.win.destroy).pack(pady=(0, 15))

    def _browse(self):
        d = filedialog.askdirectory(parent=self.win)
        if d:
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, d)

    def _add_job(self):
        name = self.name_entry.get().strip() or "Sync Job"
        local_dir = self.dir_entry.get().strip()
        bucket = self.bucket_entry.get().strip()
        prefix = self.prefix_entry.get().strip()
        direction = self.dir_var.get()
        interval = int(self.interval_entry.get().strip() or 60)

        if not local_dir or not bucket:
            messagebox.showwarning("Missing", "Local folder and bucket are required.", parent=self.win)
            return

        if prefix and not prefix.endswith("/"):
            prefix += "/"

        self.scheduler.add_job(name, local_dir, bucket, prefix, direction, interval)
        self._refresh_jobs()
        self.name_entry.delete(0, "end")

    def _refresh_jobs(self):
        """Refresh the jobs display."""
        for widget in self.jobs_frame.winfo_children():
            widget.destroy()

        colors = DARK_THEME if self.app.is_dark else LIGHT_THEME

        if not self.scheduler.jobs:
            ctk.CTkLabel(self.jobs_frame, text="No sync jobs configured.\nAdd one below.",
                         font=ctk.CTkFont(size=12),
                         text_color=colors["text_secondary"]).pack(pady=20)
            return

        for i, job in enumerate(self.scheduler.jobs):
            card = ctk.CTkFrame(self.jobs_frame, fg_color=colors["surface"], corner_radius=8)
            card.pack(fill="x", pady=3)

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=12, pady=8)

            # Status dot
            status_color = colors["success"] if job["enabled"] else colors["text_secondary"]
            ctk.CTkLabel(inner, text="●", font=ctk.CTkFont(size=10),
                         text_color=status_color).pack(side="left", padx=(0, 5))

            # Info
            direction_icon = "⬆" if job["direction"] == "upload" else "⬇"
            ctk.CTkLabel(inner,
                         text=f"{job['name']} │ {direction_icon} {job['direction']} │ every {job['interval_minutes']}m",
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=colors["text_primary"]).pack(side="left")

            # Last status
            ctk.CTkLabel(inner, text=job.get("last_status", "Never run"),
                         font=ctk.CTkFont(size=10),
                         text_color=colors["text_secondary"]).pack(side="left", padx=(10, 0))

            # Buttons
            ctk.CTkButton(inner, text="✕", width=24, height=24, corner_radius=4,
                          fg_color=colors["danger"], hover_color=colors["danger_hover"],
                          font=ctk.CTkFont(size=10),
                          command=lambda idx=i: self._remove_job(idx)).pack(side="right", padx=2)

            toggle_text = "⏸" if job["enabled"] else "▶"
            ctk.CTkButton(inner, text=toggle_text, width=24, height=24, corner_radius=4,
                          fg_color=colors["badge_bg"], hover_color=colors["surface_hover"],
                          text_color=colors["text_primary"],
                          font=ctk.CTkFont(size=10),
                          command=lambda idx=i: self._toggle_job(idx)).pack(side="right", padx=2)

    def _remove_job(self, index: int):
        self.scheduler.remove_job(index)
        self._refresh_jobs()

    def _toggle_job(self, index: int):
        self.scheduler.toggle_job(index)
        self._refresh_jobs()
