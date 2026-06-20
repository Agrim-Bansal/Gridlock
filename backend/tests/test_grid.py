from math import cos, radians

from app.grid import (
    CELL_KM,
    KM_PER_DEG_LAT,
    LAT_STEP,
    LON_STEP,
    cell_id_to_center,
    point_to_cell_id,
)


def test_roundtrip():
    lat, lon = 12.9172, 77.6230
    cell_id = point_to_cell_id(lat, lon)
    recovered_lat, recovered_lon = cell_id_to_center(cell_id)
    assert abs(recovered_lat - lat) < LAT_STEP
    assert abs(recovered_lon - lon) < LON_STEP


def test_cell_id_format():
    cell_id = point_to_cell_id(12.9172, 77.6230)
    parts = cell_id.split("_")
    assert len(parts) == 2
    int(parts[0])
    int(parts[1])


def test_known_example():
    # Verify the cell_id from the spec is in Bengaluru and round-trips
    lat, lon = cell_id_to_center("14345_83842")
    assert 12.0 < lat < 14.0
    assert 76.0 < lon < 79.0
    assert point_to_cell_id(lat, lon) == "14345_83842"


def test_constants_match_spec():
    assert CELL_KM == 0.1
    assert KM_PER_DEG_LAT == 111.0
    assert abs(LAT_STEP - 0.1 / 111.0) < 1e-10
    assert abs(LON_STEP - 0.1 / (111.0 * cos(radians(13.0)))) < 1e-10


def test_deterministic():
    a = point_to_cell_id(12.95, 77.60)
    b = point_to_cell_id(12.95, 77.60)
    assert a == b
