import assert from 'node:assert/strict';
import { it } from 'node:test';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { createServer } from 'vite';

it('real dashboard, holdings and advisor consume the selected canonical snapshot', async () => {
  const server = await createServer({ configFile: false, server: { middlewareMode: true, watch: null },
    optimizeDeps: { noDiscovery: true, include: [] } });
  try {
    // Load the real JSX components and the same context module through Vite.
    const { PortfolioContext } = await server.ssrLoadModule('/src/contexts/PortfolioContext.js');
    const { getPortfolioSnapshot } = await server.ssrLoadModule('/src/services/portfolioSnapshot.js');
    const { default: Dashboard, AllocationComparison } = await server.ssrLoadModule('/src/components/PortfolioDashboard.jsx');
    const { default: Holdings } = await server.ssrLoadModule('/src/components/HoldingsView.jsx');
    const { default: Chat } = await server.ssrLoadModule('/src/components/ChatAdvisor.jsx');
    const workspace = { selectedPortfolioId: 'second', accounts: [], portfolios: [{ id: 'first' }, { id: 'second' }],
      holdings: [{ id: 'h', portfolio_id: 'second', account_id: null, ticker: 'OWNED', currency: 'USD', quantity: 7, average_cost: 10 },
        { id: 'other', portfolio_id: 'first', ticker: 'OTHER', currency: 'USD', quantity: 99, average_cost: 1 }], transactions: [] };
    const canonical = getPortfolioSnapshot(workspace, 'second', { quotes: { OWNED: { price: 20, currency: 'USD' } } });
    let holdingsRead = false;
    let valuationRead = false;
    const snapshot = new Proxy(canonical, { get(target, key) {
      if (key === 'holdings') holdingsRead = true;
      if (key === 'valuation') valuationRead = true;
      return target[key];
    } });
    const value = { snapshot, pricing: { loading: false, revision: 0, refresh() {} } };
    const render = (component) => renderToStaticMarkup(React.createElement(MemoryRouter, null,
      React.createElement(PortfolioContext.Provider, { value }, component)));
    const dashboard = render(React.createElement(Dashboard));
    assert.equal(holdingsRead, true);
    assert.equal(valuationRead, true);
    assert.match(dashboard, /Analyzing current market-value weights/);
    assert.doesNotMatch(dashboard, /Start with your holdings/);
    const advisor = render(React.createElement(Dashboard, { advisor: true }));
    assert.match(advisor, /Preview aggressive/);
    assert.doesNotMatch(dashboard, /Preview aggressive/);
    const comparison = render(React.createElement(AllocationComparison, { data: {
      tickers: ['AAA', 'BBB', 'CCC'], weights: [.4, .5, .1],
      personalized_allocation: {weights: {AAA:.4, BBB:.3, CCC:.3}, objective_used:'black_litterman', max_weight_cap:.4},
      ai_black_litterman_allocation: {provenance: {BBB: {marketmind_net_prob:.2, finbert_score:null}}}
    }}));
    assert.match(comparison, /largest adjustment is BBB, from 50.0% to 30.0%/);
    assert.match(comparison, /FinBERT sentiment unavailable/);
    const holdings = render(React.createElement(Holdings, { workspace, setWorkspace() {} }));
    assert.match(holdings, /OWNED/);
    assert.match(holdings, /140\.00/);
    assert.doesNotMatch(holdings, /OTHER/);
    holdingsRead = false;
    render(React.createElement(Chat, { portfolioSnapshot: snapshot, tickers: ['WATCHLIST_ONLY'] }));
    assert.equal(holdingsRead, true);
    assert.equal(canonical.holdings[0].portfolio_id, 'second');
  } finally {
    await server.close();
  }
});
