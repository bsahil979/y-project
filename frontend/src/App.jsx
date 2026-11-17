import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import LandingPage from './components/LandingPage';
import DashboardLayout from './pages/DashboardLayout';
import PortfolioDashboard from './components/PortfolioDashboard';
import ForecastingView from './components/ForecastingView';
import SentimentView from './components/SentimentView';
import TradingView from './components/TradingView';
import EvaluationView from './pages/EvaluationView';
import AuthPage from './pages/AuthPage';
import PortfolioBuilderView from './components/PortfolioBuilderView';
import HoldingsView from './components/HoldingsView';
import TransactionsView from './components/TransactionsView';
import GoalsView from './components/GoalsView';
import SettingsView from './components/SettingsView';
import FundamentalsView from './components/FundamentalsView';
import ModelExplainerView from './components/ModelExplainerView';
import {
  PortfolioDataService,
  createEmptyWorkspace,
  selectPortfolio,
} from './services/portfolioData';
import useOwnedPortfolio from './hooks/useOwnedPortfolio';
import { PortfolioContext } from './contexts/PortfolioContext';
import { AuthProvider, useAuth } from './contexts/AuthContext';

function RequireAuth({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-[#0a0b10] text-gray-400">
        <div className="text-center space-y-4">
          <div className="w-10 h-10 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
          <p>Validating session…</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/auth" state={{ from: location.pathname + location.search + location.hash }} replace />;
  }

  return children;
}

function AppContent() {
  const [portfolio, setPortfolio] = useState([]);
  const [workspace, setWorkspace] = useState(createEmptyWorkspace());
  const [syncStatus, setSyncStatus] = useState('loading');
  const [syncError, setSyncError] = useState('');
  const { user } = useAuth();
  const userId = user?.id || user?.email || 'guest';

  const [workspaceOwner, setWorkspaceOwner] = useState(null);
  const emptyWorkspace = React.useMemo(() => createEmptyWorkspace(), []);
  const currentWorkspace = workspaceOwner === userId ? workspace : emptyWorkspace;
  const { snapshot, pricing } = useOwnedPortfolio(currentWorkspace);

  useEffect(() => {
    let active = true;
    const loadWorkspace = async () => {
      setSyncStatus('loading');
      const result = await PortfolioDataService.getWorkspaceResult(userId);
      if (!active) return;
      setWorkspace(result.workspace);
      setWorkspaceOwner(userId);
      setSyncStatus(result.status);
      setSyncError(result.error?.message || '');
      const nextPortfolio = result.workspace.watchlistTickers || [];
      setPortfolio(nextPortfolio);
    };
    loadWorkspace();
    return () => { active = false; };
  }, [userId]);

  const updateWorkspace = async (nextWorkspace) => {
    if (workspaceOwner !== userId || syncStatus === 'loading') throw new Error('Wait for your saved portfolio to load before making changes.');
    const normalized = PortfolioDataService.normalizeWorkspace(nextWorkspace);
    setWorkspace(normalized);
    setWorkspaceOwner(userId);
    setSyncStatus('saving');
    const result = await PortfolioDataService.saveWorkspace(userId, normalized);
    setSyncStatus(result.status);
      setSyncError(result.error?.message || '');
    return result;
  };

  useEffect(() => {
    const updateProfile = ({ detail }) => {
      if (detail.userId === userId) {
        setWorkspace(current => ({ ...current, investorProfile: detail.profile }));
      }
    };
    window.addEventListener('investor-profile-changed', updateProfile);
    return () => window.removeEventListener('investor-profile-changed', updateProfile);
  }, [userId]);

  const setTickers = (updater) => {
    setPortfolio((prevState) => {
      const nextState = typeof updater === 'function' ? updater(prevState) : updater;
      const nextWorkspace = { ...workspace, watchlistTickers: nextState };
      setWorkspace(nextWorkspace);
      setSyncStatus('saving');
      PortfolioDataService.saveWorkspace(userId, nextWorkspace).then((result) => setSyncStatus(result.status));
      return nextState;
    });
  };

  const portfolioState = {
    snapshot, pricing, portfolios: currentWorkspace.portfolios,
    syncStatus, syncError, retrySync: () => updateWorkspace(currentWorkspace),
    selectPortfolio: (id) => updateWorkspace(selectPortfolio(currentWorkspace, id)),
  };

  return (
    <PortfolioContext.Provider value={portfolioState}>
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/research" element={<Navigate to="/dashboard/research" replace />} />
      <Route path="/auth" element={<AuthPage />} />
      <Route
        path="/dashboard/*"
        element={
          <RequireAuth>
            {workspaceOwner !== userId || syncStatus === 'loading' ? <p className="p-8">Loading your saved portfolio...</p> : <DashboardLayout tickers={portfolio} setTickers={setTickers} syncStatus={syncStatus} workspace={currentWorkspace} />}
          </RequireAuth>
        }
      >
        <Route index element={<PortfolioDashboard key={snapshot.portfolioId || userId} />} />
        <Route path="advisor" element={<PortfolioDashboard key={snapshot.portfolioId || userId} advisor />} />
        <Route path="manage" element={<PortfolioBuilderView tickers={portfolio} setTickers={setTickers} />} />
        <Route path="portfolio" element={<HoldingsView key={snapshot.portfolioId || userId} workspace={currentWorkspace} setWorkspace={updateWorkspace} />} />
        <Route path="portfolio/transactions" element={<TransactionsView key={snapshot.portfolioId || userId} workspace={currentWorkspace} setWorkspace={updateWorkspace} />} />
        <Route path="planning/goals" element={<GoalsView workspace={workspace} setWorkspace={updateWorkspace} />} />
        <Route path="ai-architecture" element={<ModelExplainerView />} />
        <Route path="research" element={<EvaluationView />} />
        <Route path="training" element={<Navigate to="/dashboard" replace />} />
        <Route path="settings" element={<SettingsView tickers={portfolio} setTickers={setTickers} />} />
        <Route path="fundamentals" element={<FundamentalsView tickers={portfolio} />} />
        <Route path="forecast" element={<ForecastingView tickers={portfolio} setTickers={setTickers} />} />
        <Route path="sentiment" element={<SentimentView tickers={portfolio} />} />
        <Route path="chat" element={null} />
        <Route path="trading" element={<TradingView tickers={portfolio} />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
    </PortfolioContext.Provider>
  );
}

function App() {
  return (
    <Router>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </Router>
  );
}

export default App;
