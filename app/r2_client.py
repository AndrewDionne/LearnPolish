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


# ---- Config via env (works on local + Render/GitHub Actions) ----
R2_ENDPOINT = _env("R2_ENDPOINT") or _env("CLOUDFLARE_R2_ENDPOINT")
R2_BUCKET = _env("R2_BUCKET") or _env("CLOUDFLARE_R2_BUCKET")
R2_ACCESS_KEY_ID = _env("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = _env("R2_SECRET_ACCESS_KEY")
R2_REGION = _env("R2_REGION") or "auto"  # R2 ignores region, but boto3 wants something

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

    Parameters
    ----------
    key : str | Path
        The S3 key (object path) in the bucket. Will be coerced to str.
    body : bytes | Path
        Content to upload. If Path, the file is read to bytes.
    content_type : str | None
        Optional Content-Type header.
    cache_control : str | None
        Optional Cache-Control header.
    """
    if not enabled or not _client:
        return None

    key_str = str(key)  # <-- ensure Key is a STRING
    if isinstance(body, Path):
        data = body.read_bytes()
    else:
        data = body

    put_kwargs = {
        "Bucket": R2_BUCKET,
        "Key": key_str,
        "Body": data,
    }
    if content_type:
        put_kwargs["ContentType"] = content_type
    if cache_control:
        put_kwargs["CacheControl"] = cache_control

    # propagate exceptions so caller can log context
    _client.put_object(**put_kwargs)

    # Build a public URL.
    try:
        # Preferred path: your helper that reads Config.R2_CDN_BASE
        from .utils import asset_url
        return asset_url(key_str)
    except Exception:
        # Fallback to env if utils/Config isn't importable at this stage
        cdn_base = _env("R2_CDN_BASE") or _env("CLOUDFLARE_R2_PUBLIC_BASE") or ""
        return f"{cdn_base.rstrip('/')}/{key_str.lstrip('/')}" if cdn_base else None
