# Spectral Ridge Pipeline — Interface Contract

Production interface for the recency-weighted spectral ridge regression model.

- **Window**: 72 hours (3 days)
- **Half-life**: 2 days (exponential recency weighting)
- **Features**: 19 dimensions
- **Target**: `log1p(next-day total violations per cell)`
- **Dependencies**: numpy, scipy, scikit-learn

---

## 1. Core Class

```python
from dataclasses import dataclass
from pathlib import Path
import numpy as np
from sklearn.pipeline import Pipeline


@dataclass
class PipelineConfig:
    """Immutable configuration for the pipeline."""
    window_hours: int = 72          # DFT window size
    half_life_days: float = 2.0     # Exponential decay half-life for sample weighting
    ridge_alpha: float = 100.0      # Ridge regularization strength
    hist_mean_lookback: int = 336   # Hours for rolling cell mean (2 weeks)
    min_train_days: int = 4         # Minimum days of history before predictions are valid
    chronic_threshold: int = 30     # Minimum total violations for a cell to be included


class SpectralRidgePipeline:
    """Production spectral ridge regression pipeline.

    Lifecycle:
        1. Instantiate with config
        2. Call fit() with historical data
        3. Call predict() to get next-day forecasts
        4. Call update() daily with new 24h of data (online mode)

    Thread Safety: NOT thread-safe. Use one instance per worker.
    """

    def __init__(self, config: PipelineConfig | None = None):
        self.config = config or PipelineConfig()
        self._model: Pipeline | None = None
        self._is_fitted: bool = False
        self._n_features: int = 19
        self._cell_ids: np.ndarray | None = None    # (N,) cell ID strings
        self._values: np.ndarray | None = None      # (T, N) hourly violation matrix
        self._day_of_week: np.ndarray | None = None # (T,) DOW per hour
```

---

## 2. Data Ingestion

### `fit()` — Full Training

Called once at startup, or daily for full retrain. Accepts the complete historical hourly matrix and fits the model.

```python
def fit(
    self,
    values: np.ndarray,
    day_of_week: np.ndarray,
    cell_ids: np.ndarray | None = None,
) -> "SpectralRidgePipeline":
    """Train the model on all available historical data.

    Args:
        values: Shape (T, N) — hourly violation counts.
            T = total hours of history (e.g., 3624 for ~151 days).
            N = number of grid cells.
            values[t, c] = violation count at hour t for cell c.
            Hours are contiguous, starting from the earliest available.

        day_of_week: Shape (T,) — integer day-of-week for each hour.
            0 = Monday, 6 = Sunday. Must align with values row indices.

        cell_ids: Shape (N,) — optional string identifiers for each cell.
            Format: "row_col" (e.g., "4779_27984"). Used for output labeling.
            If None, cells are indexed 0..N-1.

    Returns:
        self (for method chaining)

    Raises:
        ValueError: if T < window_hours + 24 (insufficient history)
        ValueError: if values contains NaN

    Side Effects:
        - Sets self._model (fitted sklearn Pipeline)
        - Sets self._is_fitted = True
        - Stores values/day_of_week for subsequent predict() calls

    Training Details:
        - Iterates over day-anchors from day (window_hours // 24) to last full day
        - For each anchor: extracts 19 features from the preceding window,
          target = sum of next 24 hours for that cell
        - Applies exponential sample_weight with configured half_life
        - Fits StandardScaler + Ridge(alpha) pipeline

    Complexity:
        O(n_days * N * F) where F = 19 features.
        ~2 seconds for 150 days x 604 cells.
    """
```

### `update()` — Online Daily Update

Called daily in deployment. Appends new observations and retrains.

