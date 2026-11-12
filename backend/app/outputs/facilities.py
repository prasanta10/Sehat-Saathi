"""Facility directory (knowledge/facilities/<STATE>.csv). Until official data is loaded the plan
shows the facility *level* only. Never presents opening hours or beds the data does not have."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

LEVEL_ORDER = ["SC_HWC", "PHC", "CHC", "SDH", "DH", "MEDICAL_COLLEGE"]
COLUMNS = ["name", "level", "district", "block", "lat", "lon", "source", "as_of"]


@dataclass(frozen=True)
class Facility:
    name: str
    level: str
    district: str
    block: str
    lat: float | None
    lon: float | None
    source: str
    as_of: str


def load_facilities(root: Path, state: str | None) -> list[Facility]:
    if not state:
        return []
    path = root / "knowledge" / "facilities" / f"{state}.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        if r["level"] not in LEVEL_ORDER or not r.get("source") or not r.get("as_of"):
            continue  # unsourced rows are never shown
        out.append(
            Facility(
                name=r["name"],
                level=r["level"],
                district=r["district"],
                block=r.get("block", ""),
                lat=float(r["lat"]) if r.get("lat") else None,
                lon=float(r["lon"]) if r.get("lon") else None,
                source=r["source"],
                as_of=r["as_of"],
            )
        )
    return out


def _km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 6371 * 2 * math.asin(math.sqrt(h))


def suggest(
    facilities: list[Facility],
    min_level: str,
    district: str | None,
    near: tuple[float, float] | None = None,
    limit: int = 3,
) -> list[Facility]:
    """Facilities at or above ``min_level`` in the district; nearest first if location known."""
    floor = LEVEL_ORDER.index(min_level)
    ok = [
        f
        for f in facilities
        if LEVEL_ORDER.index(f.level) >= floor and (not district or f.district == district)
    ]
    if near:
        located = [f for f in ok if f.lat is not None and f.lon is not None]
        located.sort(key=lambda f: _km(near, (f.lat, f.lon)))  # type: ignore[arg-type]
        return located[:limit]
    return sorted(ok, key=lambda f: (LEVEL_ORDER.index(f.level), f.name))[:limit]
