import { create } from 'zustand';
import type { Hotspot, HeatmapCell, CellNameMap } from '../types';
import { fetchPredictions } from '../api/predictions';
import { fetchCellNames, staticNames } from '../api/geocode';

interface PredictionState {
  rankedHotspots: Hotspot[];
  heatmapCells: HeatmapCell[];
  selectedDate: string;
  selectedCellId: string | null;
  cellNames: CellNameMap;
  cellNamesLoaded: boolean;
  loading: boolean;
  error: string | null;
  setSelectedDate: (date: string) => void;
  setSelectedCellId: (cellId: string | null) => void;
  loadCellNames: () => Promise<void>;
  loadPredictions: () => Promise<void>;
}

const todayStr = () => new Date().toISOString().slice(0, 10);

const enrichHotspots = (hotspots: Hotspot[], names: CellNameMap): Hotspot[] =>
  hotspots.map((h) => {
    if (h.locationName) return h;
    const geo = names[h.cellId];
    return geo ? { ...h, locationName: geo.displayName } : h;
  });

export const usePredictionStore = create<PredictionState>((set, get) => ({
  rankedHotspots: [],
  heatmapCells: [],
  selectedDate: todayStr(),
  selectedCellId: null,
  cellNames: staticNames,
  cellNamesLoaded: false,
  loading: false,
  error: null,

  setSelectedDate: (date) => set({ selectedDate: date }),

  setSelectedCellId: (cellId) => set({ selectedCellId: cellId }),

  loadCellNames: async () => {
    if (get().cellNamesLoaded) return;
    const names = await fetchCellNames();
    const { rankedHotspots } = get();
    set({
      cellNames: names,
      cellNamesLoaded: true,
      rankedHotspots: enrichHotspots(rankedHotspots, names),
    });
  },

  loadPredictions: async () => {
    set({ loading: true, error: null });
    try {
      const result = await fetchPredictions(get().selectedDate);
      const { cellNames } = get();
      set({
        rankedHotspots: enrichHotspots(result.rankedHotspots, cellNames),
        heatmapCells: result.heatmapCells,
        selectedDate: result.date,
        loading: false,
      });
    } catch {
      set({ error: 'Failed to fetch predictions. Check backend connection.', loading: false });
    }
  },
}));
