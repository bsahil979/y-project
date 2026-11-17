import React, { useState, useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { needsOnboarding } from '../services/onboarding';
import Sidebar from '../components/Sidebar';
import Layout from '../components/Layout';
import OnboardingWizard from '../components/OnboardingWizard';
import { TrainedUniverseProvider } from '../contexts/TrainedUniverseContext';
import { useAuth } from '../contexts/AuthContext';
import ChatAdvisor from '../components/ChatAdvisor';
import { PortfolioContext } from '../contexts/PortfolioContext';

const DashboardLayout = ({ tickers, setTickers, syncStatus, workspace }) => {
  const { user } = useAuth();
  const userId = user?.id || user?.email || 'guest';
  const location = useLocation();
  const { snapshot, syncError, retrySync } = React.useContext(PortfolioContext);
  const advisorVisible = location.pathname.replace(/\/$/, '') === '/dashboard/chat';
  const [advisorVisited, setAdvisorVisited] = useState(advisorVisible);
  useEffect(() => {
    if (advisorVisible) setAdvisorVisited(true);
  }, [advisorVisible]);
  const [finishedUser, setFinishedUser] = useState(null);

  if (finishedUser !== userId && needsOnboarding(user)) {
    return (
      <OnboardingWizard
        userId={userId}
        key={userId}
        user={user}
        onComplete={() => setFinishedUser(userId)}
      />
    );
  }

  return (
    <TrainedUniverseProvider>
      <div className="portfolio-app min-h-screen bg-[#f5f6fa] text-slate-900 font-sans selection:bg-violet-500/20">

        <Sidebar tickers={tickers} workspace={workspace} />
        <Layout tickers={tickers} setTickers={setTickers} syncStatus={syncStatus}>
          <div className="animate-in fade-in duration-500">
            {syncStatus === 'sync-failed' && <section role="alert" className="rounded-xl border border-amber-300 bg-amber-50 p-4 mb-5 text-slate-900"><strong>Cloud sync needs attention</strong><p>Your local copy is retained. {syncError}</p><button className="mt-3 rounded-lg border border-blue-500 px-4 py-2 text-blue-700" onClick={retrySync}>Retry cloud sync</button></section>}
            {/* Preserve the advisor instance and its in-flight request across routes. */}
            {(advisorVisited || advisorVisible) && (
              <div hidden={!advisorVisible}>
                <ChatAdvisor key={`${userId}:${snapshot?.portfolioId || ''}`} userId={userId} portfolioSnapshot={snapshot} />
              </div>
            )}
            {!advisorVisible && <Outlet />}
          </div>
        </Layout>
      </div>
    </TrainedUniverseProvider>
  );
};

export default DashboardLayout;
