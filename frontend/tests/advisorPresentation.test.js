import test from 'node:test';
import assert from 'node:assert/strict';
import {benchmarkGrowth,metricText} from '../src/services/advisorPresentation.js';
test('advisor compounds aligned engine returns instead of inventing growth',()=>{
 const data={return_series:{portfolio_daily:[{date:'2025-01-02',return:.1},{date:'2025-01-03',return:-.1}],benchmark_daily:[{date:'2025-01-02',return:.02},{date:'2025-01-03',return:0}]}};
 const rows=benchmarkGrowth(data);
 assert.ok(Math.abs(rows[1].portfolio-99)<1e-9);
 assert.equal(rows[1].benchmark,102);
 assert.deepEqual(benchmarkGrowth({}),[]);
 data.return_series.benchmark_daily.pop();
 assert.deepEqual(benchmarkGrowth(data),[]);
});
test('advisor missing metrics are unavailable, never zero',()=>{
 assert.equal(metricText(null,true),'Unavailable');
 assert.equal(metricText(undefined),'Unavailable');
 assert.equal(metricText(NaN),'Unavailable');
 assert.equal(metricText(0,true),'0.0%');
 assert.equal(metricText(-.125,true),'-12.5%');
});
