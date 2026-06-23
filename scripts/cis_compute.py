"""Pure CIS computation — no I/O, no API calls. Importable by the backend."""

from __future__ import annotations

import math

CELL_M = 300.0
LAT_STEP = CELL_M / 111_000.0
LON_STEP = CELL_M / (111_000.0 * math.cos(math.radians(13.0)))

DEFAULT_DAY_WEIGHTS: dict[str, float] = {"prev_day": 0.3, "same_weekday": 0.7}
DEFAULT_SLOT_WEIGHTS: dict[int, float] = {6: 2.0, 12: 2.5, 18: 1.5, 0: 0.5}
SLOT_LABELS: dict[int, str] = {6: "06:00", 12: "12:00", 18: "18:00", 0: "00:00"}


def cell_center(cell_id: str) -> tuple[float, float]:
    i, j = map(int, cell_id.split("_"))
    return (i * LAT_STEP, j * LON_STEP)


def compute_slot_ratios(
    freeflow: dict[str, float],
    traffic: dict[str, dict[int, dict[str, float]]],
    day_weights: dict[str, float] | None = None,
) -> dict[str, dict[int, float]]:
    """
    Per-zone, per-slot congestion ratio.
    Returns {cell_id: {hour_int: weighted_ratio}}.
    """
    if day_weights is None:
        day_weights = DEFAULT_DAY_WEIGHTS

    zones = list(freeflow.keys())
    hours = set()
    for day_data in traffic.values():
        hours.update(day_data.keys())
    hours_list = sorted(hours)

    slot_ratios: dict[str, dict[int, float]] = {}
    for cid in zones:
        ff = freeflow.get(cid, 0)
        if not ff or ff <= 0:
            slot_ratios[cid] = {h: 1.0 for h in hours_list}
            continue

        ratios: dict[int, float] = {}
        for hour in hours_list:
            weighted_r = 0.0
            total_w = 0.0
            for day_label, day_w in day_weights.items():
                dur = traffic.get(day_label, {}).get(hour, {}).get(cid, ff)
                if not dur or dur <= 0:
                    dur = ff
                r = max(dur / ff, 1.0)
                weighted_r += day_w * r
                total_w += day_w
            ratios[hour] = weighted_r / total_w if total_w > 0 else 1.0
        slot_ratios[cid] = ratios

    return slot_ratios


def compute_congestion_ratios(
    freeflow: dict[str, float],
    traffic: dict[str, dict[int, dict[str, float]]],
    day_weights: dict[str, float] | None = None,
    slot_weights: dict[int, float] | None = None,
) -> dict[str, float]:
    """
    Compute a single slot-weighted congestion_ratio per zone.
    Higher = more congested during violation-prone hours.
    """
    if day_weights is None:
        day_weights = DEFAULT_DAY_WEIGHTS
    if slot_weights is None:
        slot_weights = DEFAULT_SLOT_WEIGHTS

    slot_ratios = compute_slot_ratios(freeflow, traffic, day_weights)
    result: dict[str, float] = {}

    for cid, ratios in slot_ratios.items():
        weighted_sum = 0.0
        total_w = 0.0
        for hour, sw in slot_weights.items():
            r = ratios.get(hour, 1.0)
            weighted_sum += sw * r
            total_w += sw
        result[cid] = weighted_sum / total_w if total_w > 0 else 1.0

    return result


def compute_cis_raw(
    predicted_vpd: dict[str, float],
    congestion_ratios: dict[str, float],
    junction_boost: dict[str, float] | None = None,
    cameras_per_zone: dict[str, float] | None = None,
) -> dict[str, float]:
    """
    Apply CIS formula: (vpd / cameras) * max(cr - 1, 0.01)^1.25 * junction_boost
    Returns {cell_id: raw_cis_score} (unbounded).
    """
    result: dict[str, float] = {}
    for cid, vpd in predicted_vpd.items():
        cr = congestion_ratios.get(cid, 1.0)
        jb = junction_boost.get(cid, 1.0) if junction_boost else 1.0
        cameras = cameras_per_zone.get(cid, 1.0) if cameras_per_zone else 1.0

        freq = vpd / cameras
        cong_term = max(cr - 1, 0.01) ** 1.25
        raw = freq * cong_term * jb
        result[cid] = raw

    return result


def normalize_cis(
    raw_scores: dict[str, float],
    floor: float = 5.0,
    ceil: float = 100.0,
) -> dict[str, float]:
    """Linear normalize raw CIS scores to [floor, ceil] range."""
    if not raw_scores:
        return {}

    values = list(raw_scores.values())
    max_s = max(values)
    min_s = min(values)

    if max_s <= min_s:
        mid = (floor + ceil) / 2
        return {cid: mid for cid in raw_scores}

    span = ceil - floor
    return {
        cid: round(floor + span * (score - min_s) / (max_s - min_s), 1)
        for cid, score in raw_scores.items()
    }


def patrol_slot_for_cell(slot_ratios: dict[int, float]) -> str:
    """Return HH:MM string of the slot with highest congestion ratio."""
    if not slot_ratios:
        return "12:00"
    best_hour = max(slot_ratios, key=lambda h: slot_ratios[h])
    return SLOT_LABELS.get(best_hour, f"{best_hour:02d}:00")
