"""Transfer engine — parallel download/upload with resume and integrity verification."""
import os
import time
import shutil
import hashlib
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Callable, Optional

from botocore.exceptions import ClientError
from boto3.s3.transfer import TransferConfig

from s3_manager_pro_v5.utils.constants import MAX_RETRIES, CHUNK_SIZE, MULTIPART_THRESHOLD
from s3_manager_pro_v5.utils.formatting import format_size

logger = logging.getLogger(__name__)


@dataclass
class TransferProgress:
    """Tracks overall transfer progress."""
    total_files: int = 0
    completed_files: int = 0
    failed_files: int = 0
    skipped_files: int = 0
    total_bytes: int = 0
    transferred_bytes: int = 0
    current_file: str = ""
    speed_bps: float = 0
    eta_seconds: float = 0
    is_active: bool = False
    errors: list = field(default_factory=list)


class TransferEngine:
    """Manages parallel file transfers with resume, pause, cancel."""

    def __init__(self, s3_client):
        self.s3 = s3_client
        self.cancel_event = threading.Event()
        self.pause_event = threading.Event()
        self.progress = TransferProgress()
        self._lock = threading.Lock()
        self._start_time = 0
        self._progress_callback: Optional[Callable] = None

    def set_progress_callback(self, callback: Callable):
        """Set callback for progress updates. Called with TransferProgress."""
        self._progress_callback = callback

    def _notify_progress(self):
        """Notify the UI of progress changes."""
        if self._progress_callback:
            with self._lock:
                transferred = self.progress.transferred_bytes
                total = self.progress.total_bytes
            elapsed = time.time() - self._start_time
            if elapsed > 0:
                self.progress.speed_bps = transferred / elapsed
                remaining = total - transferred
                self.progress.eta_seconds = remaining / self.progress.speed_bps if self.progress.speed_bps > 0 else 0
            self._progress_callback(self.progress)

    def cancel(self):
        """Cancel current transfer."""
        self.cancel_event.set()

    def pause(self):
        """Toggle pause state."""
        if self.pause_event.is_set():
            self.pause_event.clear()
        else:
            self.pause_event.set()

    @property
    def is_paused(self) -> bool:
        return self.pause_event.is_set()

    def download_files(self, bucket: str, objects: list, download_dir: str,
                       prefix: str = "", parallel: int = 3) -> TransferProgress:
        """Download multiple files in parallel with resume support."""
        self.cancel_event.clear()
        self.pause_event.clear()
        self._start_time = time.time()

        self.progress = TransferProgress(
            total_files=len(objects),
            total_bytes=sum(o.size for o in objects),
            is_active=True,
        )

        # Check disk space
        try:
            free_space = shutil.disk_usage(download_dir).free
            if self.progress.total_bytes > free_space:
                self.progress.errors.append(
                    f"Not enough disk space. Need: {format_size(self.progress.total_bytes)}, "
                    f"Free: {format_size(free_space)}"
                )
                self.progress.is_active = False
                return self.progress
        except Exception:
            pass

        os.makedirs(download_dir, exist_ok=True)

        def download_one(obj):
            if self.cancel_event.is_set():
                return

            # Wait while paused
            while self.pause_event.is_set() and not self.cancel_event.is_set():
                time.sleep(0.3)

            key = obj.key
            filename = key.split("/")[-1] if "/" in key else key

            with self._lock:
                self.progress.current_file = filename
            self._notify_progress()

            # Determine local path
            if prefix and key.startswith(prefix):
                relative_key = key[len(prefix):]
            else:
                relative_key = key

            local_path = os.path.join(download_dir, relative_key.replace("/", os.sep))
            local_dir = os.path.dirname(local_path)
            if local_dir:
                os.makedirs(local_dir, exist_ok=True)

            # Download with resume
            for attempt in range(1, MAX_RETRIES + 1):
                if self.cancel_event.is_set():
                    return

                success = self._download_single(bucket, key, local_path, obj.size)
                if success:
                    # Verify integrity
                    ok, msg = self._verify_integrity(bucket, key, local_path)
                    if ok:
                        logger.info(f"Downloaded & verified: {key}")
                    else:
                        logger.warning(f"Integrity warning for {key}: {msg}")

                    with self._lock:
                        self.progress.completed_files += 1
                        self.progress.transferred_bytes += obj.size
                    self._notify_progress()
                    return

                elif self.cancel_event.is_set():
                    return
                else:
                    if attempt < MAX_RETRIES:
                        logger.warning(f"Retry {attempt}/{MAX_RETRIES}: {key}")
                        time.sleep(2)

            # All retries failed
            with self._lock:
                self.progress.failed_files += 1
                self.progress.errors.append(f"{filename}: Failed after {MAX_RETRIES} retries")
            self._notify_progress()

        with ThreadPoolExecutor(max_workers=parallel) as executor:
            futures = [executor.submit(download_one, obj) for obj in objects]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Unexpected download error: {e}")

        self.progress.is_active = False
        self._notify_progress()
        return self.progress

    def _download_single(self, bucket: str, key: str, local_path: str, total_size: int) -> bool:
        """Download a single file with resume support."""
        downloaded = 0
        mode = "wb"

        if os.path.exists(local_path):
            existing_size = os.path.getsize(local_path)
            if existing_size == total_size and total_size > 0:
                return True  # Already complete
            elif existing_size < total_size:
                downloaded = existing_size
                mode = "ab"
                logger.info(f"Resuming {key} from {downloaded / (1024*1024):.1f} MB")

        body = None
        try:
            get_kwargs = {"Bucket": bucket, "Key": key}
            if downloaded > 0:
                get_kwargs["Range"] = f"bytes={downloaded}-"

            response = self.s3.s3_client.get_object(**get_kwargs)
            body = response["Body"]

            with open(local_path, mode) as f:
                while True:
                    if self.cancel_event.is_set():
                        return False

                    while self.pause_event.is_set() and not self.cancel_event.is_set():
                        time.sleep(0.3)

                    chunk = body.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    f.write(chunk)

            return True

        except Exception as e:
            logger.error(f"Download error for {key}: {e}")
            return False
        finally:
            if body is not None:
                try:
                    body.close()
                except Exception:
                    pass

    def _verify_integrity(self, bucket: str, key: str, local_path: str) -> tuple:
        """Verify file integrity by comparing size and MD5/ETag."""
        try:
            resp = self.s3.s3_client.head_object(Bucket=bucket, Key=key)
            etag = resp["ETag"].strip('"')
            remote_size = resp["ContentLength"]
            local_size = os.path.getsize(local_path)

            if local_size != remote_size:
                return False, f"Size mismatch: local={local_size}, remote={remote_size}"

            # Skip MD5 for multipart uploads
            if "-" in etag:
                return True, f"Size verified ({local_size} bytes)"

            md5_hash = hashlib.md5()
            with open(local_path, "rb") as f:
                while chunk := f.read(CHUNK_SIZE):
                    md5_hash.update(chunk)
            local_md5 = md5_hash.hexdigest()

            if local_md5 == etag:
                return True, f"MD5 verified: {local_md5}"
            else:
                return False, f"MD5 mismatch: local={local_md5}, remote={etag}"

        except Exception as e:
            return False, f"Verification error: {e}"

    def upload_files(self, bucket: str, files: list, upload_prefix: str = "",
                     storage_class: str = "STANDARD", parallel: int = 3,
                     base_folder: str = None, skip_existing: bool = True) -> TransferProgress:
        """Upload multiple files in parallel.

        Args:
            files: List of local file paths
            upload_prefix: S3 prefix to upload under
            storage_class: Target storage class
            parallel: Number of parallel uploads
            base_folder: Base folder for preserving relative paths
            skip_existing: Skip files that already exist with same size
        """
        self.cancel_event.clear()
        self.pause_event.clear()
        self._start_time = time.time()

        total_size = sum(os.path.getsize(f) for f in files if os.path.isfile(f))
        self.progress = TransferProgress(
            total_files=len(files),
            total_bytes=total_size,
            is_active=True,
        )

        def upload_one(local_path):
            if self.cancel_event.is_set():
                return

            while self.pause_event.is_set() and not self.cancel_event.is_set():
                time.sleep(0.3)

            if not os.path.isfile(local_path):
                return

            file_size = os.path.getsize(local_path)
            filename = os.path.basename(local_path)

            with self._lock:
                self.progress.current_file = filename
            self._notify_progress()

            # Determine S3 key
            if base_folder and local_path.startswith(base_folder):
                relative_path = os.path.relpath(local_path, base_folder)
                s3_key = upload_prefix + relative_path.replace(os.sep, "/")
            else:
                s3_key = upload_prefix + filename

            # Skip existing check
            if skip_existing:
                try:
                    resp = self.s3.s3_client.head_object(Bucket=bucket, Key=s3_key)
                    if resp["ContentLength"] == file_size:
                        with self._lock:
                            self.progress.skipped_files += 1
                            self.progress.transferred_bytes += file_size
                        self._notify_progress()
                        return
                except ClientError:
                    pass

            try:
                config = TransferConfig(
                    multipart_threshold=MULTIPART_THRESHOLD,
                    multipart_chunksize=MULTIPART_THRESHOLD,
                    max_concurrency=5,
                )

                extra_args = {"StorageClass": storage_class}
                self.s3.s3_client.upload_file(
                    local_path, bucket, s3_key,
                    Config=config, ExtraArgs=extra_args,
                )

                with self._lock:
                    self.progress.completed_files += 1
                    self.progress.transferred_bytes += file_size
                self._notify_progress()
                logger.info(f"Uploaded: {local_path} -> s3://{bucket}/{s3_key}")

            except Exception as e:
                with self._lock:
                    self.progress.failed_files += 1
                    self.progress.errors.append(f"{filename}: {str(e)}")
                self._notify_progress()
                logger.error(f"Upload failed: {local_path} - {e}")

        with ThreadPoolExecutor(max_workers=parallel) as executor:
            futures = [executor.submit(upload_one, f) for f in files]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Unexpected upload error: {e}")

        self.progress.is_active = False
        self._notify_progress()
        return self.progress
