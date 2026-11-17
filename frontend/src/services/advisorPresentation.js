export const metricText = (value, percent = false) => Number.isFinite(value) ? (value * (percent ? 100 : 1)).toFixed(percent ? 1 : 2) + (percent ? '%' : '') : 'Unavailable';
export function benchmarkGrowth(benchmark) {
  const left = benchmark?.return_series?.portfolio_daily || [];
  const right = new Map((benchmark?.return_series?.benchmark_daily || []).map(row => [row.date, row.return]));
  let portfolio = 100, index = 100;
  const rows = [];
  for (const row of left) {
    const other = right.get(row.date);
    // Do not bridge gaps or silently compound a partial series.
    if (!Number.isFinite(row.return) || !Number.isFinite(other)) return [];
    portfolio *= 1 + row.return; index *= 1 + other;
    rows.push({date:row.date, portfolio, benchmark:index});
  }
  return rows;
}
