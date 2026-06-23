import { create } from 'zustand';
import { AxiosError } from 'axios';
import type { Dataset } from '../types';
import { listDatasets, uploadDataset, deleteDataset } from '../api/data';

const FORMAT_ERROR_CODES = ['invalid_csv', 'empty_csv', 'unsupported_media_type'];

interface BackendError {
  error?: string;
  message?: string;
}

function extractUploadError(err: unknown): { message: string; isFormatError: boolean } {
  if (err instanceof AxiosError && err.response?.data) {
    const body = err.response.data as BackendError & { detail?: string | unknown };
    const message =
      body.message ||
      (typeof body.detail === 'string' ? body.detail : 'Failed to upload dataset.');
    const isFormat =
      FORMAT_ERROR_CODES.includes(body.error ?? '') ||
      /missing required column|only csv|empty_csv|invalid_csv|unparseable/i.test(message);
    return { message, isFormatError: isFormat };
  }
  return { message: 'Failed to upload dataset.', isFormatError: false };
}

interface DataState {
  datasets: Dataset[];
  loading: boolean;
  uploading: boolean;
  error: string | null;
  isFormatError: boolean;
  loadDatasets: () => Promise<void>;
  refreshDatasets: () => Promise<void>;
  upload: (file: File) => Promise<void>;
  remove: (id: string) => Promise<void>;
}

export const useDataStore = create<DataState>((set, get) => ({
  datasets: [],
  loading: false,
  uploading: false,
  error: null,
  isFormatError: false,

  loadDatasets: async () => {
    set({ loading: true, error: null, isFormatError: false });
    try {
      const datasets = await listDatasets();
      set({ datasets, loading: false });
    } catch {
      set({ error: 'Failed to load datasets.', loading: false });
    }
  },

  refreshDatasets: async () => {
    try {
      const datasets = await listDatasets();
      set({ datasets });
    } catch {
      // silent — background refresh shouldn't flash errors
    }
  },

  upload: async (file) => {
    set({ uploading: true, error: null, isFormatError: false });
    try {
      const dataset = await uploadDataset(file);
      set({ datasets: [...get().datasets, dataset], uploading: false });
    } catch (err) {
      const { message, isFormatError } = extractUploadError(err);
      set({ error: message, isFormatError, uploading: false });
    }
  },

  remove: async (id) => {
    set({ error: null, isFormatError: false });
    try {
      await deleteDataset(id);
      set({ datasets: get().datasets.filter((d) => d.id !== id) });
    } catch {
      set({ error: 'Failed to delete dataset.' });
    }
  },
}));
