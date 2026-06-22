import io

from fastapi.testclient import TestClient

from app.main import app
from app.services.model_state import model_state

client = TestClient(app)

SAMPLE_CSV = (
    "timestamp,latitude,longitude,violation,severity\n"
    "2024-01-15 08:30:00,12.9172,77.6230,No Parking,high\n"
    "2024-01-15 09:00:00,12.9591,77.6974,No Parking,moderate\n"
    "2024-01-15 17:30:00,12.9352,77.6245,No Parking,low\n"
)


def test_model_status_initial():
    r = client.get("/api/model/status")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "idle"
    assert body["last_trained_at"] is None
    assert body["dataset_count"] == 0
    assert body["total_rows"] == 0


def test_predictions_no_model_returns_409():
    r = client.get("/api/predictions?date=2026-06-20")
    assert r.status_code == 409
    body = r.json()
    assert body["error"] == "no_model"
    assert "message" in body


def test_predictions_missing_date():
    r = client.get("/api/predictions")
    assert r.status_code == 400
    assert r.json()["error"] == "missing_date"


def test_predictions_invalid_date():
    r = client.get("/api/predictions?date=not-a-date")
    assert r.status_code == 400
    assert r.json()["error"] == "invalid_date"


def test_data_list_empty():
    r = client.get("/api/data")
    assert r.status_code == 200
    assert r.json()["datasets"] == []


def test_delete_nonexistent():
    r = client.delete("/api/data/nonexistent")
    assert r.status_code == 404
    assert r.json()["error"] == "not_found"


def test_upload_non_csv():
    r = client.post(
        "/api/data/upload",
        files={"file": ("test.txt", b"hello", "text/plain")},
    )
    assert r.status_code == 415


def test_upload_invalid_csv():
    bad_csv = "col_a,col_b\n1,2\n"
    r = client.post(
        "/api/data/upload",
        files={"file": ("bad.csv", bad_csv.encode(), "text/csv")},
    )
    assert r.status_code == 422


def test_upload_valid_csv():
    r = client.post(
        "/api/data/upload",
        files={"file": ("traffic.csv", SAMPLE_CSV.encode(), "text/csv")},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["id"].startswith("d_")
    assert body["filename"] == "traffic.csv"
    assert body["row_count"] == 3
    assert body["status"] == "processing"
    assert "uploaded_at" in body


def test_predictions_after_training():
    from datetime import datetime

    from app.db import SessionLocal
    from app.ml import get_predictor
    from app.models import ViolationRow
    from app.services.ranking_snapshot import build_snapshot

    model_state.set_ready()

    db = SessionLocal()
    try:
        rows = [
            ViolationRow(
                dataset_id="d_test",
                timestamp=datetime(2024, 1, 15, 8, 30),
                cell_id="4780_27925",
                violation_type="No Parking",
            ),
            ViolationRow(
                dataset_id="d_test",
                timestamp=datetime(2024, 1, 15, 9, 0),
                cell_id="4781_27926",
                violation_type="No Parking",
            ),
            ViolationRow(
                dataset_id="d_test",
                timestamp=datetime(2024, 1, 15, 17, 30),
                cell_id="4782_27927",
                violation_type="No Parking",
            ),
        ]
        predictor = get_predictor()
        predictor.train(rows)
        snapshot = build_snapshot(predictor, rows)
        forecast_date = snapshot.date
    finally:
        db.close()

    r = client.get(f"/api/predictions?date={forecast_date}")
    assert r.status_code == 200
    body = r.json()
    assert body["date"] == forecast_date
    assert "generated_at" in body
    assert isinstance(body["ranked_hotspots"], list)
    assert isinstance(body["heatmap_cells"], list)
    assert isinstance(body["hotspots"], list)
    assert len(body["ranked_hotspots"]) > 0

    hotspot = body["ranked_hotspots"][0]
    assert "cell_id" in hotspot
    assert isinstance(hotspot["violation_count"], int)
    assert isinstance(hotspot["violation_types"], list)
    assert hotspot["severity"] in ("low", "moderate", "high", "critical")
    assert isinstance(hotspot["congestion_impact_score"], float)
    assert "patrol_time" in hotspot
    assert isinstance(hotspot["rank"], int)
    assert isinstance(hotspot["peak_hours"], list)


def test_predictions_stable_per_date():
    from datetime import datetime

    from app.ml import get_predictor
    from app.models import ViolationRow
    from app.services.ranking_snapshot import build_snapshot

    model_state.set_ready()
    rows = [
        ViolationRow(
            dataset_id="d_test",
            timestamp=datetime(2024, 1, 15, 8, 30),
            cell_id="4780_27925",
            violation_type="No Parking",
        ),
    ]
    predictor = get_predictor()
    predictor.train(rows)
    snapshot = build_snapshot(predictor, rows)
    forecast_date = snapshot.date

    r1 = client.get(f"/api/predictions?date={forecast_date}")
    r2 = client.get(f"/api/predictions?date={forecast_date}")
    assert r1.json()["ranked_hotspots"] == r2.json()["ranked_hotspots"]


def test_predictions_differ_by_date():
    from datetime import datetime

    from app.ml import get_predictor
    from app.models import ViolationRow
    from app.services.ranking_snapshot import build_snapshot

    model_state.set_ready()
    rows = [
        ViolationRow(
            dataset_id="d_test",
            timestamp=datetime(2024, 1, 15, 8, 30),
            cell_id="4780_27925",
            violation_type="No Parking",
        ),
    ]
    predictor = get_predictor()
    predictor.train(rows)
    snapshot = build_snapshot(predictor, rows)
    forecast_date = snapshot.date

    r1 = client.get(f"/api/predictions?date={forecast_date}")
    r2 = client.get("/api/predictions?date=2099-01-01")
    assert r1.json()["ranked_hotspots"] != r2.json()["ranked_hotspots"]


def test_error_body_shape():
    r = client.get("/api/predictions")
    body = r.json()
    assert "error" in body
    assert "message" in body
    assert isinstance(body["error"], str)
    assert isinstance(body["message"], str)
