import { useState, useRef, type DragEvent } from 'react';
import Papa from 'papaparse';
import { CsvPreview } from './CsvPreview';

interface UploadZoneProps {
  onUpload: (file: File) => Promise<void>;
  uploading: boolean;
}

const formatSize = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

export const UploadZone = ({ onUpload, uploading }: UploadZoneProps) => {
  const [dragOver, setDragOver] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [headers, setHeaders] = useState<string[]>([]);
  const [previewRows, setPreviewRows] = useState<string[][]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  const parseFile = (f: File) => {
    setFile(f);
    Papa.parse(f, {
      preview: 6,
      complete: (result) => {
        const data = result.data as string[][];
        if (data.length > 0) {
          setHeaders(data[0]);
          setPreviewRows(data.slice(1, 6));
        }
      },
    });
  };

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f?.name.endsWith('.csv')) parseFile(f);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) parseFile(f);
  };

  const handleUpload = async () => {
    if (!file) return;
    await onUpload(file);
    setFile(null);
    setHeaders([]);
    setPreviewRows([]);
  };

  const cancel = () => {
    setFile(null);
    setHeaders([]);
    setPreviewRows([]);
  };

  if (file && headers.length > 0) {
    return (
      <div className="animate-fade-in">
        <CsvPreview
          filename={file.name}
          fileSize={formatSize(file.size)}
          headers={headers}
          rows={previewRows}
          onCancel={cancel}
          onUpload={handleUpload}
          uploading={uploading}
        />
      </div>
    );
  }

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      className={`group flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed py-14 transition-all duration-200 ${
        dragOver
          ? 'border-stone-400 bg-stone-100 scale-[1.01] dark:border-stone-400 dark:bg-stone-800'
          : 'border-stone-200 hover:border-stone-300 hover:bg-stone-50/50 dark:border-stone-700 dark:hover:border-stone-600 dark:hover:bg-stone-800/30'
      }`}
    >
      <div className={`mb-3 flex h-10 w-10 items-center justify-center rounded-lg transition-colors duration-200 ${
        dragOver
          ? 'bg-stone-200 dark:bg-stone-700'
          : 'bg-stone-100 group-hover:bg-stone-200/70 dark:bg-stone-800 dark:group-hover:bg-stone-700/70'
      }`}>
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-stone-400 dark:text-stone-500">
          <path d="M10 14V4m0 0L6.5 7.5M10 4l3.5 3.5M3 14v1.5A1.5 1.5 0 004.5 17h11a1.5 1.5 0 001.5-1.5V14" />
        </svg>
      </div>
      <p className="text-sm text-stone-500 dark:text-stone-400">
        Drop a <span className="font-mono text-xs">.csv</span> file here, or click to browse
      </p>
      <input
        ref={inputRef}
        type="file"
        accept=".csv"
        onChange={handleFileSelect}
        className="hidden"
      />
    </div>
  );
};
