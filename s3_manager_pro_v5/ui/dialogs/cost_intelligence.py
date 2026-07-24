"""Advanced Cost Intelligence — access patterns, trends, transfer costs, budget alerts, region comparison.

Uses PricingEngine to fetch real costs from AWS Cost Explorer when available,
falls back to configurable local rates (editable in s3_pricing.json).
"""
import threading
from datetime import datetime, timedelta
import customtkinter as ctk
from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME
from s3_manager_pro_v5.utils.formatting import format_size, STORAGE_CLASS_INFO
from s3_manager_pro_v5.backend.pricing import PricingEngine


class CostIntelligenceDialog:
    """Comprehensive cost intelligence with 5 analysis panels."""

    def __init__(self, parent, app, bucket: str, objects: list):
        self.app = app
        self.bucket = bucket
        self.objects = objects
        self.region = app.cred_manager.get("region", "ap-south-1")

        # Initialize pricing engine with live data
        self.pricing = PricingEngine(app.s3_client)

        # Try to fetch actual costs from Cost Explorer (async)
        if app.s3_client and app.s3_client.session:
            try:
                self.pricing.fetch_actual_costs(app.s3_client.session)
            except Exception:
                pass  # Will use local rates

        colors = DARK_THEME if app.is_dark else LIGHT_THEME

        self.win = ctk.CTkToplevel(parent)
        self.win.title("💰 Cost Intelligence Center")
        self.win.geometry("750x620")
        self.win.transient(parent)
        self.win.grab_set()
        self.win.resizable(True, True)
        self.win.configure(fg_color=colors["bg"])

        # Title
        ctk.CTkLabel(self.win, text="💰 Cost Intelligence Center",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=colors["text_primary"]).pack(pady=(15, 5))
        ctk.CTkLabel(self.win, text=f"s3://{bucket}/ │ {len(objects):,} objects │ Region: {self.region}",
                     font=ctk.CTkFont(size=11),
                     text_color=colors["text_secondary"]).pack(pady=(0, 3))

        # Show pricing data source
        ctk.CTkLabel(self.win, text=f"📡 Pricing: {self.pricing.rates_source}",
                     font=ctk.CTkFont(size=10),
                     text_color=colors["text_secondary"]).pack(pady=(0, 8))

        # Tabview for different analysis panels
        self.tabview = ctk.CTkTabview(self.win, fg_color=colors["surface"])
        self.tabview.pack(fill="both", expand=True, padx=15, pady=(0, 5))

        # Tab 1: Access Pattern Analysis
        tab1 = self.tabview.add("📊 Access Patterns")
        self._build_access_patterns(tab1, colors)

        # Tab 2: Cost Trends
        tab2 = self.tabview.add("📈 Cost Trend")
        self._build_cost_trend(tab2, colors)

        # Tab 3: Transfer Costs
        tab3 = self.tabview.add("🌐 Transfer Costs")
        self._build_transfer_costs(tab3, colors)

        # Tab 4: Budget Alerts
        tab4 = self.tabview.add("🔔 Budget")
        self._build_budget(tab4, colors)

        # Tab 5: Region Comparison
        tab5 = self.tabview.add("🌍 Region Compare")
        self._build_region_comparison(tab5, colors)

        # Close
        ctk.CTkButton(self.win, text="Close", width=80, height=32,
                      corner_radius=6, fg_color=colors["badge_bg"],
                      hover_color=colors["surface_hover"],
                      text_color=colors["text_primary"],
                      command=self.win.destroy).pack(pady=(5, 15))

    # ═══════════════════════════════════════════
    # TAB 1: Access Pattern Analysis
    # ═══════════════════════════════════════════
    def _build_access_patterns(self, parent, colors):
        """Analyze files by last modified date to suggest archival."""
        content = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(content, text="📊 Access Pattern Analysis",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=colors["text_primary"]).pack(anchor="w", pady=(0, 8))

        ctk.CTkLabel(content, text="Files grouped by last modification date (proxy for access frequency):",
                     font=ctk.CTkFont(size=11),
                     text_color=colors["text_secondary"]).pack(anchor="w", pady=(0, 10))

        # Categorize by age
        now = datetime.now()
        buckets = {
            "< 7 days": [],
            "7-30 days": [],
            "30-90 days": [],
            "90-180 days": [],
            "180-365 days": [],
            "> 365 days": [],
        }

        for obj in self.objects:
            try:
                # Parse last_modified string
                mod_date = datetime.strptime(obj.last_modified, "%Y-%m-%d %H:%M")
                age_days = (now - mod_date).days
            except Exception:
                age_days = 999

            if age_days < 7:
                buckets["< 7 days"].append(obj)
            elif age_days < 30:
                buckets["7-30 days"].append(obj)
            elif age_days < 90:
                buckets["30-90 days"].append(obj)
            elif age_days < 180:
                buckets["90-180 days"].append(obj)
            elif age_days < 365:
                buckets["180-365 days"].append(obj)
            else:
                buckets["> 365 days"].append(obj)

        recommendations = []

        for age_label, objs in buckets.items():
            if not objs:
                continue

            total_size = sum(o.size for o in objs)
            standard_count = sum(1 for o in objs if o.storage_class == "STANDARD")

            row = ctk.CTkFrame(content, fg_color=colors["surface"], corner_radius=6)
            row.pack(fill="x", pady=3)
            inner = ctk.CTkFrame(row, fg_color="transparent")
            inner.pack(fill="x", padx=12, pady=8)

            ctk.CTkLabel(inner, text=f"🕐 {age_label}",
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=colors["text_primary"]).pack(side="left")

            ctk.CTkLabel(inner, text=f"{len(objs)} files │ {format_size(total_size)}",
                         font=ctk.CTkFont(size=11),
                         text_color=colors["text_secondary"]).pack(side="left", padx=15)

            # Recommendation
            if age_label in ("90-180 days", "180-365 days") and standard_count > 0:
                ctk.CTkLabel(inner, text=f"💡 {standard_count} STANDARD files → move to IA",
                             font=ctk.CTkFont(size=10, weight="bold"),
                             text_color=colors["warning"]).pack(side="right")
            elif age_label == "> 365 days" and standard_count > 0:
                ctk.CTkLabel(inner, text=f"💡 {standard_count} files → move to GLACIER",
                             font=ctk.CTkFont(size=10, weight="bold"),
                             text_color="#f44336").pack(side="right")

        # Summary recommendation
        old_standard = [o for o in self.objects
                        if o.storage_class == "STANDARD" and self._get_age_days(o) > 90]
        if old_standard:
            total_old = sum(o.size for o in old_standard)
            savings = (total_old / (1024**3)) * (0.023 - 0.0125)  # Std vs IA
            ctk.CTkLabel(content,
                         text=f"\n💚 Recommendation: Move {len(old_standard)} files not modified in 90+ days "
                              f"({format_size(total_old)}) to STANDARD_IA → Save ~${savings:.4f}/month",
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=colors["success"], wraplength=600).pack(anchor="w", pady=(10, 0))

    def _get_age_days(self, obj) -> int:
        try:
            mod_date = datetime.strptime(obj.last_modified, "%Y-%m-%d %H:%M")
            return (datetime.now() - mod_date).days
        except Exception:
            return 0

    # ═══════════════════════════════════════════
    # TAB 2: Cost Trend
    # ═══════════════════════════════════════════
    def _build_cost_trend(self, parent, colors):
        """Show estimated cost trend."""
        content = ctk.CTkFrame(parent, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(content, text="📈 Storage Cost Projection",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=colors["text_primary"]).pack(anchor="w", pady=(0, 10))

        total_size_gb = sum(o.size for o in self.objects) / (1024**3)

        # Calculate current monthly cost using pricing engine
        cost_result = self.pricing.estimate_monthly_cost(self.objects, self.region)
        current_cost = cost_result["total"]

        # Show actual cost from Cost Explorer if available
        if self.pricing.actual_cost:
            actual = self.pricing.actual_cost
            ctk.CTkLabel(content,
                         text=f"📡 Actual AWS Bill (last 30 days): ${actual['monthly_cost']:.2f} "
                              f"({actual['currency']}) — from Cost Explorer API",
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=colors["success"]).pack(anchor="w", pady=(0, 10))

        # Project growth (assume 5% monthly growth)
        growth_rate = 0.05

        months = ["Current", "+1 mo", "+3 mo", "+6 mo", "+12 mo"]
        costs = [
            current_cost,
            current_cost * (1 + growth_rate),
            current_cost * (1 + growth_rate) ** 3,
            current_cost * (1 + growth_rate) ** 6,
            current_cost * (1 + growth_rate) ** 12,
        ]

        # Display as table
        for i, (month, cost) in enumerate(zip(months, costs)):
            row = ctk.CTkFrame(content, fg_color=colors["surface"] if i % 2 == 0 else "transparent",
                               corner_radius=4)
            row.pack(fill="x", pady=1)
            inner = ctk.CTkFrame(row, fg_color="transparent")
            inner.pack(fill="x", padx=12, pady=6)

            ctk.CTkLabel(inner, text=month, font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=colors["text_primary"], width=80).pack(side="left")

            size_at_month = total_size_gb * (1 + growth_rate) ** i
            ctk.CTkLabel(inner, text=f"{size_at_month:.2f} GB",
                         font=ctk.CTkFont(size=11),
                         text_color=colors["text_secondary"], width=80).pack(side="left")

            cost_color = colors["success"] if cost < current_cost * 1.5 else colors["warning"]
            ctk.CTkLabel(inner, text=f"${cost:.4f}/mo",
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=cost_color).pack(side="left", padx=20)

            # Annual projection
            ctk.CTkLabel(inner, text=f"(${cost * 12:.2f}/yr)",
                         font=ctk.CTkFont(size=10),
                         text_color=colors["text_secondary"]).pack(side="left")

        # Note
        ctk.CTkLabel(content, text="ℹ️ Projection based on 5% monthly growth rate estimate.",
                     font=ctk.CTkFont(size=10),
                     text_color=colors["text_secondary"]).pack(anchor="w", pady=(15, 0))

    # ═══════════════════════════════════════════
    # TAB 3: Transfer Costs
    # ═══════════════════════════════════════════
    def _build_transfer_costs(self, parent, colors):
        """Estimate data transfer and retrieval costs."""
        content = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(content, text="🌐 Data Transfer Cost Estimator",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=colors["text_primary"]).pack(anchor="w", pady=(0, 10))

        total_size_gb = sum(o.size for o in self.objects) / (1024**3)

        # Download all to internet — use pricing engine rates
        transfer_rate = self.pricing.get_transfer_rate(self.region, "to_internet")
        download_cost = total_size_gb * transfer_rate

        # Retrieval costs by class — use pricing engine rates
        retrieval_cost = 0
        for obj in self.objects:
            rate = self.pricing.get_retrieval_rate(self.region, obj.storage_class)
            retrieval_cost += (obj.size / (1024**3)) * rate

        # Display
        ctk.CTkLabel(content, text="If you download ALL files:",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=colors["text_primary"]).pack(anchor="w", pady=(0, 8))

        costs = [
            ("Data transfer (to internet)", f"${download_cost:.4f}", "Per-GB egress charge"),
            ("Retrieval fees (Glacier/IA)", f"${retrieval_cost:.4f}", "Storage class retrieval charge"),
            ("Total download cost", f"${download_cost + retrieval_cost:.4f}", "One-time cost for all data"),
        ]

        for label, value, note in costs:
            row = ctk.CTkFrame(content, fg_color=colors["surface"], corner_radius=6)
            row.pack(fill="x", pady=2)
            inner = ctk.CTkFrame(row, fg_color="transparent")
            inner.pack(fill="x", padx=12, pady=8)

            ctk.CTkLabel(inner, text=label, font=ctk.CTkFont(size=11),
                         text_color=colors["text_primary"]).pack(side="left")
            ctk.CTkLabel(inner, text=value, font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=colors["primary"]).pack(side="right")

        # Per-class breakdown
        ctk.CTkLabel(content, text="\nRetrieval Cost by Storage Class:",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=colors["text_primary"]).pack(anchor="w", pady=(10, 5))

        class_groups = {}
        for obj in self.objects:
            sc = obj.storage_class
            if sc not in class_groups:
                class_groups[sc] = 0
            class_groups[sc] += obj.size

        for sc, total_bytes in sorted(class_groups.items()):
            size_gb = total_bytes / (1024**3)
            rate = self.pricing.get_retrieval_rate(self.region, sc)
            cost = size_gb * rate
            info = STORAGE_CLASS_INFO.get(sc, {"icon": "⚪"})

            row = ctk.CTkFrame(content, fg_color="transparent")
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(row, text=f"  {info['icon']} {sc}: {format_size(total_bytes)} × ${rate}/GB = ${cost:.4f}",
                         font=ctk.CTkFont(size=11),
                         text_color=colors["text_secondary"]).pack(anchor="w")

    # ═══════════════════════════════════════════
    # TAB 4: Budget Alerts
    # ═══════════════════════════════════════════
    def _build_budget(self, parent, colors):
        """Budget tracking and alerts."""
        content = ctk.CTkFrame(parent, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(content, text="🔔 Budget Tracker",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=colors["text_primary"]).pack(anchor="w", pady=(0, 10))

        # Calculate current cost using pricing engine
        cost_result = self.pricing.estimate_monthly_cost(self.objects, self.region)
        current_cost = cost_result["total"]

        # Budget input
        budget_frame = ctk.CTkFrame(content, fg_color=colors["surface"], corner_radius=8)
        budget_frame.pack(fill="x", pady=(0, 10))

        inner = ctk.CTkFrame(budget_frame, fg_color="transparent")
        inner.pack(fill="x", padx=15, pady=12)

        ctk.CTkLabel(inner, text="Monthly Budget ($):",
                     font=ctk.CTkFont(size=12),
                     text_color=colors["text_primary"]).pack(side="left")

        self.budget_entry = ctk.CTkEntry(inner, width=80, height=30)
        self.budget_entry.insert(0, "50")
        self.budget_entry.pack(side="left", padx=10)

        self.budget_status = ctk.CTkLabel(inner, text="",
                                          font=ctk.CTkFont(size=12, weight="bold"))
        self.budget_status.pack(side="left", padx=10)

        ctk.CTkButton(inner, text="Check", width=70, height=28, corner_radius=6,
                      fg_color=colors["primary"], hover_color=colors["primary_hover"],
                      command=lambda: self._check_budget(current_cost)).pack(side="right")

        # Current usage display
        ctk.CTkLabel(content, text=f"Current estimated monthly cost: ${current_cost:.4f}",
                     font=ctk.CTkFont(size=13),
                     text_color=colors["text_primary"]).pack(anchor="w", pady=(10, 5))

        # Budget scenarios
        ctk.CTkLabel(content, text="Budget Alert Thresholds:",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=colors["text_primary"]).pack(anchor="w", pady=(15, 5))

        budgets = [1, 5, 10, 25, 50, 100]
        for b in budgets:
            pct = (current_cost / b * 100) if b > 0 else 0
            status = "✅ Under" if pct < 80 else ("⚠️ Near limit" if pct < 100 else "🔴 Over!")
            status_color = colors["success"] if pct < 80 else (colors["warning"] if pct < 100 else colors["danger"])

            row = ctk.CTkFrame(content, fg_color="transparent")
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(row, text=f"  ${b}/mo budget: {pct:.1f}% used — {status}",
                         font=ctk.CTkFont(size=11),
                         text_color=status_color).pack(anchor="w")

    def _check_budget(self, current_cost):
        """Check budget against current cost."""
        colors = DARK_THEME if self.app.is_dark else LIGHT_THEME
        try:
            budget = float(self.budget_entry.get().strip())
            pct = (current_cost / budget * 100) if budget > 0 else 0

            if pct < 50:
                self.budget_status.configure(text=f"✅ {pct:.1f}% — Well under budget", text_color=colors["success"])
            elif pct < 80:
                self.budget_status.configure(text=f"✅ {pct:.1f}% — OK", text_color=colors["success"])
            elif pct < 100:
                self.budget_status.configure(text=f"⚠️ {pct:.1f}% — Approaching limit!", text_color=colors["warning"])
            else:
                self.budget_status.configure(text=f"🔴 {pct:.1f}% — OVER BUDGET!", text_color=colors["danger"])
        except ValueError:
            self.budget_status.configure(text="Enter a valid number", text_color=colors["danger"])

    # ═══════════════════════════════════════════
    # TAB 5: Region Comparison
    # ═══════════════════════════════════════════
    def _build_region_comparison(self, parent, colors):
        """Compare storage costs across AWS regions."""
        content = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(content, text="🌍 Region Cost Comparison",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=colors["text_primary"]).pack(anchor="w", pady=(0, 5))

        ctk.CTkLabel(content, text="Same data stored in different AWS regions:",
                     font=ctk.CTkFont(size=11),
                     text_color=colors["text_secondary"]).pack(anchor="w", pady=(0, 10))

        total_size_gb = sum(o.size for o in self.objects) / (1024**3)

        # Calculate cost per region using pricing engine
        region_costs = []
        all_regions = self.pricing.get_all_region_rates()
        for region in all_regions:
            cost_data = self.pricing.estimate_monthly_cost(self.objects, region)
            region_costs.append((region, cost_data["total"]))

        # Sort by cost
        region_costs.sort(key=lambda x: x[1])
        cheapest = region_costs[0][1] if region_costs else 0

        # Current region marker
        current_cost = next((c for r, c in region_costs if r == self.region), 0)

        for region, cost in region_costs:
            is_current = region == self.region
            is_cheapest = cost == cheapest

            card_color = colors["surface"] if not is_current else colors["primary"]
            text_color = colors["text_primary"] if not is_current else "#ffffff"

            row = ctk.CTkFrame(content, fg_color=card_color, corner_radius=6)
            row.pack(fill="x", pady=2)
            inner = ctk.CTkFrame(row, fg_color="transparent")
            inner.pack(fill="x", padx=12, pady=8)

            # Region name
            label = region
            if is_current:
                label += " ← CURRENT"
            if is_cheapest:
                label += " ⭐ CHEAPEST"

            ctk.CTkLabel(inner, text=label,
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=text_color).pack(side="left")

            # Cost
            ctk.CTkLabel(inner, text=f"${cost:.4f}/mo",
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=text_color).pack(side="right")

            # Savings vs current
            if not is_current and current_cost > 0:
                diff = current_cost - cost
                if diff > 0:
                    ctk.CTkLabel(inner, text=f"Save ${diff:.4f}",
                                 font=ctk.CTkFont(size=10),
                                 text_color="#00c853" if not is_current else "#a5d6a7").pack(side="right", padx=10)
                elif diff < 0:
                    ctk.CTkLabel(inner, text=f"+${abs(diff):.4f}",
                                 font=ctk.CTkFont(size=10),
                                 text_color="#ff9800").pack(side="right", padx=10)

        # Note
        ctk.CTkLabel(content,
                     text="\nℹ️ Cross-region data transfer costs (~$0.02/GB) not included.\n"
                          "Consider latency and compliance requirements when choosing region.",
                     font=ctk.CTkFont(size=10),
                     text_color=colors["text_secondary"], wraplength=550).pack(anchor="w", pady=(10, 0))
