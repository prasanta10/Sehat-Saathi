"""Keyword search (SQLite FTS5) over the curated official excerpts for "tell me more".
Only verbatim excerpts with their source are returned; nothing is generated."""

from __future__ import annotations

import re
import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.content.yamlio import load_yaml


@lru_cache
def _index(root: Path) -> sqlite3.Connection:
    con = sqlite3.connect(":memory:", check_same_thread=False)
    con.execute("CREATE VIRTUAL TABLE excerpts USING fts5(ref, locator, text, kind UNINDEXED)")
    for p in sorted((root / "knowledge" / "references").glob("*.yaml")):
        r = load_yaml(p)
        for e in r["excerpts"]:
            con.execute(
                "INSERT INTO excerpts VALUES (?, ?, ?, ?)",
                (r["id"], e["locator"], e["text"], r["kind"]),
            )
    return con


def search(
    root: Path, query: str, kinds: tuple[str, ...] = ("scheme", "helpline"), limit: int = 5
) -> list[dict[str, Any]]:
    words = re.findall(r"\w+", query, flags=re.UNICODE)
    if not words:
        return []
    fts = " OR ".join(f'"{w}"' for w in words[:10])
    rows = _index(root).execute(
        "SELECT ref, locator, text, kind FROM excerpts "
        "WHERE excerpts MATCH ? ORDER BY rank LIMIT ?",
        (fts, limit * 3),
    )
    return [{"ref": r, "locator": loc, "text": t} for r, loc, t, k in rows if k in kinds][:limit]
