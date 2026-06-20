import { create } from 'zustand';
import type { ModelInfo, ModelStatus } from '../types';
import { getModelStatus } from '../api/model';

interface ModelState extends ModelInfo {
  loading: boolean;
  fetchStatus: () => Promise<void>;
}

export const useModelStore = create<ModelState>((set) => ({
  status: 'idle' as ModelStatus,
  lastTrainedAt: null,
  datasetCount: 0,
  totalRows: 0,
  loading: false,

  fetchStatus: async () => {
    set({ loading: true });
    try {
      const info = await getModelStatus();
      set({ ...info, loading: false });
    } catch {
      set({ loading: false });
    }
  },
}));
