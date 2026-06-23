"""CIS tests."""

from app.services.cis import compute_cis, zone_data_for_cell


def test_compute_cis_mean_and_patrol_time():
    zone = {"06:00": 60.0, "12:00": 80.0, "18:00": 70.0, "00:00": 50.0}
    score, patrol = compute_cis("4780_27925", 100, zone)
    assert score == 65.0
    assert patrol == "12:00"


def test_compute_cis_v2_format():
    zone = {
        "version": 2,
        "congestion_ratio": 2.0,
        "junction_boost": 1.5,
        "cameras_per_zone": 1.0,
        "patrol_slot": "12:00",
    }
    score, patrol = compute_cis("4780_27925", 100, zone)
    assert patrol == "12:00"
    # CIS = 100 * max(2.0 - 1, 0.01)^1.25 * 1.5 = 100 * 1.0 * 1.5 = 150.0
    assert score == 150.0


def test_synthetic_fallback():
    zone = zone_data_for_cell("9999_9999", 50)
    assert len(zone) == 4
    score, patrol = compute_cis("9999_9999", 50, zone)
    assert 0 <= score <= 100
    assert patrol in zone
