"""Large File Operations — handles files of ANY size (up to 5 TB).

Provides multipart copy, multipart upload, and chunked download
that works regardless of file size.

Limits:
- copy_object: max 5 GB (single part)
- multipart copy: up to 5 TB (using copy_part)
- upload_file: handled by boto3 TransferConfig automatically
- download: handled by range-based chunking
"""
import os
import logging
import threading
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# 5 GB threshold for multipart copy
MULTIPART_COPY_THRESHOLD = 5 * 1024 * 1024 * 1024  # 5 GB
COPY_PART_SIZE = 500 * 1024 * 1024  # 500 MB per part (default)
MAX_PARTS = 9999  # S3 limit is 10,000 parts


def copy_object_any_size(s3_client, source_bucket: str, source_key: str,
                          dest_bucket: str, dest_key: str,
                          source_size: int = None,
                          progress_callback: Callable = None) -> bool:
    """Copy an S3 object of ANY size between buckets.

    Uses single copy for <5GB, multipart copy for >=5GB.

    Args:
        s3_client: boto3 S3 client
        source_bucket: Source bucket name
        source_key: Source object key
        dest_bucket: Destination bucket name
        dest_key: Destination object key
        source_size: Object size in bytes (if known, avoids HEAD call)
        progress_callback: Called with (bytes_copied, total_bytes)

    Returns:
        True on success, raises exception on failure
    """
    # Get size if not provided
    if source_size is None:
        resp = s3_client.head_object(Bucket=source_bucket, Key=source_key)
        source_size = resp["ContentLength"]

    if source_size < MULTIPART_COPY_THRESHOLD:
        # Simple copy — under 5 GB
        s3_client.copy_object(
            Bucket=dest_bucket,
            Key=dest_key,
            CopySource={"Bucket": source_bucket, "Key": source_key},
        )
        if progress_callback:
            progress_callback(source_size, source_size)
        return True
    else:
        # Multipart copy — 5 GB or larger
        return _multipart_copy(s3_client, source_bucket, source_key,
                               dest_bucket, dest_key, source_size,
                               progress_callback)


