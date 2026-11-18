export function buildAllocationDraft(group, allocation, accounts = []) {
  if (!group?.complete || !(group.market > 0) || !allocation?.success) return null;
  const targets = group.tickers.map(ticker => allocation.weights?.[ticker]);
  if (targets.some(w => !Number.isFinite(w) || w < 0) ||
      Math.abs(targets.reduce((sum,w)=>sum+w,0)-1)>0.0001) return null;
  const rows = group.positions.map(position => {
    const {ticker,market,quantity,account_id} = position;
    const current = market/group.market;
    const target = allocation.weights[ticker]*market/group.marketByTicker[ticker];
    const amount = group.market*target-market;
    return {ticker,account:accounts.find(a=>a.id===account_id)?.name || 'Unassigned',
      current,target,amount,units:amount/(market/quantity)};
  });
  return {rows,objective:allocation.objective_used};
}