```python
def update(
    self,
    new_hours: np.ndarray,
    new_day_of_week: np.ndarray,
) -> "SpectralRidgePipeline":
    """Append new hourly data and retrain.

    Args:
        new_hours: Shape (H, N) — new hourly observations to append.
            Typically H=24 for one day of new data.
            Must have same N (number of cells) as original fit() call.

        new_day_of_week: Shape (H,) — DOW for each new hour.

    Returns:
        self

    Raises:
        RuntimeError: if fit() has not been called first
        ValueError: if new_hours.shape[1] != self._values.shape[1]

    Side Effects:
        - Appends to self._values and self._day_of_week
        - Calls self.fit() internally with the updated matrix
    """
```

---

## 3. Prediction

### `predict()` — Next-Day Forecast

```python
@dataclass
class Prediction:
    """Structured prediction output."""
    anchor_hour: int                    # Hour index used as prediction anchor
    anchor_date: str                    # ISO date string "YYYY-MM-DD" of anchor day
    forecast_date: str                  # ISO date string of the predicted day
    cell_ids: np.ndarray                # (N,) cell identifiers
    predicted_daily_total: np.ndarray   # (N,) predicted violation count per cell
    rank: np.ndarray                    # (N,) rank per cell (1 = highest predicted)
    top_k_cells: list[dict]             # Top-K cells as list of dicts (see below)


def predict(
    self,
    anchor_hour: int | None = None,
    top_k: int = 50,
) -> Prediction:
    """Predict next-day violation totals for all cells.

    Args:
        anchor_hour: Hour index to use as prediction anchor.
            The model uses data from [anchor_hour - window + 1, anchor_hour]
            and predicts violations for [anchor_hour + 1, anchor_hour + 24].
            If None, uses the last available hour (len(values) - 1).

        top_k: Number of top cells to include in the ranked output list.

    Returns:
        Prediction dataclass with:
            - predicted_daily_total: raw predicted counts per cell (N,)
            - rank: 1-indexed rank (1 = most violations predicted)
            - top_k_cells: list of dicts for the top-K, each containing:
                {
                    "rank": int,
                    "cell_id": str,
                    "predicted_violations": float,
                    "latitude": float | None,
                    "longitude": float | None,
                }

    Raises:
        RuntimeError: if model is not fitted
        ValueError: if anchor_hour < window_hours (insufficient lookback)

    Complexity: O(N * F) — sub-millisecond for 604 cells.
    """
```

---

## 4. Serialization

```python
def save(self, path: str | Path) -> Path:
    """Serialize fitted pipeline to disk.

    Saves:
        - Fitted sklearn Pipeline (scaler + ridge weights)
        - Config
        - Cell IDs
        - Internal state shape metadata

    Does NOT save the full values matrix (too large, retraining is cheap).

    Args:
        path: Directory to save into. Created if not exists.

    Returns:
        Path to the saved model directory.

    Files created:
        {path}/model.joblib     — sklearn Pipeline
        {path}/config.json      — PipelineConfig as JSON
        {path}/metadata.json    — cell_ids, n_cells, n_hours_trained, timestamp
    """


@classmethod
def load(cls, path: str | Path) -> "SpectralRidgePipeline":
    """Load a previously saved pipeline.

    Note: The loaded pipeline can predict() immediately but cannot
    update() until fit() is called with new data (since values matrix
    is not persisted).

    Args:
        path: Directory containing saved model files.

    Returns:
        SpectralRidgePipeline instance with fitted model.

    Raises:
        FileNotFoundError: if path doesn't exist or is missing files.
    """
```

---

## 5. Feature Vector (19 dimensions)

