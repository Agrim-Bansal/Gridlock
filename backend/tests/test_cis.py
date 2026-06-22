"""CIS tests."""

from app.services.cis import compute_cis, zone_data_for_cell


def test_compute_cis_mean_and_patrol_time():
    zone = {"08:00": 60.0, "12:00": 80.0, "17:00": 70.0, "21:00": 50.0}
    score, patrol = compute_cis("4780_27925", 100, zone)
    assert score == 65.0
    assert patrol == "12:00"


def test_synthetic_fallback():
    zone = zone_data_for_cell("9999_9999", 50)
    assert len(zone) == 4
    score, patrol = compute_cis("9999_9999", 50, zone)
    assert 0 <= score <= 100
    assert patrol in zone
