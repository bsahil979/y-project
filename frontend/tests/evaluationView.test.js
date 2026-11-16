import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createServer } from 'vite';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

const read = path => JSON.parse(fs.readFileSync(new URL(`../../analytics-engine/${path}`, import.meta.url), 'utf8'));
test('research renders actual holdout results, historical coverage and stale warning', async () => {
  const server = await createServer({ server: { middlewareMode: true, hmr: false }, appType: 'custom', logLevel: 'silent' });
  try {
    const { EvaluationContent } = await server.ssrLoadModule('/src/pages/EvaluationView.jsx');
    const study = read('research/personalized_phase8_2026-11-16/summary.json');
    const data = {
      regime: { manifest: read('research/regime_phase4_2026-11-15/manifest.json'), convergence: {converged:70,fits:70}, holdout_metrics:[], status:'ready', changed_sources:[] },
      personalized: {holdout: {...study, stale:true}, scope:study.scope, constraints:[], provenance_fields:[]},
      marketmind: {rows:42568,models:{},majority_baseline:{accuracy:.39,macro_f1:.18}},
      forecasting: {lstm:read('models/forecast_v2/MSFT/report.json'),timesfm:read('evaluations/timesfm_replay_2026-11-04.json')},
      integrity:{quarantined_rf_count:100}, sources:[]
    };
    const html = renderToStaticMarkup(React.createElement(EvaluationContent, {data}));
    assert.match(html, /unavailable_in_historical_replay/);
    assert.match(html, /Saved study is stale/);
    assert.match(html, /Conservative 20% caps force equal weight/);
    for (const row of study.metrics) {
      assert.ok(html.includes(row.strategy));
      assert.ok(html.includes(row.sharpe.toFixed(4)));
    }
    assert.doesNotMatch(html, /Not yet evaluated out of sample/);
  } finally { await server.close(); }
});
