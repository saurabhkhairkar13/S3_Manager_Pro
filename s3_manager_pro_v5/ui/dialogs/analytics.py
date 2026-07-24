"""S3 Bucket Analytics Dashboard — storage breakdown, top files, stats."""
import threading
import customtkinter as ctk
from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME
from s3_manager_pro_v5.utils.formatting import format_size, STORAGE_CLASS_INFO


class AnalyticsDashboard:
    """Visual analytics for current bucket — storage class breakdown, top files, stats."""

    def __init__(self, parent, app, bucket: str, prefix: str):
        self.app = app
        self.bucket = bucket
        self.prefix = prefix

        colors = DARK_THEME if app.is_dark else LIGHT_THEME

        self.win = ctk.CTkToplevel(parent)
        self.win.title(f"📊 Analytics — {bucket}")
        self.win.geometry("700x600")
        self.win.transient(parent)
        self.win.grab_set()
        self.win.resizable(True, True)
        self.win.configure(fg_color=colors["bg"])

        # Title
        ctk.CTkLabel(self.win, text="📊 Bucket Analytics",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=colors["text_primary"]).pack(pady=(15, 5))
        ctk.CTkLabel(self.win, text=f"s3://{bucket}/{prefix}",
                     font=ctk.CTkFont(size=12),
                     text_color=colors["primary"]).pack(pady=(0, 10))

        # Loading
        self.content = ctk.CTkScrollableFrame(self.win, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        self.loading = ctk.CTkLabel(self.content, text="⏳ Analyzing bucket...",
                                    font=ctk.CTkFont(size=13),
                                    text_color=colors["text_secondary"])
        self.loading.pack(pady=30)

        # Close
        ctk.CTkButton(self.win, text="Close", width=80, height=32,
                      corner_radius=6, fg_color=colors["badge_bg"],
                      hover_color=colors["surface_hover"],
                      text_color=colors["text_primary"],
                      command=self.win.destroy).pack(pady=(0, 15))

        # Load data
        threading.Thread(target=self._analyze, daemon=True).start()

    def _analyze(self):
        """Analyze bucket contents."""
        try:
            objects = self.app.s3_client.list_all_objects(self.bucket, self.prefix)
            self.win.after(0, lambda: self._render(objects))
        except Exception as e:
            self.win.after(0, lambda: self.loading.configure(
                text=f"❌ Analysis failed: {str(e)[:60]}", text_color="#f44336"
            ))

    def _render(self, objects):
        """Render analytics data."""
        self.loading.destroy()
        colors = DARK_THEME if self.app.is_dark else LIGHT_THEME

        if not objects:
            ctk.CTkLabel(self.content, text="No objects found.",
                         text_color=colors["text_secondary"]).pack(pady=20)
            return

        total_size = sum(o.size for o in objects)
        total_count = len(objects)

        # ── Summary Cards ──
        cards_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        cards_frame.pack(fill="x", pady=(0, 15))

        self._card(cards_frame, "📦 Objects", f"{total_count:,}", colors)
        self._card(cards_frame, "💾 Total Size", format_size(total_size), colors)

        avg_size = total_size // total_count if total_count > 0 else 0
        self._card(cards_frame, "📐 Avg Size", format_size(avg_size), colors)

        # Monthly cost estimate
        from s3_manager_pro_v5.ui.dialogs.cost_estimation import estimate_monthly_cost
        cost_data = estimate_monthly_cost(objects)
        self._card(cards_frame, "💰 Monthly Cost", f"${cost_data['total_cost']:.3f}", colors)

        # ── Storage Class Breakdown (Visual Bar) ──
        ctk.CTkLabel(self.content, text="Storage Class Breakdown",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=colors["text_primary"]).pack(anchor="w", pady=(10, 8))

        class_breakdown = {}
        for o in objects:
            sc = o.storage_class
            if sc not in class_breakdown:
                class_breakdown[sc] = {"count": 0, "size": 0}
            class_breakdown[sc]["count"] += 1
            class_breakdown[sc]["size"] += o.size

        # Sort by size descending
        sorted_classes = sorted(class_breakdown.items(), key=lambda x: x[1]["size"], reverse=True)

        for sc, data in sorted_classes:
            info = STORAGE_CLASS_INFO.get(sc, {"icon": "⚪", "label": sc, "color": "#888"})
            pct_count = (data["count"] / total_count * 100) if total_count > 0 else 0
            pct_size = (data["size"] / total_size * 100) if total_size > 0 else 0

            row = ctk.CTkFrame(self.content, fg_color="transparent")
            row.pack(fill="x", pady=3)

            # Label
            ctk.CTkLabel(row, text=f"{info['icon']} {sc}",
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=colors["text_primary"], width=140).pack(side="left")

            # Bar
            bar_frame = ctk.CTkFrame(row, fg_color=colors["border"], height=18,
                                     corner_radius=4, width=250)
            bar_frame.pack(side="left", padx=5)
            bar_frame.pack_propagate(False)

            bar_width = max(3, int(250 * pct_size / 100))
            bar = ctk.CTkFrame(bar_frame, fg_color=info["color"], height=18,
                               corner_radius=4, width=bar_width)
            bar.pack(side="left")
            bar.pack_propagate(False)

            # Stats
            ctk.CTkLabel(row, text=f"{pct_size:.1f}% │ {data['count']:,} files │ {format_size(data['size'])}",
                         font=ctk.CTkFont(size=10),
                         text_color=colors["text_secondary"]).pack(side="left", padx=8)

        # ── File Type Breakdown ──
        ctk.CTkLabel(self.content, text="File Type Distribution",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=colors["text_primary"]).pack(anchor="w", pady=(20, 8))

        ext_breakdown = {}
        for o in objects:
            import os
            ext = os.path.splitext(o.key)[1].lower() or "(no extension)"
            if ext not in ext_breakdown:
                ext_breakdown[ext] = {"count": 0, "size": 0}
            ext_breakdown[ext]["count"] += 1
            ext_breakdown[ext]["size"] += o.size

        # Top 10 extensions
        sorted_exts = sorted(ext_breakdown.items(), key=lambda x: x[1]["size"], reverse=True)[:10]

        for ext, data in sorted_exts:
            row = ctk.CTkFrame(self.content, fg_color="transparent")
            row.pack(fill="x", pady=1)

            ctk.CTkLabel(row, text=ext, font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=colors["text_primary"], width=100).pack(side="left")
            ctk.CTkLabel(row, text=f"{data['count']:,} files │ {format_size(data['size'])}",
                         font=ctk.CTkFont(size=10),
                         text_color=colors["text_secondary"]).pack(side="left", padx=10)

        # ── Top 10 Largest Files ──
        ctk.CTkLabel(self.content, text="Top 10 Largest Files",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=colors["text_primary"]).pack(anchor="w", pady=(20, 8))

        sorted_by_size = sorted(objects, key=lambda o: o.size, reverse=True)[:10]

        for i, obj in enumerate(sorted_by_size, 1):
            filename = obj.key.split("/")[-1] if "/" in obj.key else obj.key
            row = ctk.CTkFrame(self.content, fg_color="transparent")
            row.pack(fill="x", pady=1)

            ctk.CTkLabel(row, text=f"{i}.",
                         font=ctk.CTkFont(size=11),
                         text_color=colors["text_secondary"], width=25).pack(side="left")
            ctk.CTkLabel(row, text=filename[:50],
                         font=ctk.CTkFont(size=11),
                         text_color=colors["text_primary"]).pack(side="left", padx=(0, 10))
            ctk.CTkLabel(row, text=format_size(obj.size),
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=colors["primary"]).pack(side="right")

    def _card(self, parent, title: str, value: str, colors: dict):
        """Create a summary stat card."""
        card = ctk.CTkFrame(parent, fg_color=colors["surface"], corner_radius=8, width=150)
        card.pack(side="left", padx=5, pady=5, expand=True, fill="x")

        ctk.CTkLabel(card, text=value,
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=colors["primary"]).pack(pady=(10, 0))
        ctk.CTkLabel(card, text=title,
                     font=ctk.CTkFont(size=10),
                     text_color=colors["text_secondary"]).pack(pady=(0, 8))
