"""Cost Estimation Panel — calculate monthly costs by storage class."""
import customtkinter as ctk
from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME
from s3_manager_pro_v5.utils.formatting import format_size, STORAGE_CLASS_INFO

# S3 pricing (approximate, us-east-1)
STORAGE_COST_PER_GB_MONTH = {
    "STANDARD": 0.023,
    "REDUCED_REDUNDANCY": 0.024,
    "STANDARD_IA": 0.0125,
    "ONEZONE_IA": 0.01,
    "INTELLIGENT_TIERING": 0.023,
    "GLACIER_IR": 0.004,
    "GLACIER": 0.004,
    "DEEP_ARCHIVE": 0.00099,
}

# Retrieval costs per GB
RETRIEVAL_COST_PER_GB = {
    "STANDARD": 0.0,
    "REDUCED_REDUNDANCY": 0.0,
    "STANDARD_IA": 0.01,
    "ONEZONE_IA": 0.01,
    "INTELLIGENT_TIERING": 0.0,
    "GLACIER_IR": 0.03,
    "GLACIER": 0.03,
    "DEEP_ARCHIVE": 0.02,
}

# Request costs per 1000 requests
REQUEST_COST_PUT = {
    "STANDARD": 0.005,
    "STANDARD_IA": 0.01,
    "ONEZONE_IA": 0.01,
    "INTELLIGENT_TIERING": 0.005,
    "GLACIER_IR": 0.02,
    "GLACIER": 0.05,
    "DEEP_ARCHIVE": 0.05,
}


def estimate_monthly_cost(objects: list) -> dict:
    """Estimate monthly storage cost for a list of S3Objects.

    Returns dict with breakdown by class and total.
    """
    breakdown = {}
    total_cost = 0.0
    total_size = 0

    for obj in objects:
        sc = obj.storage_class
        size_gb = obj.size / (1024 ** 3)
        rate = STORAGE_COST_PER_GB_MONTH.get(sc, 0.023)
        cost = size_gb * rate

        if sc not in breakdown:
            breakdown[sc] = {"count": 0, "size": 0, "cost": 0.0}
        breakdown[sc]["count"] += 1
        breakdown[sc]["size"] += obj.size
        breakdown[sc]["cost"] += cost

        total_cost += cost
        total_size += obj.size

    return {
        "breakdown": breakdown,
        "total_cost": total_cost,
        "total_size": total_size,
        "total_objects": len(objects),
    }


def estimate_class_change_savings(objects: list, target_class: str) -> dict:
    """Estimate savings from moving all objects to target_class.

    Returns dict with current cost, new cost, savings, percentage.
    """
    current_cost = 0.0
    total_size_gb = 0.0

    for obj in objects:
        size_gb = obj.size / (1024 ** 3)
        rate = STORAGE_COST_PER_GB_MONTH.get(obj.storage_class, 0.023)
        current_cost += size_gb * rate
        total_size_gb += size_gb

    new_rate = STORAGE_COST_PER_GB_MONTH.get(target_class, 0.023)
    new_cost = total_size_gb * new_rate
    savings = current_cost - new_cost
    pct = (savings / current_cost * 100) if current_cost > 0 else 0

    return {
        "current_cost": current_cost,
        "new_cost": new_cost,
        "savings": savings,
        "savings_pct": pct,
        "total_size_gb": total_size_gb,
    }