def _multipart_copy(s3_client, source_bucket: str, source_key: str,
                    dest_bucket: str, dest_key: str,
                    total_size: int, progress_callback: Callable = None) -> bool:
    """Perform multipart copy for large objects (>5 GB)."""
    logger.info(f"Starting multipart copy: {source_key} ({total_size} bytes)")

    # Dynamically calculate part size to stay within 10,000 parts limit
    part_size = COPY_PART_SIZE
    num_parts = (total_size + part_size - 1) // part_size
    if num_parts > MAX_PARTS:
        # Increase part size to fit within limit
        part_size = (total_size + MAX_PARTS - 1) // MAX_PARTS
        # Round up to nearest MB
        part_size = ((part_size + 1024 * 1024 - 1) // (1024 * 1024)) * (1024 * 1024)

    # Initiate multipart upload
    mpu = s3_client.create_multipart_upload(Bucket=dest_bucket, Key=dest_key)
    upload_id = mpu["UploadId"]

    try:
        parts = []
        part_number = 1
        bytes_copied = 0

        while bytes_copied < total_size:
            # Calculate byte range for this part
            start = bytes_copied
            end = min(bytes_copied + part_size - 1, total_size - 1)
            part_range_size = end - start + 1

            # Copy this part
            response = s3_client.upload_part_copy(
                Bucket=dest_bucket,
                Key=dest_key,
                UploadId=upload_id,
                PartNumber=part_number,
                CopySource={"Bucket": source_bucket, "Key": source_key},
                CopySourceRange=f"bytes={start}-{end}",
            )

            # Store the ETag for completion
            etag = response["CopyPartResult"]["ETag"]
            parts.append({"PartNumber": part_number, "ETag": etag})

            bytes_copied += part_range_size
            part_number += 1

            if progress_callback:
                progress_callback(bytes_copied, total_size)

            logger.debug(f"  Part {part_number - 1}: {start}-{end} ({part_range_size} bytes)")

        # Complete the multipart upload
        s3_client.complete_multipart_upload(
            Bucket=dest_bucket,
            Key=dest_key,
            UploadId=upload_id,
            MultipartUpload={"Parts": parts},
        )

        logger.info(f"Multipart copy complete: {dest_key} ({len(parts)} parts)")
        return True

    except Exception as e:
        # Abort the multipart upload on failure
        logger.error(f"Multipart copy failed, aborting: {e}")
        try:
            s3_client.abort_multipart_upload(
                Bucket=dest_bucket, Key=dest_key, UploadId=upload_id
            )
        except Exception:
            pass
        raise


def move_object_any_size(s3_client, source_bucket: str, source_key: str,
                          dest_bucket: str, dest_key: str,
                          source_size: int = None,
                          progress_callback: Callable = None) -> bool:
    """Move (copy + delete) an S3 object of ANY size.

    Args: Same as copy_object_any_size
    Returns: True on success
    """
    # Copy first
    copy_object_any_size(s3_client, source_bucket, source_key,
                         dest_bucket, dest_key, source_size, progress_callback)

    # Delete source only after successful copy
    s3_client.delete_object(Bucket=source_bucket, Key=source_key)
    return True


def upload_file_any_size(s3_client, local_path: str, bucket: str, key: str,
                          storage_class: str = "STANDARD",
                          progress_callback: Callable = None) -> bool:
    """Upload a local file of ANY size to S3.

    Uses boto3's managed transfer which automatically handles multipart.

    Args:
        s3_client: boto3 S3 client
        local_path: Local file path
        bucket: Target bucket
        key: Target S3 key
        storage_class: Storage class to use
        progress_callback: Called with (bytes_uploaded, total_bytes)
    """
    from boto3.s3.transfer import TransferConfig

    file_size = os.path.getsize(local_path)

    # Configure multipart: 50MB chunks, up to 10 concurrent parts
    config = TransferConfig(
        multipart_threshold=50 * 1024 * 1024,  # 50 MB
        multipart_chunksize=50 * 1024 * 1024,
        max_concurrency=10,
        use_threads=True,
    )

    extra_args = {"StorageClass": storage_class}

    # Progress tracking
    uploaded = [0]

    def callback(bytes_amount):
        uploaded[0] += bytes_amount
        if progress_callback:
            progress_callback(uploaded[0], file_size)

    s3_client.upload_file(
        local_path, bucket, key,
        Config=config,
        ExtraArgs=extra_args,
        Callback=callback,
    )
    return True


def download_file_any_size(s3_client, bucket: str, key: str, local_path: str,
                            progress_callback: Callable = None,
                            cancel_event: threading.Event = None) -> bool:
    """Download an S3 object of ANY size to local file.

    Uses range-based chunked download with resume support.

    Args:
        s3_client: boto3 S3 client
        bucket: Source bucket
        key: Source key
        local_path: Local destination path
        progress_callback: Called with (bytes_downloaded, total_bytes)
        cancel_event: Set this to cancel the download
    """
    CHUNK = 8 * 1024 * 1024  # 8 MB chunks

    # Get total size
    resp = s3_client.head_object(Bucket=bucket, Key=key)
    total_size = resp["ContentLength"]

    # Resume support
    downloaded = 0
    mode = "wb"
    if os.path.exists(local_path):
        existing = os.path.getsize(local_path)
        if existing == total_size:
            if progress_callback:
                progress_callback(total_size, total_size)
            return True  # Already complete
        elif existing < total_size:
            downloaded = existing
            mode = "ab"

    # Download with range header
    get_kwargs = {"Bucket": bucket, "Key": key}
    if downloaded > 0:
        get_kwargs["Range"] = f"bytes={downloaded}-"

    response = s3_client.get_object(**get_kwargs)
    body = response["Body"]

    try:
        with open(local_path, mode) as f:
            while True:
                if cancel_event and cancel_event.is_set():
                    return False

                chunk = body.read(CHUNK)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)

                if progress_callback:
                    progress_callback(downloaded, total_size)
    finally:
        body.close()

    return True
