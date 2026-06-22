const CELL_KM = 0.3;
const KM_PER_DEG_LAT = 111.0;
const COS_LAT = Math.cos((13.0 * Math.PI) / 180);
const LAT_STEP = CELL_KM / KM_PER_DEG_LAT;
const LON_STEP = CELL_KM / (KM_PER_DEG_LAT * COS_LAT);

export const cellCenter = (cellId: string): [number, number] => {
  const [i, j] = cellId.split('_').map(Number);
  return [i * LAT_STEP, j * LON_STEP];
};

export type CellBounds = [[number, number], [number, number], [number, number], [number, number]];

export const cellBounds = (cellId: string): CellBounds => {
  const [lat, lon] = cellCenter(cellId);
  const dLat = LAT_STEP / 2;
  const dLon = LON_STEP / 2;
  return [
    [lon - dLon, lat - dLat],
    [lon + dLon, lat - dLat],
    [lon + dLon, lat + dLat],
    [lon - dLon, lat + dLat],
  ];
};

export const cellToGeoJSON = (cellId: string) => {
  const bounds = cellBounds(cellId);
  return {
    type: 'Feature' as const,
    properties: { cellId },
    geometry: {
      type: 'Polygon' as const,
      coordinates: [[...bounds, bounds[0]]],
    },
  };
};
