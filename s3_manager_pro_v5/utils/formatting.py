"""Formatting and display utilities."""


def format_size(size_bytes: int) -> str:
    """Format bytes to human-readable string."""
    if size_bytes < 0:
        return "0 B"
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024**2):.1f} MB"
    elif size_bytes < 1024 ** 4:
        return f"{size_bytes / (1024**3):.2f} GB"
    else:
        return f"{size_bytes / (1024**4):.2f} TB"


def format_duration(seconds: float) -> str:
    """Format seconds to human-readable duration."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m {int(seconds % 60)}s"
    else:
        return f"{int(seconds // 3600)}h {int((seconds % 3600) // 60)}m"


def truncate_text(text: str, max_length: int = 40) -> str:
    """Truncate text with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


# Storage class display names and colors
STORAGE_CLASS_INFO = {
    "STANDARD": {"label": "Standard", "color": "#28a745", "icon": "🟢"},
    "REDUCED_REDUNDANCY": {"label": "Reduced", "color": "#6c757d", "icon": "⚪"},
    "STANDARD_IA": {"label": "Std-IA", "color": "#0984e3", "icon": "🔵"},
    "ONEZONE_IA": {"label": "1Z-IA", "color": "#00b894", "icon": "🔵"},
    "INTELLIGENT_TIERING": {"label": "Intelligent", "color": "#00cec9", "icon": "🟣"},
    "GLACIER_IR": {"label": "Glacier-IR", "color": "#74b9ff", "icon": "🧊"},
    "GLACIER": {"label": "Glacier", "color": "#f39c12", "icon": "🟠"},
    "DEEP_ARCHIVE": {"label": "Deep Archive", "color": "#d63031", "icon": "🔴"},
}

from s3_manager_pro_v5.utils.constants import NON_GLACIER_CLASSES  # noqa: F401 - re-export

FILE_TYPE_ICONS = {
    ".pdf": "📄",
    ".doc": "📝", ".docx": "📝",
    ".xls": "📊", ".xlsx": "📊", ".csv": "📊",
    ".png": "🖼️", ".jpg": "🖼️", ".jpeg": "🖼️", ".gif": "🖼️", ".svg": "🖼️",
    ".mp4": "🎬", ".mov": "🎬", ".avi": "🎬",
    ".mp3": "🎵", ".wav": "🎵",
    ".zip": "📦", ".tar": "📦", ".gz": "📦", ".rar": "📦", ".7z": "📦",
    ".py": "🐍", ".js": "📜", ".ts": "📜", ".java": "☕",
    ".json": "📋", ".xml": "📋", ".yaml": "📋", ".yml": "📋",
    ".log": "📃", ".txt": "📃",
    ".sql": "🗃️", ".db": "🗃️",
    ".exe": "⚙️", ".sh": "⚙️", ".bat": "⚙️",
    ".html": "🌐", ".css": "🎨",
}


def get_file_icon(filename: str) -> str:
    """Get icon for file based on extension."""
    import os
    ext = os.path.splitext(filename)[1].lower()
    return FILE_TYPE_ICONS.get(ext, "📄")
