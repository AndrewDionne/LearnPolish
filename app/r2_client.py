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
R2_ACCESS_KEY_ID = _env("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = _env("R2_SECRET_ACCESS_KEY")
R2_REGION = _env("R2_REGION", "auto")  # R2 ignores region, but boto3 wants something
R2_CDN_BASE = _env("R2_CDN_BASE")  # can be your *.r2.dev or CDN domain

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
    key: Union[str, Path],
    body: Union[bytes, Path],
    *,
    content_type: Optional[str] = None,
    cache_control: Optional[str] = None,
) -> Optional[str]:
    """
    Upload one object to R2. Returns a public CDN URL (if known) or None.
    """
    if not enabled or not _client:
        return None

    key_str = str(key)
    data = body.read_bytes() if isinstance(body, Path) else body

    put_kwargs = {
        "Bucket": R2_BUCKET,
        "Key": key_str,
        "Body": data,
    }
    if content_type:
        put_kwargs["ContentType"] = content_type
    if cache_control:
        put_kwargs["CacheControl"] = cache_control

    _client.put_object(**put_kwargs)

    # Build a public URL.
    try:
        from .utils import asset_url  # optional helper if present
        return asset_url(key_str)
    except Exception:
        return f"{R2_CDN_BASE.rstrip('/')}/{key_str.lstrip('/')}" if R2_CDN_BASE else None
