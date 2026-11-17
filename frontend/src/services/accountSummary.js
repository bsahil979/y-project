export function securitiesAccountGroups(snapshot) {
  const groups = new Map();
  for (const position of snapshot.valuation.positions) {
    const key = JSON.stringify([position.account_id || null, position.currency]);
    if (!groups.has(key)) groups.set(key, {
      key, accountId:position.account_id || null, currency:position.currency,
      name:position.account_id ? snapshot.accounts.find(a => a.id === position.account_id)?.name || 'Unknown account' : 'Unassigned holdings',
      market:0,
    });
    const group=groups.get(key);
    group.market = group.market === null || !Number.isFinite(position.market) ? null : group.market + position.market;
  }
  return [...groups.values()];
}
