"""File storage provider abstraction - the same "clean interface + mock/
real provider" pattern as `trustbuy_agent_sdk.llm` (DECISIONS.md ADR-010),
applied to report-attachment uploads (invoices, delivery photos, refund
screenshots - docs/USER_FLOWS.md §5).

`LocalDiskStorageProvider` is real and fully working - not a stub - and is
what actually runs in this environment (no AWS credentials configured).
`S3StorageProvider` activates automatically once AWS credentials +
TRUSTBUY_S3_BUCKET are set, with zero code changes anywhere that calls
`get_storage_provider()`.
"""

from __future__ import annotations

import os
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Protocol

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


class UploadRejectedError(Exception):
    """Raised for a disallowed content type or oversized upload -
    docs/SECURITY.md §4 file-upload allowlist."""


class StorageProvider(Protocol):
    name: str

    def save(self, *, content: bytes, content_type: str, suggested_kind: str) -> str:
        """Persist `content`, return an opaque storage key."""
        ...

    def url_for(self, storage_key: str) -> str:
        """Return a URL (or path) the current deployment can serve this key from."""
        ...


def _validate(content: bytes, content_type: str) -> None:
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise UploadRejectedError(f"Unsupported content type: {content_type}")
    if len(content) > MAX_UPLOAD_BYTES:
        raise UploadRejectedError("File exceeds the 10 MB upload limit.")


class LocalDiskStorageProvider:
    """Dev/self-hosted default - writes to a local directory (a Docker
    volume in docker-compose). Real and fully functional, not a stub."""

    name = "local_disk"

    def __init__(self, base_dir: str, public_base_url: str) -> None:
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._public_base_url = public_base_url.rstrip("/")

    def save(self, *, content: bytes, content_type: str, suggested_kind: str) -> str:
        _validate(content, content_type)
        extension = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "application/pdf": ".pdf"}.get(
            content_type, ""
        )
        key = f"{suggested_kind}/{uuid.uuid4().hex}{extension}"
        target = self._base_dir / key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return key

    def url_for(self, storage_key: str) -> str:
        return f"{self._public_base_url}/{storage_key}"


class S3StorageProvider:
    """Real implementation using boto3, imported lazily so it's never a
    hard dependency for deployments that only ever use local disk."""

    name = "s3"

    def __init__(self, bucket: str, region: str | None = None) -> None:
        self._bucket = bucket
        self._region = region
        self._client = None

    def _get_client(self):
        if self._client is None:
            import boto3

            self._client = boto3.client("s3", region_name=self._region)
        return self._client

    def save(self, *, content: bytes, content_type: str, suggested_kind: str) -> str:
        _validate(content, content_type)
        extension = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "application/pdf": ".pdf"}.get(
            content_type, ""
        )
        key = f"{suggested_kind}/{uuid.uuid4().hex}{extension}"
        self._get_client().put_object(Bucket=self._bucket, Key=key, Body=content, ContentType=content_type)
        return key

    def url_for(self, storage_key: str) -> str:
        region_segment = f".{self._region}" if self._region else ""
        return f"https://{self._bucket}.s3{region_segment}.amazonaws.com/{storage_key}"


@lru_cache
def get_storage_provider() -> StorageProvider:
    bucket = os.environ.get("TRUSTBUY_S3_BUCKET")
    if bucket:
        return S3StorageProvider(bucket=bucket, region=os.environ.get("AWS_REGION"))

    base_dir = os.environ.get("TRUSTBUY_LOCAL_STORAGE_DIR", "/data/uploads")
    public_base_url = os.environ.get("TRUSTBUY_LOCAL_STORAGE_PUBLIC_URL", "/uploads")
    return LocalDiskStorageProvider(base_dir=base_dir, public_base_url=public_base_url)
