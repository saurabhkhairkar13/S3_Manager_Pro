"""Export file listing to CSV/Excel."""
import os
import csv
import logging
from datetime import datetime
from tkinter import filedialog, messagebox

from s3_manager_pro_v5.utils.formatting import format_size, STORAGE_CLASS_INFO

logger = logging.getLogger(__name__)


def export_to_csv(parent, objects: list, bucket: str, prefix: str):
    """Export the current file listing to a CSV file.

    Columns: Key, Filename, Size (bytes), Size (readable), Storage Class, Last Modified, Status
    """
    if not objects:
        messagebox.showwarning("Export", "No files to export.", parent=parent)
        return

    # Suggest filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    default_name = f"s3_export_{bucket}_{timestamp}.csv"

    filepath = filedialog.asksaveasfilename(
        parent=parent,
        title="Export File Listing",
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        initialfile=default_name,
    )

    if not filepath:
        return

    try:
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # Header row
            writer.writerow([
                "S3 Key",
                "Filename",
                "Size (Bytes)",
                "Size (Readable)",
                "Storage Class",
                "Last Modified",
                "Type",
                "Extension",
            ])

            # Metadata row
            writer.writerow([])
            writer.writerow([f"# Bucket: {bucket}"])
            writer.writerow([f"# Prefix: {prefix or '(root)'}"])
            writer.writerow([f"# Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
            writer.writerow([f"# Total Objects: {len(objects)}"])
            writer.writerow([f"# Total Size: {format_size(sum(o.size for o in objects))}"])
            writer.writerow([])

            # Header again after metadata
            writer.writerow([
                "S3 Key",
                "Filename",
                "Size (Bytes)",
                "Size (Readable)",
                "Storage Class",
                "Last Modified",
                "Type",
                "Extension",
            ])

            # Data rows
            for obj in objects:
                if obj.is_folder:
                    continue

                filename = obj.key.split("/")[-1] if "/" in obj.key else obj.key
                ext = os.path.splitext(filename)[1].lower() if "." in filename else ""

                # Determine type
                if obj.is_folder:
                    file_type = "Folder"
                elif ext in (".jpg", ".jpeg", ".png", ".gif", ".svg", ".bmp"):
                    file_type = "Image"
                elif ext in (".mp4", ".mov", ".avi", ".mkv"):
                    file_type = "Video"
                elif ext in (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt"):
                    file_type = "Document"
                elif ext in (".zip", ".tar", ".gz", ".rar", ".7z"):
                    file_type = "Archive"
                elif ext in (".py", ".js", ".ts", ".java", ".go", ".rs"):
                    file_type = "Code"
                elif ext in (".log", ".txt", ".csv", ".json", ".xml"):
                    file_type = "Text"
                else:
                    file_type = "Other"

                writer.writerow([
                    obj.key,
                    filename,
                    obj.size,
                    format_size(obj.size),
                    obj.storage_class,
                    obj.last_modified,
                    file_type,
                    ext,
                ])

        messagebox.showinfo("Export Complete",
                            f"Exported {len(objects)} files to:\n{filepath}",
                            parent=parent)
        logger.info(f"Exported {len(objects)} objects to {filepath}")

        # Open containing folder
        try:
            os.startfile(os.path.dirname(filepath))
        except Exception:
            pass

    except Exception as e:
        messagebox.showerror("Export Failed", f"Error: {str(e)}", parent=parent)
        logger.error(f"CSV export failed: {e}")
