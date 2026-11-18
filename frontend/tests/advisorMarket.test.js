import test from 'node:test';
import assert from 'node:assert/strict';
import { formatNewsSentiment, resolveChatSymbol } from '../src/services/advisorMarket.js';

test('news questions resolve only their explicit ticker', () => {
  const owned = ['RELIANCE.NS', 'TCS.NS'];
  assert.equal(resolveChatSymbol('What is the news sentiment for RELIANCE.NS?', owned), 'RELIANCE.NS');
  assert.equal(resolveChatSymbol('news for reliance?', owned), 'RELIANCE.NS');
  assert.equal(resolveChatSymbol('forecast for bhartiartl.ns?', owned), 'BHARTIARTL.NS');
  assert.equal(resolveChatSymbol('news for my stock?', owned), null);
  assert.equal(resolveChatSymbol('compare RELIANCE and TCS', owned), null);
});

test('reports actual news coverage and model', () => {
  assert.match(formatNewsSentiment({articles_analyzed: 2, overall_score: 0.2, overall_sentiment: 'Positive', models_used: ['VADER']}, 'MSFT'), /2 headlines, scored by VADER/);
  assert.match(formatNewsSentiment({articles_analyzed: 0}, 'MSFT'), /No scored news/);
});
import { createServer } from 'vite';

test('Reliance news bypasses unavailable portfolio prices and reports a failed fetch', async () => {
  const server = await createServer({server: {middlewareMode:true}, appType:'custom', logLevel:'silent'});
  try {
    const {buildAdvisorReply} = await server.ssrLoadModule('/src/components/ChatAdvisor.jsx');
    const {PortfolioService} = await server.ssrLoadModule('/src/services/api.js');
    const calls = [];
    PortfolioService.getSentiment = async symbol => {
      calls.push(symbol);
      throw new Error('provider offline');
    };
    PortfolioService.getPortfolioAnalysis = () => { throw new Error('Unexpected portfolio analysis'); };
    const answer = await buildAdvisorReply('What is the news sentiment for RELIANCE.NS?', ['RELIANCE.NS'], {error:'Missing prices'});
    assert.deepEqual(calls, ['RELIANCE.NS']);
    assert.match(answer, /could not retrieve sentiment for RELIANCE.NS/);
  } finally { await server.close(); }
});
