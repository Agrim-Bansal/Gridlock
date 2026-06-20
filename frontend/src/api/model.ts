import { apiClient } from './client';
import type { RawModelStatusResponse } from './types';
import { mapModelInfo } from './mappers';
import type { ModelInfo } from '../types';
import mockStatus from './mocks/modelStatus.json';

const useMocks = import.meta.env.VITE_USE_MOCKS === 'true';

export const getModelStatus = async (): Promise<ModelInfo> => {
  if (useMocks) {
    await new Promise((r) => setTimeout(r, 200));
    return mapModelInfo(mockStatus as RawModelStatusResponse);
  }
  const { data } = await apiClient.get<RawModelStatusResponse>('/model/status');
  return mapModelInfo(data);
};
