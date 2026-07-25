"""File Preview Panel — preview images, JSON, CSV, text without downloading."""
import io
import json
import threading
import customtkinter as ctk
from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME
from s3_manager_pro_v5.utils.formatting import format_size

# Max size to preview (15 MB for images, any size for text first 5MB)
MAX_PREVIEW_SIZE = 15 * 1024 * 1024
MAX_TEXT_PREVIEW_SIZE = 50 * 1024 * 1024  # Allow text files up to 50 MB (shows first 5 MB)

# File types we can preview
PREVIEWABLE_TEXT = {".json", ".yaml", ".yml", ".xml", ".txt", ".log", ".md",
                   ".csv", ".tsv", ".py", ".js", ".ts", ".html", ".css",
                   ".sh", ".bat", ".cfg", ".ini", ".conf", ".env", ".sql"}
PREVIEWABLE_IMAGE = {".png", ".jpg", ".jpeg", ".gif", ".bmp"}
BROWSER_OPEN_TYPES = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".mp3", ".wav",
                      ".ogg", ".flac", ".m4a", ".pdf", ".docx", ".xlsx", ".pptx"}


class FilePreviewPanel:
    """Preview file contents inline without full download."""

    def __init__(self, parent, app, bucket: str, obj):
        self.app = app
        self.bucket = bucket
        self.obj = obj

        colors = DARK_THEME if app.is_dark else LIGHT_THEME
        filename = obj.key.split("/")[-1] if "/" in obj.key else obj.key
        import os
        ext = os.path.splitext(filename)[1].lower()

        self.win = ctk.CTkToplevel(parent)
        self.win.title(f"👁 Preview — {filename}")
        self.win.geometry("700x550")
        self.win.transient(parent)
        self.win.grab_set()
        self.win.resizable(True, True)
        self.win.configure(fg_color=colors["bg"])

        # Header
        header = ctk.CTkFrame(self.win, fg_color=colors["surface"], height=50)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(header, text=f"👁 {filename}",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=colors["text_primary"]).pack(side="left", padx=15, pady=10)

        ctk.CTkLabel(header, text=f"{format_size(obj.size)} │ {obj.storage_class}",
                     font=ctk.CTkFont(size=11),
                     text_color=colors["text_secondary"]).pack(side="left", padx=10)

        ctk.CTkButton(header, text="✕", width=30, height=30, corner_radius=6,
                      fg_color=colors["badge_bg"], hover_color=colors["surface_hover"],
                      text_color=colors["text_primary"],
                      command=self.win.destroy).pack(side="right", padx=10)

        # Content area
        self.content = ctk.CTkFrame(self.win, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=10, pady=10)

        # Check if previewable
        is_text = ext in PREVIEWABLE_TEXT or ext in (".csv", ".tsv", ".sql")

        # Videos/Audio/PDF — always open directly in browser (any size)
        if ext in BROWSER_OPEN_TYPES:
            self._open_directly_in_browser(obj, ext, colors)
            return

        if ext in PREVIEWABLE_IMAGE and obj.size > MAX_PREVIEW_SIZE:
            ctk.CTkLabel(self.content,
                         text=f"⚠ Image too large to preview ({format_size(obj.size)})\n"
                              f"Maximum image preview: {format_size(MAX_PREVIEW_SIZE)}",
                         font=ctk.CTkFont(size=13),
                         text_color=colors["warning"]).pack(pady=40)
            return

        if not is_text and obj.size > MAX_PREVIEW_SIZE:
            ctk.CTkLabel(self.content,
                         text=f"⚠ File too large to preview ({format_size(obj.size)})\n"
                              f"Maximum preview size: {format_size(MAX_PREVIEW_SIZE)}",
                         font=ctk.CTkFont(size=13),
                         text_color=colors["warning"]).pack(pady=40)
            return

        if ext in PREVIEWABLE_IMAGE:
            self._load_image_preview(ext)
        elif is_text:
            # Text files: always preview (loads first 5 MB only)
            self._load_text_preview(ext)
        else:
            # Try text preview for unknown small files
            if obj.size < 1024 * 100:
                self._load_text_preview(ext)
            else:
                # Unsupported type — offer "Open in Browser" option
                self._show_open_in_browser(ext, obj, colors)

    def _open_directly_in_browser(self, obj, ext: str, colors: dict):
        """Immediately generate presigned URL and open in browser for video/audio/pdf."""
        import webbrowser

        media_video = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
        media_audio = {".mp3", ".wav", ".ogg", ".flac", ".m4a"}

        if ext in media_video:
            icon, file_type = "🎬", "Video"
        elif ext in media_audio:
            icon, file_type = "🎵", "Audio"
        else:
            icon, file_type = "📄", "Document"

        ctk.CTkLabel(self.content, text=icon,
                     font=ctk.CTkFont(size=40)).pack(pady=(30, 10))

        ctk.CTkLabel(self.content,
                     text=f"Opening {file_type} in browser...",
                     font=ctk.CTkFont(size=13),
                     text_color=colors["text_primary"]).pack(pady=(0, 10))

        # Generate URL and open immediately
        url = self.app.s3_client.generate_presigned_url(self.bucket, obj.key, expires_in=3600)
        if url:
            webbrowser.open(url)
            ctk.CTkLabel(self.content,
                         text="Opened in browser (link valid for 1 hour)",
                         font=ctk.CTkFont(size=11),
                         text_color=colors["success"]).pack(pady=(10, 0))

            # Show URL for copy
            url_box = ctk.CTkEntry(self.content, width=500, height=28)
            url_box.insert(0, url)
            url_box.configure(state="readonly")
            url_box.pack(pady=(10, 5))

            def copy_url():
                self.win.clipboard_clear()
                self.win.clipboard_append(url)

            ctk.CTkButton(self.content, text="Copy URL", width=90, height=28,
                          corner_radius=6, fg_color=colors["primary"],
                          hover_color=colors["primary_hover"],
                          command=copy_url).pack(pady=5)
        else:
            ctk.CTkLabel(self.content,
                         text="Failed to generate URL",
                         font=ctk.CTkFont(size=12),
                         text_color="#f44336").pack(pady=10)

    def _show_open_in_browser(self, ext: str, obj, colors: dict):
        """Show 'Open in Browser' option for unsupported file types (video, audio, pdf, etc)."""
        import webbrowser

        # Determine file type category
        media_exts = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".mp3", ".wav", ".ogg", ".flac", ".m4a"}
        doc_exts = {".pdf", ".docx", ".xlsx", ".pptx", ".doc", ".xls"}

        if ext in media_exts:
            icon = "🎬" if ext in (".mp4", ".mov", ".avi", ".mkv", ".webm") else "🎵"
            file_type = "Video" if ext in (".mp4", ".mov", ".avi", ".mkv", ".webm") else "Audio"
            hint = "Your browser can play this file directly."
        elif ext in doc_exts:
            icon = "📄"
            file_type = "Document"
            hint = "Your browser can display PDF files. Office files will download."
        else:
            icon = "📦"
            file_type = "Binary"
            hint = "This file type cannot be previewed inline."

        ctk.CTkLabel(self.content, text=icon,
                     font=ctk.CTkFont(size=40)).pack(pady=(30, 10))

        ctk.CTkLabel(self.content,
                     text=f"Cannot preview {file_type} files ({ext}) in app",
                     font=ctk.CTkFont(size=13),
                     text_color=colors["text_primary"]).pack(pady=(0, 5))

        ctk.CTkLabel(self.content, text=hint,
                     font=ctk.CTkFont(size=11),
                     text_color=colors["text_secondary"]).pack(pady=(0, 20))

        # "Open in Browser" button — generates presigned URL and opens
        def open_in_browser():
            url = self.app.s3_client.generate_presigned_url(self.bucket, obj.key, expires_in=3600)
            if url:
                webbrowser.open(url)
                self._status_label.configure(text="Opened in browser (link valid for 1 hour)",
                                             text_color=colors["success"])
            else:
                self._status_label.configure(text="Failed to generate URL",
                                             text_color="#f44336")

        ctk.CTkButton(self.content, text=f"🌐 Open in Browser",
                      width=180, height=36, corner_radius=8,
                      font=ctk.CTkFont(size=13, weight="bold"),
                      fg_color=colors["primary"], hover_color=colors["primary_hover"],
                      command=open_in_browser).pack(pady=(0, 10))

        # Also offer download
        ctk.CTkButton(self.content, text="⬇ Download Instead",
                      width=150, height=30, corner_radius=6,
                      font=ctk.CTkFont(size=11),
                      fg_color=colors["surface"], hover_color=colors["surface_hover"],
                      text_color=colors["text_primary"],
                      command=self.app.download_selected).pack(pady=(0, 10))

        self._status_label = ctk.CTkLabel(self.content, text="",
                                          font=ctk.CTkFont(size=10))
        self._status_label.pack()

    def _load_text_preview(self, ext: str):
        """Load and display text content."""
        colors = DARK_THEME if self.app.is_dark else LIGHT_THEME

        loading = ctk.CTkLabel(self.content, text="⏳ Loading preview...",
                               text_color=colors["text_secondary"])
        loading.pack(pady=20)

        def do_load():
            try:
                response = self.app.s3_client.s3_client.get_object(
                    Bucket=self.bucket, Key=self.obj.key,
                    Range=f"bytes=0-{MAX_PREVIEW_SIZE}"
                )
                raw_bytes = response["Body"].read()

                # Try to decode as text
                try:
                    text = raw_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    try:
                        text = raw_bytes.decode("latin-1")
                    except Exception:
                        text = "[Binary content — cannot display]"

                # Format JSON nicely
                if ext == ".json":
                    try:
                        parsed = json.loads(text)
                        text = json.dumps(parsed, indent=2, ensure_ascii=False)
                    except Exception:
                        pass  # Show raw if not valid JSON

                # Limit lines for display
                lines = text.split("\n")
                if len(lines) > 500:
                    text = "\n".join(lines[:500]) + f"\n\n... ({len(lines) - 500} more lines)"

                self.win.after(0, lambda: self._show_text(text, loading))

            except Exception as e:
                self.win.after(0, lambda: loading.configure(
                    text=f"❌ Preview failed: {str(e)[:60]}", text_color="#f44336"
                ))

        threading.Thread(target=do_load, daemon=True).start()

    def _show_text(self, text: str, loading_widget):
        """Display text in a textbox."""
        loading_widget.destroy()
        colors = DARK_THEME if self.app.is_dark else LIGHT_THEME

        textbox = ctk.CTkTextbox(self.content,
                                 font=ctk.CTkFont(family="Consolas", size=11),
                                 fg_color=colors["surface"],
                                 text_color=colors["text_primary"],
                                 wrap="none")
        textbox.pack(fill="both", expand=True)
        textbox.insert("0.0", text)
        textbox.configure(state="disabled")

        # Line count
        line_count = text.count("\n") + 1
        ctk.CTkLabel(self.content,
                     text=f"{line_count} lines │ {format_size(len(text.encode()))}",
                     font=ctk.CTkFont(size=10),
                     text_color=colors["text_secondary"]).pack(anchor="w", pady=(3, 0))

    def _load_image_preview(self, ext: str):
        """Load and display image preview."""
        colors = DARK_THEME if self.app.is_dark else LIGHT_THEME

        loading = ctk.CTkLabel(self.content, text="⏳ Loading image...",
                               text_color=colors["text_secondary"])
        loading.pack(pady=20)

        def do_load():
            try:
                response = self.app.s3_client.s3_client.get_object(
                    Bucket=self.bucket, Key=self.obj.key
                )
                image_bytes = response["Body"].read()

                try:
                    from PIL import Image, ImageTk
                    image = Image.open(io.BytesIO(image_bytes))
                    orig_size = image.size

                    # Resize to fit (max 600x400)
                    max_w, max_h = 600, 400
                    image.thumbnail((max_w, max_h), Image.LANCZOS)

                    self.win.after(0, lambda: self._show_image(image, orig_size, loading))

                except ImportError:
                    self.win.after(0, lambda: loading.configure(
                        text="⚠ Install Pillow for image preview: pip install Pillow",
                        text_color="#ff9800"
                    ))

            except Exception as e:
                self.win.after(0, lambda: loading.configure(
                    text=f"❌ Image load failed: {str(e)[:60]}", text_color="#f44336"
                ))

        threading.Thread(target=do_load, daemon=True).start()

    def _show_image(self, image, orig_size, loading_widget):
        """Display the image."""
        loading_widget.destroy()
        colors = DARK_THEME if self.app.is_dark else LIGHT_THEME

        try:
            from PIL import ImageTk
            import tkinter as tk

            # Convert to PhotoImage — keep reference to prevent garbage collection
            self._photo = ImageTk.PhotoImage(image)

            # Use a Label to display image (more reliable than Canvas)
            img_label = tk.Label(self.content, image=self._photo,
                                 bg=colors["bg"], borderwidth=0)
            img_label.image = self._photo  # Extra reference to prevent GC
            img_label.pack(pady=10, expand=True)

            ctk.CTkLabel(self.content,
                         text=f"Original: {orig_size[0]}x{orig_size[1]}  |  "
                              f"Displayed: {image.width}x{image.height}",
                         font=ctk.CTkFont(size=10),
                         text_color=colors["text_secondary"]).pack()
        except Exception as e:
            ctk.CTkLabel(self.content, text=f"Display error: {e}",
                         text_color="#f44336").pack()
