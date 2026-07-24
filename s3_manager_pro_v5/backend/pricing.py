"""AWS Pricing — fetch real costs from Cost Explorer API or fallback to configurable rates.

Priority:
1. AWS Cost Explorer API (real billing data) — requires ce:GetCostAndUsage permission
2. AWS Pricing API (published rates) — requires pricing:GetProducts permission
3. Configurable local rates (user can edit) — always available as fallback

The local rates are stored in s3_pricing.json and can be manually updated.
"""
import os
import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

PRICING_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "s3_pricing.json"
)

# Default rates (approximate, updated manually) — used only if API fails
DEFAULT_RATES = {
    "_last_updated": "2024-01-01",
    "_note": "These are approximate rates. Update manually or enable Cost Explorer API access.",
    "us-east-1": {
        "storage_per_gb": {"STANDARD": 0.023, "STANDARD_IA": 0.0125, "ONEZONE_IA": 0.01,
                           "INTELLIGENT_TIERING": 0.023, "GLACIER_IR": 0.004,
                           "GLACIER": 0.004, "DEEP_ARCHIVE": 0.00099},
        "retrieval_per_gb": {"STANDARD": 0.0, "STANDARD_IA": 0.01, "ONEZONE_IA": 0.01,
                             "GLACIER_IR": 0.03, "GLACIER": 0.03, "DEEP_ARCHIVE": 0.02},
        "transfer_per_gb": {"to_internet": 0.09, "cross_region": 0.02},
    },
    "us-west-2": {
        "storage_per_gb": {"STANDARD": 0.023, "STANDARD_IA": 0.0125, "ONEZONE_IA": 0.01,
                           "INTELLIGENT_TIERING": 0.023, "GLACIER_IR": 0.004,
                           "GLACIER": 0.004, "DEEP_ARCHIVE": 0.00099},
        "retrieval_per_gb": {"STANDARD": 0.0, "STANDARD_IA": 0.01, "ONEZONE_IA": 0.01,
                             "GLACIER_IR": 0.03, "GLACIER": 0.03, "DEEP_ARCHIVE": 0.02},
        "transfer_per_gb": {"to_internet": 0.09, "cross_region": 0.02},
    },
    "eu-west-1": {
        "storage_per_gb": {"STANDARD": 0.024, "STANDARD_IA": 0.0131, "ONEZONE_IA": 0.0105,
                           "INTELLIGENT_TIERING": 0.024, "GLACIER_IR": 0.005,
                           "GLACIER": 0.0045, "DEEP_ARCHIVE": 0.002},
        "retrieval_per_gb": {"STANDARD": 0.0, "STANDARD_IA": 0.01, "ONEZONE_IA": 0.01,
                             "GLACIER_IR": 0.03, "GLACIER": 0.03, "DEEP_ARCHIVE": 0.02},
        "transfer_per_gb": {"to_internet": 0.09, "cross_region": 0.02},
    },
    "ap-south-1": {
        "storage_per_gb": {"STANDARD": 0.025, "STANDARD_IA": 0.0138, "ONEZONE_IA": 0.011,
                           "INTELLIGENT_TIERING": 0.025, "GLACIER_IR": 0.005,
                           "GLACIER": 0.005, "DEEP_ARCHIVE": 0.002},
        "retrieval_per_gb": {"STANDARD": 0.0, "STANDARD_IA": 0.01, "ONEZONE_IA": 0.01,
                             "GLACIER_IR": 0.03, "GLACIER": 0.03, "DEEP_ARCHIVE": 0.02},
        "transfer_per_gb": {"to_internet": 0.109, "cross_region": 0.02},
    },
    "ap-southeast-1": {
        "storage_per_gb": {"STANDARD": 0.025, "STANDARD_IA": 0.0138, "ONEZONE_IA": 0.011,
                           "INTELLIGENT_TIERING": 0.025, "GLACIER_IR": 0.005,
                           "GLACIER": 0.005, "DEEP_ARCHIVE": 0.002},
        "retrieval_per_gb": {"STANDARD": 0.0, "STANDARD_IA": 0.01, "ONEZONE_IA": 0.01,
                             "GLACIER_IR": 0.03, "GLACIER": 0.03, "DEEP_ARCHIVE": 0.02},
        "transfer_per_gb": {"to_internet": 0.12, "cross_region": 0.02},
    },
    "ap-northeast-1": {
        "storage_per_gb": {"STANDARD": 0.025, "STANDARD_IA": 0.019, "ONEZONE_IA": 0.0152,
                           "INTELLIGENT_TIERING": 0.025, "GLACIER_IR": 0.005,
                           "GLACIER": 0.005, "DEEP_ARCHIVE": 0.002},
        "retrieval_per_gb": {"STANDARD": 0.0, "STANDARD_IA": 0.01, "ONEZONE_IA": 0.01,
                             "GLACIER_IR": 0.03, "GLACIER": 0.03, "DEEP_ARCHIVE": 0.02},
        "transfer_per_gb": {"to_internet": 0.114, "cross_region": 0.02},
    },
}


