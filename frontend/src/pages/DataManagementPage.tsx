import { useEffect, useRef } from 'react';
import { useDataStore } from '../stores/dataStore';
import { useModelStore } from '../stores/modelStore';
import { UploadZone } from '../components/data/UploadZone';
import { DatasetTable } from '../components/data/DatasetTable';
import { UploadFormatHint } from '../components/data/UploadFormatHint';
import { ErrorBanner } from '../components/shared/ErrorBanner';
import { Spinner } from '../components/shared/Spinner';

export const DataManagementPage = () => {
  const { datasets, loading, uploading, error, isFormatError, loadDatasets, refreshDatasets, upload, remove } =
    useDataStore();
  const fetchModelStatus = useModelStore((s) => s.fetchStatus);
  const modelStatus = useModelStore((s) => s.status);
  const prevModelStatus = useRef(modelStatus);

  useEffect(() => {
    loadDatasets();
  }, [loadDatasets]);

  useEffect(() => {
    const hasProcessing = datasets.some((d) => d.status === 'processing');
    if (!hasProcessing) return;
    const interval = setInterval(refreshDatasets, 5000);
    return () => clearInterval(interval);
  }, [datasets, refreshDatasets]);

  useEffect(() => {
    if (prevModelStatus.current === 'training' && modelStatus === 'ready') {
      refreshDatasets();
    }
    prevModelStatus.current = modelStatus;
  }, [modelStatus, refreshDatasets]);

  const handleUpload = async (file: File) => {
    await upload(file);
    fetchModelStatus();
  };

  const handleDelete = async (id: string) => {
    await remove(id);
    fetchModelStatus();
  };

  return (
    <div className="mx-auto max-w-3xl space-y-10 px-6 py-8">
      {error && (
        <ErrorBanner
          message={error}
          onDismiss={() => useDataStore.setState({ error: null, isFormatError: false })}
          onRetry={loadDatasets}
        />
      )}
      {isFormatError && <UploadFormatHint />}

      <section className="animate-fade-in">
        <h2 className="mb-4 font-serif text-xl text-stone-800 dark:text-stone-200">
          Upload training data
        </h2>
        <UploadZone onUpload={handleUpload} uploading={uploading} />
        {!isFormatError && <div className="mt-4"><UploadFormatHint /></div>}
      </section>

      <section className="animate-fade-in" style={{ animationDelay: '80ms' }}>
        <div className="mb-4 flex items-baseline justify-between">
          <h2 className="font-serif text-xl text-stone-800 dark:text-stone-200">
            Datasets
          </h2>
          {datasets.length > 0 && (
            <span className="text-xs tabular-nums text-stone-400 dark:text-stone-500">
              {datasets.length} file{datasets.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>
        {loading ? (
          <div className="flex justify-center py-16">
            <Spinner size="lg" />
          </div>
        ) : (
          <DatasetTable datasets={datasets} onDelete={handleDelete} />
        )}
      </section>
    </div>
  );
};
