import { create } from 'zustand';
import type { Hotspot } from '../types';
import { fetchPredictions } from '../api/predictions';

interface PredictionState {
  hotspots: Hotspot[];
  selectedDate: string;
  selectedCellId: string | null;
  loading: boolean;
  error: string | null;
  setSelectedDate: (date: string) => void;
  setSelectedCellId: (cellId: string | null) => void;
  loadPredictions: () => Promise<void>;
}

const todayStr = () => new Date().toISOString().slice(0, 10);

export const usePredictionStore = create<PredictionState>((set, get) => ({
  hotspots: [],
  selectedDate: todayStr(),
  selectedCellId: null,
  loading: false,
  error: null,

  setSelectedDate: (date) => set({ selectedDate: date }),

  setSelectedCellId: (cellId) => set({ selectedCellId: cellId }),

  loadPredictions: async () => {
    set({ loading: true, error: null });
    try {
      const result = await fetchPredictions(get().selectedDate);
      set({ hotspots: result.hotspots, loading: false });
    } catch {
      set({ error: 'Failed to fetch predictions. Check backend connection.', loading: false });
    }
  },
}));
