"""Object storage for clips and postcard images, behind one interface.

The default keeps files in a directory. The S3 implementation covers any
S3-compatible store (AWS, R2, MinIO) and needs `pip install boto3`.
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Any, Protocol

_KEY = re.compile(r"^[a-z0-9][a-z0-9_\-/]*\.[a-z0-9]+$")


class BlobStore(Protocol):
    def put(self, key: str, data: bytes, content_type: str) -> None: ...
    def get(self, key: str) -> bytes: ...
    def exists(self, key: str) -> bool: ...
    def delete(self, key: str) -> None: ...
    def public_url(self, key: str) -> str | None:
        """A URL browsers can fetch directly, or None when the API should serve the bytes."""
        ...


def check_key(key: str) -> str:
    if not _KEY.match(key) or ".." in key or "//" in key:
        raise ValueError(f"invalid storage key: {key!r}")
    return key


class LocalDirStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self.root / check_key(key)

    def put(self, key: str, data: bytes, content_type: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Write next to the target and rename, so a reader never sees half a file.
        handle, temp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
        try:
            with os.fdopen(handle, "wb") as out:
                out.write(data)
            os.replace(temp, path)
        except BaseException:
            Path(temp).unlink(missing_ok=True)
            raise

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def public_url(self, key: str) -> str | None:
        return None


class S3Store:
    """S3-compatible storage. Written against the boto3 API and not run against a real bucket."""

    def __init__(
        self,
        *,
        bucket: str,
        endpoint_url: str = "",
        region: str = "auto",
        access_key_id: str = "",
        secret_access_key: str = "",
        public_base_url: str = "",
        client: Any | None = None,
    ) -> None:
        if not bucket:
            raise ValueError("S3_BUCKET is required when STORAGE_BACKEND=s3")
        self._bucket = bucket
        self._public_base_url = public_base_url.rstrip("/")
        if client is None:
            import boto3  # type: ignore[import-not-found]

            client = boto3.client(
                "s3",
                endpoint_url=endpoint_url or None,
                region_name=region,
                aws_access_key_id=access_key_id or None,
                aws_secret_access_key=secret_access_key or None,
            )
        self._client = client

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self._client.put_object(Bucket=self._bucket, Key=check_key(key), Body=data, ContentType=content_type)

    def get(self, key: str) -> bytes:
        body: bytes = self._client.get_object(Bucket=self._bucket, Key=check_key(key))["Body"].read()
        return body

    def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self._bucket, Key=check_key(key))
        except Exception:
            return False
        return True

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=check_key(key))

    def public_url(self, key: str) -> str | None:
        if not self._public_base_url:
            return None
        return f"{self._public_base_url}/{check_key(key)}"
