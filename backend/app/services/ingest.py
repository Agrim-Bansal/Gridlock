from __future__ import annotations

import csv
import io
from datetime import datetime

from app.grid import point_to_cell_id
from app.models import ViolationRow

_COLUMN_ALIASES: dict[str, list[str]] = {
    "timestamp": ["timestamp", "time", "datetime", "date_time"],
    "latitude": ["latitude", "lat"],
    "longitude": ["longitude", "lon", "lng", "long"],
    "violation_type": ["violation_type", "violation", "type"],
    "severity": ["severity", "severity_src"],
}

_TIMESTAMP_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%m/%d/%Y %H:%M:%S",
]


def parse_csv(content: bytes, dataset_id: str) -> list[ViolationRow]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames:
        raise ValueError("CSV has no headers")

    col_map = _resolve_columns(list(reader.fieldnames))

    for required in ("timestamp", "latitude", "longitude"):
        if required not in col_map:
            raise ValueError(f"Missing required column: {required}")

    rows: list[ViolationRow] = []
    for line in reader:
        try:
            ts_raw = line[col_map["timestamp"]].strip()
            lat = float(line[col_map["latitude"]].strip())
            lon = float(line[col_map["longitude"]].strip())
        except (ValueError, KeyError):
            continue

        ts = _parse_timestamp(ts_raw)
        if ts is None:
            continue

        vtype = None
        if "violation_type" in col_map:
            vtype = line.get(col_map["violation_type"], "").strip() or None

        sev = None
        if "severity" in col_map:
            sev = line.get(col_map["severity"], "").strip() or None

        rows.append(
            ViolationRow(
                dataset_id=dataset_id,
                timestamp=ts,
                cell_id=point_to_cell_id(lat, lon),
                violation_type=vtype,
                severity_src=sev,
            )
        )

    return rows


def _resolve_columns(headers: list[str]) -> dict[str, str]:
    lower_map = {h.strip().lower(): h.strip() for h in headers}
    resolved: dict[str, str] = {}
    for field, aliases in _COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in lower_map:
                resolved[field] = lower_map[alias]
                break
    return resolved


def _parse_timestamp(raw: str) -> datetime | None:
    for fmt in _TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None
