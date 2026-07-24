"""Error Handling — user-friendly error dialogs with retry options."""
import customtkinter as ctk
from tkinter import messagebox
from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME


# Error classification
ERROR_MESSAGES = {
    "AccessDenied": {
        "title": "🔒 Access Denied",
        "message": "You don't have permission to perform this action.",
        "help": "Check your IAM policy or contact your AWS administrator.",
        "retryable": False,
    },
    "NoSuchBucket": {
        "title": "🪣 Bucket Not Found",
        "message": "The specified bucket does not exist.",
        "help": "Verify the bucket name or check if it was deleted.",
        "retryable": False,
    },
    "NoSuchKey": {
        "title": "📄 Object Not Found",
        "message": "The specified file no longer exists in S3.",
        "help": "The file may have been deleted or moved. Refresh the listing.",
        "retryable": False,
    },
    "InvalidAccessKeyId": {
        "title": "🔑 Invalid Credentials",
        "message": "Your Access Key ID is invalid or disabled.",
        "help": "Go to Settings and re-enter your credentials.",
        "retryable": False,
    },
    "SignatureDoesNotMatch": {
        "title": "🔑 Authentication Failed",
        "message": "Your Secret Access Key doesn't match the Access Key ID.",
        "help": "Go to Settings and re-enter your Secret Key.",
        "retryable": False,
    },
    "ExpiredToken": {
        "title": "⏰ Session Expired",
        "message": "Your temporary credentials have expired.",
        "help": "Reconnect or refresh your credentials.",
        "retryable": True,
    },
    "RequestTimeout": {
        "title": "⏳ Request Timeout",
        "message": "The request took too long to complete.",
        "help": "Check your internet connection and try again.",
        "retryable": True,
    },
    "SlowDown": {
        "title": "🐢 Rate Limited",
        "message": "Too many requests. AWS is throttling your requests.",
        "help": "Wait a few seconds and try again, or reduce parallel transfers.",
        "retryable": True,
    },
    "ServiceUnavailable": {
        "title": "🔧 Service Unavailable",
        "message": "AWS S3 is temporarily unavailable.",
        "help": "This is usually brief. Wait 30 seconds and retry.",
        "retryable": True,
    },
    "NetworkError": {
        "title": "🌐 Network Error",
        "message": "Cannot reach AWS. Check your internet connection.",
        "help": "Verify Wi-Fi/Ethernet is connected, then retry.",
        "retryable": True,
    },
    "InternalError": {
        "title": "⚠️ Internal Error",
        "message": "An unexpected error occurred in S3.",
        "help": "This is rare. Wait a moment and retry.",
        "retryable": True,
    },
}


def classify_error(error) -> dict:
    """Classify an exception into a user-friendly error category."""
    error_str = str(error)

    # Check for botocore ClientError
    if hasattr(error, "response"):
        code = error.response.get("Error", {}).get("Code", "")
        if code in ERROR_MESSAGES:
            return ERROR_MESSAGES[code]
        # Check message
        message = error.response.get("Error", {}).get("Message", "")
        return {
            "title": f"⚠️ AWS Error: {code}",
            "message": message or error_str,
            "help": "Check the error details and retry if appropriate.",
            "retryable": code in ("InternalError", "ServiceUnavailable", "SlowDown"),
        }

    # Network errors
    if "ConnectionError" in error_str or "MaxRetryError" in error_str:
        return ERROR_MESSAGES["NetworkError"]
    if "timeout" in error_str.lower() or "timed out" in error_str.lower():
        return ERROR_MESSAGES["RequestTimeout"]
    if "credentials" in error_str.lower():
        return ERROR_MESSAGES["InvalidAccessKeyId"]

    # Generic
    return {
        "title": "⚠️ Error",
        "message": error_str[:200],
        "help": "An unexpected error occurred.",
        "retryable": False,
    }


class ErrorDialog:
    """User-friendly error dialog with details and retry option."""

    def __init__(self, parent, error, on_retry=None, is_dark=True):
        """Show an error dialog.

        Args:
            parent: Parent window
            error: The exception or error info dict
            on_retry: Callback for retry button (if retryable)
            is_dark: Theme mode
        """
        colors = DARK_THEME if is_dark else LIGHT_THEME

        # Classify the error
        if isinstance(error, dict):
            info = error
        else:
            info = classify_error(error)

        self.win = ctk.CTkToplevel(parent)
        self.win.title(info["title"])
        self.win.geometry("450x260")
        self.win.transient(parent)
        self.win.grab_set()
        self.win.resizable(False, False)
        self.win.configure(fg_color=colors["bg"])

        # Icon + title
        ctk.CTkLabel(self.win, text=info["title"],
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=colors["danger"]).pack(pady=(20, 10))

        # Message
        ctk.CTkLabel(self.win, text=info["message"],
                     font=ctk.CTkFont(size=12),
                     text_color=colors["text_primary"],
                     wraplength=380).pack(padx=20, pady=(0, 8))

        # Help text
        ctk.CTkLabel(self.win, text=f"💡 {info['help']}",
                     font=ctk.CTkFont(size=11),
                     text_color=colors["text_secondary"],
                     wraplength=380).pack(padx=20, pady=(0, 15))

        # Buttons
        btn_frame = ctk.CTkFrame(self.win, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 20))

        if info.get("retryable") and on_retry:
            ctk.CTkButton(btn_frame, text="🔄 Retry", width=100, height=34,
                          corner_radius=8, fg_color=colors["primary"],
                          hover_color=colors["primary_hover"],
                          font=ctk.CTkFont(size=12, weight="bold"),
                          command=lambda: self._retry(on_retry)).pack(side="left", padx=(0, 10))

        ctk.CTkButton(btn_frame, text="OK", width=80, height=34,
                      corner_radius=8, fg_color=colors["badge_bg"],
                      hover_color=colors["surface_hover"],
                      text_color=colors["text_primary"],
                      command=self.win.destroy).pack(side="right")

    def _retry(self, callback):
        self.win.destroy()
        callback()


def show_error(parent, error, on_retry=None, is_dark=True):
    """Convenience function to show an error dialog."""
    ErrorDialog(parent, error, on_retry, is_dark)


def show_empty_bucket_message(parent, bucket: str, is_dark=True):
    """Show a friendly message when bucket/prefix is empty."""
    colors = DARK_THEME if is_dark else LIGHT_THEME
    messagebox.showinfo("Empty", f"No objects found in s3://{bucket}/\n\n"
                        "The bucket may be empty or you don't have ListObjects permission.")
