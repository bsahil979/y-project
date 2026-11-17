import React, {useEffect, useState} from 'react';
import {API_BASE_URL} from '../config/api';
import {profileForAnalysis} from '../services/investorProfile';
import {formatMoney} from '../services/portfolioValuation';
export default function FundAdvisor({snapshot}) {
  const funds = (snapshot.trackedAssets || []).filter(a => a.asset_type === 'mutual_fund');
  const request = JSON.stringify({holdings:funds.map(a=>({identifier:a.ticker.replace(/^MF:/,''),quantity:Number(a.quantity)})),...profileForAnalysis(snapshot,'INR')});
  const [state,setState] = useState({});
  const [refresh,setRefresh] = useState(0);
  useEffect(()=>{
    if (!funds.length || refresh === 0) return;
    const controller=new AbortController();
    setState({loading:true});
    fetch(API_BASE_URL+'/funds/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:request,signal:controller.signal})
      .then(async r=>{const data=await r.json();if(!r.ok) throw new Error(typeof data.detail === 'string'? data.detail:'Fund analysis request failed');return data;})
      .then(data=>setState({data})).catch(e=>{if(e.name!=='AbortError')setState({error:e.message});});
    return ()=>controller.abort();
  },[request,refresh]);
  if(!funds.length) return null;
  const data=state.data;
  const percent=n=>n==null?'Unavailable':(n*100).toFixed(2)+'%';
  return <section className="rounded-xl border p-6 space-y-4">
    <div className="flex justify-between gap-4"><h2 className="text-xl font-semibold">Mutual fund advisor</h2><button disabled={state.loading} className="text-blue-700" onClick={()=>setRefresh(x=>x+1)}>{refresh === 0 ? 'Analyze mutual funds' : 'Refresh analysis'}</button></div>
    {refresh === 0 && <p>Analyze using public AMFI and MFapi NAV data. Scheme codes are sent to MFapi; your quantities and account credentials stay on this server.</p>}
    {state.loading && <p>Resolving your schemes and loading historical NAVs...</p>}
    {state.error && <p role="alert">{state.error}</p>}
    {data?.status==='unavailable' && <div role="alert"><p>{data.message}</p>{data.issues.map((x,i)=><p key={i}>{x.identifier}: {x.reason}</p>)}</div>}
    {data?.status==='ok' && <>
      <p>{data.profile.risk_preference} profile · {data.profile.investment_horizon_years == null ? 'No goal horizon supplied' : data.profile.investment_horizon_years.toFixed(1)+'-year horizon'}</p>
      <p>NAV analysis period: {data.period.start} to {data.period.end} ({data.period.observations} common observations).</p>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">{[['Historical CAGR',percent(data.metrics.cagr)],['Annualized volatility',percent(data.metrics.annualized_volatility)],['Maximum drawdown',percent(data.metrics.max_drawdown)],['Historical Sharpe (0% risk-free)',data.metrics.sharpe_ratio?.toFixed(2) ?? 'Unavailable']].map(([label,value])=><div key={label} className="rounded-lg border p-4"><p>{label}</p><strong className="text-xl">{value}</strong></div>)}</div>
      <h3 className="font-semibold">What to review</h3><ul className="list-disc pl-5 space-y-3">{data.recommendations.map((r,i)=><li key={i}>{r.message}</li>)}</ul>
      <div className="overflow-auto"><table className="w-full text-left"><thead><tr>{['Fund / category','Weight','NAV value','Volatility','Drawdown'].map(h=><th className="p-2" key={h}>{h}</th>)}</tr></thead><tbody>{data.funds.map(f=><tr key={f.identifier} className="border-t"><td className="p-2">{f.name}<small className="block">{f.category}</small></td><td>{percent(f.weight)}</td><td>{formatMoney(f.value,'INR')}</td><td>{percent(f.annualized_volatility)}</td><td>{percent(f.max_drawdown)}</td></tr>)}</tbody></table></div>
      {data.correlations.map((p,i)=><p key={i}>{p.first} / {p.second}: historical return correlation {p.correlation.toFixed(2)}.</p>)}
      <details><summary>Data and methodology</summary><p>{data.methodology}</p><p>Scheme identity: AMFI. Historical NAV source: MFapi.in. Data is cached for up to one hour. CAGR requires at least one year of common history.</p><ul>{data.limitations.map(x=><li key={x}>{x}</li>)}</ul></details>
    </>}
  </section>;
}
