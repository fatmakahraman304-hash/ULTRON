"""Narrow allowlist for owner-requested Image Studio downloads in Qt."""

import re
from urllib.parse import urlsplit


def generated_image_filename(address: str, mime: str, local_origin: str) -> str | None:
    target, origin = urlsplit(address), urlsplit(local_origin)
    suffix = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}.get(mime)
    if (
        not suffix
        or origin.scheme not in {"http", "https"}
        or target.scheme != origin.scheme
        or target.netloc != origin.netloc
        or target.username
        or target.password
        or target.query
        or target.fragment
    ):
        return None
    match = re.fullmatch(
        r"/api/merged/image-studio/generated/([1-9][0-9]{0,18})", target.path
    )
    return f"golge-gorsel-{match[1]}.{suffix}" if match else None
