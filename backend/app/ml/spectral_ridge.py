"""Spectral-ridge daily forecaster (72h window, half-life=2, Ridge alpha=100)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.ml.predictor import HotspotPrediction

if TYPE_CHECKING:
    from app.models import ViolationRow

WINDOW_HOURS = 72
HALF_LIFE_DAYS = 2.0
RIDGE_ALPHA = 100.0
HIST_MEAN_LOOKBACK = 336
MIN_TOTAL_VIOLATIONS = 30
TWO_PI_OVER_7 = 2.0 * math.pi / 7.0


@dataclass
class HourlyMatrix:
    values: np.ndarray
    cell_ids: list[str]
    dates: list[pd.Timestamp]
    day_of_week: np.ndarray


def _band_energy(spectrum_sq: np.ndarray, center: int, width: int = 1) -> np.ndarray:
    lo = max(0, center - width)
    hi = min(len(spectrum_sq), center + width + 1)
    return spectrum_sq[lo:hi].sum(axis=0)


def extract_features(
    window: np.ndarray, dow: int, hist_mean: np.ndarray
) -> np.ndarray:
    t_len, n_cells = window.shape
    short_window = min(48, t_len // 2)

    x_fft = np.fft.rfft(window, axis=0)
    mag_sq = np.abs(x_fft) ** 2
    n_bins = mag_sq.shape[0]

    features: list[np.ndarray] = []
    features.append(np.sqrt(mag_sq[0]))

    for period in (24, 12, 8, 6):
        bin_idx = round(t_len / period)
        if bin_idx < n_bins:
            features.append(_band_energy(mag_sq, bin_idx, width=1))
        else:
            features.append(np.zeros(n_cells))

    hf_start = max(1, n_bins * 3 // 4)
    features.append(mag_sq[hf_start:].sum(axis=0))
    features.append(mag_sq.sum(axis=0))

    for period in (24, 12):
        bin_idx = round(t_len / period)
        if bin_idx < n_bins:
            phase = np.angle(x_fft[bin_idx])
            features.append(np.sin(phase))
            features.append(np.cos(phase))
        else:
            features.append(np.zeros(n_cells))
            features.append(np.zeros(n_cells))

    recent_dc = window[-short_window:].mean(axis=0)
    full_dc = window.mean(axis=0)
    features.append(recent_dc / (full_dc + 1e-9))

    x_short = np.fft.rfft(window[-short_window:], axis=0)
    mag_sq_short = np.abs(x_short) ** 2
    norm_full = mag_sq / (mag_sq.sum(axis=0, keepdims=True) + 1e-9)
    norm_short = mag_sq_short / (mag_sq_short.sum(axis=0, keepdims=True) + 1e-9)
    n_s = mag_sq_short.shape[0]
    flux = np.sqrt(((norm_short - norm_full[:n_s]) ** 2).sum(axis=0))
    features.append(flux)

    half = t_len // 2
    sq_1st = np.abs(np.fft.rfft(window[:half], axis=0)) ** 2
    sq_2nd = np.abs(np.fft.rfft(window[half:], axis=0)) ** 2
    for period in (24, 12):
        b = round(half / period)
        if b < sq_1st.shape[0]:
            e1 = _band_energy(sq_1st, b, width=1)
            e2 = _band_energy(sq_2nd, b, width=1)
            features.append(e2 / (e1 + 1e-9))
        else:
            features.append(np.ones(n_cells))

    dow_angle = TWO_PI_OVER_7 * dow
    features.append(np.full(n_cells, math.sin(dow_angle)))
    features.append(np.full(n_cells, math.cos(dow_angle)))
    features.append(np.full(n_cells, 1.0 if dow >= 5 else 0.0))
    features.append(np.log1p(hist_mean))

    return np.column_stack(features)


def _compute_recent_mean(
    values: np.ndarray, anchor_hour: int, lookback: int = HIST_MEAN_LOOKBACK
) -> np.ndarray:
    start = max(0, anchor_hour - lookback + 1)
    return values[start : anchor_hour + 1].mean(axis=0)


def _exp_weights(n_samples: int, n_cells: int, half_life: float) -> np.ndarray:
    n_days = n_samples // n_cells
    decay = math.log(2) / half_life
    day_weights = np.exp(-decay * np.arange(n_days - 1, -1, -1))
    return np.repeat(day_weights, n_cells)


def _rows_to_hourly(rows: list[ViolationRow]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=["cell_id", "date", "hour", "count"])

    records = [
        {
            "cell_id": r.cell_id,
            "date": r.timestamp.date(),
            "hour": r.timestamp.hour,
        }
        for r in rows
    ]
    df = pd.DataFrame(records)
    hourly = (
        df.groupby(["cell_id", "date", "hour"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
    )
    hourly["date"] = pd.to_datetime(hourly["date"])
    return hourly.sort_values(["cell_id", "date", "hour"]).reset_index(drop=True)


def _build_hourly_matrix(
    hourly: pd.DataFrame, min_total_violations: int = MIN_TOTAL_VIOLATIONS
) -> HourlyMatrix:
    dates = sorted(hourly["date"].unique())
    timesteps = [(d, h) for d in dates for h in range(24)]

    totals = hourly.groupby("cell_id")["count"].sum()
    cell_ids = totals[totals >= min_total_violations].index.tolist()
    cell_to_col = {cid: idx for idx, cid in enumerate(cell_ids)}

    values = np.zeros((len(timesteps), len(cell_ids)), dtype=np.float32)
    if cell_ids:
        sub = hourly[hourly["cell_id"].isin(cell_ids)].copy()
        date_codes = pd.Categorical(sub["date"], categories=dates, ordered=True).codes
        t_idx = date_codes * 24 + sub["hour"].to_numpy(dtype=np.int32)
        col_idx = sub["cell_id"].map(cell_to_col).to_numpy()
        valid = (t_idx >= 0) & (col_idx >= 0)
        np.add.at(
            values,
            (t_idx[valid], col_idx[valid]),
            sub.loc[valid, "count"].to_numpy(),
        )

    day_of_week = np.array(
        [pd.Timestamp(d).dayofweek for d, _ in timesteps], dtype=np.int8
    )
    return HourlyMatrix(
        values=values,
        cell_ids=cell_ids,
        dates=dates,
        day_of_week=day_of_week,
    )


@dataclass
class SpectralRidgePredictor:
    _pipeline: Pipeline | None = field(default=None, repr=False)
    _matrix: HourlyMatrix | None = field(default=None, repr=False)
    forecast_date: date | None = field(default=None, repr=False)

    def train(self, rows: list[ViolationRow]) -> None:
        hourly = _rows_to_hourly(rows)
        if hourly.empty:
            self._pipeline = None
            self._matrix = None
            self.forecast_date = None
            return

        matrix = _build_hourly_matrix(hourly)
        values = matrix.values
        n_cells = len(matrix.cell_ids)
        if n_cells == 0 or values.shape[0] < WINDOW_HOURS + 48:
            self._pipeline = None
            self._matrix = matrix
            self.forecast_date = self._compute_forecast_date(rows)
            return

        max_ts = max(r.timestamp for r in rows)
        anchor_hour = values.shape[0] - 1
        min_day = WINDOW_HOURS // 24
        max_train_day = anchor_hour // 24 - 1

        x_list: list[np.ndarray] = []
        y_list: list[np.ndarray] = []
        for day_idx in range(min_day, max_train_day + 1):
            ah = day_idx * 24 + 23
            if ah - WINDOW_HOURS + 1 < 0 or ah + 24 > anchor_hour + 1:
                continue
            window = values[ah - WINDOW_HOURS + 1 : ah + 1]
            dow = int(matrix.day_of_week[ah])
            hist_mean = _compute_recent_mean(values, ah)
            features = extract_features(window, dow, hist_mean)
            target = values[ah + 1 : ah + 25].sum(axis=0)
            x_list.append(features)
            y_list.append(target)

        if not x_list:
            self._pipeline = None
            self._matrix = matrix
            self.forecast_date = max_ts.date() + timedelta(days=1)
            return

        x_train = np.vstack(x_list)
        y_train = np.log1p(np.concatenate(y_list))
        weights = _exp_weights(len(y_train), n_cells, HALF_LIFE_DAYS)

        pipeline = Pipeline(
            [
                ("scaler", StandardScaler()),
                ("ridge", Ridge(alpha=RIDGE_ALPHA)),
            ]
        )
        pipeline.fit(x_train, y_train, ridge__sample_weight=weights)

        self._pipeline = pipeline
        self._matrix = matrix
        self.forecast_date = max_ts.date() + timedelta(days=1)

    def predict(self, day: date) -> list[HotspotPrediction]:
        if self._matrix is None or not self._matrix.cell_ids:
            return []

        if self._pipeline is None:
            return self._zero_predictions(day)

        matrix = self._matrix
        values = matrix.values
        target = pd.Timestamp(day)

        if target in matrix.dates:
            day_idx = matrix.dates.index(target)
        else:
            day_idx = len(matrix.dates)

        anchor_hour = day_idx * 24 - 1
        if anchor_hour < WINDOW_HOURS - 1 or anchor_hour >= values.shape[0]:
            return self._zero_predictions(day)

        window = values[anchor_hour - WINDOW_HOURS + 1 : anchor_hour + 1]
        dow = int(matrix.day_of_week[anchor_hour])
        hist_mean = _compute_recent_mean(values, anchor_hour)
        features = extract_features(window, dow, hist_mean)

        pred_log = self._pipeline.predict(features)
        pred = np.clip(np.expm1(pred_log), 0, None)

        hotspots: list[HotspotPrediction] = []
        for idx, cell_id in enumerate(matrix.cell_ids):
            count = int(round(float(pred[idx])))
            hotspots.append(
                HotspotPrediction(
                    cell_id=cell_id,
                    violation_count=count,
                    violation_types=[{"type": "No Parking", "count": count}],
                    congestion_impact_score=0.0,
                    peak_hours=[],
                )
            )
        return hotspots

    def _zero_predictions(self, day: date) -> list[HotspotPrediction]:
        assert self._matrix is not None
        return [
            HotspotPrediction(
                cell_id=cid,
                violation_count=0,
                violation_types=[],
                congestion_impact_score=0.0,
                peak_hours=[],
            )
            for cid in self._matrix.cell_ids
        ]

    @staticmethod
    def _compute_forecast_date(rows: list[ViolationRow]) -> date | None:
        if not rows:
            return None
        max_ts = max(r.timestamp for r in rows)
        return max_ts.date() + timedelta(days=1)
