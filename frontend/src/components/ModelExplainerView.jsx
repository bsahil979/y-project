import React from 'react';
import { Link } from 'react-router-dom';

const facts = [
  {
    title: 'Price projection',
    body: 'The stock advisor requests a 30-session TimesFM estimate from recent price history. If that model is unavailable, the response identifies the fallback model. The chart names the model actually used.',
  },
  {
    title: 'Portfolio comparison',
    body: 'The proposed position is compared with your recorded holdings in the same currency, using aligned historical returns. The change in return, volatility, and Sharpe is an estimate based on that history.',
  },
  {
    title: 'Market state',
    body: 'A Hidden Markov Model groups historical market behavior into statistical states. A state label does not predict a stock’s next move.',
  },
];

export default function ModelExplainerView() {
  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-slate-200 bg-white p-7">
        <p className="text-xs font-bold uppercase tracking-widest text-indigo-700">Understanding your estimates</p>
        <h1 className="mt-2 text-3xl font-bold text-slate-950">How the stock advisor works</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">
          Model availability and predictive accuracy are different. A model can produce an estimate without having demonstrated that it beats a simple baseline on future data.
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        {facts.map((fact) => (
          <section key={fact.title} className="rounded-2xl border border-slate-200 bg-white p-6">
            <h2 className="font-semibold text-slate-950">{fact.title}</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">{fact.body}</p>
          </section>
        ))}
      </div>
      <div className="rounded-2xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-950">
        Forecast accuracy has not been established for the stocks shown in the advisor. Treat projections as scenarios, and check the model name and data availability shown with each result.
      </div>
      <Link to="/dashboard/forecast" className="inline-block rounded-xl bg-indigo-700 px-5 py-3 text-sm font-semibold text-[#ffffff]">Open stock advisor</Link>
    </div>
  );
}