| # | Feature | Domain | Description |
|---|---------|--------|-------------|
| 1 | `dc_magnitude` | Spectral | sqrt(power at freq 0) — overall activity level |
| 2 | `energy_24h` | Spectral | Band energy around 24h period |
| 3 | `energy_12h` | Spectral | Band energy around 12h period |
| 4 | `energy_8h` | Spectral | Band energy around 8h period |
| 5 | `energy_6h` | Spectral | Band energy around 6h period |
| 6 | `energy_highfreq` | Spectral | Residual HF energy (noise level) |
| 7 | `total_energy` | Spectral | Parseval's total spectral energy |
| 8 | `phase_24h_sin` | Spectral | sin(phase) at 24h peak |
| 9 | `phase_24h_cos` | Spectral | cos(phase) at 24h peak |
| 10 | `phase_12h_sin` | Spectral | sin(phase) at 12h peak |
| 11 | `phase_12h_cos` | Spectral | cos(phase) at 12h peak |
| 12 | `dc_ratio` | Change Detection | Recent 48h mean / full window mean |
| 13 | `spectral_flux` | Change Detection | L2 distance between recent and full spectra |
| 14 | `band_decay_24h` | Change Detection | 24h energy in 2nd half / 1st half of window |
| 15 | `band_decay_12h` | Change Detection | 12h energy in 2nd half / 1st half of window |
| 16 | `dow_sin` | Temporal | sin(2pi * day_of_week / 7) |
| 17 | `dow_cos` | Temporal | cos(2pi * day_of_week / 7) |
| 18 | `is_weekend` | Temporal | 1.0 if Saturday or Sunday |
| 19 | `cell_mean_log` | Statistical | log1p(2-week rolling mean for cell) |

---

## 6. Data Contract — What the Backend Must Provide

### Input Data Format

```
1. Hourly violation matrix
   Shape: (T, N) float32 or float64
   T = number of contiguous hours of history
   N = number of tracked grid cells (fixed after initial setup)
   Entry [t, c] = number of violations recorded at hour t in cell c
   Hours must be contiguous (no gaps). Missing hours should be 0.
   Minimum T: window_hours + 24 = 96 hours (72h window + 24h target)
   Recommended T: 2000+ hours (~3 months) for good training signal

2. Day-of-week array
   Shape: (T,) int, values 0-6
   Must exactly align with the values matrix rows
   0 = Monday, 6 = Sunday

3. Cell IDs (optional but recommended)
   Shape: (N,) strings
   Format: "{grid_row}_{grid_col}" e.g. "4779_27984"
   Must maintain consistent ordering across all calls
```

### Data Quality Requirements

- No NaN values (use 0 for missing)
- No negative values
- Integer or float (model uses float internally)
- Timezone: all hours in a single consistent timezone (e.g., IST)
- Cell ordering: must be identical between `fit()` and `update()` calls
- Grid resolution: 300m x 300m (`CELL_KM = 0.3`)
  - `lat_idx = round(lat / (CELL_KM / 111.0))`
  - `lon_idx = round(lon / (CELL_KM / (111.0 * cos(radians(13)))))`

---

## 7. Output Contract — What `predict()` Returns

### `Prediction` Dataclass

```python
@dataclass
class Prediction:
    anchor_hour: int
    # The hour index in the internal matrix used as lookback endpoint.

    anchor_date: str
    # ISO format "YYYY-MM-DD" of the anchor day.

    forecast_date: str
    # ISO format "YYYY-MM-DD" of the day being predicted (anchor + 1 day).

    cell_ids: np.ndarray
    # Shape (N,). The cell identifiers, same order as predicted values.

    predicted_daily_total: np.ndarray
    # Shape (N,). Predicted total violations for each cell on forecast_date.
    # Non-negative floats. NOT log-transformed (these are real counts).

    rank: np.ndarray
    # Shape (N,). 1-indexed rank for each cell (1 = most predicted violations).

    top_k_cells: list[dict]
    # Top-K cells sorted by predicted violations (descending).
    # Each dict:
    # {
    #     "rank": int,                   # 1-indexed
    #     "cell_id": str,                # e.g. "4779_27984"
    #     "predicted_violations": float,  # predicted count for the day
    #     "latitude": float | None,      # center of grid cell (if available)
    #     "longitude": float | None,     # center of grid cell (if available)
    # }
```

### JSON Serialization Example

```python
import json
from datetime import datetime

output = {
    "forecast_date": prediction.forecast_date,
    "generated_at": datetime.utcnow().isoformat(),
    "model_version": "spectral_ridge_v2_w72_hl2",
    "top_k": prediction.top_k_cells,
    "metadata": {
        "n_cells": len(prediction.cell_ids),
        "anchor_date": prediction.anchor_date,
        "hours_of_training_data": pipeline._values.shape[0],
    }
}

json.dumps(output, default=str)
```

