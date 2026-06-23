"""Reverse geocode lookup — maps cell_id to street/locality names."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CellLocation:
    road: str
    locality: str
    area: str
    display_name: str


_lookup: dict[str, CellLocation] = {}


def _build_display_name(road: str, locality: str) -> str:
    has_road = road and road != "Unnamed Road"
    has_locality = bool(locality)
    if has_road and has_locality:
        return f"{road}, {locality}"
    if has_road:
        return road
    if has_locality:
        return locality
    return ""


def load(path: str | Path) -> int:
    """Load reverse geocode JSON into memory. Returns count of cells loaded."""
    global _lookup
    p = Path(path)
    if not p.exists():
        logger.warning("Geocode data not found at %s", p)
        return 0
    try:
        raw: dict[str, dict] = json.loads(p.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Failed to load geocode data: %s", exc)
        return 0

    _lookup = {}
    for cell_id, info in raw.items():
        road = info.get("road", "")
        locality = info.get("locality", "")
        area = info.get("area", "")
        display = _build_display_name(road, locality)
        if display:
            _lookup[cell_id] = CellLocation(
                road=road, locality=locality, area=area, display_name=display,
            )
    logger.info("Geocode lookup loaded: %d cells with names", len(_lookup))
    return len(_lookup)


def resolve(cell_id: str) -> CellLocation | None:
    return _lookup.get(cell_id)


def resolve_display_name(cell_id: str) -> str | None:
    loc = _lookup.get(cell_id)
    return loc.display_name if loc else None


def resolve_bulk(cell_ids: list[str]) -> dict[str, CellLocation]:
    return {cid: _lookup[cid] for cid in cell_ids if cid in _lookup}


def all_locations() -> dict[str, CellLocation]:
    return _lookup
