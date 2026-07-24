"""Glacier Smart Restore — cost estimation per tier before restore.

Shows:
- File count & total size
- Cost estimate per tier (Expedited/Standard/Bulk)
- Time estimate per tier
- Automatic tier recommendation based on urgency/budget
"""
import threading
import customtkinter as ctk
from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME
from s3_manager_pro_v5.utils.formatting import format_size


# Glacier restore pricing (approximate, us-east-1)
# Per GB retrieval cost
RESTORE_COSTS = {
    "GLACIER": {
        "Expedited": {"cost_per_gb": 0.03, "time": "1-5 minutes", "request_cost": 10.00},
        "Standard": {"cost_per_gb": 0.01, "time": "3-5 hours", "request_cost": 0.05},
        "Bulk": {"cost_per_gb": 0.0025, "time": "5-12 hours", "request_cost": 0.025},
    },
    "DEEP_ARCHIVE": {
        "Standard": {"cost_per_gb": 0.02, "time": "12 hours", "request_cost": 0.10},
        "Bulk": {"cost_per_gb": 0.0025, "time": "48 hours", "request_cost": 0.025},
    },
}


def estimate_restore_cost(objects: list, tier: str) -> dict:
    """Estimate restore cost for a list of objects at a given tier.

    Returns: {total_cost, per_gb_cost, request_cost, retrieval_cost, time_estimate}
    """
    total_size_gb = sum(o.size for o in objects) / (1024 ** 3)
    total_requests = len(objects)

    # Determine cost rates based on storage class
    # Use the most expensive class rate if mixed
    has_deep = any(o.storage_class == "DEEP_ARCHIVE" for o in objects)
    cost_table = RESTORE_COSTS.get("DEEP_ARCHIVE" if has_deep else "GLACIER", {})
    tier_info = cost_table.get(tier, {})

    if not tier_info:
        return {"total_cost": 0, "available": False, "time_estimate": "N/A"}

    per_gb = tier_info["cost_per_gb"]
    request_per_1000 = tier_info["request_cost"]

    retrieval_cost = total_size_gb * per_gb
    request_cost = (total_requests / 1000) * request_per_1000
    total_cost = retrieval_cost + request_cost

    return {
        "total_cost": total_cost,
        "retrieval_cost": retrieval_cost,
        "request_cost": request_cost,
        "per_gb_cost": per_gb,
        "time_estimate": tier_info["time"],
        "total_size_gb": total_size_gb,
        "total_files": total_requests,
        "available": True,
    }


