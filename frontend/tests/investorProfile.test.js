import assert from 'node:assert/strict';
import { test } from 'node:test';
import { normalizeInvestorProfile, profileForAnalysis } from '../src/services/investorProfile.js';
import { analysisRequest } from '../src/services/portfolioValuation.js';

test('legacy profiles migrate and blank horizons stay optional', () => {
  assert.equal(normalizeInvestorProfile({ risk: 'mod_conservative' }).risk_preference, 'conservative');
  assert.equal(normalizeInvestorProfile({ risk: 'mod_aggressive' }).risk_preference, 'moderate');
  assert.equal(normalizeInvestorProfile({ risk: 'very_aggressive' }).risk_preference, 'aggressive');
  assert.equal(normalizeInvestorProfile({ investment_horizon_years: '' }).investment_horizon_years, null);
});

test('goals supply nearest unfinished same currency horizon unless explicitly set', () => {
  const snapshot = { asOf: '2026-01-01', goals: [
    { currency: 'INR', target_amount: 100, current_amount: 0, target_date: '2027-01-01' },
    { currency: 'USD', target_amount: 100, current_amount: 100, target_date: '2027-01-01' },
    { currency: 'USD', target_amount: 100, current_amount: 0, target_date: '2028-01-01' },
  ] };
  assert.ok(Math.abs(profileForAnalysis(snapshot, 'USD').investment_horizon_years - 2) < .01);
  assert.equal(profileForAnalysis(snapshot, 'USD').horizon_source, 'nearest_goal');
  assert.equal(normalizeInvestorProfile(profileForAnalysis(snapshot, 'USD')).horizon_source, 'nearest_goal');
  snapshot.investorProfile = { risk_preference: 'aggressive', investment_horizon_years: 7 };
  assert.equal(profileForAnalysis(snapshot, 'USD').investment_horizon_years, 7);
  assert.equal(profileForAnalysis(snapshot, 'USD').horizon_source, 'explicit');
  assert.equal(profileForAnalysis({}, 'USD').horizon_source, 'default');
});

test('canonical payload changes when profile changes even with identical holdings', () => {
  const group = { complete: true, weights: [.5, .5], tickers: ['A','B'], currency: 'USD', market: 100 };
  const snapshot = { portfolioId: 'p', portfolioRevision: 'r', asOf: '2026-01-01' };
  const c = analysisRequest(group, { ...snapshot, investorProfile: { risk_preference: 'conservative', investment_horizon_years: 3 } });
  const a = analysisRequest(group, { ...snapshot, investorProfile: { risk_preference: 'aggressive', investment_horizon_years: 9 } });
  assert.equal(c.risk_preference, 'conservative');
  assert.equal(a.investment_horizon_years, 9);
  assert.notEqual(JSON.stringify(c), JSON.stringify(a));
});

test('profile persistence is user scoped and both API clients forward it', async () => {
  const { createServer } = await import('vite');
  const server = await createServer({ configFile: false, server: { middlewareMode: true, watch: null },
    optimizeDeps: { noDiscovery: true, include: [] } });
  const oldStorage = globalThis.localStorage;
  const oldWindow = globalThis.window;
  const oldEvent = globalThis.CustomEvent;
  const saved = new Map();
  const events = [];
  globalThis.localStorage = { getItem: key => saved.get(key) ?? null, setItem: (key, value) => saved.set(key, value) };
  globalThis.window = { dispatchEvent: event => events.push(event) };
  globalThis.CustomEvent = class { constructor(type, options) { this.type = type; this.detail = options.detail; } };
  try {
    const { PortfolioDataService } = await server.ssrLoadModule('/src/services/portfolioData.js');
    const profile = { risk_preference: 'conservative', investment_horizon_years: 4, horizon_source: 'explicit' };
    PortfolioDataService.saveInvestorProfile('demo-user', profile);
    assert.deepEqual(PortfolioDataService.getInvestorProfile('demo-user'), profile);
    assert.equal(PortfolioDataService.getInvestorProfile('another-user').risk_preference, 'moderate');
    assert.deepEqual((await PortfolioDataService.getWorkspaceResult('demo-user')).workspace.investorProfile, profile);
    assert.deepEqual(events[0].detail, { userId: 'demo-user', profile });
    const { default: api, PortfolioService } = await server.ssrLoadModule('/src/services/api.js');
    const calls = [];
    api.defaults.adapter = async config => {
      calls.push({ url: config.url, payload: JSON.parse(config.data) });
      return { data: {}, status: 200, statusText: 'OK', headers: {}, config };
    };
    const payload = { tickers: ['A'], weights: [1], ...profile };
    await PortfolioService.getPortfolioAnalysis(payload, true);
    await PortfolioService.optimizePortfolio(payload);
    assert.deepEqual(calls.map(c => c.url), ['/portfolio/analyze', '/portfolio/optimize']);
    for (const { payload: sent } of calls) {
      assert.equal(sent.risk_preference, 'conservative');
      assert.equal(sent.investment_horizon_years, 4);
      assert.equal(sent.horizon_source, 'explicit');
    }
  } finally {
    globalThis.localStorage = oldStorage; globalThis.window = oldWindow; globalThis.CustomEvent = oldEvent;
    await server.close();
  }
});
