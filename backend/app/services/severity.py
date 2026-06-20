from app.ml.predictor import HotspotPrediction


def assign_severity(hotspots: list[HotspotPrediction]) -> None:
    if not hotspots:
        return

    counts = sorted(h.violation_count for h in hotspots)
    n = len(counts)

    p40 = counts[int(0.4 * n)] if n > 1 else counts[0]
    p70 = counts[int(0.7 * n)] if n > 1 else counts[0]
    p90 = counts[int(0.9 * n)] if n > 1 else counts[0]

    for h in hotspots:
        c = h.violation_count
        if c >= p90:
            h.severity = "critical"
        elif c >= p70:
            h.severity = "high"
        elif c >= p40:
            h.severity = "moderate"
        else:
            h.severity = "low"
