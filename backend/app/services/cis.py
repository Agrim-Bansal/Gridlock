"""Congestion Impact Score (CIS) provider — real formula with API/fallback data."""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

DEFAULT_TIME_SLOTS = ("06:00", "12:00", "18:00", "00:00")


def _time_slots() -> list[str]:
    return list(settings.cis_time_slots or DEFAULT_TIME_SLOTS)


def _fallback_dir() -> Path:
    return settings.data_dir / "cis_fallback"


def _load_fallback(cell_id: str) -> dict | None:
    """Load per-cell CIS data. Supports v2 (congestion_ratio) and legacy (slot scores)."""
    path = _fallback_dir() / f"{cell_id}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        if data.get("version") == 2:
            return data
        return {k: float(v) for k, v in data.items()}
    except (json.JSONDecodeError, TypeError, ValueError):
        logger.warning("Invalid CIS fallback for %s", cell_id)
        return None


def _synthetic_slot_scores(predicted_violations: int, cell_id: str) -> dict:
    """Generate deterministic placeholder scores when no real data available."""
    base = min(100.0, max(5.0, predicted_violations * 0.35))
    slots = _time_slots()
    scores: dict[str, float] = {}
    for i, slot in enumerate(slots):
        i_part, j_part = cell_id.split("_")
        jitter = (int(i_part) + int(j_part) + i * 7) % 15
        scores[slot] = round(min(100.0, base + jitter - 5), 1)
    return scores


def _fetch_cis_api(cell_id: str, predicted_violations: int) -> dict | None:
    """Placeholder for live CIS API integration."""
    if not settings.cis_api_key:
        return None
    logger.info("CIS API stub called for %s (violations=%d)", cell_id, predicted_violations)
    return None


def zone_data_for_cell(cell_id: str, predicted_violations: int) -> dict:
    """Return CIS zone data for a cell. Priority: API > file fallback > synthetic."""
    api_data = _fetch_cis_api(cell_id, predicted_violations)
    if api_data:
        return api_data

    fallback = _load_fallback(cell_id)
    if fallback:
        return fallback

    return _synthetic_slot_scores(predicted_violations, cell_id)


def compute_cis(
    cell_id: str,
    predicted_violations: int,
    zone_data_per_slot: dict | None = None,
) -> tuple[float, str]:
    """
    Return (cis_score, patrol_time).

    V2 format: applies real CIS formula → returns raw (unbounded) score.
    Legacy format: averages slot scores → returns 0-100 score.
    Normalization to 0-100 happens in ranking_snapshot.py for v2.
    """
    scores = zone_data_per_slot or zone_data_for_cell(cell_id, predicted_violations)

    if isinstance(scores, dict) and scores.get("version") == 2:
        cr = scores["congestion_ratio"]
        jb = scores.get("junction_boost", 1.0)
        cameras = scores.get("cameras_per_zone", 1.0)
        vpd = predicted_violations / cameras
        raw_cis = vpd * max(cr - 1, 0.01) ** 1.25 * jb
        patrol_time = scores.get("patrol_slot", "12:00")
        return raw_cis, patrol_time

    slots = _time_slots()
    slot_values = [float(scores.get(slot, 0.0)) for slot in slots]
    if not slot_values:
        return 0.0, slots[0]

    cis_score = round(sum(slot_values) / len(slot_values), 1)
    best_idx = max(range(len(slots)), key=lambda i: slot_values[i])
    patrol_time = slots[best_idx]
    return cis_score, patrol_time
