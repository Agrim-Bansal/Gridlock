"""Build and serve the post-retrain prediction snapshot (no inference on read)."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

from app.config import settings
from app.ml.predictor import HotspotPrediction, Predictor
from app.models import ViolationRow
from app.services.cis import compute_cis, zone_data_for_cell
from app.services import geocode_lookup
from app.services.severity import assign_severity_by_cis

logger = logging.getLogger(__name__)


@dataclass
class RankedHotspot:
    cell_id: str
    violation_count: int
    congestion_impact_score: float
    patrol_time: str
    rank: int
    violation_types: list[dict]
    location_name: str | None = None
    severity: str = ""


@dataclass
class HeatmapCell:
    cell_id: str
    violation_count: int


@dataclass
class PredictionSnapshot:
    date: str
    generated_at: str
    ranked_hotspots: list[RankedHotspot] = field(default_factory=list)
    heatmap_cells: list[HeatmapCell] = field(default_factory=list)


def _normalize_cis(ranked: list[RankedHotspot]) -> None:
    """Normalize raw CIS scores to 0-100 for frontend compatibility."""
    if not ranked:
        return
    raw = [r.congestion_impact_score for r in ranked]
    max_s, min_s = max(raw), min(raw)
    if max_s > min_s:
        for r in ranked:
            r.congestion_impact_score = round(
                5.0 + 95.0 * (r.congestion_impact_score - min_s) / (max_s - min_s), 1
            )
    elif max_s > 0:
        for r in ranked:
            r.congestion_impact_score = 50.0


_store: PredictionSnapshot | None = None


def _snapshot_path() -> Path:
    return settings.data_dir / "prediction_snapshot.json"


def build_snapshot(predictor: Predictor, rows: list[ViolationRow]) -> PredictionSnapshot | None:
    global _store

    if not rows:
        _store = None
        _persist(None)
        return None

    forecast_date = _forecast_date(predictor, rows)
    logger.info("Building snapshot for %s (%d rows)", forecast_date.isoformat(), len(rows))
    raw = predictor.predict(forecast_date)
    if not raw:
        _store = PredictionSnapshot(
            date=forecast_date.isoformat(),
            generated_at=_utc_now(),
            ranked_hotspots=[],
            heatmap_cells=[],
        )
        _persist(_store)
        return _store

    raw.sort(key=lambda h: h.violation_count, reverse=True)
    top_k = settings.cis_top_k
    shortlist = raw[:top_k]

    ranked: list[RankedHotspot] = []
    for h in shortlist:
        zone_data = zone_data_for_cell(h.cell_id, h.violation_count)
        cis_score, patrol_time = compute_cis(h.cell_id, h.violation_count, zone_data)
        location = h.location_name
        if not location:
            location = geocode_lookup.resolve_display_name(h.cell_id)
        if not location and isinstance(zone_data, dict):
            road = zone_data.get("road_name")
            locality = zone_data.get("locality")
            if road and locality:
                location = f"{road}, {locality}"
            elif road:
                location = road
        ranked.append(
            RankedHotspot(
                cell_id=h.cell_id,
                violation_count=h.violation_count,
                congestion_impact_score=cis_score,
                patrol_time=patrol_time,
                rank=0,
                violation_types=h.violation_types or [
                    {"type": "No Parking", "count": h.violation_count}
                ],
                location_name=location,
            )
        )

    _normalize_cis(ranked)
    ranked.sort(key=lambda r: r.congestion_impact_score, reverse=True)
    for i, item in enumerate(ranked, start=1):
        item.rank = i

    assign_severity_by_cis(ranked)
    logger.info(
        "Ranked %d hotspots (CIS range: %.1f–%.1f), top: %s (%.1f)",
        len(ranked),
        ranked[-1].congestion_impact_score if ranked else 0,
        ranked[0].congestion_impact_score if ranked else 0,
        ranked[0].cell_id if ranked else "-",
        ranked[0].congestion_impact_score if ranked else 0,
    )

    heatmap = [
        HeatmapCell(cell_id=h.cell_id, violation_count=h.violation_count)
        for h in raw
    ]

    snapshot = PredictionSnapshot(
        date=forecast_date.isoformat(),
        generated_at=_utc_now(),
        ranked_hotspots=ranked,
        heatmap_cells=heatmap,
    )
    _store = snapshot
    _persist(snapshot)
    return snapshot


def get_snapshot(requested_date: date | None = None) -> PredictionSnapshot | None:
    global _store
    if _store is None:
        _store = _load()
    if _store is None:
        return None
    if requested_date is not None and _store.date != requested_date.isoformat():
        return None
    return _store


def get_any_snapshot() -> PredictionSnapshot | None:
    global _store
    if _store is None:
        _store = _load()
    return _store


def clear_snapshot() -> None:
    global _store
    _store = None
    path = _snapshot_path()
    if path.exists():
        path.unlink()


def _forecast_date(predictor: Predictor, rows: list[ViolationRow]) -> date:
    fd = getattr(predictor, "forecast_date", None)
    if fd is not None:
        return fd
    from datetime import timedelta

    max_ts = max(r.timestamp for r in rows)
    return max_ts.date() + timedelta(days=1)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _persist(snapshot: PredictionSnapshot | None) -> None:
    path = _snapshot_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if snapshot is None:
        if path.exists():
            path.unlink()
        return
    path.write_text(json.dumps(asdict(snapshot), indent=2))


def _load() -> PredictionSnapshot | None:
    path = _snapshot_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return PredictionSnapshot(
            date=data["date"],
            generated_at=data["generated_at"],
            ranked_hotspots=[RankedHotspot(**h) for h in data.get("ranked_hotspots", [])],
            heatmap_cells=[HeatmapCell(**c) for c in data.get("heatmap_cells", [])],
        )
    except (json.JSONDecodeError, KeyError, TypeError):
        return None
