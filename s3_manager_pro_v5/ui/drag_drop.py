"""Drag-and-drop upload support.

Uses tkinterdnd2 if available, otherwise provides a fallback drop zone button.
"""
import os
import logging
import threading
from tkinter import messagebox

logger = logging.getLogger(__name__)

# Try importing tkinterdnd2
DND_AVAILABLE = False
try:
    import tkinterdnd2
    DND_AVAILABLE = True
except ImportError:
    logger.info("tkinterdnd2 not available. Drag-and-drop disabled. Install with: pip install tkinterdnd2")


def setup_dnd(file_table_widget, app):
    """Setup drag-and-drop on the file table.

    If tkinterdnd2 is available, registers file drop on the treeview.
    Otherwise silently does nothing (upload button is the fallback).
    """
    if not DND_AVAILABLE:
        return False

    try:
        # Register the treeview widget for file drops
        tree = file_table_widget.tree
        tree.drop_target_register(tkinterdnd2.DND_FILES)
        tree.dnd_bind("<<Drop>>", lambda event: _on_drop(event, app))
        tree.dnd_bind("<<DragEnter>>", lambda event: _on_drag_enter(event, file_table_widget))
        tree.dnd_bind("<<DragLeave>>", lambda event: _on_drag_leave(event, file_table_widget))
        logger.info("Drag-and-drop enabled on file table")
        return True
    except Exception as e:
        logger.warning(f"Failed to setup drag-and-drop: {e}")
        return False


def _on_drag_enter(event, file_table_widget):
    """Visual feedback when dragging over."""
    try:
        file_table_widget.tree.configure(style="DragOver.Treeview")
    except Exception:
        pass
    return event.action


def _on_drag_leave(event, file_table_widget):
    """Remove visual feedback."""
    try:
        file_table_widget.tree.configure(style="Treeview")
    except Exception:
        pass
    return event.action


def _on_drop(event, app):
    """Handle file/folder drop event."""
    if not app.current_bucket:
        messagebox.showwarning("Drop Upload", "Select a bucket first before dropping files.")
        return

    # Parse dropped file paths (tkinterdnd2 format)
    raw = event.data
    files = _parse_drop_data(raw)

    if not files:
        return

    # Expand directories into file lists
    all_files = []
    base_folder = None

    for path in files:
        if os.path.isdir(path):
            base_folder = path
            for root, dirs, filenames in os.walk(path):
                for f in filenames:
                    all_files.append(os.path.join(root, f))
        elif os.path.isfile(path):
            all_files.append(path)

    if not all_files:
        return

    from s3_manager_pro_v5.utils.formatting import format_size
    total_size = sum(os.path.getsize(f) for f in all_files)

    confirm = messagebox.askyesno(
        "Drop Upload",
        f"Upload {len(all_files)} files ({format_size(total_size)}) to:\n"
        f"s3://{app.current_bucket}/{app.current_prefix}\n\nContinue?"
    )
    if not confirm:
        return

    # Execute upload
    app.action_bar.set_transfer_active(True)
    parallel = app.cred_manager.get("parallel", 3)

    def do_upload():
        app.transfer_engine.upload_files(
            bucket=app.current_bucket,
            files=all_files,
            upload_prefix=app.current_prefix,
            parallel=int(parallel),
            base_folder=base_folder,
        )
        app.root.after(0, lambda: app.action_bar.set_transfer_active(False))
        app.root.after(0, app.refresh_listing)

    threading.Thread(target=do_upload, daemon=True).start()


def _parse_drop_data(data: str) -> list:
    """Parse tkinterdnd2 drop data into list of file paths.

    Handles various formats:
    - Space-separated paths
    - Paths with spaces wrapped in {}
    - Windows and Unix paths
    """
    files = []
    if not data:
        return files

    # Handle curly-brace wrapped paths (tkinterdnd2 on Windows)
    i = 0
    while i < len(data):
        if data[i] == '{':
            # Find closing brace
            end = data.index('}', i + 1)
            path = data[i + 1:end]
            files.append(path)
            i = end + 2  # Skip } and space
        elif data[i] == ' ':
            i += 1
        else:
            # Find next space or end
            end = data.find(' ', i)
            if end == -1:
                end = len(data)
            path = data[i:end]
            if path:
                files.append(path)
            i = end + 1

    # Validate paths exist
    return [f for f in files if os.path.exists(f)]
