"""Intelligent Cost Advisor — analyze and recommend storage optimizations."""
import threading
import customtkinter as ctk
from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME
from s3_manager_pro_v5.utils.formatting import format_size, STORAGE_CLASS_INFO
from s3_manager_pro_v5.ui.dialogs.cost_estimation import (
    STORAGE_COST_PER_GB_MONTH, estimate_monthly_cost, estimate_class_change_savings
)


class CostAdvisorDialog:
    """Intelligent cost advisor — analyzes bucket and recommends optimizations."""

    def __init__(self, parent, app, bucket: str, objects: list):
        self.app = app
        self.bucket = bucket
        self.objects = objects

        colors = DARK_THEME if app.is_dark else LIGHT_THEME

        self.win = ctk.CTkToplevel(parent)
        self.win.title("💡 Cost Advisor")
        self.win.geometry("620x580")
        self.win.transient(parent)
        self.win.grab_set()
        self.win.resizable(True, True)
        self.win.configure(fg_color=colors["bg"])

        # Title
        ctk.CTkLabel(self.win, text="💡 Intelligent Cost Advisor",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=colors["text_primary"]).pack(pady=(15, 5))

        ctk.CTkLabel(self.win, text=f"Analyzing {len(objects):,} objects in s3://{bucket}/",
                     font=ctk.CTkFont(size=12),
                     text_color=colors["text_secondary"]).pack(pady=(0, 10))

        # Content
        self.content = ctk.CTkScrollableFrame(self.win, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=20, pady=(0, 5))

        # Generate recommendations
        self._analyze(objects)

        # Close
        ctk.CTkButton(self.win, text="Close", width=80, height=32,
                      corner_radius=6, fg_color=colors["badge_bg"],
                      hover_color=colors["surface_hover"],
                      text_color=colors["text_primary"],
                      command=self.win.destroy).pack(pady=(5, 15))

    def _analyze(self, objects):
        """Generate cost recommendations."""
        colors = DARK_THEME if self.app.is_dark else LIGHT_THEME

        # Current cost
        cost_data = estimate_monthly_cost(objects)
        current_cost = cost_data["total_cost"]

        # Current cost card
        cost_card = ctk.CTkFrame(self.content, fg_color=colors["surface"], corner_radius=10)
        cost_card.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(cost_card, text=f"${current_cost:.4f}/month",
                     font=ctk.CTkFont(size=24, weight="bold"),
                     text_color=colors["primary"]).pack(pady=(12, 0))
        ctk.CTkLabel(cost_card, text="Current Monthly Storage Cost",
                     font=ctk.CTkFont(size=11),
                     text_color=colors["text_secondary"]).pack(pady=(0, 10))

        # Generate recommendations
        recommendations = self._generate_recommendations(objects, current_cost)

        if not recommendations:
            ctk.CTkLabel(self.content, text="✅ Your storage is already well-optimized!",
                         font=ctk.CTkFont(size=14, weight="bold"),
                         text_color=colors["success"]).pack(pady=20)
            return

        ctk.CTkLabel(self.content, text="💡 Recommendations:",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=colors["text_primary"]).pack(anchor="w", pady=(0, 10))

        total_potential_savings = 0

        for i, rec in enumerate(recommendations, 1):
            total_potential_savings += rec["savings"]
            self._render_recommendation(i, rec, colors)

        # Total savings summary
        if total_potential_savings > 0:
            summary = ctk.CTkFrame(self.content, fg_color="#1b5e20", corner_radius=10)
            summary.pack(fill="x", pady=(15, 5))

            pct = (total_potential_savings / current_cost * 100) if current_cost > 0 else 0
            ctk.CTkLabel(summary,
                         text=f"💚 Total Potential Savings: ${total_potential_savings:.4f}/month ({pct:.0f}%)",
                         font=ctk.CTkFont(size=14, weight="bold"),
                         text_color="#ffffff").pack(pady=12)

    def _generate_recommendations(self, objects, current_cost) -> list:
        """Generate optimization recommendations."""
        recommendations = []

        # Group by storage class
        by_class = {}
        for o in objects:
            sc = o.storage_class
            if sc not in by_class:
                by_class[sc] = []
            by_class[sc].append(o)

        # Recommendation 1: STANDARD files not accessed recently → STANDARD_IA
        standard_objects = by_class.get("STANDARD", [])
        if standard_objects:
            large_standard = [o for o in standard_objects if o.size > 128 * 1024]  # > 128KB (IA minimum)
            if large_standard:
                savings_data = estimate_class_change_savings(large_standard, "STANDARD_IA")
                if savings_data["savings"] > 0.001:
                    recommendations.append({
                        "title": "Move infrequently accessed files to STANDARD_IA",
                        "description": f"{len(large_standard)} files ({format_size(sum(o.size for o in large_standard))}) "
                                       f"in STANDARD could move to Infrequent Access",
                        "savings": savings_data["savings"],
                        "savings_pct": savings_data["savings_pct"],
                        "action": "STANDARD → STANDARD_IA",
                        "objects": large_standard,
                        "target_class": "STANDARD_IA",
                    })

        # Recommendation 2: Large STANDARD files → GLACIER_IR
        if standard_objects:
            very_large = [o for o in standard_objects if o.size > 10 * 1024 * 1024]  # > 10MB
            if very_large:
                savings_data = estimate_class_change_savings(very_large, "GLACIER_IR")
                if savings_data["savings"] > 0.001:
                    recommendations.append({
                        "title": "Archive large files to Glacier Instant Retrieval",
                        "description": f"{len(very_large)} files > 10MB ({format_size(sum(o.size for o in very_large))}) "
                                       f"could save significantly with instant retrieval still available",
                        "savings": savings_data["savings"],
                        "savings_pct": savings_data["savings_pct"],
                        "action": "STANDARD → GLACIER_IR",
                        "objects": very_large,
                        "target_class": "GLACIER_IR",
                    })

        # Recommendation 3: STANDARD_IA → GLACIER for backup-like files
        ia_objects = by_class.get("STANDARD_IA", [])
        if ia_objects:
            savings_data = estimate_class_change_savings(ia_objects, "GLACIER")
            if savings_data["savings"] > 0.001:
                recommendations.append({
                    "title": "Deep archive IA files to Glacier",
                    "description": f"{len(ia_objects)} files in STANDARD_IA could move to Glacier "
                                   f"(3-5 hour retrieval)",
                    "savings": savings_data["savings"],
                    "savings_pct": savings_data["savings_pct"],
                    "action": "STANDARD_IA → GLACIER",
                    "objects": ia_objects,
                    "target_class": "GLACIER",
                })

        return recommendations

    def _render_recommendation(self, index: int, rec: dict, colors: dict):
        """Render a single recommendation card."""
        card = ctk.CTkFrame(self.content, fg_color=colors["surface"], corner_radius=8)
        card.pack(fill="x", pady=4)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=15, pady=10)

        # Title row
        title_row = ctk.CTkFrame(inner, fg_color="transparent")
        title_row.pack(fill="x")

        ctk.CTkLabel(title_row, text=f"#{index} {rec['title']}",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=colors["text_primary"]).pack(side="left")

        ctk.CTkLabel(title_row, text=f"Save ${rec['savings']:.4f}/mo ({rec['savings_pct']:.0f}%)",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=colors["success"]).pack(side="right")

        # Description
        ctk.CTkLabel(inner, text=rec["description"],
                     font=ctk.CTkFont(size=11),
                     text_color=colors["text_secondary"],
                     wraplength=500, justify="left").pack(anchor="w", pady=(3, 5))

        # Apply button
        ctk.CTkButton(inner, text=f"⚡ Apply: {rec['action']}", width=200, height=28,
                      corner_radius=6, font=ctk.CTkFont(size=11, weight="bold"),
                      fg_color=colors["primary"], hover_color=colors["primary_hover"],
                      command=lambda r=rec: self._apply_recommendation(r)).pack(anchor="w")

    def _apply_recommendation(self, rec: dict):
        """Apply a recommendation — change storage class."""
        from tkinter import messagebox
        count = len(rec["objects"])
        confirm = messagebox.askyesno(
            "Apply Optimization",
            f"Move {count} objects to {rec['target_class']}?\n\n"
            f"Estimated savings: ${rec['savings']:.4f}/month\n\n"
            f"This uses COPY operations (standard charges apply).",
            parent=self.win
        )
        if not confirm:
            return

        # Use the storage class dialog to execute
        from s3_manager_pro_v5.ui.dialogs.storage_class import StorageClassDialog
        self.win.destroy()
        StorageClassDialog(self.app.root, self.app, self.bucket, rec["objects"])
