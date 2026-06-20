import { apiClient } from './client';
import type { RawDatasetListResponse, RawUploadResponse, RawDeleteResponse } from './types';
import { mapDataset } from './mappers';
import type { Dataset } from '../types';
import mockDatasets from './mocks/datasets.json';

const useMocks = import.meta.env.VITE_USE_MOCKS === 'true';

export const listDatasets = async (): Promise<Dataset[]> => {
  if (useMocks) {
    await new Promise((r) => setTimeout(r, 300));
    return (mockDatasets as RawDatasetListResponse).datasets.map(mapDataset);
  }
  const { data } = await apiClient.get<RawDatasetListResponse>('/data');
  return data.datasets.map(mapDataset);
};

export const uploadDataset = async (file: File): Promise<Dataset> => {
  if (useMocks) {
    await new Promise((r) => setTimeout(r, 1000));
    return {
      id: `d_${Date.now()}`,
      filename: file.name,
      uploadedAt: new Date().toISOString(),
      rowCount: 10000,
      status: 'processing',
    };
  }
  const form = new FormData();
  form.append('file', file);
  const { data } = await apiClient.post<RawUploadResponse>('/data/upload', form);
  return mapDataset(data);
};

export const deleteDataset = async (id: string): Promise<void> => {
  if (useMocks) {
    await new Promise((r) => setTimeout(r, 500));
    return;
  }
  await apiClient.delete<RawDeleteResponse>(`/data/${id}`);
};
