from math import cos, radians

CELL_KM = 0.1
KM_PER_DEG_LAT = 111.0
COS_LAT = cos(radians(13.0))
LAT_STEP = CELL_KM / KM_PER_DEG_LAT
LON_STEP = CELL_KM / (KM_PER_DEG_LAT * COS_LAT)


def point_to_cell_id(lat: float, lon: float) -> str:
    i = round(lat / LAT_STEP)
    j = round(lon / LON_STEP)
    return f"{i}_{j}"


def cell_id_to_center(cell_id: str) -> tuple[float, float]:
    i_str, j_str = cell_id.split("_")
    return int(i_str) * LAT_STEP, int(j_str) * LON_STEP
