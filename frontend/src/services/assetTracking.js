export const assetCategories = [
  ['mutual_fund', 'Mutual funds', 'Units valued at a dated NAV. Use the AMFI scheme code for Indian funds.'],
  ['real_estate', 'Real estate', 'Homes, investment properties, and land.'],
  ['private_equity', 'Private equity', 'Private company investments and funds.'],
  ['cash', 'Cash', 'Savings, checking, and cash balances.'],
  ['other', 'Other assets', 'Vehicles, pensions, jewelry, art, and custom assets.'],
  ['liability', 'Liabilities', 'Outstanding loans and credit card balances.'],
];
export const isTrackedAsset = row => assetCategories.some(([type]) => type === row.asset_type);
export function assetValue(row) {
  const value = Number(row.manual_value), units = Number(row.quantity);
  if (row.manual_value == null || !Number.isFinite(value) || value < 0 || !Number.isFinite(units) || units <= 0) return null;
  return value * units * (row.asset_type === 'liability' ? -1 : 1);
}
export function trackingTotals(rows) {
  const totals = {};
  for (const row of rows) {
    const amount = assetValue(row);
    const previous = totals[row.currency];
    totals[row.currency] = amount == null || previous === null ? null : (previous || 0) + amount;
  }
  return totals;
}