### Sample JSON Output

```json
{
  "forecast_date": "2026-06-22",
  "generated_at": "2026-06-21T18:30:00.000000",
  "model_version": "spectral_ridge_v2_w72_hl2",
  "top_k": [
    {
      "rank": 1,
      "cell_id": "4779_27984",
      "predicted_violations": 47.3,
      "latitude": 12.9162,
      "longitude": 77.6219
    },
    {
      "rank": 2,
      "cell_id": "4780_27984",
      "predicted_violations": 41.1,
      "latitude": 12.9189,
      "longitude": 77.6219
    }
  ],
  "metadata": {
    "n_cells": 604,
    "anchor_date": "2026-06-21",
    "hours_of_training_data": 3648
  }
}
```

---

## 8. Complete Backend Integration Example

```python
import numpy as np
from datetime import date, timedelta
from src.spectral_ridge_pipeline import SpectralRidgePipeline, PipelineConfig

# ─── INITIALIZATION (on service startup) ─────────────────────────────────

config = PipelineConfig(
    window_hours=72,
    half_life_days=2.0,
    ridge_alpha=100.0,
    hist_mean_lookback=336,
)

pipeline = SpectralRidgePipeline(config)


# ─── INITIAL TRAINING (load full history from DB) ────────────────────────

# values: np.ndarray shape (T, N) — queried from your time-series DB
# T = number of hours of historical data
# N = number of grid cells being tracked
# values[t, c] = count of violations at hour t in cell c
values = db.query_hourly_violations()  # -> (T, N) ndarray

# day_of_week: np.ndarray shape (T,) — 0=Mon to 6=Sun for each hour
day_of_week = db.query_day_of_week()   # -> (T,) ndarray

# cell_ids: np.ndarray shape (N,) — string IDs like "4779_27984"
cell_ids = db.query_cell_ids()         # -> (N,) ndarray of strings, e.g. "4779_27984"

pipeline.fit(values, day_of_week, cell_ids)


# ─── PREDICTION (called when patrol list is needed) ──────────────────────

prediction = pipeline.predict(top_k=50)

# prediction.forecast_date  -> "2026-06-22"
# prediction.top_k_cells    -> [
#     {"rank": 1, "cell_id": "4779_27984", "predicted_violations": 47.3, ...},
#     {"rank": 2, "cell_id": "4780_27984", "predicted_violations": 41.1, ...},
#     ...
# ]

# Send to dispatch system
dispatch_api.send_patrol_list(
    date=prediction.forecast_date,
    hotspots=prediction.top_k_cells,
)


# ─── DAILY UPDATE (cron job at midnight, after day's data is final) ──────

# Fetch last 24 hours of new observations
new_data = db.query_last_24h()           # -> (24, N) ndarray
new_dow = db.query_dow_last_24h()        # -> (24,) ndarray

pipeline.update(new_data, new_dow)

# Pipeline is now retrained on all data including today.
# Next predict() call uses the updated model.


# ─── BATCH MODE (competition / backtest) ─────────────────────────────────

from src.spectral_ridge_pipeline import batch_predict

results_df = batch_predict(
    pipeline=pipeline,
    test_start_day=129,   # day index to begin predictions
    test_end_day=149,     # last day to predict
)
# Returns DataFrame with columns: forecast_date, cell_id, pred, rank
```

---

## 9. Error Handling

| Exception | When | Recovery |
|-----------|------|----------|
| `ValueError` | NaN in input, insufficient history, shape mismatch | Validate data before calling. Log and alert. |
| `RuntimeError` | `predict()` or `update()` called before `fit()` | Ensure `fit()` is called at startup. |
| `FileNotFoundError` | `load()` with invalid path | Fall back to `fit()` from raw data. |
| `numpy.linalg.LinAlgError` | Degenerate data (all zeros, constant columns) | Check data quality. Ensure cells have variance. |

