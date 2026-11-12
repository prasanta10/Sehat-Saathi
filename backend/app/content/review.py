"""Review-status helpers. A reviewed file records the hash of what was reviewed."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def content_hash(data: dict[str, Any]) -> str:
    """Hash of a content file's data excluding its ``review`` block."""
    body = {k: v for k, v in data.items() if k != "review"}
    canonical = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
