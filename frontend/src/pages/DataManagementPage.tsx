import { useEffect } from 'react';
import { useDataStore } from '../stores/dataStore';
import { useModelStore } from '../stores/modelStore';
import { UploadZone } from '../components/data/UploadZone';
import { DatasetTable } from '../components/data/DatasetTable';
import { ErrorBanner } from '../components/shared/ErrorBanner';
import { Spinner } from '../components/shared/Spinner';

export const DataManagementPage = () => {
  const { datasets, loading, uploading, error, loadDatasets, upload, remove } = useDataStore();
  const fetchModelStatus = useModelStore((s) => s.fetchStatus);

  useEffect(() => {
    loadDatasets();
  }, [loadDatasets]);

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
          onDismiss={() => useDataStore.setState({ error: null })}
          onRetry={loadDatasets}
        />
      )}

      <section className="animate-fade-in">
        <h2 className="mb-4 font-serif text-xl text-stone-800 dark:text-stone-200">
          Upload training data
        </h2>
        <UploadZone onUpload={handleUpload} uploading={uploading} />
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