class CostEstimationDialog:
    """Cost estimation dialog showing breakdown and optimization suggestions."""

    def __init__(self, parent, app, objects: list, bucket: str):
        self.app = app
        self.objects = objects

        colors = DARK_THEME if app.is_dark else LIGHT_THEME

        self.win = ctk.CTkToplevel(parent)
        self.win.title("💰 Cost Estimation")
        self.win.geometry("550x500")
        self.win.transient(parent)
        self.win.grab_set()
        self.win.resizable(False, True)
        self.win.configure(fg_color=colors["bg"])

        # Title
        ctk.CTkLabel(self.win, text="💰 Storage Cost Estimation",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=colors["text_primary"]).pack(pady=(20, 5))

        ctk.CTkLabel(self.win, text=f"Bucket: {bucket} │ {len(objects):,} objects",
                     font=ctk.CTkFont(size=12),
                     text_color=colors["text_secondary"]).pack(pady=(0, 15))

        # Calculate
        estimate = estimate_monthly_cost(objects)

        # Total cost card
        total_frame = ctk.CTkFrame(self.win, fg_color=colors["surface"], corner_radius=8)
        total_frame.pack(fill="x", padx=25, pady=(0, 10))

        ctk.CTkLabel(total_frame, text=f"${estimate['total_cost']:.4f}",
                     font=ctk.CTkFont(size=28, weight="bold"),
                     text_color=colors["primary"]).pack(pady=(12, 0))
        ctk.CTkLabel(total_frame, text="Estimated Monthly Storage Cost",
                     font=ctk.CTkFont(size=11),
                     text_color=colors["text_secondary"]).pack(pady=(0, 10))

        # Breakdown by class
        breakdown_frame = ctk.CTkFrame(self.win, fg_color="transparent")
        breakdown_frame.pack(fill="x", padx=25, pady=(5, 10))

        ctk.CTkLabel(breakdown_frame, text="Breakdown by Storage Class:",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=colors["text_primary"]).pack(anchor="w", pady=(0, 8))

        for sc, data in sorted(estimate["breakdown"].items(), key=lambda x: x[1]["cost"], reverse=True):
            info = STORAGE_CLASS_INFO.get(sc, {"icon": "⚪", "label": sc})
            row = ctk.CTkFrame(breakdown_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)

            ctk.CTkLabel(row, text=f"{info['icon']} {sc}",
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=colors["text_primary"], width=160).pack(side="left")
            ctk.CTkLabel(row, text=f"{data['count']} files",
                         font=ctk.CTkFont(size=11),
                         text_color=colors["text_secondary"], width=80).pack(side="left")
            ctk.CTkLabel(row, text=format_size(data["size"]),
                         font=ctk.CTkFont(size=11),
                         text_color=colors["text_secondary"], width=80).pack(side="left")
            ctk.CTkLabel(row, text=f"${data['cost']:.4f}/mo",
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=colors["success"]).pack(side="right")

        # Optimization suggestions
        if estimate["total_cost"] > 0:
            opt_frame = ctk.CTkFrame(self.win, fg_color=colors["surface"], corner_radius=8)
            opt_frame.pack(fill="x", padx=25, pady=(10, 10))

            ctk.CTkLabel(opt_frame, text="💡 Optimization Suggestions:",
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=colors["text_primary"]).pack(anchor="w", padx=12, pady=(10, 5))

            # Show savings for moving to cheaper classes
            standard_objects = [o for o in objects if o.storage_class == "STANDARD"]
            if standard_objects:
                for target in ["STANDARD_IA", "GLACIER_IR", "DEEP_ARCHIVE"]:
                    result = estimate_class_change_savings(standard_objects, target)
                    if result["savings"] > 0:
                        info = STORAGE_CLASS_INFO.get(target, {})
                        ctk.CTkLabel(
                            opt_frame,
                            text=f"  {info.get('icon', '')} Move STANDARD → {target}: "
                                 f"Save ${result['savings']:.4f}/mo ({result['savings_pct']:.0f}%)",
                            font=ctk.CTkFont(size=11),
                            text_color=colors["text_secondary"],
                        ).pack(anchor="w", padx=12, pady=1)

            ctk.CTkLabel(opt_frame, text="").pack(pady=3)  # Spacer

        # Close button
        ctk.CTkButton(self.win, text="Close", width=80, height=32,
                      corner_radius=6, fg_color=colors["badge_bg"],
                      hover_color=colors["surface_hover"],
                      text_color=colors["text_primary"],
                      command=self.win.destroy).pack(pady=(10, 15))
