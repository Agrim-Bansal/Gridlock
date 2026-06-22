from datetime import date as DateType

from fastapi import APIRouter, Query

from app.errors import GridlockError
from app.ml import get_predictor
from app.models import ViolationRow
from app.schemas import (
    HeatmapCellOut,
    HotspotOut,
    PeakHourOut,
    PredictionResponse,
    ViolationTypeOut,
)
from app.services.model_state import model_state
from app.services.ranking_snapshot import build_snapshot, get_any_snapshot, get_snapshot

router = APIRouter()


def _patrol_to_peak_hours(patrol_time: str, violation_count: int) -> list[dict]:
    hour = int(patrol_time.split(":")[0])
    end_hour = min(hour + 1, 23)
    expected = max(1, violation_count // 4)
    return [
        {
            "start": patrol_time,
            "end": f"{end_hour:02d}:00",
            "expected_violations": expected,
        }
    ]


def _hotspot_out(h) -> HotspotOut:
    peak_hours = getattr(h, "peak_hours", None)
    if not peak_hours and hasattr(h, "patrol_time"):
        peak_hours = _patrol_to_peak_hours(h.patrol_time, h.violation_count)
    return HotspotOut(
        cell_id=h.cell_id,
        location_name=getattr(h, "location_name", None),
        violation_count=h.violation_count,
        violation_types=[ViolationTypeOut(**vt) for vt in h.violation_types],
        severity=h.severity,
        congestion_impact_score=h.congestion_impact_score,
        patrol_time=h.patrol_time,
        rank=h.rank,
        peak_hours=[PeakHourOut(**ph) for ph in (peak_hours or [])],
    )


@router.get("/predictions", response_model=PredictionResponse)
def get_predictions(date: str | None = Query(None)):
    if not date:
        raise GridlockError(
            400, "missing_date", "Query param 'date' is required (YYYY-MM-DD)."
        )

    try:
        parsed = DateType.fromisoformat(date)
    except ValueError:
        raise GridlockError(
            400, "invalid_date", f"'{date}' is not a valid YYYY-MM-DD date."
        )

    if model_state.status == "idle":
        raise GridlockError(
            409,
            "no_model",
            "No model trained yet. Upload data first.",
        )

    snapshot = get_snapshot(parsed)
    if snapshot is None:
        existing = get_any_snapshot()
        if existing is not None:
            return PredictionResponse(
                date=date,
                generated_at=existing.generated_at,
                ranked_hotspots=[],
                heatmap_cells=[],
                hotspots=[],
            )

        from app.db import SessionLocal

        db = SessionLocal()
        try:
            rows = db.query(ViolationRow).all()
            predictor = get_predictor()
            snapshot = build_snapshot(predictor, rows)
        finally:
            db.close()

    if snapshot is None:
        raise GridlockError(
            409,
            "no_model",
            "No model trained yet. Upload data first.",
        )

    if snapshot.date != date:
        return PredictionResponse(
            date=date,
            generated_at=snapshot.generated_at,
            ranked_hotspots=[],
            heatmap_cells=[],
            hotspots=[],
        )

    ranked = [_hotspot_out(h) for h in snapshot.ranked_hotspots]
    heatmap = [
        HeatmapCellOut(cell_id=c.cell_id, violation_count=c.violation_count)
        for c in snapshot.heatmap_cells
    ]

    return PredictionResponse(
        date=snapshot.date,
        generated_at=snapshot.generated_at,
        ranked_hotspots=ranked,
        heatmap_cells=heatmap,
        hotspots=ranked,
    )
