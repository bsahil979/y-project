import { useMemo } from 'react';
import { getPortfolioSnapshot } from '../services/portfolioSnapshot.js';
import usePortfolioQuotes from './usePortfolioQuotes.js';

/** Called once at the application boundary; consumers share snapshot and quotes. */
export default function useOwnedPortfolio(workspace) {
  const quoteInputs = useMemo(() => [...workspace.holdings, ...workspace.transactions]
    .filter((row) => row.portfolio_id === workspace.selectedPortfolioId), [workspace]);
  const pricing = usePortfolioQuotes(quoteInputs);
  const snapshot = useMemo(() => getPortfolioSnapshot(workspace, workspace.selectedPortfolioId,
    { quotes: pricing.quotes }), [workspace, pricing.quotes]);
  return { snapshot, pricing };
}
