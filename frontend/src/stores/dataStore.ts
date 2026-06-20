import { create } from 'zustand';
import type { Dataset } from '../types';
import { listDatasets, uploadDataset, deleteDataset } from '../api/data';

interface DataState {
  datasets: Dataset[];
  loading: boolean;
  uploading: boolean;
  error: string | null;
  loadDatasets: () => Promise<void>;
  upload: (file: File) => Promise<void>;
  remove: (id: string) => Promise<void>;
}

export const useDataStore = create<DataState>((set, get) => ({
  datasets: [],
  loading: false,
  uploading: false,
  error: null,

  loadDatasets: async () => {
    set({ loading: true, error: null });
    try {
      const datasets = await listDatasets();
      set({ datasets, loading: false });
    } catch {
      set({ error: 'Failed to load datasets.', loading: false });
    }
  },

  upload: async (file) => {
    set({ uploading: true, error: null });
    try {
      const dataset = await uploadDataset(file);
      set({ datasets: [...get().datasets, dataset], uploading: false });
    } catch {
      set({ error: 'Failed to upload dataset.', uploading: false });
    }
  },

  remove: async (id) => {
    set({ error: null });
    try {
      await deleteDataset(id);
      set({ datasets: get().datasets.filter((d) => d.id !== id) });
    } catch {
      set({ error: 'Failed to delete dataset.' });
    }
  },
}));
