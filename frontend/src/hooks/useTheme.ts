import { useEffect } from 'react';
import { create } from 'zustand';

interface ThemeState {
  isDark: boolean;
  setDark: (isDark: boolean) => void;
  toggle: () => void;
}

const prefersDark = () => window.matchMedia('(prefers-color-scheme: dark)').matches;

const useThemeStore = create<ThemeState>((set) => ({
  isDark: prefersDark(),
  setDark: (isDark) => set({ isDark }),
  toggle: () => set((s) => ({ isDark: !s.isDark })),
}));

// Single source of truth shared across consumers (AppShell, DashboardPage, …).
export const useTheme = () => {
  const { isDark, setDark, toggle } = useThemeStore();

  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = (e: MediaQueryListEvent) => setDark(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, [setDark]);

  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDark);
  }, [isDark]);

  return { isDark, toggle };
};
