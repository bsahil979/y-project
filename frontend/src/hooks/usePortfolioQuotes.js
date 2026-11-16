import { useEffect, useState } from 'react';
import { PortfolioService } from '../services/api';

const EMPTY_QUOTES = {};

export default function usePortfolioQuotes(holdings) {
  const symbols = [...new Set(holdings.map((h) => String(h.ticker || '').trim().toUpperCase()).filter(Boolean))].sort();
  const symbolsKey = JSON.stringify(symbols);
  const [revision, setRevision] = useState(0);
  const requestKey = `${symbolsKey}:${revision}`;
  const [snapshot, setSnapshot] = useState({ key: '', quotes: {}, error: '' });
  useEffect(() => {
    let active = true;
    const requestedSymbols = JSON.parse(symbolsKey);
    if (requestedSymbols.length) {
      PortfolioService.getQuotes(requestedSymbols)
        .then((result) => { if (active) setSnapshot({ key: requestKey, quotes: result.quotes || {}, error: '' }); })
        .catch(() => { if (active) setSnapshot({ key: requestKey, quotes: {}, error: 'Prices could not be loaded. Check the backend connection and retry.' }); });
    }
    return () => { active = false; };
  }, [symbolsKey, requestKey]);
  const current = snapshot.key === requestKey;
  return { quotes: current ? snapshot.quotes : EMPTY_QUOTES, error: current ? snapshot.error : '',
    loading: symbols.length > 0 && !current, revision,
    refresh: () => setRevision((value) => value + 1) };
}
