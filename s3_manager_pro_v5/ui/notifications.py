"""System Notifications — Windows toast notifications on transfer completion."""
import logging
import sys

logger = logging.getLogger(__name__)

# Try to import notification libraries
NOTIFICATION_AVAILABLE = False
_notify_backend = None

if sys.platform == "win32":
    try:
        from win10toast import ToastNotifier
        _notifier = ToastNotifier()
        NOTIFICATION_AVAILABLE = True
        _notify_backend = "win10toast"
    except ImportError:
        try:
            from plyer import notification as plyer_notification
            NOTIFICATION_AVAILABLE = True
            _notify_backend = "plyer"
        except ImportError:
            logger.info("No notification library available. Install: pip install win10toast OR pip install plyer")
else:
    try:
        from plyer import notification as plyer_notification
        NOTIFICATION_AVAILABLE = True
        _notify_backend = "plyer"
    except ImportError:
        logger.info("Plyer not available for notifications. Install: pip install plyer")


def send_notification(title: str, message: str, duration: int = 5):
    """Send a system notification.

    Args:
        title: Notification title
        message: Notification body
        duration: Display time in seconds
    """
    if not NOTIFICATION_AVAILABLE:
        logger.debug(f"Notification (no backend): {title} - {message}")
        return False

    try:
        if _notify_backend == "win10toast":
            _notifier.show_toast(
                title, message,
                duration=duration,
                threaded=True,
            )
            return True
        elif _notify_backend == "plyer":
            plyer_notification.notify(
                title=title,
                message=message,
                app_name="S3 Manager Pro",
                timeout=duration,
            )
            return True
    except Exception as e:
        logger.warning(f"Notification failed: {e}")
        return False


def notify_download_complete(success: int, failed: int, total_size_str: str):
    """Send notification for download completion."""
    if failed == 0:
        title = "✅ Download Complete"
        message = f"{success} files downloaded ({total_size_str})"
    else:
        title = "⚠️ Download Finished"
        message = f"{success} success, {failed} failed ({total_size_str})"
    send_notification(title, message)


def notify_upload_complete(success: int, failed: int, total_size_str: str):
    """Send notification for upload completion."""
    if failed == 0:
        title = "✅ Upload Complete"
        message = f"{success} files uploaded ({total_size_str})"
    else:
        title = "⚠️ Upload Finished"
        message = f"{success} success, {failed} failed ({total_size_str})"
    send_notification(title, message)


def notify_sync_complete(operations: int, failed: int):
    """Send notification for sync completion."""
    if failed == 0:
        send_notification("✅ Sync Complete", f"{operations} operations completed")
    else:
        send_notification("⚠️ Sync Finished", f"{operations} done, {failed} failed")


def notify_restore_complete(success: int, total: int):
    """Send notification for Glacier restore request completion."""
    send_notification("🔄 Restore Requested", f"{success}/{total} objects queued for restore")
