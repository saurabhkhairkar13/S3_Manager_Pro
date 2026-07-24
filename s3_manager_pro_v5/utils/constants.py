"""Application-wide constants and configuration."""
import os

APP_NAME = "S3 Manager Pro"
APP_VERSION = "5.0.0"
APP_TITLE = f"{APP_NAME} v{APP_VERSION}"

# Paths
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(APP_DIR, "s3_manager_pro.log")
SETTINGS_FILE = os.path.join(APP_DIR, "s3_settings.json")
BOOKMARKS_FILE = os.path.join(APP_DIR, "s3_bookmarks.json")

# Storage classes that don't need Glacier restore
NON_GLACIER_CLASSES = [
    "STANDARD", "REDUCED_REDUNDANCY", "STANDARD_IA",
    "ONEZONE_IA", "INTELLIGENT_TIERING", "GLACIER_IR",
]

# Transfer settings
MAX_RETRIES = 3
CHUNK_SIZE = 8 * 1024 * 1024  # 8 MB
DEFAULT_PARALLEL = 3
MULTIPART_THRESHOLD = 50 * 1024 * 1024  # 50 MB

# Virtual table
PAGE_SIZE = 200  # Objects loaded per page
MAX_VISIBLE_ROWS = 500  # Max rows rendered at a time

# Keyring service name
KEYRING_SERVICE = "s3_manager_pro"

# Theme colors
DARK_THEME = {
    "bg": "#1a1a2e",
    "surface": "#16213e",
    "surface_hover": "#1f2f50",
    "primary": "#0f9ef7",
    "primary_hover": "#0d8de0",
    "success": "#00c853",
    "warning": "#ff9800",
    "danger": "#f44336",
    "danger_hover": "#d32f2f",
    "text_primary": "#e8e8e8",
    "text_secondary": "#8b8b8b",
    "border": "#2d2d44",
    "sidebar_bg": "#0f1526",
    "header_bg": "#101829",
    "badge_bg": "#2d2d44",
}

LIGHT_THEME = {
    "bg": "#f5f7fa",
    "surface": "#ffffff",
    "surface_hover": "#eef2f7",
    "primary": "#0984e3",
    "primary_hover": "#0773c5",
    "success": "#28a745",
    "warning": "#f39c12",
    "danger": "#dc3545",
    "danger_hover": "#c82333",
    "text_primary": "#2d3436",
    "text_secondary": "#636e72",
    "border": "#dfe6e9",
    "sidebar_bg": "#eaf0f7",
    "header_bg": "#ffffff",
    "badge_bg": "#dfe6e9",
}

# AWS Regions
AWS_REGIONS = [
    "us-east-1", "us-east-2", "us-west-1", "us-west-2",
    "ap-south-1", "ap-south-2", "ap-southeast-1", "ap-southeast-2",
    "ap-northeast-1", "ap-northeast-2", "ap-northeast-3",
    "eu-west-1", "eu-west-2", "eu-west-3", "eu-central-1", "eu-north-1",
    "sa-east-1", "ca-central-1", "me-south-1", "af-south-1",
]