class GlacierRestoreDialog:
    """Smart Glacier Restore with cost estimation per tier."""

    def __init__(self, parent, app, bucket: str, glacier_objects: list):
        self.app = app
        self.bucket = bucket
        self.objects = glacier_objects

        colors = DARK_THEME if app.is_dark else LIGHT_THEME
        total_size = sum(o.size for o in glacier_objects)
        has_deep = any(o.storage_class == "DEEP_ARCHIVE" for o in glacier_objects)

        self.win = ctk.CTkToplevel(parent)
        self.win.title("🧊 Smart Glacier Restore")
        self.win.geometry("580x560")
        self.win.transient(parent)
        self.win.grab_set()
        self.win.resizable(False, True)
        self.win.configure(fg_color=colors["bg"])

        # Title
        ctk.CTkLabel(self.win, text="🧊 Smart Glacier Restore",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=colors["text_primary"]).pack(pady=(20, 5))

        # Summary
        ctk.CTkLabel(self.win,
                     text=f"{len(glacier_objects)} objects │ {format_size(total_size)} │ "
                          f"{'DEEP_ARCHIVE' if has_deep else 'GLACIER'}",
                     font=ctk.CTkFont(size=12),
                     text_color=colors["text_secondary"]).pack(pady=(0, 15))

        # Tier comparison cards
        form = ctk.CTkFrame(self.win, fg_color="transparent")
        form.pack(fill="x", padx=25)

        ctk.CTkLabel(form, text="Choose Restore Tier:",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=colors["text_primary"]).pack(anchor="w", pady=(0, 10))

        self.tier_var = ctk.StringVar(value="Standard")
        tiers = ["Expedited", "Standard", "Bulk"] if not has_deep else ["Standard", "Bulk"]

        # Recommendation
        recommended = "Bulk" if total_size > 100 * 1024 * 1024 * 1024 else "Standard"  # > 100GB = Bulk
        if len(glacier_objects) <= 3 and total_size < 1 * 1024 * 1024 * 1024 and not has_deep:
            recommended = "Expedited"

        for tier in tiers:
            estimate = estimate_restore_cost(glacier_objects, tier)
            if not estimate["available"]:
                continue

            is_recommended = (tier == recommended)
            card_color = colors["surface"] if not is_recommended else colors["primary"]
            text_color = colors["text_primary"] if not is_recommended else "#ffffff"

            card = ctk.CTkFrame(form, fg_color=card_color, corner_radius=10)
            card.pack(fill="x", pady=4)

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=15, pady=10)

            # Radio button + tier name
            top_row = ctk.CTkFrame(inner, fg_color="transparent")
            top_row.pack(fill="x")

            ctk.CTkRadioButton(
                top_row, text=f"{tier}",
                variable=self.tier_var, value=tier,
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=text_color,
            ).pack(side="left")

            if is_recommended:
                ctk.CTkLabel(top_row, text="⭐ RECOMMENDED",
                             font=ctk.CTkFont(size=10, weight="bold"),
                             text_color="#ffeb3b").pack(side="right")

            # Details row
            detail_color = colors["text_secondary"] if not is_recommended else "#e0e0e0"

            details = ctk.CTkFrame(inner, fg_color="transparent")
            details.pack(fill="x", padx=24, pady=(4, 0))

            ctk.CTkLabel(details,
                         text=f"⏱ {estimate['time_estimate']}  │  "
                              f"💰 ${estimate['total_cost']:.4f}  │  "
                              f"${estimate['per_gb_cost']:.4f}/GB",
                         font=ctk.CTkFont(size=11),
                         text_color=detail_color).pack(anchor="w")

        # Days to keep
        days_frame = ctk.CTkFrame(form, fg_color="transparent")
        days_frame.pack(fill="x", pady=(15, 0))

        ctk.CTkLabel(days_frame, text="Days to keep restored copy:",
                     font=ctk.CTkFont(size=12),
                     text_color=colors["text_primary"]).pack(side="left")
        self.days_entry = ctk.CTkEntry(days_frame, width=60, height=30)
        self.days_entry.insert(0, "7")
        self.days_entry.pack(side="left", padx=10)

        # Cost breakdown
        self.cost_detail = ctk.CTkLabel(form, text="",
                                        font=ctk.CTkFont(size=11),
                                        text_color=colors["text_secondary"])
        self.cost_detail.pack(anchor="w", pady=(10, 0))
        self._update_cost_detail()
        self.tier_var.trace_add("write", lambda *a: self._update_cost_detail())

        # Buttons
        btn_frame = ctk.CTkFrame(form, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(15, 0))

        self.restore_btn = ctk.CTkButton(
            btn_frame, text="🔄 Start Restore", width=150, height=36,
            corner_radius=8, font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#6f42c1", hover_color="#5a32a3",
            command=self._execute_restore,
        )
        self.restore_btn.pack(side="left", padx=(0, 10))

        self.status_label = ctk.CTkLabel(btn_frame, text="",
                                         font=ctk.CTkFont(size=11))
        self.status_label.pack(side="left")

        ctk.CTkButton(btn_frame, text="Cancel", width=80, height=36,
                      corner_radius=8, fg_color=colors["badge_bg"],
                      hover_color=colors["surface_hover"],
                      text_color=colors["text_primary"],
                      command=self.win.destroy).pack(side="right")

    def _update_cost_detail(self):
        """Update cost breakdown text."""
        tier = self.tier_var.get()
        estimate = estimate_restore_cost(self.objects, tier)
        if estimate["available"]:
            self.cost_detail.configure(
                text=f"Retrieval: ${estimate['retrieval_cost']:.4f} + "
                     f"Requests: ${estimate['request_cost']:.4f} = "
                     f"Total: ${estimate['total_cost']:.4f}"
            )

    def _execute_restore(self):
        """Execute the restore requests."""
        tier = self.tier_var.get()
        days = int(self.days_entry.get().strip() or 7)

        self.restore_btn.configure(state="disabled")
        self.status_label.configure(text="⏳ Requesting restores...", text_color="#ff9800")

        def do_restore():
            success = 0
            skipped = 0
            failed = 0

            for obj in self.objects:
                try:
                    self.app.s3_client.request_restore(self.bucket, obj.key, tier, days)
                    success += 1
                except Exception as e:
                    error_str = str(e)
                    if "RestoreAlreadyInProgress" in error_str:
                        skipped += 1
                    else:
                        failed += 1

                self.win.after(0, lambda s=success, sk=skipped, f=failed:
                    self.status_label.configure(
                        text=f"Progress: {s} initiated, {sk} already in progress, {f} failed"
                    ))

            final_msg = f"✓ Done: {success} initiated, {skipped} already restoring, {failed} failed"
            self.win.after(0, lambda: self.status_label.configure(
                text=final_msg, text_color="#00c853"
            ))
            self.win.after(0, lambda: self.restore_btn.configure(state="normal"))

            # System notification
            from s3_manager_pro_v5.ui.notifications import notify_restore_complete
            notify_restore_complete(success, len(self.objects))

        threading.Thread(target=do_restore, daemon=True).start()
