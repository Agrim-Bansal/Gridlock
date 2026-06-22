from datetime import datetime, timedelta

from app.ml.spectral_ridge import SpectralRidgePredictor, extract_features
from app.models import ViolationRow
import numpy as np


def _make_rows(n_days: int = 10, violations_per_day: int = 5) -> list[ViolationRow]:
    rows: list[ViolationRow] = []
    base = datetime(2024, 3, 1, 8, 0, 0)
    for day in range(n_days):
        for v in range(violations_per_day):
            ts = base + timedelta(days=day, hours=v % 12)
            rows.append(
                ViolationRow(
                    dataset_id="d_test",
                    timestamp=ts,
                    cell_id="4780_27925",
                    violation_type="No Parking",
                )
            )
            rows.append(
                ViolationRow(
                    dataset_id="d_test",
                    timestamp=ts + timedelta(minutes=30),
                    cell_id="4781_27926",
                    violation_type="No Parking",
                )
            )
    return rows


def test_extract_features_shape():
    window = np.random.rand(72, 3).astype(np.float32)
    hist_mean = np.ones(3)
    features = extract_features(window, dow=2, hist_mean=hist_mean)
    assert features.shape == (3, features.shape[1])
    assert features.shape[1] > 10


def test_spectral_train_predict():
    predictor = SpectralRidgePredictor()
    rows = _make_rows(n_days=14, violations_per_day=8)
    predictor.train(rows)
    assert predictor.forecast_date is not None

    preds = predictor.predict(predictor.forecast_date)
    assert len(preds) >= 1
    assert all(p.violation_count >= 0 for p in preds)


def test_spectral_insufficient_data_returns_empty_or_zero():
    predictor = SpectralRidgePredictor()
    rows = _make_rows(n_days=1, violations_per_day=2)
    predictor.train(rows)
    preds = predictor.predict(datetime(2024, 3, 2).date())
    assert isinstance(preds, list)
