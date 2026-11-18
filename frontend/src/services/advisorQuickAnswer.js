import { formatMoney } from './portfolioValuation.js';
import { assetCategories, trackingTotals } from './assetTracking.js';

export function portfolioOverview(snapshot, currency) {
  if (!snapshot.valid) return 'Review the transaction errors in Manage holdings before analyzing this portfolio.';
  const group = snapshot.valuation.groups[currency];
  const assets = snapshot.trackedAssets.filter(row => row.currency === currency);
  if (!group && !assets.length) return 'There are no recorded assets in the selected currency.';
  const lines = [`**Your ${currency} portfolio overview**`];
  if (group) {
    lines.push(`Stocks: ${group.tickers.length}. Recorded cost: ${formatMoney(group.cost, currency)}.`);
    if (group.complete) {
      lines.push(`Market value: ${formatMoney(group.market, currency)}. Unrealized gain/loss since purchase: ${formatMoney(group.pnl, currency)}.`);
      const largest = group.tickers.map((ticker, i) => [ticker, group.weights[i]]).sort((a,b) => b[1] - a[1])[0];
      if (Number.isFinite(largest?.[1])) lines.push(`Largest stock position: ${largest[0]} at ${(100 * largest[1]).toFixed(1)}% of stock value.`);
      const dates = group.positions.map(p => p.quote?.last_daily_session).filter(Boolean).sort();
      if (dates.length) lines.push(`Available quote session dates: ${dates[0]}${dates.at(-1) !== dates[0] ? ' to ' + dates.at(-1) : ''}.`);
    } else {
      lines.push(`Stock market value and weights are unavailable. Missing valid prices for ${[...new Set(group.missing.map(p => p.ticker))].join(', ')}.`);
    }
  }
  for (const [type, label] of assetCategories) {
    const rows = assets.filter(row => row.asset_type === type);
    if (rows.length) lines.push(`${label} (recorded value): ${formatMoney(trackingTotals(rows)[currency], currency)}.`);
  }
  return lines.join('\n\n');
}

export function quickPortfolioIntent(query) {
  if (/\b(?:forecast|sentiment|news|finbert|marketmind|predict|future)\b|black[\s-]+litterman/i.test(query)) return null;
  if (/\b(?:suggested|recommended|personalized|target)\s+(?:allocation|weights?)\b|\b(?:biggest|largest)\s+weight\s+change\b/i.test(query)) return 'allocation';
  if (/^\s*(?:what(?:'s| is| are)|show|explain|which)\b.*\b(?:risks?\s+matter|portfolio risk|sharpe ratio|max(?:imum)? drawdown|annualized volatility)\b/i.test(query)) return 'risk';
  if (/^(?:(?:please|can you|could you|give me|show me|provide|give|show)\s+)*(?:(?:an? |the )?(?:analysis|overview|summary|review|breakdown) (?:of |for )?(?:my |the )?portfolio|(?:analy[sz]e|review|summari[sz]e) (?:my |the )?portfolio|(?:my |the )?portfolio (?:overview|analysis|summary))(?: (?:for )?today| right now)?[.!?]*$/i.test(query.trim())) return 'overview';
  return null;
}

export function quickPortfolioAnswer(intent, analysis) {
  if (intent === 'allocation') {
    const allocation = analysis.personalized_allocation;
    if (!allocation?.success) {
      return allocation?.reason || 'The analytics engine did not find a feasible allocation for this portfolio.';
    }
    const rows = analysis.tickers.map((ticker, index) => ({
      ticker, current: analysis.weights[index], target: allocation.weights[ticker],
    }));
    if (!rows.length || rows.some(row => !Number.isFinite(row.current) || !Number.isFinite(row.target))) {
      return 'The analytics engine did not return a complete allocation.';
    }
    const change = ({ current, target }) => 100 * (target - current);
    const signed = value => `${value > 0 ? '+' : ''}${value.toFixed(1)}`;
    rows.sort((a, b) => Math.abs(change(b)) - Math.abs(change(a)));
    const first = rows[0];
    const summary = Math.abs(change(first)) < 0.05
      ? 'Current and suggested weights match at the precision shown.'
      : `**Largest change: ${first.ticker}, ${signed(change(first))} percentage points.**`;
    const details = [
      allocation.applied_profile && `Profile: ${allocation.applied_profile}.`,
      Number.isFinite(allocation.investment_horizon_years) && `Horizon: ${allocation.investment_horizon_years} years.`,
      allocation.objective_used && `Objective: ${allocation.objective_used.replaceAll('_', ' ')}.`,
      Number.isFinite(allocation.max_weight_cap) && `Maximum position: ${(allocation.max_weight_cap * 100).toFixed(1)}%.`,
    ].filter(Boolean).join(' ');
    return [
      summary,
      ['| Holding | Current | Suggested | Change (pp) |', '| --- | ---: | ---: | ---: |',
        ...rows.map(row => `| ${row.ticker} | ${(row.current * 100).toFixed(1)}% | ${(row.target * 100).toFixed(1)}% | ${signed(change(row))} |`)].join('\n'),
      details,
      allocation.signal_status === 'prior_only' ? 'This allocation uses equilibrium returns because no AI views were included.' : '',
    ].filter(Boolean).join('\n\n');
  }

  const risk = analysis.portfolio_risk || {};
  const percent = value => Number.isFinite(value) ? `${(value * 100).toFixed(2)}%` : 'Unavailable';
  const risks = [...(analysis.risk_budget?.risk_contributions || [])]
    .filter(row => Number.isFinite(row.percentage_contribution_to_risk))
    .sort((a, b) => b.percentage_contribution_to_risk - a.percentage_contribution_to_risk);
  return [
    '**Historical portfolio risk**',
    `- Annualized volatility: ${percent(risk.portfolio_volatility)}\n- Maximum drawdown: ${percent(risk.portfolio_max_drawdown)}\n- Sharpe ratio: ${Number.isFinite(risk.portfolio_sharpe) ? risk.portfolio_sharpe.toFixed(2) : 'Unavailable'}`,
    risks[0]?.ticker ? `${risks[0].ticker} contributed the most to estimated portfolio risk.` : '',
  ].filter(Boolean).join('\n\n');
}