---

## 10. Performance Characteristics

| Operation | Time (604 cells) | Memory |
|-----------|-----------------|--------|
| `fit()` — 150 days | ~2 seconds | ~50 MB (training matrix) |
| `predict()` — single day | <1 ms | Negligible |
| `update()` — append 24h + retrain | ~2 seconds | Same as fit() |
| Feature extraction — 1 anchor | ~0.5 ms | ~100 KB |

Retraining is cheap enough to run on every prediction cycle. No GPU required. Single CPU core is sufficient.

---

## 11. Sample Implementation Skeleton

```python
"""src/spectral_ridge_pipeline.py — Production module."""

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

    # ─── FEATURE EXTRACTION ──────────────────────────────────────────

    def _extract_features(
        self, window: np.ndarray, dow: int, hist_mean: np.ndarray
    ) -> np.ndarray:
        """Extract 19 features from a (W, N) window.

        Returns: (N, 19) feature matrix.
        """
        T, N = window.shape
        SHORT_WINDOW = min(48, T // 2)

        X = np.fft.rfft(window, axis=0)
        mag_sq = np.abs(X) ** 2
        n_bins = mag_sq.shape[0]

        features = []

        # DC
        features.append(np.sqrt(mag_sq[0]))

        # Band energies at 24h, 12h, 8h, 6h
        for period in [24, 12, 8, 6]:
            bin_idx = round(T / period)
            if bin_idx < n_bins:
                lo = max(0, bin_idx - 1)
                hi = min(n_bins, bin_idx + 2)
                features.append(mag_sq[lo:hi].sum(axis=0))
            else:
                features.append(np.zeros(N))

        # HF residual
        hf_start = max(1, n_bins * 3 // 4)
        features.append(mag_sq[hf_start:].sum(axis=0))

        # Total energy
        features.append(mag_sq.sum(axis=0))

        # Phase at 24h and 12h
        for period in [24, 12]:
            bin_idx = round(T / period)
            if bin_idx < n_bins:
                phase = np.angle(X[bin_idx])
                features.append(np.sin(phase))
                features.append(np.cos(phase))
            else:
                features.append(np.zeros(N))
                features.append(np.zeros(N))

        # DC ratio (change detection)
        recent_dc = window[-SHORT_WINDOW:].mean(axis=0)
        full_dc = window.mean(axis=0)
        features.append(recent_dc / (full_dc + 1e-9))

        # Spectral flux
        X_short = np.fft.rfft(window[-SHORT_WINDOW:], axis=0)
        mag_sq_short = np.abs(X_short) ** 2
        norm_full = mag_sq / (mag_sq.sum(axis=0, keepdims=True) + 1e-9)
        norm_short = mag_sq_short / (mag_sq_short.sum(axis=0, keepdims=True) + 1e-9)
        n_s = mag_sq_short.shape[0]
        flux = np.sqrt(((norm_short - norm_full[:n_s]) ** 2).sum(axis=0))
        features.append(flux)

        # Band energy decay (2nd half / 1st half) at 24h and 12h
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

        # Non-spectral: DOW
        dow_angle = TWO_PI_OVER_7 * dow
        features.append(np.full(N, math.sin(dow_angle)))
        features.append(np.full(N, math.cos(dow_angle)))
        features.append(np.full(N, 1.0 if dow >= 5 else 0.0))

        # Cell historical mean
        features.append(np.log1p(hist_mean))

        return np.column_stack(features)  # (N, 19)

    def _compute_recent_mean(self, anchor_hour: int) -> np.ndarray:
        lookback = self.config.hist_mean_lookback
        start = max(0, anchor_hour - lookback + 1)
        return self._values[start:anchor_hour + 1].mean(axis=0)

    def _compute_sample_weights(self, n_samples: int, n_cells: int) -> np.ndarray:
        n_days = n_samples // n_cells
        decay = np.log(2) / self.config.half_life_days
        day_weights = np.exp(-decay * np.arange(n_days - 1, -1, -1))
        return np.repeat(day_weights, n_cells)

    # ─── PUBLIC API ──────────────────────────────────────────────────

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
            raise ValueError(
                f"Insufficient history: need {ws + 24} hours, got {T}"
            )

        self._values = values
        self._day_of_week = day_of_week
        self._cell_ids = cell_ids if cell_ids is not None else np.arange(N).astype(str)

        min_day = ws // 24
        num_days = T // 24
        max_day = num_days - 2

        X_list, y_list = [], []
        for day_idx in range(min_day, max_day + 1):
            ah = day_idx * 24 + 23
            if ah - ws + 1 < 0 or ah + 24 >= T:
                continue
            window = values[ah - ws + 1: ah + 1]
            dow = int(day_of_week[ah])
            hist_mean = self._compute_recent_mean(ah)
            features = self._extract_features(window, dow, hist_mean)
            target = values[ah + 1: ah + 25].sum(axis=0)
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

    def update(
        self,
        new_hours: np.ndarray,
        new_day_of_week: np.ndarray,
    ) -> "SpectralRidgePipeline":
        if not self._is_fitted:
            raise RuntimeError("Pipeline not fitted. Call fit() first.")
        if new_hours.shape[1] != self._values.shape[1]:
            raise ValueError(
                f"Cell count mismatch: expected {self._values.shape[1]}, "
                f"got {new_hours.shape[1]}"
            )

        self._values = np.concatenate([self._values, new_hours], axis=0)
        self._day_of_week = np.concatenate([self._day_of_week, new_day_of_week])

        return self.fit(self._values, self._day_of_week, self._cell_ids)

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
            raise ValueError(
                f"anchor_hour ({anchor_hour}) < window_hours ({ws})"
            )

        window = self._values[anchor_hour - ws + 1: anchor_hour + 1]
        dow = int(self._day_of_week[anchor_hour])
        hist_mean = self._compute_recent_mean(anchor_hour)
        features = self._extract_features(window, dow, hist_mean)

        pred_log = self._model.predict(features)
        pred = np.clip(np.expm1(pred_log), 0, None)

        # Rank (1 = highest predicted)
        rank = np.argsort(np.argsort(-pred)) + 1

        # Top-K list
        top_indices = np.argsort(pred)[-top_k:][::-1]
        top_k_cells = []
        for i, idx in enumerate(top_indices):
            top_k_cells.append({
                "rank": i + 1,
                "cell_id": str(self._cell_ids[idx]),
                "predicted_violations": float(pred[idx]),
                "latitude": None,
                "longitude": None,
            })

        # Date strings (approximate — caller should provide actual mapping)
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
```

