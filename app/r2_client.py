# app/r2_client.py
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Union

try:
    import boto3  # type: ignore
except Exception:
    boto3 = None  # uploading is disabled if boto3 isn't available


def _env(name: str, default: str | None = None) -> Optional[str]:
    v = os.getenv(name)
    return v if (v and v.strip()) else default


# ---- Canonical env (aliases already bridged in __init__.py) ----
R2_ENDPOINT = _env("R2_ENDPOINT")
R2_BUCKET = _env("R2_BUCKET")
R2_ACCESS_KEY_ID = _env("R2_ACCESS_KEY_ID") or _env("R2_ACCESS_KEY")
R2_SECRET_ACCESS_KEY = _env("R2_SECRET_ACCESS_KEY") or _env("R2_SECRET_KEY")
R2_REGION = _env("R2_REGION", "auto")  # R2 ignores region, but boto3 wants something
R2_CDN_BASE = _env("R2_CDN_BASE") or _env("R2_PUBLIC_BASE") # can be your *.r2.dev or CDN domain

_enabled = bool(
    boto3
    and R2_ENDPOINT
    and R2_BUCKET
    and R2_ACCESS_KEY_ID
    and R2_SECRET_ACCESS_KEY
)
enabled: bool = _enabled

_client = None
if enabled:
    _client = boto3.client(
        "s3",
        region_name=R2_REGION,
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    )


def put_file(
    a: Union[str, Path],
    b: Union[bytes, Path, str],
    *,
    content_type: Optional[str] = None,
    cache_control: Optional[str] = None,
) -> Optional[str]:
    """
    Upload one object to R2. Supports both calling styles:

      put_file(local_path: Path, key: str)
      put_file(key: str, body: bytes|Path)

    Returns a public CDN URL (if known) or None.
    """
    if not enabled or not _client:
        return None

    # Normalize args (support both orders)
    key_str: str
    data: bytes

    if isinstance(a, Path) and isinstance(b, (str, Path)):
        # (local_path, key)
        local_path = a
        key_str = str(b)
        data = local_path.read_bytes()
    elif isinstance(a, str) and isinstance(b, (bytes, bytearray, Path)):
        # (key, body)  where body may be bytes or Path
        key_str = a
        data = b.read_bytes() if isinstance(b, Path) else (bytes(b) if isinstance(b, bytearray) else b)
    else:
        raise TypeError("put_file expects (Path, str) or (str, bytes|Path)")

    # Best-effort content type
    if not content_type:
        ext = key_str.lower().rsplit(".", 1)[-1] if "." in key_str else ""
        content_type = {
            "mp3": "audio/mpeg",
            "wav": "audio/wav",
            "mp4": "video/mp4",
            "json": "application/json",
            "js": "application/javascript",
            "css": "text/css",
            "html": "text/html",
            "txt": "text/plain",
            "svg": "image/svg+xml",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "webp": "image/webp",
        }.get(ext, "application/octet-stream")

    if not cache_control:
        cache_control = "public, max-age=31536000, immutable"

    put_kwargs = {
        "Bucket": R2_BUCKET,
        "Key": key_str,
        "Body": data,
        "ContentType": content_type,
        "CacheControl": cache_control,
    }

    _client.put_object(**put_kwargs)

    try:
        from .utils import asset_url
        return asset_url(key_str)
    except Exception:
        return f"{R2_CDN_BASE.rstrip('/')}/{key_str.lstrip('/')}" if R2_CDN_BASE else None
