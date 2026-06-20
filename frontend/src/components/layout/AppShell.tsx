import type { ReactNode } from 'react';
import { useEffect } from 'react';
import { TopBar } from './TopBar';
import { StatusBar } from './StatusBar';
import { useTheme } from '../../hooks/useTheme';
import { useModelStore } from '../../stores/modelStore';

export const AppShell = ({ children }: { children: ReactNode }) => {
  const { isDark, toggle } = useTheme();
  const { status, lastTrainedAt, datasetCount, fetchStatus } = useModelStore();

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 10000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  return (
    <div className="flex h-screen flex-col bg-stone-50 text-stone-900 transition-colors duration-300 dark:bg-stone-950 dark:text-stone-100">
      <TopBar isDark={isDark} onToggleTheme={toggle} />
      <main className="flex-1 overflow-hidden">{children}</main>
      <StatusBar status={status} lastTrainedAt={lastTrainedAt} datasetCount={datasetCount} />
    </div>
  );
};
