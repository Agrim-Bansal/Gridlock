from datetime import date as DateType, datetime, timezone

from fastapi import APIRouter, Query

from app.errors import GridlockError
from app.ml import get_predictor
from app.schemas import HotspotOut, PeakHourOut, PredictionResponse, ViolationTypeOut
from app.services.model_state import model_state
from app.services.severity import assign_severity

router = APIRouter()


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

    predictor = get_predictor()
    raw = predictor.predict(parsed)
    assign_severity(raw)

    hotspots = [
        HotspotOut(
            cell_id=h.cell_id,
            location_name=h.location_name,
            violation_count=h.violation_count,
            violation_types=[ViolationTypeOut(**vt) for vt in h.violation_types],
            severity=h.severity,
            congestion_impact_score=h.congestion_impact_score,
            peak_hours=[PeakHourOut(**ph) for ph in h.peak_hours],
        )
        for h in raw
    ]
    hotspots.sort(key=lambda h: h.violation_count, reverse=True)

    return PredictionResponse(
        date=date,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        hotspots=hotspots,
    )
