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
  const { snapshot } = React.useContext(PortfolioContext);
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
        <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(124,58,237,0.06),_transparent_25%),radial-gradient(circle_at_bottom_right,_rgba(37,99,235,0.05),_transparent_28%)]" />
        <Sidebar tickers={tickers} workspace={workspace} />
        <Layout tickers={tickers} setTickers={setTickers} syncStatus={syncStatus}>
          <div className="animate-in fade-in duration-500">
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
