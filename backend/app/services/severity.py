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


def assign_severity_by_cis(ranked: list) -> None:
    """Percentile severity from congestion_impact_score (CIS) for ranked hotspots."""
    if not ranked:
        return

    scores = sorted(r.congestion_impact_score for r in ranked)
    n = len(scores)

    p40 = scores[int(0.4 * n)] if n > 1 else scores[0]
    p70 = scores[int(0.7 * n)] if n > 1 else scores[0]
    p90 = scores[int(0.9 * n)] if n > 1 else scores[0]

    for r in ranked:
        s = r.congestion_impact_score
        if s >= p90:
            r.severity = "critical"
        elif s >= p70:
            r.severity = "high"
        elif s >= p40:
            r.severity = "moderate"
        else:
            r.severity = "low"
