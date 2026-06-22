"""Congestion Impact Score (CIS) provider — API or synthetic fallback."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

DEFAULT_TIME_SLOTS = ("08:00", "12:00", "17:00", "21:00")


def _time_slots() -> list[str]:
    return list(settings.cis_time_slots or DEFAULT_TIME_SLOTS)


def _fallback_dir() -> Path:
    return settings.data_dir / "cis_fallback"


def _synthetic_slot_scores(predicted_violations: int, cell_id: str) -> dict[str, float]:
    """Generate deterministic placeholder scores until real CIS formula is wired."""
    # TODO: replace with real zone-density / capacity formula from CIS script.
    base = min(100.0, max(5.0, predicted_violations * 0.35))
    slots = _time_slots()
    scores: dict[str, float] = {}
    for i, slot in enumerate(slots):
        i_part, j_part = cell_id.split("_")
        jitter = (int(i_part) + int(j_part) + i * 7) % 15
        scores[slot] = round(min(100.0, base + jitter - 5), 1)
    return scores


def _load_fallback(cell_id: str) -> dict[str, float] | None:
    path = _fallback_dir() / f"{cell_id}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return {k: float(v) for k, v in data.items()}
    except (json.JSONDecodeError, TypeError, ValueError):
        logger.warning("Invalid CIS fallback for %s", cell_id)
        return None


def _fetch_cis_api(cell_id: str, predicted_violations: int) -> dict[str, float] | None:
    """Placeholder for live CIS API integration."""
    # TODO: call external CIS API with zone geometry per time slot when CIS_API_KEY is set.
    if not settings.cis_api_key:
        return None
    logger.info("CIS API stub called for %s (violations=%d)", cell_id, predicted_violations)
    return None


def zone_data_for_cell(cell_id: str, predicted_violations: int) -> dict[str, float]:
    """Return per-slot CIS component scores for a cell."""
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
    zone_data_per_slot: dict[str, float] | None = None,
) -> tuple[float, str]:
    """Return (cis_score 0-100, patrol_time HH:MM)."""
    slots = _time_slots()
    scores = zone_data_per_slot or zone_data_for_cell(cell_id, predicted_violations)

    slot_values = [float(scores.get(slot, 0.0)) for slot in slots]
    if not slot_values:
        return 0.0, slots[0]

    cis_score = round(sum(slot_values) / len(slot_values), 1)
    best_idx = max(range(len(slots)), key=lambda i: slot_values[i])
    patrol_time = slots[best_idx]
    return cis_score, patrol_time
