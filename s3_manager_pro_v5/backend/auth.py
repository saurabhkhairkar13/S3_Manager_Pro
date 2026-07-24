"""Secure credential management using OS keyring."""
import json
import os
import logging

logger = logging.getLogger(__name__)

# Try to import keyring, fallback to file-based if not available
try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False
    logger.warning("keyring not installed. Credentials will be stored less securely. Run: pip install keyring")

from s3_manager_pro_v5.utils.constants import KEYRING_SERVICE, SETTINGS_FILE, BOOKMARKS_FILE


class CredentialManager:
    """Manages AWS credentials securely using OS keyring or fallback JSON."""

    def __init__(self):
        self._settings = self._load_settings()

    def _load_settings(self) -> dict:
        """Load non-secret settings from JSON file."""
        if not os.path.exists(SETTINGS_FILE):
            return self._default_settings()
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load settings: {e}")
            return self._default_settings()

    def _default_settings(self) -> dict:
        return {
            "auth_mode": "keys",
            "profile": "",
            "region": "ap-south-1",
            "download_dir": os.path.join(os.path.expanduser("~"), "Downloads"),
            "parallel": 3,
            "theme": "dark",
            "last_bucket": "",
            "last_prefix": "",
        }

    def save_settings(self, settings: dict) -> bool:
        """Save non-secret settings to JSON. Secrets go to keyring."""
        try:
            # Extract secrets before saving to file
            safe_settings = {k: v for k, v in settings.items()
                            if k not in ("access_key", "secret_key")}
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(safe_settings, f, indent=2)
            self._settings = safe_settings
            return True
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            return False

    def store_credentials(self, access_key: str, secret_key: str) -> bool:
        """Store AWS credentials securely."""
        try:
            if KEYRING_AVAILABLE:
                keyring.set_password(KEYRING_SERVICE, "aws_access_key", access_key)
                keyring.set_password(KEYRING_SERVICE, "aws_secret_key", secret_key)
            else:
                # Fallback: store in settings file (not ideal but functional)
                import base64
                self._settings["_ak"] = base64.b64encode(access_key.encode()).decode()
                self._settings["_sk"] = base64.b64encode(secret_key.encode()).decode()
                self.save_settings(self._settings)
            return True
        except Exception as e:
            logger.error(f"Failed to store credentials: {e}")
            return False

    def get_credentials(self) -> tuple:
        """Retrieve stored AWS credentials. Returns (access_key, secret_key)."""
        try:
            if KEYRING_AVAILABLE:
                access_key = keyring.get_password(KEYRING_SERVICE, "aws_access_key") or ""
                secret_key = keyring.get_password(KEYRING_SERVICE, "aws_secret_key") or ""
            else:
                import base64
                ak_enc = self._settings.get("_ak", "")
                sk_enc = self._settings.get("_sk", "")
                access_key = base64.b64decode(ak_enc.encode()).decode() if ak_enc else ""
                secret_key = base64.b64decode(sk_enc.encode()).decode() if sk_enc else ""
            return access_key, secret_key
        except Exception as e:
            logger.error(f"Failed to retrieve credentials: {e}")
            return "", ""

    def delete_credentials(self) -> bool:
        """Remove stored credentials."""
        try:
            if KEYRING_AVAILABLE:
                keyring.delete_password(KEYRING_SERVICE, "aws_access_key")
                keyring.delete_password(KEYRING_SERVICE, "aws_secret_key")
            else:
                self._settings.pop("_ak", None)
                self._settings.pop("_sk", None)
                self.save_settings(self._settings)
            return True
        except Exception:
            return False

    @property
    def settings(self) -> dict:
        return self._settings

    def get(self, key: str, default=None):
        return self._settings.get(key, default)


class BookmarkManager:
    """Manages saved bucket/prefix bookmarks."""

    def __init__(self):
        self._bookmarks = self._load()

    def _load(self) -> list:
        if not os.path.exists(BOOKMARKS_FILE):
            return []
        try:
            with open(BOOKMARKS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save(self):
        try:
            with open(BOOKMARKS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._bookmarks, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save bookmarks: {e}")

    def add(self, bucket: str, prefix: str, label: str = ""):
        """Add a bookmark."""
        entry = {"bucket": bucket, "prefix": prefix, "label": label or f"{bucket}/{prefix}"}
        if entry not in self._bookmarks:
            self._bookmarks.append(entry)
            self._save()

    def remove(self, index: int):
        """Remove a bookmark by index."""
        if 0 <= index < len(self._bookmarks):
            self._bookmarks.pop(index)
            self._save()

    @property
    def bookmarks(self) -> list:
        return self._bookmarks
