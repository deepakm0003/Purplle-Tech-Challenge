import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/Layout';
import { StoreProvider } from './context/StoreContext';
import { BrigadeOverview } from './pages/BrigadeOverview';
import { POSAnalytics } from './pages/POSAnalytics';
import { StoreCCTV } from './pages/StoreCCTV';
import { StoreView } from './pages/StoreView';
import { SystemHealth } from './pages/SystemHealth';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <StoreProvider>
        <Router>
          <Layout>
            <Routes>
              <Route path="/" element={<BrigadeOverview />} />
              <Route path="/store" element={<StoreView />} />
              <Route path="/health" element={<SystemHealth />} />
              <Route path="/sales" element={<POSAnalytics />} />
              <Route path="/cctv" element={<StoreCCTV />} />
              <Route path="/intelligence" element={<Navigate to="/sales" replace />} />
              <Route path="/funnel" element={<Navigate to="/sales" replace />} />
              <Route path="/anomalies" element={<Navigate to="/sales" replace />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Layout>
        </Router>
      </StoreProvider>
    </QueryClientProvider>
  );
}

export default App;
