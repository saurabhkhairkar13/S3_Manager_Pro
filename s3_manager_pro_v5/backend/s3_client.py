"""S3 Client — all AWS S3 API operations."""
import logging
from typing import Optional
from dataclasses import dataclass, field

import boto3
from botocore.exceptions import ClientError, NoCredentialsError, ProfileNotFound
from botocore.config import Config as BotoConfig

from s3_manager_pro_v5.utils.constants import NON_GLACIER_CLASSES, PAGE_SIZE

logger = logging.getLogger(__name__)


@dataclass
class S3Object:
    """Represents an S3 object."""
    key: str
    size: int
    storage_class: str
    last_modified: str
    etag: str = ""
    is_folder: bool = False


@dataclass
class ListResult:
    """Result from listing objects — supports pagination."""
    objects: list = field(default_factory=list)
    folders: list = field(default_factory=list)
    is_truncated: bool = False
    continuation_token: str = ""
    total_size: int = 0


class S3Client:
    """Handles all S3 operations with connection management."""

    def __init__(self, region: str, profile: str = None,
                 access_key: str = None, secret_key: str = None):
        self.region = region
        self.profile = profile
        self.access_key = access_key
        self.secret_key = secret_key
        self.s3_client = None
        self.session = None
        self.account_id = ""
        self.user_name = ""
        self._connected = False

    def connect(self) -> tuple:
        """Establish connection. Returns (success, message)."""
        try:
            session_kwargs = {"region_name": self.region}

            if self.access_key and self.secret_key:
                session_kwargs["aws_access_key_id"] = self.access_key
                session_kwargs["aws_secret_access_key"] = self.secret_key
            elif self.profile:
                session_kwargs["profile_name"] = self.profile

            self.session = boto3.Session(**session_kwargs)

            # Validate with STS
            sts = self.session.client("sts")
            identity = sts.get_caller_identity()
            self.account_id = identity.get("Account", "Unknown")
            arn = identity.get("Arn", "")
            self.user_name = arn.split("/")[-1] if "/" in arn else arn

            # Create S3 client
            boto_config = BotoConfig(
                retries={"max_attempts": 3, "mode": "adaptive"},
                max_pool_connections=20,
            )
            self.s3_client = self.session.client("s3", config=boto_config)
            self._connected = True

            return True, f"Connected: {self.account_id} | {self.user_name}"

        except ProfileNotFound:
            return False, f"Profile '{self.profile}' not found."
        except NoCredentialsError:
            return False, "Invalid or missing credentials."
        except ClientError as e:
            return False, f"AWS Error: {e.response['Error']['Message']}"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def connection_info(self) -> str:
        if self._connected:
            return f"{self.account_id} | {self.user_name}"
        return "Not connected"

    def list_buckets(self) -> list:
        """List all buckets. Returns list of bucket names."""
        if not self._connected:
            return []
        try:
            response = self.s3_client.list_buckets()
            return sorted([b["Name"] for b in response.get("Buckets", [])])
        except Exception as e:
            logger.error(f"Failed to list buckets: {e}")
            return []

    def list_objects_page(self, bucket: str, prefix: str = "",
                          delimiter: str = "/",
                          continuation_token: str = "",
                          max_keys: int = PAGE_SIZE) -> ListResult:
        """List one page of objects (folder-level navigation)."""
        result = ListResult()
        try:
            kwargs = {
                "Bucket": bucket,
                "MaxKeys": max_keys,
            }
            if prefix:
                kwargs["Prefix"] = prefix
            if delimiter:
                kwargs["Delimiter"] = delimiter
            if continuation_token:
                kwargs["ContinuationToken"] = continuation_token

            response = self.s3_client.list_objects_v2(**kwargs)

            # Folders (common prefixes)
            for cp in response.get("CommonPrefixes", []):
                folder_path = cp["Prefix"]
                result.folders.append(S3Object(
                    key=folder_path,
                    size=0,
                    storage_class="",
                    last_modified="",
                    is_folder=True,
                ))

            # Files
            for obj in response.get("Contents", []):
                key = obj["Key"]
                # Skip the prefix itself if it appears as an object
                if key == prefix:
                    continue
                if key.endswith("/") and obj["Size"] == 0:
                    continue
                result.objects.append(S3Object(
                    key=key,
                    size=obj["Size"],
                    storage_class=obj.get("StorageClass", "STANDARD"),
                    last_modified=obj["LastModified"].strftime("%Y-%m-%d %H:%M"),
                    etag=obj.get("ETag", "").strip('"'),
                ))
                result.total_size += obj["Size"]

            result.is_truncated = response.get("IsTruncated", False)
            result.continuation_token = response.get("NextContinuationToken", "")

        except Exception as e:
            logger.error(f"List objects failed: {e}")

        return result

    def list_all_objects(self, bucket: str, prefix: str = "") -> list:
        """List ALL objects under a prefix (no delimiter — flat listing)."""
        objects = []
        try:
            paginator = self.s3_client.get_paginator("list_objects_v2")
            kwargs = {"Bucket": bucket}
            if prefix:
                kwargs["Prefix"] = prefix

            for page in paginator.paginate(**kwargs):
                for obj in page.get("Contents", []):
                    if obj["Key"].endswith("/") and obj["Size"] == 0:
                        continue
                    objects.append(S3Object(
                        key=obj["Key"],
                        size=obj["Size"],
                        storage_class=obj.get("StorageClass", "STANDARD"),
                        last_modified=obj["LastModified"].strftime("%Y-%m-%d %H:%M"),
                        etag=obj.get("ETag", "").strip('"'),
                    ))
        except Exception as e:
            logger.error(f"List all objects failed: {e}")
        return objects

    def get_restore_status(self, bucket: str, key: str, storage_class: str) -> str:
        """Get restore status for a Glacier object."""
        if storage_class in NON_GLACIER_CLASSES:
            return "Ready"
        try:
            resp = self.s3_client.head_object(Bucket=bucket, Key=key)
            restore = resp.get("Restore", "")
            if not restore:
                return "Frozen"
            elif 'ongoing-request="true"' in restore:
                return "Restoring"
            elif 'ongoing-request="false"' in restore:
                return "Ready"
            return "Unknown"
        except ClientError:
            return "Error"

    def request_restore(self, bucket: str, key: str, tier: str = "Standard", days: int = 7):
        """Request Glacier restore for an object. Raises ClientError on failure."""
        try:
            self.s3_client.restore_object(
                Bucket=bucket,
                Key=key,
                RestoreRequest={
                    "Days": days,
                    "GlacierJobParameters": {"Tier": tier},
                },
            )
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "RestoreAlreadyInProgress":
                logger.info(f"Restore already in progress for {key}")
            else:
                logger.error(f"Restore request failed for {key}: {e}")
                raise

    def generate_presigned_url(self, bucket: str, key: str, expires_in: int = 3600) -> str:
        """Generate a presigned URL for an object."""
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=expires_in,
            )
            return url
        except Exception as e:
            logger.error(f"Presigned URL generation failed: {e}")
            return ""

    def head_object(self, bucket: str, key: str) -> dict:
        """Get object metadata."""
        try:
            return self.s3_client.head_object(Bucket=bucket, Key=key)
        except Exception as e:
            logger.error(f"Head object failed: {e}")
            return {}

    def delete_objects(self, bucket: str, keys: list) -> tuple:
        """Delete multiple objects. Returns (success_count, error_count)."""
        if not keys:
            return 0, 0
        try:
            delete_objects = [{"Key": k} for k in keys]
            # S3 delete_objects max 1000 at a time
            success = 0
            errors = 0
            for i in range(0, len(delete_objects), 1000):
                batch = delete_objects[i:i + 1000]
                response = self.s3_client.delete_objects(
                    Bucket=bucket,
                    Delete={"Objects": batch, "Quiet": False},
                )
                success += len(response.get("Deleted", []))
                errors += len(response.get("Errors", []))
            return success, errors
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return 0, len(keys)

    def get_bucket_size_info(self, bucket: str, prefix: str = "") -> dict:
        """Get quick stats about a bucket/prefix."""
        stats = {"total_objects": 0, "total_size": 0, "by_class": {}}
        try:
            paginator = self.s3_client.get_paginator("list_objects_v2")
            kwargs = {"Bucket": bucket}
            if prefix:
                kwargs["Prefix"] = prefix

            for page in paginator.paginate(**kwargs):
                for obj in page.get("Contents", []):
                    if obj["Key"].endswith("/") and obj["Size"] == 0:
                        continue
                    stats["total_objects"] += 1
                    stats["total_size"] += obj["Size"]
                    sc = obj.get("StorageClass", "STANDARD")
                    stats["by_class"][sc] = stats["by_class"].get(sc, 0) + 1
        except Exception as e:
            logger.error(f"Bucket stats failed: {e}")
        return stats
