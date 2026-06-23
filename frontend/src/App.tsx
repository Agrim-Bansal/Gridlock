import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AppShell } from './components/layout/AppShell';
import { ErrorBoundary } from './components/shared/ErrorBoundary';
import { DashboardPage } from './pages/DashboardPage';
import { DataManagementPage } from './pages/DataManagementPage';

export const App = () => (
  <ErrorBoundary>
    <BrowserRouter>
      <AppShell>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/data" element={<DataManagementPage />} />
        </Routes>
      </AppShell>
    </BrowserRouter>
  </ErrorBoundary>
);
