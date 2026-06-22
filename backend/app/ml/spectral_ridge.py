"""Spectral Ridge Pipeline — recency-weighted spectral ridge regression.

Window: 72h, Half-life: 2 days, Features: 19 dims.
Target: log1p(next-day total violations per cell).
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

TWO_PI_OVER_7 = 2.0 * math.pi / 7.0


@dataclass
class PipelineConfig:
    window_hours: int = 72
    half_life_days: float = 2.0
    ridge_alpha: float = 100.0
    hist_mean_lookback: int = 336
    min_train_days: int = 4
    chronic_threshold: int = 30


@dataclass
class Prediction:
    anchor_hour: int
    anchor_date: str
    forecast_date: str
    cell_ids: np.ndarray
    predicted_daily_total: np.ndarray
    rank: np.ndarray
    top_k_cells: list[dict]


class SpectralRidgePipeline:

    def __init__(self, config: PipelineConfig | None = None):
        self.config = config or PipelineConfig()
        self._model: Pipeline | None = None
        self._is_fitted: bool = False
        self._n_features: int = 19
        self._cell_ids: np.ndarray | None = None
        self._values: np.ndarray | None = None
        self._day_of_week: np.ndarray | None = None

    @property
    def is_fitted(self) -> bool:
        return self._is_fitted

    def _extract_features(
        self, window: np.ndarray, dow: int, hist_mean: np.ndarray
    ) -> np.ndarray:
        """Extract 19 features from a (W, N) window. Returns (N, 19)."""
        T, N = window.shape
        SHORT_WINDOW = min(48, T // 2)

        X = np.fft.rfft(window, axis=0)
        mag_sq = np.abs(X) ** 2
        n_bins = mag_sq.shape[0]

        features = []

        features.append(np.sqrt(mag_sq[0]))

        for period in [24, 12, 8, 6]:
            bin_idx = round(T / period)
            if bin_idx < n_bins:
                lo = max(0, bin_idx - 1)
                hi = min(n_bins, bin_idx + 2)
                features.append(mag_sq[lo:hi].sum(axis=0))
            else:
                features.append(np.zeros(N))

        hf_start = max(1, n_bins * 3 // 4)
        features.append(mag_sq[hf_start:].sum(axis=0))

        features.append(mag_sq.sum(axis=0))

        for period in [24, 12]:
            bin_idx = round(T / period)
            if bin_idx < n_bins:
                phase = np.angle(X[bin_idx])
                features.append(np.sin(phase))
                features.append(np.cos(phase))
            else:
                features.append(np.zeros(N))
                features.append(np.zeros(N))

        recent_dc = window[-SHORT_WINDOW:].mean(axis=0)
        full_dc = window.mean(axis=0)
        features.append(recent_dc / (full_dc + 1e-9))

        X_short = np.fft.rfft(window[-SHORT_WINDOW:], axis=0)
        mag_sq_short = np.abs(X_short) ** 2
        norm_full = mag_sq / (mag_sq.sum(axis=0, keepdims=True) + 1e-9)
        norm_short = mag_sq_short / (mag_sq_short.sum(axis=0, keepdims=True) + 1e-9)
        n_s = mag_sq_short.shape[0]
        flux = np.sqrt(((norm_short - norm_full[:n_s]) ** 2).sum(axis=0))
        features.append(flux)

        half = T // 2
        X_1st = np.fft.rfft(window[:half], axis=0)
        X_2nd = np.fft.rfft(window[half:], axis=0)
        sq_1st = np.abs(X_1st) ** 2
        sq_2nd = np.abs(X_2nd) ** 2
        for period in [24, 12]:
            b = round(half / period)
            if b < sq_1st.shape[0]:
                lo = max(0, b - 1)
                hi = min(sq_1st.shape[0], b + 2)
                e1 = sq_1st[lo:hi].sum(axis=0)
                e2 = sq_2nd[lo:hi].sum(axis=0)
                features.append(e2 / (e1 + 1e-9))
            else:
                features.append(np.ones(N))

        dow_angle = TWO_PI_OVER_7 * dow
        features.append(np.full(N, math.sin(dow_angle)))
        features.append(np.full(N, math.cos(dow_angle)))
        features.append(np.full(N, 1.0 if dow >= 5 else 0.0))

        features.append(np.log1p(hist_mean))

        return np.column_stack(features)

    def _compute_recent_mean(self, anchor_hour: int) -> np.ndarray:
        lookback = self.config.hist_mean_lookback
        start = max(0, anchor_hour - lookback + 1)
        return self._values[start : anchor_hour + 1].mean(axis=0)

    def _compute_sample_weights(self, n_samples: int, n_cells: int) -> np.ndarray:
        n_days = n_samples // n_cells
        decay = np.log(2) / self.config.half_life_days
        day_weights = np.exp(-decay * np.arange(n_days - 1, -1, -1))
        return np.repeat(day_weights, n_cells)

    def fit(
        self,
        values: np.ndarray,
        day_of_week: np.ndarray,
        cell_ids: np.ndarray | None = None,
    ) -> "SpectralRidgePipeline":
        if np.isnan(values).any():
            raise ValueError("values contains NaN")

        T, N = values.shape
        ws = self.config.window_hours
        if T < ws + 24:
            raise ValueError(f"Insufficient history: need {ws + 24} hours, got {T}")

        self._values = values
        self._day_of_week = day_of_week
        self._cell_ids = (
            cell_ids if cell_ids is not None else np.arange(N).astype(str)
        )

        min_day = ws // 24
        num_days = T // 24
        max_day = num_days - 2

        X_list, y_list = [], []
        for day_idx in range(min_day, max_day + 1):
            ah = day_idx * 24 + 23
            if ah - ws + 1 < 0 or ah + 24 >= T:
                continue
            window = values[ah - ws + 1 : ah + 1]
            dow = int(day_of_week[ah])
            hist_mean = self._compute_recent_mean(ah)
            features = self._extract_features(window, dow, hist_mean)
            target = values[ah + 1 : ah + 25].sum(axis=0)
            X_list.append(features)
            y_list.append(target)

        X_train = np.vstack(X_list)
        y_train = np.log1p(np.concatenate(y_list))
        weights = self._compute_sample_weights(len(y_train), N)

        self._model = Pipeline([
            ("scaler", StandardScaler()),
            ("ridge", Ridge(alpha=self.config.ridge_alpha)),
        ])
        self._model.fit(X_train, y_train, ridge__sample_weight=weights)
        self._is_fitted = True

        return self

    def predict(
        self,
        anchor_hour: int | None = None,
        top_k: int = 50,
    ) -> Prediction:
        if not self._is_fitted:
            raise RuntimeError("Pipeline not fitted. Call fit() first.")

        ws = self.config.window_hours
        if anchor_hour is None:
            anchor_hour = len(self._values) - 1

        if anchor_hour < ws:
            raise ValueError(f"anchor_hour ({anchor_hour}) < window_hours ({ws})")

        window = self._values[anchor_hour - ws + 1 : anchor_hour + 1]
        dow = int(self._day_of_week[anchor_hour])
        hist_mean = self._compute_recent_mean(anchor_hour)
        features = self._extract_features(window, dow, hist_mean)

        pred_log = self._model.predict(features)
        pred = np.clip(np.expm1(pred_log), 0, None)

        rank = np.argsort(np.argsort(-pred)) + 1

        top_indices = np.argsort(pred)[-top_k:][::-1]
        top_k_cells = []
        for i, idx in enumerate(top_indices):
            top_k_cells.append({
                "rank": i + 1,
                "cell_id": str(self._cell_ids[idx]),
                "predicted_violations": float(pred[idx]),
            })

        anchor_day = anchor_hour // 24
        anchor_date = f"day_{anchor_day}"
        forecast_date = f"day_{anchor_day + 1}"

        return Prediction(
            anchor_hour=anchor_hour,
            anchor_date=anchor_date,
            forecast_date=forecast_date,
            cell_ids=self._cell_ids,
            predicted_daily_total=pred,
            rank=rank,
            top_k_cells=top_k_cells,
        )

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        joblib.dump(self._model, path / "model.joblib")
        with open(path / "config.json", "w") as f:
            json.dump(asdict(self.config), f, indent=2)
        metadata = {
            "cell_ids": self._cell_ids.tolist(),
            "n_cells": len(self._cell_ids),
            "n_hours_trained": len(self._values) if self._values is not None else 0,
            "n_features": self._n_features,
        }
        with open(path / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
        return path

    @classmethod
    def load(cls, path: str | Path) -> "SpectralRidgePipeline":
        path = Path(path)
        with open(path / "config.json") as f:
            config = PipelineConfig(**json.load(f))
        with open(path / "metadata.json") as f:
            metadata = json.load(f)
        instance = cls(config)
        instance._model = joblib.load(path / "model.joblib")
        instance._cell_ids = np.array(metadata["cell_ids"])
        instance._is_fitted = True
        instance._n_features = metadata["n_features"]
        return instance