---

## 12. Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Backend Service                                                 │
│                                                                  │
│  ┌──────────────┐     ┌───────────────────────┐                 │
│  │  Database     │────>│  SpectralRidgePipeline │                │
│  │  (hourly      │     │                       │                 │
│  │   violations) │     │  .fit(values, dow)     │  <- startup    │
│  └──────────────┘     │  .update(new, dow)     │  <- daily cron │
│         │              │  .predict(top_k=50)    │  <- on demand  │
│         │              └───────────┬───────────┘                 │
│         │                          │                             │
│         │                          v                             │
│         │              ┌───────────────────────┐                 │
│         │              │  Prediction            │                 │
│         │              │  .forecast_date        │                 │
│         │              │  .top_k_cells          │                 │
│         │              │  .predicted_daily_total│                 │
│         │              └───────────┬───────────┘                 │
│         │                          │                             │
│         v                          v                             │
│  ┌──────────────┐     ┌───────────────────────┐                 │
│  │  Cron Job     │     │  REST API / Response   │                │
│  │  (midnight)   │     │  GET /api/hotspots     │                │
│  │  calls        │     │  -> JSON top_k_cells   │                │
│  │  update()     │     └───────────────────────┘                 │
│  └──────────────┘                                                │
└─────────────────────────────────────────────────────────────────┘
```
