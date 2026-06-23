import { apiClient } from './client';
import type { RawCellNamesResponse } from './types';
import { mapCellNames } from './mappers';
import type { CellNameMap } from '../types';
import mockData from './mocks/cellNames.json';
import fallbackData from './mocks/reverseGeocodeFallback.json';

const useMocks = import.meta.env.VITE_USE_MOCKS === 'true';
export const staticNames = mapCellNames(fallbackData as RawCellNamesResponse);

export const fetchCellNames = async (cellIds?: string[]): Promise<CellNameMap> => {
  if (useMocks) {
    await new Promise((r) => setTimeout(r, 200));
    return { ...staticNames, ...mapCellNames(mockData as RawCellNamesResponse) };
  }
  try {
    const params = cellIds?.length ? { cell_ids: cellIds.join(',') } : {};
    const { data } = await apiClient.get<RawCellNamesResponse>('/cell-names', { params });
    return { ...staticNames, ...mapCellNames(data) };
  } catch {
    return staticNames;
  }
};