class PricingEngine:
    """Fetches and manages S3 pricing data.

    Tries live APIs first, falls back to configurable local rates.
    """

    def __init__(self, s3_client=None):
        self.s3_client = s3_client
        self._rates = self._load_local_rates()
        self._actual_cost_data = None  # From Cost Explorer

    def _load_local_rates(self) -> dict:
        """Load rates from local file, or use defaults."""
        if os.path.exists(PRICING_FILE):
            try:
                with open(PRICING_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return DEFAULT_RATES.copy()

    def save_rates(self):
        """Save current rates to local file."""
        try:
            with open(PRICING_FILE, "w", encoding="utf-8") as f:
                json.dump(self._rates, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save pricing: {e}")

    def fetch_actual_costs(self, session) -> dict:
        """Fetch actual S3 costs from AWS Cost Explorer API.

        Returns dict with daily/monthly actual spend.
        Requires: ce:GetCostAndUsage permission.
        """
        if session is None:
            logger.warning("No session provided for Cost Explorer")
            return None

        try:
            ce_client = session.client("ce", region_name="us-east-1")  # CE is global

            # Last 30 days
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

            response = ce_client.get_cost_and_usage(
                TimePeriod={"Start": start_date, "End": end_date},
                Granularity="MONTHLY",
                Metrics=["UnblendedCost"],
                Filter={
                    "Dimensions": {
                        "Key": "SERVICE",
                        "Values": ["Amazon Simple Storage Service"]
                    }
                }
            )

            results = response.get("ResultsByTime", [])
            if results:
                amount = float(results[-1]["Total"]["UnblendedCost"]["Amount"])
                currency = results[-1]["Total"]["UnblendedCost"]["Unit"]
                self._actual_cost_data = {
                    "monthly_cost": amount,
                    "currency": currency,
                    "period_start": start_date,
                    "period_end": end_date,
                    "source": "AWS Cost Explorer (actual billing)",
                }
                return self._actual_cost_data

        except Exception as e:
            logger.info(f"Cost Explorer not available: {e}")
            # This is expected if user doesn't have ce: permissions

        return None

    def fetch_s3_metrics(self, session, bucket: str) -> dict:
        """Fetch S3 bucket metrics from CloudWatch for size/count.

        Returns actual BucketSizeBytes and NumberOfObjects.
        """
        if session is None:
            logger.warning("No session provided for CloudWatch metrics")
            return None

        try:
            cw_client = session.client("cloudwatch")

            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=2)

            # Get bucket size
            size_response = cw_client.get_metric_statistics(
                Namespace="AWS/S3",
                MetricName="BucketSizeBytes",
                Dimensions=[
                    {"Name": "BucketName", "Value": bucket},
                    {"Name": "StorageType", "Value": "StandardStorage"},
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=86400,
                Statistics=["Average"],
            )

            # Get object count
            count_response = cw_client.get_metric_statistics(
                Namespace="AWS/S3",
                MetricName="NumberOfObjects",
                Dimensions=[
                    {"Name": "BucketName", "Value": bucket},
                    {"Name": "StorageType", "Value": "AllStorageTypes"},
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=86400,
                Statistics=["Average"],
            )

            result = {}
            if size_response["Datapoints"]:
                sorted_size = sorted(size_response["Datapoints"], key=lambda x: x["Timestamp"])
                result["bucket_size_bytes"] = int(sorted_size[-1]["Average"])
            if count_response["Datapoints"]:
                sorted_count = sorted(count_response["Datapoints"], key=lambda x: x["Timestamp"])
                result["object_count"] = int(sorted_count[-1]["Average"])

            return result if result else None

        except Exception as e:
            logger.debug(f"CloudWatch metrics not available: {e}")
            return None

    def get_storage_rate(self, region: str, storage_class: str) -> float:
        """Get storage cost per GB/month for a region and class."""
        region_data = self._rates.get(region, self._rates.get("us-east-1", {}))
        if isinstance(region_data, dict) and "storage_per_gb" in region_data:
            return region_data["storage_per_gb"].get(storage_class, 0.023)
        return 0.023

    def get_retrieval_rate(self, region: str, storage_class: str) -> float:
        """Get retrieval cost per GB for a region and class."""
        region_data = self._rates.get(region, self._rates.get("us-east-1", {}))
        if isinstance(region_data, dict) and "retrieval_per_gb" in region_data:
            return region_data["retrieval_per_gb"].get(storage_class, 0.0)
        return 0.0

    def get_transfer_rate(self, region: str, transfer_type: str = "to_internet") -> float:
        """Get data transfer cost per GB."""
        region_data = self._rates.get(region, self._rates.get("us-east-1", {}))
        if isinstance(region_data, dict) and "transfer_per_gb" in region_data:
            return region_data["transfer_per_gb"].get(transfer_type, 0.09)
        return 0.09

    def estimate_monthly_cost(self, objects: list, region: str) -> dict:
        """Estimate monthly cost using configured rates for the specific region.

        Returns: {total, breakdown_by_class, source}
        """
        breakdown = {}
        total = 0.0

        for obj in objects:
            sc = obj.storage_class
            rate = self.get_storage_rate(region, sc)
            cost = (obj.size / (1024**3)) * rate

            if sc not in breakdown:
                breakdown[sc] = {"count": 0, "size": 0, "cost": 0.0, "rate": rate}
            breakdown[sc]["count"] += 1
            breakdown[sc]["size"] += obj.size
            breakdown[sc]["cost"] += cost
            total += cost

        source = "Local rates"
        if self._actual_cost_data:
            source = f"AWS Cost Explorer (actual: ${self._actual_cost_data['monthly_cost']:.2f}/mo total S3)"

        return {
            "total": total,
            "breakdown": breakdown,
            "source": source,
            "region": region,
            "rates_last_updated": self._rates.get("_last_updated", "Unknown"),
        }

    def get_all_region_rates(self) -> dict:
        """Get all configured region rates."""
        return {k: v for k, v in self._rates.items() if not k.startswith("_")}

    @property
    def actual_cost(self) -> dict:
        """Return actual cost data if fetched from Cost Explorer."""
        return self._actual_cost_data

    @property
    def rates_source(self) -> str:
        """Describe where rates come from."""
        if self._actual_cost_data:
            return "AWS Cost Explorer (actual billing)"
        if os.path.exists(PRICING_FILE):
            return f"Local file ({PRICING_FILE})"
        return "Default estimates (editable in s3_pricing.json)"
