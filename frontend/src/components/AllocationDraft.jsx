import React, {useState} from 'react';
import {useAuth} from '../contexts/AuthContext';
import {buildAllocationDraft} from '../services/allocationDraft';
import {formatMoney} from '../services/portfolioValuation';

export default function AllocationDraft(props) {
  const {user} = useAuth();
  if (!user?.id || !props.snapshot.portfolioId) return null;
  const storageKey = JSON.stringify(['allocation-draft', user.id, props.snapshot.portfolioId, props.group.currency]);
  return <DraftReview key={storageKey} {...props} storageKey={storageKey}/>;
}

function DraftReview({data, snapshot, group, storageKey}) {
  const [saved,setSaved] = useState(() => {
    try {
      const draft = JSON.parse(localStorage.getItem(storageKey));
      return Array.isArray(draft?.rows) ? draft : null;
    } catch { return null; }
  });
  const [error,setError] = useState('');
  const [strategy,setStrategy] = useState('personalized_allocation');
  const proposal = buildAllocationDraft(group, data[strategy], snapshot.accounts);
  function save() {
    const draft = {...proposal, date:new Date().toISOString(), strategy, revision:snapshot.portfolioRevision,
      currentRisk:data.allocation?.current_performance?.volatility, targetRisk:data[strategy]?.performance?.volatility};
    try {
      localStorage.setItem(storageKey,JSON.stringify(draft));
      setSaved(draft);
      setError('');
    } catch { setError('Unable to save this draft on this device.'); }
  }
  const pct = n => Number.isFinite(n) ? (100*n).toFixed(2)+'%' : 'Unavailable';
  return <section className="space-y-3 border-t pt-4">
    <h4 className="font-semibold">Rebalance draft</h4>
    <label>Model <select value={strategy} onChange={e=>setStrategy(e.target.value)}>
      <option value="personalized_allocation">Personalized allocation</option>
      {data.ai_black_litterman_allocation?.success && <option value="ai_black_litterman_allocation">AI Black–Litterman</option>}
    </select></label>
    <button className="ml-3 text-blue-700" disabled={!proposal} onClick={save}>{saved?'Replace saved draft':'Save draft on this device'}</button>
    {error && <p role="alert">{error}</p>}
    {saved && <><p>Saved {new Date(saved.date).toLocaleString()} · {saved.objective?.replaceAll('_',' ')} · {group.currency}</p>
    {saved.revision !== snapshot.portfolioRevision && <p>Holdings or account details have changed since this draft was saved.</p>}
    <p>Estimated annual volatility {pct(saved.currentRisk)} → {pct(saved.targetRisk)}. Quantities use saved prices and split each adjustment across accounts in proportion to their holdings. Fractional estimates exclude fees and taxes. Check available cash in each account before using the draft.</p>
    <div className="overflow-auto"><table className="w-full text-left text-sm"><thead><tr>{['Account','Stock','Current → target weight¹','Estimated action','Value'].map(x=><th key={x}>{x}</th>)}</tr></thead>
    <tbody>{saved.rows.map((r,i)=><tr key={i}><td>{r.account}</td><td>{r.ticker}</td><td>{pct(r.current)} → {pct(r.target)}</td><td>{Math.abs(r.units)<0.00005?'Hold':(r.units>0?'Buy ':'Sell ')+Math.abs(r.units).toFixed(4)}</td><td>{formatMoney(Math.abs(r.amount),group.currency)}</td></tr>)}</tbody></table></div>
    <small>¹ Share of the selected stock portfolio held in this account.</small></>}
  </section>;
}
