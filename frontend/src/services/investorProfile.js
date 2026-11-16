// Legacy five-option questionnaires map deterministically to the API's three profiles.
export function normalizeInvestorProfile(value = {}) {
  const aliases = { conservative: 'conservative', mod_conservative: 'conservative',
    moderate: 'moderate', mod_aggressive: 'moderate', aggressive: 'aggressive', very_aggressive: 'aggressive' };
  const rawHorizon = value.investment_horizon_years;
  const horizon = rawHorizon === '' || rawHorizon == null ? null : Number(rawHorizon);
  const validHorizon = Number.isFinite(horizon) && horizon > 0;
  return {
    risk_preference: aliases[value.risk_preference ?? value.risk] || 'moderate',
    investment_horizon_years: validHorizon ? horizon : null,
    horizon_source: validHorizon ? (value.horizon_source === 'nearest_goal' ? 'nearest_goal' : 'explicit') : 'default',
  };
}

export function profileForAnalysis(snapshot, currency) {
  const profile = normalizeInvestorProfile(snapshot?.investorProfile);
  if (profile.investment_horizon_years !== null) return profile;
  const now = Date.parse(snapshot?.asOf || new Date().toISOString());
  const horizons = (snapshot?.goals || [])
    .filter(goal => goal.currency === currency && Number(goal.current_amount || 0) < Number(goal.target_amount))
    .map(goal => (Date.parse(goal.target_date) - now) / (365.25 * 86400000))
    .filter(years => Number.isFinite(years) && years > 0);
  // With no explicit horizon, use the nearest unfinished goal in this currency.
  return { ...profile, investment_horizon_years: horizons.length ? Math.min(...horizons) : null,
    horizon_source: horizons.length ? 'nearest_goal' : 'default' };
}
