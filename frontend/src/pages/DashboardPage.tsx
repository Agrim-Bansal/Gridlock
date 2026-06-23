import { useEffect } from 'react';
import { usePredictionStore } from '../stores/predictionStore';
import { useModelStore } from '../stores/modelStore';
import { useTheme } from '../hooks/useTheme';
import { HotspotMap } from '../components/map/HotspotMap';
import { MapFallback } from '../components/map/MapFallback';
import { RankingPanel } from '../components/rankings/RankingPanel';
import { ErrorBanner } from '../components/shared/ErrorBanner';
import { EmptyState } from '../components/shared/EmptyState';
import { Spinner } from '../components/shared/Spinner';

export const DashboardPage = () => {
  const {
    rankedHotspots,
    heatmapCells,
    selectedDate,
    selectedCellId,
    loading,
    error,
    setSelectedDate,
    setSelectedCellId,
    loadPredictions,
  } = usePredictionStore();
  const modelStatus = useModelStore((s) => s.status);
  const { isDark } = useTheme();
  const hasMapbox = !!import.meta.env.VITE_MAPBOX_TOKEN;

  useEffect(() => {
    if (modelStatus === 'ready' && rankedHotspots.length === 0 && !loading) loadPredictions();
  }, [modelStatus]); // eslint-disable-line react-hooks/exhaustive-deps

  const isTraining = modelStatus === 'training';
  const hasData = rankedHotspots.length > 0 || heatmapCells.length > 0;

  return (
    <div className="flex h-full flex-col overflow-hidden lg:flex-row">
      <aside className="w-full shrink-0 overflow-y-auto border-b border-stone-200/60 bg-white lg:w-[300px] lg:border-b-0 lg:border-r dark:border-stone-800/60 dark:bg-stone-900">
        <RankingPanel
          rankedHotspots={rankedHotspots}
          selectedCellId={selectedCellId}
          onSelectCell={setSelectedCellId}
          modelStatus={modelStatus}
          loading={loading}
        />
      </aside>

      <div className="flex flex-1 flex-col overflow-hidden">
        {error && (
          <div className="px-4 pt-3">
            <ErrorBanner
              message={error}
              onDismiss={() => usePredictionStore.setState({ error: null })}
              onRetry={loadPredictions}
            />
          </div>
        )}

        <div className="flex items-center gap-3 bg-stone-50/80 px-4 py-2.5 shadow-[0_1px_2px_rgba(0,0,0,0.04)] dark:bg-stone-900/90 dark:shadow-[0_1px_3px_rgba(0,0,0,0.3)]">
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="rounded-lg border border-stone-200 bg-white px-3 py-1.5 font-mono text-sm tabular-nums text-stone-700 shadow-sm transition-all duration-200 focus:border-stone-400 focus:outline-none focus:ring-2 focus:ring-stone-200 dark:border-stone-600 dark:bg-stone-800 dark:text-stone-200 dark:shadow-none dark:focus:border-stone-400 dark:focus:ring-stone-600/50"
          />
          <button
            onClick={loadPredictions}
            disabled={loading || isTraining}
            className="inline-flex items-center gap-2 rounded-lg bg-stone-800 px-4 py-1.5 text-sm font-medium text-stone-100 shadow-sm transition-all duration-200 hover:bg-stone-700 hover:shadow-md active:scale-[0.98] disabled:pointer-events-none disabled:opacity-40 dark:bg-stone-200 dark:text-stone-900 dark:hover:bg-stone-100"
          >
            {loading && <Spinner size="sm" />}
            {isTraining ? 'Training...' : 'Fetch predictions'}
          </button>
          {heatmapCells.length > 0 && (
            <span className="animate-fade-in text-xs tabular-nums text-stone-400 dark:text-stone-500">
              {rankedHotspots.length} patrol · {heatmapCells.length} cells on map
            </span>
          )}
        </div>

        <div className="relative flex-1">
          {modelStatus === 'idle' && !hasData ? (
            <div className="flex h-full items-center justify-center px-8">
              <EmptyState
                title="No predictions yet"
                message="Upload training data to see violation forecasts across Bengaluru."
                linkTo="/data"
                linkLabel="Upload data"
              />
            </div>
          ) : hasMapbox ? (
            <HotspotMap
              rankedHotspots={rankedHotspots}
              heatmapCells={heatmapCells}
              selectedCellId={selectedCellId}
              onSelectCell={setSelectedCellId}
              isDark={isDark}
            />
          ) : (
            <MapFallback
              rankedHotspots={rankedHotspots}
              heatmapCells={heatmapCells}
              selectedCellId={selectedCellId}
              onSelectCell={setSelectedCellId}
              isDark={isDark}
            />
          )}
          {loading && hasData && (
            <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-white/30 backdrop-blur-[1px] dark:bg-stone-950/30">
              <div className="flex items-center gap-2.5 rounded-xl bg-white/90 px-5 py-3 shadow-lg dark:bg-stone-800/90">
                <Spinner />
                <span className="text-sm font-medium text-stone-600 dark:text-stone-300">
                  Loading predictions...
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
