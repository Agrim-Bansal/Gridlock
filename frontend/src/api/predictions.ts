import { apiClient } from './client';
import type { RawPredictionResponse } from './types';
import { mapPredictions } from './mappers';
import type { PredictionResult } from '../types';
import mockData from './mocks/predictions.json';

const useMocks = import.meta.env.VITE_USE_MOCKS === 'true';

export const fetchPredictions = async (date: string): Promise<PredictionResult> => {
  if (useMocks) {
    await new Promise((r) => setTimeout(r, 600));
    return mapPredictions(mockData as RawPredictionResponse);
  }
  const { data } = await apiClient.get<RawPredictionResponse>('/predictions', {
    params: { date },
  });
  return mapPredictions(data);
};
